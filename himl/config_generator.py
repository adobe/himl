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

from .interpolation import InterpolationResolver, EscapingResolver, InterpolationValidator, SecretResolver, \
    DictIterator, replace_parent_working_directory, EnvVarResolver
from .python_compat import iteritems, primitive_types, PY3

logging.basicConfig()
logging.root.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigProcessor(object):

    def process(self, cwd=None,
                path=None,
                filters=(),
                exclude_keys=(),
                enclosing_key=None,
                remove_enclosing_key=None,
                output_format="yaml",
                print_data=False,
                output_file=None,
                skip_interpolations=False,
                skip_interpolation_validation=False,
                skip_secrets=False,
                multi_line_string=False,
                type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
                fallback_strategies=["override"],
                type_conflict_strategies=["override"]):

        # Prepare parameters and create generator
        path = self.get_relative_path(path)
        skip_interpolation_validation = self._should_skip_interpolation_validation(
            skip_interpolations, skip_secrets, skip_interpolation_validation)
        cwd = cwd or os.getcwd()

        generator = self._create_and_initialize_generator(
            cwd, path, multi_line_string, type_strategies, fallback_strategies, type_conflict_strategies)

        # Process data exclusions and interpolations
        self._process_exclusions(generator, exclude_keys)
        self._process_interpolations(generator, skip_interpolations, skip_secrets)
        self._process_filters_and_validation(generator, filters, skip_interpolation_validation)

        # Handle enclosing key operations and get final data
        data = self._handle_enclosing_key_operations(generator, enclosing_key, remove_enclosing_key)
        generator.clean_escape_characters()

        # Handle output operations
        self._handle_output_operations(generator, data, output_format, print_data, output_file)

        return data

    def _should_skip_interpolation_validation(self, skip_interpolations, skip_secrets, skip_interpolation_validation):
        """Determine if interpolation validation should be skipped."""
        return skip_interpolation_validation or skip_interpolations or skip_secrets

    def _create_and_initialize_generator(self, cwd, path, multi_line_string, type_strategies,
                                         fallback_strategies, type_conflict_strategies):
        """Create and initialize the ConfigGenerator."""
        generator = ConfigGenerator(cwd, path, multi_line_string, type_strategies, fallback_strategies,
                                    type_conflict_strategies)
        generator.generate_hierarchy()
        generator.process_hierarchy()
        return generator

    def _process_exclusions(self, generator, exclude_keys):
        """Process key exclusions before interpolations."""
        if len(exclude_keys) > 0:
            generator.exclude_keys(exclude_keys)

    def _process_interpolations(self, generator, skip_interpolations, skip_secrets):
        """Process all interpolation steps."""
        if not skip_interpolations:
            self._resolve_basic_interpolations(generator)
            self._resolve_dynamic_interpolations(generator)
            self._resolve_env_interpolations(generator)
            self._resolve_secret_interpolations(generator, skip_secrets)

    def _resolve_basic_interpolations(self, generator):
        """Resolve basic and nested interpolations."""
        # TODO: reduce the number of calls to resolve_interpolations
        generator.resolve_interpolations()

        # Resolve nested interpolations:
        # Example:
        # map1:
        #    key1: value1
        # map2: "{{map1.key1}}"
        # value: "something-{{map2.key1}} <--- this will be resolved at this step
        generator.resolve_interpolations()

    def _resolve_dynamic_interpolations(self, generator):
        """Add dynamic data and resolve interpolations using dynamic data."""
        generator.add_dynamic_data()
        generator.resolve_interpolations()

    def _resolve_env_interpolations(self, generator):
        """Add env vars and resolve interpolations using env vars."""
        generator.resolve_env()
        generator.resolve_interpolations()

    def _resolve_secret_interpolations(self, generator, skip_secrets):
        """Add secrets and resolve interpolations using secrets."""
        if not skip_secrets:
            default_aws_profile = self.get_default_aws_profile(generator.generated_data)
            generator.resolve_secrets(default_aws_profile)
            # Perform resolving in case some secrets are used in nested interpolations.
            # Example:
            # value1: "{{ssm.mysecret}}"
            # value2: "something-{{value1}} <--- this will be resolved at this step
            generator.resolve_interpolations()

    def _process_filters_and_validation(self, generator, filters, skip_interpolation_validation):
        """Process data filtering and interpolation validation."""
        if len(filters) > 0:
            generator.filter_data(filters)
        if not skip_interpolation_validation:
            generator.validate_interpolations()

    def _handle_enclosing_key_operations(self, generator, enclosing_key, remove_enclosing_key):
        """Handle enclosing key addition or removal operations."""
        if enclosing_key:
            logger.info("Adding enclosing key {}".format(enclosing_key))
            return generator.add_enclosing_key(enclosing_key)
        elif remove_enclosing_key:
            logger.info("Removing enclosing key {}".format(remove_enclosing_key))
            return generator.remove_enclosing_key(remove_enclosing_key)
        else:
            return generator.generated_data

    def _handle_output_operations(self, generator, data, output_format, print_data, output_file):
        """Handle printing and file output operations."""
        if print_data or output_file:
            formatted_data = generator.output_data(data, output_format)

            if print_data:
                print(formatted_data)

            if output_file:
                with open(output_file, 'w') as f:
                    f.write(formatted_data)

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
    from the hierarchy of directories. The class implements methods that performs deep merging on dicts so the end
    result
    will contain merged data on each layer.
    """

    def __init__(self, cwd, path, multi_line_string, type_strategies, fallback_strategies, type_conflict_strategies):
        self.cwd = cwd
        self.path = path
        self.hierarchy = self.generate_hierarchy()
        self.generated_data = OrderedDict()
        self.interpolation_validator = InterpolationValidator()
        self.type_strategies = type_strategies
        self.fallback_strategies = fallback_strategies
        self.type_conflict_strategies = type_conflict_strategies
        if multi_line_string is True:
            yaml.representer.BaseRepresenter.represent_scalar = ConfigGenerator.custom_represent_scalar  # type: ignore

    @staticmethod
    def yaml_dumper():
        try:
            from yaml import CLoader as Loader, CDumper as Dumper
        except ImportError:
            from yaml import Loader, Dumper  # type: ignore
        _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

        def dict_representer(dumper, data):
            return dumper.represent_dict(iteritems(data))

        def dict_constructor(loader, node):
            return OrderedDict(loader.construct_pairs(node))

        Dumper.add_representer(OrderedDict, dict_representer)
        Loader.add_constructor(_mapping_tag, dict_constructor)

        def str_representer_pipestyle(dumper, data):
            style = '|' if '\n' in data else None
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)

        Dumper.add_representer(str, str_representer_pipestyle)

        if not PY3:
            def unicode_representer_pipestyle(dumper, data):
                style = u'|' if u'\n' in data else None
                return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style=style)

            # Python 3 doesn't have unicode type, use str instead
            Dumper.add_representer(str, unicode_representer_pipestyle)

        return Dumper

    @staticmethod
    def get_yaml_from_path(working_directory, path):
        yaml_files = []
        for yaml_file in os.listdir(path):
            if yaml_file.endswith(".yaml"):
                yaml_files.append(os.path.join(path, yaml_file))
        return sorted(yaml_files)

    @staticmethod
    def yaml_get_content(yaml_file):
        with open(yaml_file, 'r') as f:
            content = yaml.load(f, Loader=yaml.SafeLoader)
        return content if content else {}

    @staticmethod
    def merge_value(reference, new_value, type_strategies, fallback_strategies, type_conflict_strategies):
        merger = Merger(type_strategies, fallback_strategies, type_conflict_strategies)
        if isinstance(new_value, (list, set, dict)):
            new_reference = merger.merge(reference, new_value)
        else:
            raise TypeError("Cannot handle merge_value of type {}".format(type(new_value)))
        return new_reference

    @staticmethod
    def merge_yamls(values, yaml_content, type_strategies, fallback_strategies, type_conflict_strategies):
        for key, value in iteritems(yaml_content):
            if key in values and not isinstance(values[key], type(value)) and not isinstance(value, type(values[key])):
                raise Exception("Failed to merge key '{}', because of mismatch in type: {} vs {}"
                                .format(key, type(values[key]), type(value)))
            if key in values and not isinstance(value, primitive_types):
                values[key] = ConfigGenerator.merge_value(values[key], value, type_strategies, fallback_strategies,
                                                          type_conflict_strategies)
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

        # Start from the current working directory
        current_dir = self.cwd
        full_target_path = os.path.join(current_dir, self.path)

        # If path is a file, just process the current directory
        if os.path.isfile(full_target_path):
            hierarchy.append(self.get_yaml_from_path(".", current_dir))
            return hierarchy

        # If path is a directory, build hierarchy by traversing path components
        full_path = pathlib2.Path(self.path)
        accumulated_path = ""

        # First, add the base directory (cwd)
        hierarchy.append(self.get_yaml_from_path(".", current_dir))

        # Then traverse each directory component in the path
        for path_part in full_path.parts:
            if accumulated_path:
                accumulated_path = os.path.join(accumulated_path, path_part)
            else:
                accumulated_path = path_part

            full_dir_path = os.path.join(current_dir, accumulated_path)
            if os.path.isdir(full_dir_path):
                hierarchy.append(self.get_yaml_from_path(accumulated_path, full_dir_path))

        return hierarchy

    def process_hierarchy(self):
        # Check if the target path exists before processing
        full_target_path = os.path.join(self.cwd, self.path)
        if not os.path.exists(full_target_path):
            raise FileNotFoundError(f"Path does not exist: {full_target_path}")

        merged_values: OrderedDict = OrderedDict()
        total_files_processed = 0

        for yaml_files in self.hierarchy:
            for yaml_file in yaml_files:
                yaml_content = self.yaml_get_content(yaml_file)
                self.merge_yamls(merged_values, yaml_content, self.type_strategies, self.fallback_strategies,
                                 self.type_conflict_strategies)
                self.resolve_simple_interpolations(merged_values, yaml_file)
                total_files_processed += 1

        if total_files_processed == 0:
            raise Exception("No YAML files found to process in the hierarchy")

        self.generated_data = merged_values

    def get_values_from_dir_path(self):
        values = {}
        full_path = pathlib2.Path(self.path)
        for path in full_path.parts:
            if '=' in path:
                split_value = path.split('=')
                values[split_value[0]] = split_value[1]
        return values

    def output_yaml_data(self, data):
        return yaml.dump(data, Dumper=ConfigGenerator.yaml_dumper(), default_flow_style=False, width=200,
                         sort_keys=False)

    def yaml_to_json(self, yaml_data):
        return json.dumps(yaml.load(yaml_data, Loader=yaml.SafeLoader), indent=4)

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
        self.generated_data = OrderedDict({key: self.generated_data[key] for key in keys if key in self.generated_data})

    def exclude_keys(self, keys):
        for key in keys:
            if key in self.generated_data:
                try:
                    logger.info("Excluding key %s", key)
                    del self.generated_data[key]
                except KeyError:
                    logger.info("Excluded key %s not found or already removed", key)

    def add_dynamic_data(self):
        if "remote_states" in self.generated_data:
            from .remote_state import S3TerraformRemoteStateRetriever
            remote_state_retriever = S3TerraformRemoteStateRetriever()
            state_files = self.generated_data["remote_states"]
            remote_states = remote_state_retriever.get_dynamic_data(state_files)
            self.merge_value(self.generated_data, remote_states, self.type_strategies, self.fallback_strategies,
                             self.type_conflict_strategies)

    def resolve_interpolations(self):
        resolver = InterpolationResolver()
        self.generated_data = resolver.resolve_interpolations(self.generated_data)

    def resolve_secrets(self, default_aws_profile):
        resolver = SecretResolver()
        self.generated_data = resolver.resolve_secrets(self.generated_data, default_aws_profile)

    def resolve_env(self):
        resolver = EnvVarResolver()
        self.generated_data = resolver.resolve_env_vars(self.generated_data)

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
