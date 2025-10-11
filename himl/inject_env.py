# Copyright 2021 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from os import getenv


class EnvVarInjector(object):
    """
    Resolve variables in the form:
    {{env(HOME)}}
    """

    def __init__(self):
        return

    def is_interpolation(self, value):
        return value.startswith('{{') and value.endswith('}}')

    def inject_env_var(self, line):
        """
        Check if value is an interpolation and try to resolve it.
        Handles both full interpolations and partial interpolations.
        """
        if not isinstance(line, str):
            return line

        # Handle full interpolations (entire string is an interpolation)
        if self.is_interpolation(line):
            # remove {{ and }}
            updated_line = line[2:-2]

            # check supported function to ensure the proper format is used
            if not self.is_env_interpolation(updated_line):
                return line

            # remove env( and ) to extract the env Variable
            updated_line = updated_line[4:-1]

            # If env variable is missing or not set, the output will be None
            return getenv(updated_line)

        # Handle partial interpolations (interpolations within a string)
        import re
        pattern = r'\{\{env\([^)]+\)\}\}'

        def replace_env_var(match):
            env_interpolation = match.group(0)
            # Extract the variable name from {{env(VAR_NAME)}}
            var_name = env_interpolation[6:-3]  # Remove {{env( and )}}
            if len(var_name.strip()) > 0:
                return getenv(var_name) or ''
            return env_interpolation

        return re.sub(pattern, replace_env_var, line)

    def is_env_interpolation(self, value):
        if not (value.startswith('env(') and value.endswith(')')):
            return False
        # Extract the variable name and check it's not empty
        var_name = value[4:-1]  # Remove 'env(' and ')'
        return len(var_name.strip()) > 0
