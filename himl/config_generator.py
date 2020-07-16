# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import json
import os
from collections import OrderedDict
import logging

import pathlib2
import yaml
from deepmerge import Merger

from .interpolation import InterpolationResolver, EscapingResolver, InterpolationValidator, SecretResolver, DictIterator, replace_parent_working_directory
from .python_compat import iteritems, primitive_types, PY3
from .remote_state import S3TerraformRemoteStateRetriever

logger = logging.getLogger(__name__)


class ConfigProcessor(object):

    def process(self, cwd=None, path=None, filters=(), exclude_keys=(), enclosing_key=None, remove_enclosing_key=None, output_format="yaml",
                print_data=False, output_file=None, skip_interpolations=False, skip_interpolation_validation=False, skip_secrets=False, multi_line_string=False):

        path = self.get_relative_path(path)

        if skip_interpolations:
            skip_interpolation_validation = True

        elif skip_secrets:
            skip_interpolation_validation = True

        if cwd is None:
            cwd = os.getcwd()

        generator = ConfigGenerator(cwd, path, multi_line_string)
        generator.generate_hierarchy()
        generator.process_hierarchy()

        if len(exclude_keys) > 0:
           generator.exclude_keys(exclude_keys)

        if not skip_interpolations:
            generator.resolve_interpolations()
            # Perform another resolving, in case some secrets are used as interpolations.
            # Example:
            # map1:
            #    key1: value1
            # map2: "{{map1.key1}}"
            # value: "something-{{map2.key1}} <--- this will be resolved at this step
            generator.resolve_interpolations()
            generator.add_dynamic_data()
            generator.resolve_interpolations()

        if not skip_secrets:
            default_aws_profile = self.get_default_aws_profile(generator.generated_data)
            generator.resolve_secrets(default_aws_profile)
            # Perform another resolving, in case some secrets are used as interpolations.
            # Example:
            # value1: "{{ssm.mysecret}}"
            # value2: "something-{{value1}} <--- this will be resolved at this step
            generator.resolve_interpolations()

        if len(filters) > 0:
            generator.filter_data(filters)

        if not skip_interpolation_validation:
            generator.validate_interpolations()

        if enclosing_key:
            logger.info("Adding enclosing key {}".format(enclosing_key))
            data = generator.add_enclosing_key(enclosing_key)
        elif remove_enclosing_key:
            logger.info("Removing enclosing key {}".format(remove_enclosing_key))
            data = generator.remove_enclosing_key(remove_enclosing_key)
        else:
            data = generator.generated_data

        generator.clean_escape_characters()

        formatted_data = generator.output_data(data, output_format)

        if print_data:
            print(formatted_data)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(formatted_data)

        return data

    @staticmethod
    def get_default_aws_profile(data):
        return data['aws']['profile'] if 'aws' in data and 'profile' in data['aws'] else None

    @staticmethod
    def get_relative_path(path):
        cwd = os.path.join(os.getcwd(), '')
        if path.startswith(cwd):
            return path[len(cwd):]
        return path


