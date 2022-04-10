import hashlib
import itertools
import logging
import sys

import dateutil.parser
from django.conf import settings
from django.core import signing
from django.template.loader import render_to_string
from itertools import zip_longest

from oioioi.programs.models import ProgramSubmission

SUBMISSION_RECEIVED_SALT = 'submission_reveived'
logger = logging.getLogger(__name__)


class ProofCorrupted(ValueError):
    pass


def sign_submission_metadata(data):
    return signing.dumps(data, salt=SUBMISSION_RECEIVED_SALT, compress=True)


def unsign_submission_metadata(data):
    return signing.loads(data, salt=SUBMISSION_RECEIVED_SALT)


def submission_receipt_proof(submission):
    """Returns pair of data and its signed version which may be used by
    the user to prove that we received his submission someday.

    The returned data are not encrypted, just signed.
    """
    submission_no = (
        ProgramSubmission.objects.filter(
            user=submission.user,
            kind=submission.kind,
            problem_instance=submission.problem_instance,
            date__lt=submission.date,
        ).count()
        + 1
    )
    source_hash = hashlib.sha256()
    for chunk in submission.source_file.chunks():
        source_hash.update(chunk)
    submission.source_file.seek(0)

    proof_data = {
        'id': submission.id,
        'size': submission.source_file.size,
        'source_hash': source_hash.hexdigest(),
        'date': submission.date.isoformat(),
        'contest': submission.problem_instance.contest.id,
        'problem_instance_id': submission.problem_instance_id,
        'problem_name': submission.problem_instance.short_name,
        'user_id': submission.user_id,
        'username': submission.user.username,
        'submission_no': submission_no,
    }
    proof = sign_submission_metadata(proof_data)
    return proof_data, proof


# http://stackoverflow.com/questions/1624883/alternative-way-to-split-a-list-into-groups-of-n
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return list(zip_longest(*args, fillvalue=fillvalue))


def format_proof(proof):
    lines = ['--- BEGIN PROOF DATA ---']
    lines.extend(''.join(line) for line in grouper(70, proof, ' '))
    lines.append('--- END PROOF DATA ---')
    return '\n'.join(lines)


def verify_submission_receipt_proof(proof, source):
    """Verifies a signed proof of user's submission and returns proven
    metadata.

    :raises :class:`ProofCorrupted` upon failure of any reason.
    """
    proof = ''.join(proof.split())
    try:
        proof_data = unsign_submission_metadata(proof)
    except signing.BadSignature as e:
        raise ProofCorrupted(str(e), sys.exc_info()[2])

    proof_data['date'] = dateutil.parser.parse(proof_data['date'])
    source_hash = hashlib.sha256(source).hexdigest()
    if source_hash != proof_data['source_hash']:
        raise ProofCorrupted('Source file does not match the original one.')

    return proof_data


def send_submission_receipt_confirmation(request, submission):
    proof_data, proof = submission_receipt_proof(submission)
    context = {
        'proof_data': proof_data,
        'proof': format_proof(proof),
        'contest': request.contest,
        'contest_id': request.contest.id,
        'submission_id': submission.id,
        'submission_no': proof_data['submission_no'],
        'submission_date': submission.date,
        'problem_shortname': proof_data['problem_name'],
        'size': proof_data['size'],
        'full_name': submission.user.get_full_name(),
    }

    subject = render_to_string('confirmations/email_subject.txt', context)
    subject = settings.EMAIL_SUBJECT_PREFIX + ' '.join(subject.strip().splitlines())
    body = render_to_string('confirmations/email_body.txt', context)

    request.contest.controller.send_email(subject, body, [submission.user.email])

    logger.info(
        "Proof of receiving sub. #%d@%s@%s (%s) sent to %s",
        submission.id,
        context['problem_shortname'],
        context['contest_id'],
        proof_data['source_hash'],
        submission.user,
    )
