#!/usr/bin/env python

# This script is intended to be run on client's machine.
# Use this to submit your solutions to an OIOIOI server instance.

import sys
import json
import webbrowser
import itertools
import mimetools
import mimetypes
import urllib2

from optparse import OptionParser
from urlparse import urlparse
from os.path import expanduser, splitext


class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, filehandle, mimetype=None):
        """Add a file to be uploaded."""
        body = filehandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] \
                or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data,
        including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [part_boundary,
             'Content-Disposition: form-data; name="%s"' % name,
             '',
             value,
             ]
            for name, value in self.form_fields
        )

        # Add the files to upload
        parts.extend(
            [part_boundary,
             'Content-Disposition: file; name="%s"; filename="%s"' %
             (field_name, filename),
             'Content-Type: %s' % content_type,
             '',
             body,
             ]
            for field_name, filename, content_type, body in self.files
        )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


configuration = {}
config_path = expanduser('~/.oioioi-submit-config')
error_code_map = {'UNSUPPORTED_EXTENSION': "Unsupported file extension",
                  'AUTHORIZATION_FAILED':
                  "Token invalid or authorization failure",
                  'NO_SUCH_PROBLEM':
                  "File name does not match any of available problems.\n"
                  "Available problems: %(data)s",
                  "INVALID_SUBMISSION": "Submission was not valid. "
                                        "Errors: %(data)s",
                  "UNKNOWN_ERROR": "Unknown server error"}


def main():
    parser = OptionParser(usage="Usage: ./submit.py [-ch|-tkusw filename]")
    parser.add_option('-c', '--configure', action='store_true',
                      help="start interactive configuration")
    parser.add_option('-t', '--task', action='store',
                      help="override task short name (if not specified, " +
                           "filename with extension is taken)")
    parser.add_option('-k', '--token', action='store',
                      help="provide a token for authentication")
    parser.add_option('-u', '--url', action='store',
                      help="provide connection URL " +
                           "(e.g. http://oioioi.com/c/example-contest/)")
    parser.add_option('-s', '--save-config', action='store_true',
                      help="used along with --token or/and --url, saves " +
                           "configuration changes to configuration file")
    parser.add_option('-w', '--webbrowser', action='store_true',
                      help="open the web browser after successful submission")

    init_config()
    opts, args = parser.parse_args()
    if opts.save_config and opts.configure:
        parser.error("options --save-config and --configure "
                     "are mutually exclusive")
    if opts.token:
        configuration['token'] = opts.token
    if opts.url:
        configuration['contest-url'] = opts.url

    if opts.save_config:
        save_configuration()
    elif opts.configure:
        return create_configuration()
    elif args:
        return submit(args[0], opts.task,
                      configuration['token'], configuration['contest-url'],
                      opts.webbrowser)
    parser.print_usage()
    return 1


def init_config():
    # pylint: disable=global-statement
    global configuration
    try:
        json_data = open(config_path).read()
        configuration = json.loads(json_data)
    except IOError:
        configuration = {}


def submit(filename, task_name, token, contest_url, open_webbrowser):
    if 'contest-url' not in configuration:
        print >> sys.stderr, \
            "Configuration file could not be loaded. " + \
            "Please run submit.py --configure " + \
            "to configure the application."
        return 1

    print >> sys.stderr, 'oioioi-submit'
    print >> sys.stderr, '============='
    try:
        if not contest_url.endswith('/'):
            contest_url += '/'
        if not task_name:
            task_name, _ = splitext(filename)
        with open(filename, 'rb') as solution_file:
            form = MultiPartForm()
            form.add_field('token', token)
            form.add_field('task', task_name)
            form.add_file('file', solution_file.name, filehandle=solution_file)
            body = str(form)
            request = urllib2.Request('%ssubmitservice/submit/' % contest_url)
            request.add_header('Content-Type', form.get_content_type())
            request.add_header('Content-Length', len(body))
            request.add_data(body)

            result = json.loads(urllib2.urlopen(request).read())
        base_url = urlparse(contest_url)
        if 'error_code' not in result:
            result_url = '%s://%s%s' % (base_url.scheme, base_url.netloc,
                                        result['result_url'])
            print >> sys.stderr, "Submission succeeded! View your status at:"
            print >> sys.stderr, result_url
            if open_webbrowser:
                webbrowser.open_new_tab(result_url)
        else:
            raise RuntimeError(error_code_map[result['error_code']] %
                               {'data': result['error_data']})
    except StandardError as e:
        print >> sys.stderr, "Error:", e
        print >> sys.stderr, "Submission failed."
        return 1
    return 0


def query(key, value_friendly_name, mask_old_value=False):
    print >> sys.stderr, \
        "Enter new value for %s or press Enter." % value_friendly_name
    old_value = configuration.get(key)
    if not old_value:
        old_value = ''
    new_value = raw_input('[%s] ' % (key if mask_old_value and key
                                     in configuration else old_value))
    if new_value:
        configuration[key] = new_value
    elif not new_value and key not in configuration:
        print >> sys.stderr, "You must provide a value."
        return True
    return False


def create_configuration():
    print >> sys.stderr, "Fill in the fields to create your configuration."
    while query('contest-url',
                "contest website (e.g. http://oioioi.com/c/example-contest/)"):
        pass
    while query('token', "authentication token", True):
        pass
    return save_configuration()


def save_configuration():
    try:
        with open(config_path, 'w') as config_file:
            config_file.write(json.dumps(configuration))
        print >> sys.stderr, "Configuration has been saved successfully."
        return 0
    except Exception, e:
        print >> sys.stderr, "Could not write configuration: %s" % e
        return 1


if __name__ == '__main__':
    sys.exit(main())
