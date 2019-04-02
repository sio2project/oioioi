import os
import re
import sys
from pprint import pprint

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from oioioi.confirmations.utils import (ProofCorrupted,
                                        verify_submission_receipt_proof)


class Command(BaseCommand):
    help = _("Verifies the cryptographic confirmation of submission receipt "
             "given to the users. Pass the source file as the first argument "
             "and paste the email with the '--- BEGIN PROOF DATA ---' "
             "to the standard input.")

    def add_arguments(self, parser):
        parser.add_argument('source_file',
                            type=str,
                            help='Source file')

    def handle(self, *args, **options):
        filename = options['source_file']
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
