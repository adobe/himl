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
        """
        if not self.is_interpolation(line):
            return line

        # remove {{ and }}
        updated_line = line[2:-2]

        # check supported function to ensure the proper format is used
        if not self.is_env_interpolation(updated_line):
            return line

        # remove env( and ) to extract the env Variable
        updated_line = updated_line[4:-1]

        # If env variable is missing or not set, the output will be None
        return getenv(updated_line)

    def is_env_interpolation(self, value):
        return value.startswith('env(') and value.endswith(')')
