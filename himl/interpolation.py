# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import re

from .inject_secrets import SecretInjector
from .python_compat import iteritems, string_types, primitive_types


def is_interpolation(value):
    return isinstance(value, string_types) and '{{' in value and '}}' in value \
           and not is_escaped_interpolation(value)


def is_escaped_interpolation(value):
    return isinstance(value, string_types) and '{{`' in value and '`}}' in value


def is_fully_escaped_interpolation(value):
    return isinstance(value, string_types) and value.startswith('{{`') and value.endswith('`}}')


def is_full_interpolation(value):
    return is_interpolation(value) and value.startswith('{{') and value.endswith('}}') \
           and not is_fully_escaped_interpolation(value)


def remove_white_spaces(value):
    return re.sub(r"\s+", "", value)


def replace_parent_working_directory(value, cwd):
    if "{{cwd}}" in value:
        return value.replace("{{cwd}}", cwd)
    return value


class InterpolationResolver(object):

    def resolve_interpolations(self, data):
        # Resolve from dictionary. Do one iteration before secret resolving, in order to resolve interpolations such as
        # the aws.profile
        # Example:
        # my_profile: test
        # aws:
        #   profile: "{{my_profile}}"
        from_dict_injector = DictInterpolationResolver(data, FromDictInjector())
        from_dict_injector.resolve_interpolations(data)

        return data


class EscapingResolver(object):

    def resolve_escaping(self, data):
        """
        Should do one last check through all values to ensure the ones that were escaped are cleaned of the escape
        sequence
        """
        from_dict_injector = DictEscapingResolver(data, FromDictInjector())
        from_dict_injector.clean_escapes(data)

        return data


class SecretResolver(object):

    def resolve_secrets(self, data, default_aws_profile):
        # Resolve interpolations representing secrets
        # Example:
        # value1: "{{ssm.path(mysecret)}}"
        injector = SecretInjector(default_aws_profile)
        secrets_resolver = SecretsInterpolationResolver(injector)
        secrets_resolver.resolve_interpolations(data)

        return data


class DictIterator(object):

    def loop_all_items(self, data, process_func):
        if isinstance(data, string_types):
            return process_func(data)
        if isinstance(data, list):
            items = []
            for item in data:
                if isinstance(item, list):
                    items.extend(item)
                else:
                    items.append(self.loop_all_items(item, process_func))
            return items
        if isinstance(data, dict):
            for key in data:
                value = data[key]
                resolved_value = self.loop_all_items(value, process_func)
                data[key] = resolved_value
        return data


class AbstractEscapingResolver(DictIterator):

    def clean_escapes(self, data):
        return self.loop_all_items(data, self.clean_escape)

    def clean_escape(self, line):
        # Check if line is escaped
        if not is_escaped_interpolation(line):
            return line
        return self.do_clean_escapes(line)

    def do_clean_escapes(self, line):
        pass


class AbstractInterpolationResolver(DictIterator):

    def resolve_interpolations(self, data):
        return self.loop_all_items(data, self.resolve_interpolation)

    def resolve_interpolation(self, line):
        if not is_interpolation(line):
            return line
        if is_full_interpolation(line):
            line = remove_white_spaces(line)
        return self.do_resolve_interpolation(line)

    def do_resolve_interpolation(self, line):
        pass


class DictEscapingResolver(AbstractEscapingResolver):
    def __init__(self, data, from_dict_injector):
        AbstractEscapingResolver.__init__(self)
        self.data = data
        self.from_dict_injector = from_dict_injector
        self.full_blob_injector = FullBlobInjector()

    def do_clean_escapes(self, line):
        updated_line = self.from_dict_injector.resolve(line, self.data)
        return self.full_blob_injector.clean(updated_line)


class DictInterpolationResolver(AbstractInterpolationResolver):
    def __init__(self, data, from_dict_injector):
        AbstractInterpolationResolver.__init__(self)
        self.data = data
        self.from_dict_injector = from_dict_injector
        self.full_blob_injector = FullBlobInjector()

    def do_resolve_interpolation(self, line):
        updated_line = self.from_dict_injector.resolve(line, self.data)
        return self.full_blob_injector.resolve(updated_line, self.data)


class SecretsInterpolationResolver(AbstractInterpolationResolver):
    def __init__(self, secrets_injector):
        AbstractInterpolationResolver.__init__(self)
        self.secrets_injector = secrets_injector

    def do_resolve_interpolation(self, line):
        return self.secrets_injector.inject_secret(line)


class InterpolationValidator(DictIterator):

    def check_all_interpolations_resolved(self, data):
        return self.loop_all_items(data, self.validate_value)

    def validate_value(self, value):
        if is_interpolation(value):
            raise Exception("Interpolation could not be resolved {} and strict validation was enabled.".format(value))
        return value


class FromDictInjector(object):

    def __init__(self):
        self.results = {}

    def resolve(self, line, data):
        """
        :param line: {{env.name}}
        :param data: (env: name: dev)
        :return: dev
        """

        self.parse_leaves(data, "")
        for key, value in iteritems(self.results):
            placeholder = "{{" + key + "}}"
            if placeholder not in line:
                continue
            elif isinstance(value, (int, bool)):
                return value
            elif not is_interpolation(value):
                line = line.replace(placeholder, value)
        return line

    def parse_leaves(self, data, partial_key):
        if isinstance(data, primitive_types):
            self.results[partial_key] = data
            return
        if isinstance(data, dict):
            for key in data:
                value = data[key]
                new_key = partial_key
                if new_key:
                    new_key += "."
                new_key += key
                self.parse_leaves(value, new_key)


class FullBlobInjector(object):

    def resolve(self, line, data):
        if not is_full_interpolation(line):
            return line

        keys = self.get_keys_from_interpolation(line)
        resolved_value = self.get_inner_value(keys, data)
        is_valid_value = resolved_value is not None and not is_interpolation(resolved_value)

        return resolved_value if is_valid_value else line

    def clean(self, line):
        # {{` something {{ value }} `}}
        if is_fully_escaped_interpolation(line):
            resolved_value = self.get_value_from_escaping(line)
            is_valid_value = resolved_value is not None

            return resolved_value if is_valid_value else line

        # before {{` {{value}} `}} after
        elif is_escaped_interpolation(line):
            prefix = line[0:line.find('{{`')]
            escaping_string = line[line.find('{{`'):line.find('`}}') + 3]
            suffix = line[line.find('`}}') + 3:len(line)]
            resolved_value = prefix + self.get_value_from_escaping(escaping_string) + suffix
            is_valid_value = resolved_value is not None

            return resolved_value if is_valid_value else line

        # nothing to clean
        return line

    @staticmethod
    def get_inner_value(keys, data):
        for key in keys:
            if key in data:
                data = data[key]
            else:
                return None

        return data

    @staticmethod
    def get_keys_from_interpolation(line):
        # remove {{ and }}
        line = line[2:-2]

        return line.split('.')

    @staticmethod
    def get_value_from_escaping(line):
        # remove {{` and `}}
        line = line[3:-3]

        return line

