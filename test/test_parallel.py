#!/usr/bin/env python

import multiprocessing
import subprocess
import time
import os
import shutil
import argparse
import tempfile
import sys


def make_tmp_html_path(tmp_dir, proc_id):
    return os.path.join(tmp_dir, '%d.html' % proc_id)


def make_env():
    env = dict(os.environ)
    env.update({
        'DJANGO_SETTINGS_MODULE': 'oioioi.test_settings'
    })
    return env


class HtmlCollector(object):
    def __init__(self):
        self.rows = []
        self.html_header = None
        self.html_footer = None

    @staticmethod
    def _is_unnecessary_info(s):
        return not s.startswith('<p class=\'attribute\'><strong>')

    def parse_output(self, path):
        """Tries to read and recover HTML output from runner"""
        try:
            with open(path, 'r') as f:
                lines = f.read().split('\n')

            # Parse HTML the hacker way
            start = lines.index('</tr>') + 1
            end = lines.index('<tr id=\'total_row\'>')
            self.rows.append('\n'.join(lines[start:end]))

            footer_start = lines.index('</table>')
            filtered_header = filter(HtmlCollector._is_unnecessary_info,
                                    lines[0:start])

            if self.html_header is None:
                self.html_header = '\n'.join(filtered_header)
                self.html_footer = '\n'.join(lines[footer_start:])

        except:  # pylint: disable=bare-except
            print 'An error occured while processing html output. ' + \
                    'Ignoring it...'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        """Outputs an HTML string with all parsed information"""
        if not self.html_header:
            return ''
        else:
            return self.html_header + \
                   '\n'.join(self.rows) + \
                   self.html_footer


def spawn_processes(args, tmp_dir, nose_args, env):
    """Prepares arguments and spawns test runner processes.
       Returns a list of Popen objects.
    """
    def make_arg(k, v):
        return '--' + k + ('=' + str(v) if v is not None else '')
    processes = []
    for proc_id in range(0, args.total_processes):
        # Use None for options without arguments
        base_args = {
            'with-nose-picker': None,
            'with-html': None,
            'html-file': make_tmp_html_path(tmp_dir, proc_id),
            'total-processes': args.total_processes,
            'which-process': proc_id
        }
        command = ['django-admin.py', 'test']
        command += [make_arg(k, v) for k, v in base_args.iteritems()]
        command += nose_args
        processes.append(subprocess.Popen(command, env=env))
    return processes


def join_processes(args, tmp_dir, processes):
    """Waits for the tests to finish and collects html output.
       Returns a tuple containing:
       1) a string with concatenated runners' HTML output
       2) a boolean indicating if all the tests passed
    """
    html_collector = HtmlCollector()
    success = True
    for proc_id, proc in enumerate(processes):
        proc.wait()
        if proc.returncode != 0:
            success = False
        html_collector.parse_output(make_tmp_html_path(tmp_dir, proc_id))
    return str(html_collector), success


def main():
    parser = argparse.ArgumentParser(
                    description='Runs OIOIOI tests in parallel')
    parser.add_argument('--total-processes', default=0, type=int,
                        help='How many runners to use (0 = use 2/3 of cores)')
    parser.add_argument('--html-file', default='test_report.html',
                        help='Name of the html output file')

    args, nose_args = parser.parse_known_args()

    # Use 2/3 cores as a reasonable default.
    # This should take advantage of parallelism and keep the machine responsive
    if args.total_processes <= 0:
        args.total_processes = int(multiprocessing.cpu_count() * 2./3.)
    print 'Using {} processes'.format(args.total_processes)

    tmp_dir = tempfile.mkdtemp()
    try:
        process_list = spawn_processes(args, tmp_dir, nose_args, make_env())
        start_time = time.time()
        html_output, passed = join_processes(args, tmp_dir, process_list)
        with open(args.html_file, 'w') as out_file:
            out_file.write(html_output)
    except KeyboardInterrupt:
        print ''
        print 'Tests interrupted. Killing tester processes.'
        passed = False
        for proc in process_list:
            proc.kill()
    finally:
        shutil.rmtree(tmp_dir)

    print 'All done!'
    print 'Total time: %ds' % (time.time() - start_time)
    print 'PASS' if passed else 'FAILED'

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
