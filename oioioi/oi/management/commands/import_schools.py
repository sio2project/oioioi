# ~*~ coding: utf-8 ~*~
import os
import csv
import datetime
from typing import Type, Optional, Union

from django.core.management.base import BaseCommand, CommandError
from django.db import utils, transaction
from django.utils.translation import gettext as _

from oioioi.oi.models import School, SchoolType


"""
This script is used to import schools from the RSPO database,
which is provided by the Ministry of Education and contains all
educational institutions in Poland. Due to the poor quality of this data,
it is likely that SIO administrators will modify school data.
The task of this script is to detect which corrections from newer
and more recent versions of the RSPO database should be accepted and applied,
and which should not.

There are three main data types in this script called:
* db_school: school as an object,
* dict_school: a dictionary in which the keys are the attribute names of the School class,
* rspo_school: a dictionary in which the keys are the column headers from the RSPO database.
"""


CURRENT_TIME = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
DRY_RUN = False
VERBOSITY = 1

BASE_DIR = fr'{os.getcwd()}/schools'
LOG_FILENAME = fr'{BASE_DIR}/school_import_log_{CURRENT_TIME}.log'
LATEST_LOG_FILENAME = fr'{BASE_DIR}/latest.log'
BACKUP_FILENAME = fr'{BASE_DIR}/rspo_{CURRENT_TIME}.back'

CHILDREN_OR_YOUTH = 'Dzieci lub młodzież'
RSPO_CSV_COLUMNS = [
    'Numer RSPO',
    'REGON',
    'NIP',
    'Typ',
    'Nazwa',
    'Kod terytorialny województwo',
    'Kod terytorialny powiat',
    'Kod terytorialny gmina',
    'Kod terytorialny miejscowość',
    'Kod terytorialny ulica',
    'Województwo',
    'Powiat',
    'Gmina',
    'Miejscowość',
    'Rodzaj miejscowości',
    'Ulica',
    'Numer budynku',
    'Numer lokalu',
    'Kod pocztowy',
    'Poczta',
    'Telefon',
    'Faks',
    'E-mail',
    'Strona www',
    'Publiczność status',
    'Kategoria uczniów',
    'Specyfika placówki',
    'Imię i nazwisko dyrektora',
    'Data założenia',
    'Data rozpoczęcia działalności',
    'Data likwidacji',
    'Typ organu prowadzącego',
    'Nazwa organu prowadzącego',
    'REGON organu prowadzącego',
    'NIP organu prowadzącego',
    'Województwo organu prowadzącego',
    'Powiat organu prowadzącego',
    'Gmina organu prowadzącego',
    'Miejsce w strukturze',
    'RSPO podmiotu nadrzędnego',
    'Typ podmiotu nadrzędnego',
    'Nazwa podmiotu nadrzędnego',
    'Liczba uczniów',
    'Tereny sportowe',
    'Języki nauczane',
    'Czy zatrudnia logopedę',
    'Czy zatrudnia psychologa',
    'Czy zatrudnia pedagoga',
    'Oddziały podstawowe wg specyfiki',
    'Oddziały dodatkowe',
]
SCHOOL_FIELDS = [
    field.column for field in School._meta.fields if 'id' not in str(field)
]
SCHOOL_FIELDS_TO_ITERATE = SCHOOL_FIELDS
SCHOOL_FIELDS_TO_ITERATE.remove('rspo')
SCHOOL_FIELDS_TO_ITERATE.remove('is_active')
SCHOOL_FIELDS_TO_ITERATE.remove('is_approved')


# region utils

