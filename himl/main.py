# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import argparse
import os

from .config_generator import ConfigProcessor


class ConfigRunner(object):

    def run(self, args):
        parser = self.get_parser()
        opts = parser.parse_args(args)
        self.do_run(opts)

    def do_run(self, opts):
        cwd = opts.cwd if opts.cwd else os.getcwd()
        filters = opts.filter if opts.filter else ()
        excluded_keys = opts.exclude if opts.exclude else ()
        if opts.output_file is None:
            opts.print_data = True

        config_processor = ConfigProcessor()
        config_processor.process(cwd, opts.path, filters, excluded_keys, opts.enclosing_key, opts.remove_enclosing_key,
                                 opts.output_format, opts.print_data, opts.output_file, opts.skip_interpolation_resolving,
                                 opts.skip_interpolation_validation, opts.skip_secrets, opts.multi_line_string)

    @staticmethod
    def get_parser(parser=None):
        if not parser:
            parser = argparse.ArgumentParser()
            parser.add_argument('path', type=str, help='The config directory')

        parser.add_argument('--output-file', dest='output_file', type=str,
                            help='output file location')
        parser.add_argument('--print-data', action='store_true',
                            help='print generated data on screen')
        parser.add_argument('--format', dest='output_format', type=str, default="yaml",
                            help='output file format')
        parser.add_argument('--filter', dest='filter', action='append',
                            help='keep these keys from the generated data')
        parser.add_argument('--exclude', dest='exclude', action='append',
                            help='exclude these keys from generated data')
        parser.add_argument('--skip-interpolation-validation', action='store_true',
                            help='will not throw an error if interpolations can not be resolved')
        parser.add_argument('--skip-secrets', action='store_true',
                            help='will not throw an error if secrets can not be resolved')
        parser.add_argument('--skip-interpolation-resolving', action='store_true',
                            help='do not perform any AWS calls to resolve interpolations')
        parser.add_argument('--enclosing-key', dest='enclosing_key', type=str,
                            help='enclose the generated data under a common key')
        parser.add_argument('--remove-enclosing-key', dest='remove_enclosing_key', type=str,
                            help='remove enclosed data from under a common key')
        parser.add_argument('--cwd', dest='cwd', type=str, default="",
                            help='the working directory')
        parser.add_argument('--multi-line-string', action='store_true',
                            help='will overwrite the global yaml dumper to use block style')
        return parser


def run(args=None):
    ConfigRunner().run(args)
