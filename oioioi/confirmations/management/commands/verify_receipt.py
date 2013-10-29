import re
import sys
import os
from pprint import pprint

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from oioioi.confirmations.utils import verify_submission_receipt_proof, \
        ProofCorrupted


class Command(BaseCommand):
    args = _("source_file")
    help = _("Verifies the cryptographic confirmation of submission receipt "
             "given to the users. Pass the source file as the first argument "
             "and paste the email with the '--- BEGIN PROOF DATA ---' "
             "to the standard input.")

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(_("Expected exactly one argument"))

        filename = args[0]
        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)
        source = open(filename, 'r').read()

        match = re.search(
                r'--- BEGIN PROOF DATA ---(.*)--- END PROOF DATA ---',
                sys.stdin.read(), re.DOTALL)
        if not match:
            raise CommandError(_("Proof not found in the pasted text."))
        proof = match.group(1)

        try:
            proof_data = verify_submission_receipt_proof(proof, source)
        except ProofCorrupted as e:
            raise CommandError(str(e))

        sys.stdout.write(_("Confirmation is valid\n"))
        pprint(proof_data, sys.stdout)