def prepare_dir(directory):
    """Creates dir if not exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_object_or_none(klass, *args, **kwargs):
    """Uses get() to return an object, or returns None if the object does not exist.
    Argument klass must has get() attr."""
    try:
        return klass.objects.get(*args, **kwargs)
    except klass.DoesNotExist:
        return None


def prepare_address(school: 'dict[str, str]') -> str:
    """Preprocesses an address of a given school in RSPO format."""
    address = school['Ulica']
    if school['Numer budynku'] != '':
        address += f" {school['Numer budynku']}"
    if school['Numer lokalu'] != '':
        address += f" lokal {school['Numer lokalu']}"
    address += f"{', ' if address != '' else ''}{school['Miejscowość']}"
    return address


def translate_rspo_school(school: 'dict[str, str]') -> School:
    """Translates school (rspo_school) to a School object (without id)."""
    def parse_field(field):
        if len(field) > 0 and field[0] == '=':
            field = field[1:]
        field = field.strip('"')
        return field
    parsed_school = {}
    for field in school:
        parsed_school[field] = parse_field(school[field])

    return School(
        rspo=parsed_school['Numer RSPO'],
        type=SchoolType.objects.get(name=parsed_school['Typ']),
        name=parsed_school['Nazwa'],
        address=prepare_address(parsed_school),
        postal_code=parsed_school['Kod pocztowy'],
        city=parsed_school['Miejscowość'],
        province=parsed_school['Województwo'].lower(),
        phone=(parsed_school['Telefon'][-9:] if parsed_school['Telefon'] != '' else '000000000'),
        email=parsed_school['E-mail'],
    )


def translate_dict_school(school: 'dict[str, str]') -> School:
    """Translates school (dict_school) to a School object (without id)."""
    def parse_field(field):
        if len(field) > 0 and field[0] == '=':
            field = field[1:]
        field = field.strip('"')
        return field
    parsed_school = {}
    for field in school:
        if isinstance(school[field], str):
            parsed_school[field] = parse_field(school[field])
        else:
            parsed_school[field] = school[field]
    return School(
        rspo=parsed_school['rspo'],
        type=SchoolType.objects.get(pk=parsed_school['type_id']),
        name=parsed_school['name'],
        address=parsed_school['address'],
        postal_code=parsed_school['postal_code'],
        city=parsed_school['city'],
        province=parsed_school['province'],
        phone=parsed_school['phone'],
        email=parsed_school['email'],
    )


def find_school(school: 'Union[dict[str, str], School]', schools: 'list[dict[str, str]]'):
    """Searches for a particular school in the dictionary list.
    Arguments:
    - school: db_school or dict_school
    - schools: list of dict_schools"""
    if isinstance(school, School):
        school = school.__dict__
    for s in schools:
        if str(s['rspo']) == str(school['rspo']):
            return s
    return None


def are_the_same(school1: Union[dict, School], school2: Union[dict, School]) -> bool:
    """Checks if two schools are the same. Two schools must be in the same format."""
    if isinstance(school1, School):
        school1 = school1.__dict__
    if isinstance(school2, School):
        school2 = school2.__dict__
    fields = SCHOOL_FIELDS.copy()
    fields.remove("name")
    for field in fields:
        if str(school1[field]).lower() != str(school2[field]).lower():
            return False
    return True


def update_school(school_dict: 'dict[str, str]', school_obj: School):
    """Updates the school object with data from the school dictionary (dict_school)."""
    for field in SCHOOL_FIELDS_TO_ITERATE:
        setattr(school_obj, field, school_dict[field])
    school_obj.save()


def generate_school_diff_message(s_before: School, s_after: School) -> str:
    """Generates a message, about what is different between the two given schools. Both schools are objects."""
    message = f'Changes between schools [id: {s_before.pk}, rspo: {s_before.rspo}] and [id: {s_after.pk}, rspo: {s_after.rspo}]:'
    for field in SCHOOL_FIELDS_TO_ITERATE:
        if getattr(s_before, field) != getattr(s_after, field):
            message += f'\n{field}: was {getattr(s_before, field)}, is {getattr(s_after, field)}'
    return message


def copy_log_file():
    """Copies the log file and calls it 'latest'."""
    with open(LOG_FILENAME, 'r', encoding='utf-8-sig') as log_file:
        content = log_file.read()
    with open(LATEST_LOG_FILENAME, 'w', encoding='utf-8-sig') as latest_log_file:
        latest_log_file.write(content)


def set_all_schools_inactive():
    """Sets all schools as inactive."""
    for school in School.objects.all():
        school.is_active = False
        school.save()


# endregion


class Command(BaseCommand):
    help = (
        "Imports from the RSPO database (www.rspo.gov.pl) and "
        "identifies changes intelligently. Please read the output and logs carefully. "
        "This script is used to import schools from the RSPO database, "
        "which is provided by the Ministry of Education and contains all "
        "educational institutions in Poland. Due to the poor quality of this data, "
        "it is likely that SIO administrators will modify school data. "
        "The task of this script is to detect which corrections from newer "
        "and more recent versions of the RSPO database should be accepted and applied, "
        "and which should not."
    )

    def log(
        self,
        message: str,
        additional_info: Optional[str] = None,
        exception: Optional[Type[BaseException]] = None,
        school_before: Optional[School] = None,
        school_after: Optional[School] = None,
    ):
        """logs the information to a file and displays it on the screen.
        You can add additional message (additional_info), which will appear only in the log file,
        and an exception (exception), which will be thrown when the information is displayed on the screen.
        In addition, you can specify two schools (school_before, school_after) whose diff will be in the logs.
        """
        message_to_log = (f'{exception.__name__}: {message}' if exception is not None else message)
        message_to_log = (
            f'{message_to_log} {additional_info}'
            if additional_info is not None
            else message_to_log
        )
        stdout_message = (f'{message} More info in logs!' if additional_info is not None else message)
        if school_before is not None and school_after is not None:
            diff = generate_school_diff_message(school_before, school_after)
            message_to_log += f'\n{diff}'
        if VERBOSITY == 0:
            message_to_log = message
            stdout_message = ''
        with open(LOG_FILENAME, 'a', encoding='utf-8-sig') as file:
            file.write(f'{message_to_log}\n')
        if exception is not None:
            raise exception(stdout_message)
        else:
            self.stdout.write(stdout_message)

    def read_rspo_csv_file(self, filename):
        """Loads schools from CSV file in RSPO format and filters them to match SIO system needs."""
        with open(filename, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')
            if reader.fieldnames is not None and not all(
                item in reader.fieldnames for item in RSPO_CSV_COLUMNS
            ):
                self.log(
                    'Missing header or invalid columns.',
                    f"Excepted a csv file from the www.rspo.gov.pl website with headers: {', '.join(RSPO_CSV_COLUMNS)}.",
                    exception=CommandError,
                )
            SCHOOL_TYPES = [type.name for type in SchoolType.objects.all()]
            return [
                {key: school[key] for key in RSPO_CSV_COLUMNS}
                for school in reader
                if (
                    school['Typ'] in SCHOOL_TYPES
                    and school['Kategoria uczniów'] == CHILDREN_OR_YOUTH
                    and school['Data likwidacji'] == ''
                    and int(school['Liczba uczniów']) > 0
                )
            ]

    def get_last_rspo_backup(self, filename=None):
        """Searches and returns the contents of the backup file from the last RSPO database. The backup is stored in RSPO format."""
        if filename is not None:
            return self.read_rspo_csv_file(filename)
        files = [file for file in os.listdir(BASE_DIR) if 'rspo_' in file]
        sorted_files = sorted(
            files,
            key=lambda x: os.path.getmtime(os.path.join(BASE_DIR, x)),
            reverse=True,
        )
        if not sorted_files:
            return []
        filename = sorted_files[0]
        return self.read_rspo_csv_file(fr'{BASE_DIR}/{filename}')

    def save_rspo_backup(self, schools: list):
        """Saves a backup of the currently imported RSPO database to disk."""
        if DRY_RUN:
            return
        with open(BACKUP_FILENAME, 'w', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=RSPO_CSV_COLUMNS, delimiter=';')
            writer.writeheader()
            writer.writerows(schools)

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help="Source CSV file")
        parser.add_argument('--dry-run', action='store_true', default=False, help='Run in dry-run mode')
        parser.add_argument(
            '--first-import',
            action='store_true',
            default=False,
            help='Marks all schools from the DB as inactive',
        )
        parser.add_argument(
            '--backup-filename',
            type=str,
            default=None,
            help='Backup to be read (default: latest)',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        rows_affected = 0
        new_records = 0

        input_filename = kwargs['filename']
        dry_run = kwargs['dry_run']
        DRY_RUN = dry_run
        first_import = kwargs['first_import']
        backup_path = kwargs['backup_filename']
        VERBOSITY = kwargs['verbosity']

        prepare_dir(BASE_DIR)

        last_rspo_schools = self.get_last_rspo_backup(backup_path)  # List of RSPO school dicts
        self.log(f'INFO: Read {len(last_rspo_schools)} records from the RSPO database backup.')
        curr_rspo_schools = self.read_rspo_csv_file(input_filename)  # List of RSPO school dicts
        self.log(f'INFO: Read {len(curr_rspo_schools)} records from the currently imported RSPO database.')

        self.save_rspo_backup(curr_rspo_schools)
        curr_rspo_schools = [translate_rspo_school(school).__dict__ for school in curr_rspo_schools] # List of school dicts
        last_rspo_schools = [translate_rspo_school(school).__dict__ for school in last_rspo_schools] # List of school dicts

        if last_rspo_schools == [] and not first_import:
            raise CommandError(
                'Make sure to set first-import if you are importing for the first time!'
            )
        if first_import:
            set_all_schools_inactive()

        for db_school in School.objects.filter(is_active=True):
            db_school_dict = db_school.__dict__
            curr_rspo_school = find_school(db_school_dict, curr_rspo_schools)
            last_rspo_school = find_school(db_school_dict, last_rspo_schools)

            curr_rspo_school_exists = curr_rspo_school is not None
            last_rspo_school_exists = last_rspo_school is not None

            if curr_rspo_school_exists and last_rspo_school_exists:
                db_and_curr_the_same = are_the_same(db_school_dict, curr_rspo_school)
                db_and_last_the_same = are_the_same(db_school_dict, last_rspo_school)
                curr_and_last_the_same = are_the_same(curr_rspo_school, last_rspo_school)

                # If the MoE has made changes that we have not, then accept MoE changes.
                if not db_and_curr_the_same and db_and_last_the_same:
                    self.log(
                        f'Note: The school [rspo: {db_school.rspo}] has been changed in the RSPO database. The changes have been applied.',
                        school_before=db_school,
                        school_after=translate_dict_school(curr_rspo_school),
                    )
                    try:
                        with transaction.atomic():
                            update_school(curr_rspo_school, db_school)
                        rows_affected += 1
                    except utils.IntegrityError:
                        self.log(
                            f'Warning: Django found a duplicate school. Please manually check the school {db_school.rspo} data in SIO database, '
                            'current RSPO and the last backup. Something suspicious may be going on.'
                        )
                # If MoE has made changes and we have also made changes, but different ones, highlight in logs.
                elif (not db_and_curr_the_same and not db_and_last_the_same and not curr_and_last_the_same):
                    self.log(
                        f'Note: The school [rspo: {db_school.rspo}] has been changed in the SIO database and in the RSPO database. '
                        'The changes have not been applied. Please check the school manually.',
                        additional_info='Below is the diff between the school in the SIO database and the one in the currently imported RSPO database. '
                        'Keep in mind that the changes HAVE NOT BEEN applied. If you think they should be applied, do it manually.',
                        school_before=db_school,
                        school_after=translate_dict_school(curr_rspo_school),
                    )

                curr_rspo_schools.remove(curr_rspo_school)
                last_rspo_schools.remove(last_rspo_school)

            # If the school no longer appears in the MoE database, i.e. has been deleted, mark the school as inactive.
            elif not curr_rspo_school_exists and last_rspo_school_exists:
                self.log(
                    f'Note: The school [rspo: {db_school.rspo}] no longer appears in the RSPO database.',
                    additional_info='It has been set as inactive. Please check that the school with the '
                    'changed RSPO number does not appear in the currently imported RSPO database.',
                )
                db_school.is_active = False
                db_school.save()
                rows_affected += 1
                last_rspo_schools.remove(last_rspo_school)

        if len(curr_rspo_schools) > 0:
            self.log(
                f'Warning: There are still {len(curr_rspo_schools)} schools left that did not have an active counterpart in the SIO database.'
            )

        # Check all currently imported schools that do not have counterparts in the SIO database.
        for school in curr_rspo_schools:
            queried_school = get_object_or_none(School, rspo=school['rspo'])
            # If there is inactive school in the SIO database, we inform about it.
            if queried_school is not None:
                self.log(
                    f'Note: The school [rspo: {queried_school.rspo}] has been found in the imported RSPO database that is not '
                    'currently active in the SIO database. Please verify that this is the way it is supposed to be.'
                )
            else:
                try:
                    # If there has been no school with this RSPO number in the past,
                    # i.e. a new school has appeared in the RSPO database, we import it.
                    if find_school(school, last_rspo_schools) is None:
                        s = translate_dict_school(school)
                        with transaction.atomic():
                            s.save()
                        self.log(
                            f'Note: A new school [rspo: {school["rspo"]}] has been found, which previously was not in the RSPO database. '
                            'It has been added to the SIO database.'
                        )
                        new_records += 1
                    # If an attempt is made to add a school that was present in the last RSPO backup,
                    # but is not present in the SIO database (probably deleted).
                    else:
                        self.log(
                            f'Warning: An attempt was made to add a school [rspo: {school["rspo"]}] that has probably been deleted from the SIO '
                            'database. If you want to add it, do it manually.',
                            additional_info='Tip: If you want to add schools that have been deleted since the last import, delete the last two backups.',
                        )
                except utils.IntegrityError:
                    self.log(
                        f'Warning: Django found a duplicate school. Please manually check the school {school["rspo"]} data in SIO database, '
                        'current RSPO and the last backup. Something suspicious may be going on.'
                    )

        self.log('Warning: Keep in mind that schools with wrong type in RSPO database are not taken into account!')
        copy_log_file()

        if DRY_RUN:
            transaction.set_rollback(True)
            self.log(
                'IMPORTANT: The following data shows the number of queries if dry-run were disabled. Since it was on, NO CHANGES were made.'
            )
        self.log(f'Rows affected: {rows_affected}\nNew records: {new_records}')