class ConfigGenerator(object):
    """
    this class is used to create a config generator object which will be used to generate cluster definition files
    from the hierarchy of directories. The class implements methods that performs deep merging on dicts so the end result
    will contain merged data on each layer.
    """

    def __init__(self, cwd, path, multi_line_string):
        self.cwd = cwd
        self.path = path
        self.hierarchy = self.generate_hierarchy()
        self.generated_data = OrderedDict()
        self.interpolation_validator = InterpolationValidator()

        if multi_line_string is True:
            yaml.representer.BaseRepresenter.represent_scalar = ConfigGenerator.custom_represent_scalar

    @staticmethod
    def yaml_dumper():
        try:
            from yaml import CLoader as Loader, CDumper as Dumper
        except ImportError:
            from yaml import Loader, Dumper
        from yaml.representer import SafeRepresenter
        _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

        def dict_representer(dumper, data):
            return dumper.represent_dict(iteritems(data))

        def dict_constructor(loader, node):
            return OrderedDict(loader.construct_pairs(node))

        Dumper.add_representer(OrderedDict, dict_representer)
        Loader.add_constructor(_mapping_tag, dict_constructor)

        Dumper.add_representer(str, SafeRepresenter.represent_str)

        if not PY3:
            Dumper.add_representer(unicode, SafeRepresenter.represent_unicode)
        return Dumper

    @staticmethod
    def get_yaml_from_path(working_directory, path):
        yaml_files = []
        for yaml_file in os.listdir(path):
            if yaml_file.endswith(".yaml"):
                yaml_files.append(os.path.join(working_directory, yaml_file))
        return sorted(yaml_files)

    @staticmethod
    def yaml_get_content(yaml_file):
        with open(yaml_file, 'r') as f:
            content = yaml.load(f, Loader=yaml.FullLoader)
        return content if content else {}

    @staticmethod
    def merge_value(reference, new_value):
        merger = Merger([(list, ["append"]), (dict, ["merge"])], ["override"], ["override"])
        if isinstance(new_value, (list, set, dict)):
            new_reference = merger.merge(reference, new_value)
        else:
            raise TypeError("Cannot handle merge_value of type {}".format(type(new_value)))
        return new_reference

    @staticmethod
    def merge_yamls(values, yaml_content):
        for key, value in iteritems(yaml_content):
            if key in values and type(values[key]) != type(value):
                raise Exception("Failed to merge key '{}', because of mismatch in type: {} vs {}"
                                .format(key, type(values[key]), type(value)))
            if key in values and not isinstance(value, primitive_types):
                values[key] = ConfigGenerator.merge_value(values[key], value)
            else:
                values[key] = value

    @staticmethod
    def resolve_simple_interpolations(data, current_yaml_file):

        directory = os.path.dirname(current_yaml_file)
        directory = os.path.join(os.getcwd(), directory)

        looper = DictIterator()
        looper.loop_all_items(data, lambda value: replace_parent_working_directory(value, directory))

    def generate_hierarchy(self):
        """
        the method will go through the hierarchy of directories and create an ordered list of directories to be used
        when merging data at each layer
        :return: returns a list of directories in a priority order (from less specific to more specific)
        """
        hierarchy = []
        full_path = pathlib2.Path(self.path)
        for path in full_path.parts:
            os.chdir(path)
            new_path = os.path.relpath(os.getcwd(), self.cwd)
            hierarchy.append(self.get_yaml_from_path(new_path, os.getcwd()))
        os.chdir(self.cwd)
        return hierarchy

    def process_hierarchy(self):
        merged_values = OrderedDict()
        for yaml_files in self.hierarchy:
            for yaml_file in yaml_files:
                yaml_content = self.yaml_get_content(yaml_file)
                self.merge_yamls(merged_values, yaml_content)
                self.resolve_simple_interpolations(merged_values, yaml_file)
        self.generated_data = merged_values

    def get_values_from_dir_path(self):
        values = {}
        full_path = pathlib2.Path(self.path)
        for path in full_path.parts[1:]:
            split_value = path.split('=')
            values[split_value[0]] = split_value[1]
        return values

    def output_yaml_data(self, data):
        return yaml.dump(data, Dumper=ConfigGenerator.yaml_dumper(), default_flow_style=False, width=200)

    def yaml_to_json(self, yaml_data):
        return json.dumps(yaml.load(yaml_data, Loader=yaml.FullLoader), indent=4)

    def output_data(self, data, output_format):
        yaml_data = self.output_yaml_data(data)
        if "yaml" in output_format:
            return yaml_data
        elif "json" in output_format:
            return self.yaml_to_json(yaml_data)
        raise Exception("Unknown output format: {}".format(output_format))

    def add_enclosing_key(self, key):
        return {key: self.generated_data}

    def remove_enclosing_key(self, key):
        return self.generated_data[key]

    def filter_data(self, keys):
        self.generated_data = {key: self.generated_data[key] for key in keys if key in self.generated_data}

    def exclude_keys(self, keys):
        for key in keys:
            if key in self.generated_data:
                try:
                    logger.info("Excluding key %s", key)
                    del self.generated_data[key]
                except KeyNotFound:
                    logger.info("Excluded key %s not found or already removed", key)

    def add_dynamic_data(self):
        remote_state_retriever = S3TerraformRemoteStateRetriever()
        if "remote_states" in self.generated_data:
            state_files = self.generated_data["remote_states"]
            remote_states = remote_state_retriever.get_dynamic_data(state_files)
            self.merge_value(self.generated_data, remote_states)

    def resolve_interpolations(self):
        resolver = InterpolationResolver()
        self.generated_data = resolver.resolve_interpolations(self.generated_data)

    def resolve_secrets(self, default_aws_profile):
        resolver = SecretResolver()
        self.generated_data = resolver.resolve_secrets(self.generated_data, default_aws_profile)

    def validate_interpolations(self):
        self.interpolation_validator.check_all_interpolations_resolved(self.generated_data)

    def clean_escape_characters(self):
        """
        Method should clean the escaping characters {{` and `}} from all escaped values
        """
        resolver = EscapingResolver()
        self.generated_data = resolver.resolve_escaping(self.generated_data)

    @staticmethod
    def should_use_block(value):
        """
        https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
        """

        for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
            if c in value:
                return True
        return False

    @staticmethod
    def custom_represent_scalar(self, tag, value, style=None):
        if style is None:
            if ConfigGenerator.should_use_block(value):
                style = '|'
            else:
                style = self.default_style

        node = yaml.representer.ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node
