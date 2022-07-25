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
from copy import deepcopy
from .config_generator import ConfigProcessor
import importlib
from enum import Enum
from inspect import getmembers, isfunction

class DefaultMergeStrategy(Enum):
    append = 'append'
    override = 'override'
    prepend = 'prepend'
    append_unique = 'append_unique' #WARNING: current this strategy does not support list of dicts, only list of str

    def __str__(self):
        return self.name

    @staticmethod
    def from_string(s):
        try:
            return DefaultMergeStrategy[s]
        except KeyError:
            raise ValueError(f'ERROR: Allowable values for default merge strategies are: append/override/prepend/append_unique. %s is not supported. ' % s)

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

        merge_list_strategy = ["append"] #default merge strategy for list
        if opts.merge_list_strategy is not None:
            if opts.merge_list_strategy[0] == 'default': #default merge strategy provided by himl/deepmerge
                try:
                    merge_list_strategy = [DefaultMergeStrategy.from_string(opts.merge_list_strategy[1]).value] #only viable options are append/override/prepend/append_unique
                except ValueError as err:
                    print(err)
                    return       
            else:
                imported_module = importlib.import_module(opts.merge_list_strategy[0])
                if callable(func := getattr(imported_module, opts.merge_list_strategy[1])):
                    merge_list_strategy = [func,"append"] #use append as the fallback strategy
  
        config_processor = ConfigProcessor()
                                 
        config_processor.process(cwd, opts.path, filters, excluded_keys, opts.enclosing_key, opts.remove_enclosing_key,
                                 opts.output_format, opts.print_data, opts.output_file, opts.skip_interpolation_resolving,
                                 opts.skip_interpolation_validation, opts.skip_secrets, opts.multi_line_string,
                                 type_strategies= [(list, merge_list_strategy), (dict, ["merge"])] )

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
        parser.add_argument('--merge-list-strategy', dest='merge_list_strategy', nargs=2,
                            help='override default merge strategy for list. format is module_name function_name. if using default strategies, module_name is default, function_name is append/override/prepend/append_unique')
        parser.add_argument('--version', action='version', version='%(prog)s v{version}'.format(version="0.10.0"),
                            help='print himl version')
        return parser


def run(args=None):
    ConfigRunner().run(args)
