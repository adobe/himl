# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import re
from functools import lru_cache

from .inject_env import EnvVarInjector
from .inject_secrets import SecretInjector
from .python_compat import iteritems, string_types, primitive_types

# Pre-compile regex patterns for performance
_INTERPOLATION_PATTERN = re.compile(r'\{\{[^`].*?[^`]\}\}')
_ESCAPED_PATTERN = re.compile(r'\{\{`.*?`\}\}')
_FULL_INTERPOLATION_PATTERN = re.compile(r'^\{\{[^`].*?[^`]\}\}$')
_FULLY_ESCAPED_PATTERN = re.compile(r'^\{\{`.*?`\}\}$')


# Cached internal functions that only handle strings
@lru_cache(maxsize=10000)
def _is_interpolation_cached(value):
    """Internal cached function - only for strings"""
    return bool(_INTERPOLATION_PATTERN.search(value)) and not bool(_ESCAPED_PATTERN.search(value))


@lru_cache(maxsize=10000)
def _is_escaped_interpolation_cached(value):
    """Internal cached function - only for strings"""
    return bool(_ESCAPED_PATTERN.search(value))


@lru_cache(maxsize=10000)
def _is_fully_escaped_interpolation_cached(value):
    """Internal cached function - only for strings"""
    return bool(_FULLY_ESCAPED_PATTERN.match(value))


@lru_cache(maxsize=10000)
def _is_full_interpolation_cached(value):
    """Internal cached function - only for strings"""
    return bool(_FULL_INTERPOLATION_PATTERN.match(value)) and not _is_fully_escaped_interpolation_cached(value)


# Public functions with type safety
def is_interpolation(value):
    """Optimized interpolation detection with regex and caching"""
    if not isinstance(value, string_types):
        return False
    return _is_interpolation_cached(value)


def is_escaped_interpolation(value):
    """Optimized escaped interpolation detection with regex and caching"""
    if not isinstance(value, string_types):
        return False
    return _is_escaped_interpolation_cached(value)


def is_fully_escaped_interpolation(value):
    """Optimized fully escaped interpolation detection with regex and caching"""
    if not isinstance(value, string_types):
        return False
    return _is_fully_escaped_interpolation_cached(value)


def is_full_interpolation(value):
    """Optimized full interpolation detection with regex and caching"""
    if not isinstance(value, string_types):
        return False
    return _is_full_interpolation_cached(value)


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


class EnvVarResolver(object):
    def resolve_env_vars(self, data):
        injector = EnvVarInjector()
        env_resolver = EnvVarInterpolationsResolver(injector)
        env_resolver.resolve_interpolations(data)
        return data


class DictIterator(object):

    def loop_all_items(self, data, process_func):
        if isinstance(data, string_types):
            return process_func(data)
        if isinstance(data, list):
            items = []
            for item in data:
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


class EnvVarInterpolationsResolver(AbstractInterpolationResolver):
    def __init__(self, env_vars_injector):
        AbstractInterpolationResolver.__init__(self)
        self.env_vars_injector = env_vars_injector

    def do_resolve_interpolation(self, line):
        return self.env_vars_injector.inject_env_var(line)


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
        # Cache for parsed data structures to avoid redundant parsing
        self._parse_cache = {}

    def resolve(self, line, data):
        """
        :param line: {{env.name}}
        :param data: (env: name: dev)
        :return: dev
        """

        # Use cached results if available, otherwise parse and cache
        data_id = id(data)
        if data_id not in self._parse_cache:
            self._parse_cache[data_id] = {}
            self._parse_leaves_cached(data, "", self._parse_cache[data_id])
        
        # Use cached results instead of rebuilding
        cached_results = self._parse_cache[data_id]
        
        for key, value in iteritems(cached_results):
            placeholder = "{{" + key + "}}"
            if placeholder not in line:
                continue
            elif isinstance(value, (int, bool)):
                return value
            elif not is_interpolation(value):
                line = line.replace(placeholder, value)
        return line

    def _parse_leaves_cached(self, data, partial_key, cache_dict):
        """Optimized version that populates cache dictionary directly"""
        if isinstance(data, primitive_types):
            cache_dict[partial_key] = data
            return
        if isinstance(data, dict):
            for key in data:
                value = data[key]
                new_key = partial_key
                if new_key:
                    new_key += "."
                new_key += key
                self._parse_leaves_cached(value, new_key, cache_dict)

    def parse_leaves(self, data, partial_key):
        """Legacy method maintained for compatibility"""
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
