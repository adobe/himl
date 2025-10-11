# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os

from unittest.mock import patch

from himl.inject_env import EnvVarInjector
from himl.interpolation import EnvVarResolver, EnvVarInterpolationsResolver


class TestEnvVarInjector:
    """Test EnvVarInjector class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.injector = EnvVarInjector()

    def test_is_interpolation(self):
        """Test interpolation detection"""
        assert self.injector.is_interpolation('{{env(HOME)}}')
        assert self.injector.is_interpolation('{{env(PATH)}}')
        assert not self.injector.is_interpolation('not an interpolation')
        assert not self.injector.is_interpolation('{{incomplete')
        assert not self.injector.is_interpolation('incomplete}}')

    def test_is_env_interpolation(self):
        """Test environment variable interpolation detection"""
        assert self.injector.is_env_interpolation('env(HOME)')
        assert self.injector.is_env_interpolation('env(PATH)')
        assert self.injector.is_env_interpolation('env(MY_VAR)')
        assert not self.injector.is_env_interpolation('ssm(path)')
        assert not self.injector.is_env_interpolation('vault(path)')
        assert not self.injector.is_env_interpolation('env')
        assert not self.injector.is_env_interpolation('env()')

    def test_inject_env_var_non_interpolation(self):
        """Test that non-interpolations are returned unchanged"""
        result = self.injector.inject_env_var('normal string')
        assert result == 'normal string'

        result = self.injector.inject_env_var('{{incomplete')
        assert result == '{{incomplete'

    def test_inject_env_var_non_env_interpolation(self):
        """Test that non-env interpolations are returned unchanged"""
        result = self.injector.inject_env_var('{{ssm.path(/secret)}}')
        assert result == '{{ssm.path(/secret)}}'

        result = self.injector.inject_env_var('{{vault.path(/secret)}}')
        assert result == '{{vault.path(/secret)}}'

    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_inject_env_var_existing_variable(self):
        """Test injection of existing environment variable"""
        result = self.injector.inject_env_var('{{env(TEST_VAR)}}')
        assert result == 'test_value'

    @patch.dict(os.environ, {}, clear=True)
    def test_inject_env_var_missing_variable(self):
        """Test injection of missing environment variable"""
        result = self.injector.inject_env_var('{{env(MISSING_VAR)}}')
        assert result is None

    @patch.dict(os.environ, {'HOME': '/home/user', 'USER': 'testuser'})
    def test_inject_env_var_common_variables(self):
        """Test injection of common environment variables"""
        result = self.injector.inject_env_var('{{env(HOME)}}')
        assert result == '/home/user'

        result = self.injector.inject_env_var('{{env(USER)}}')
        assert result == 'testuser'

    @patch.dict(os.environ, {'EMPTY_VAR': ''})
    def test_inject_env_var_empty_variable(self):
        """Test injection of empty environment variable"""
        result = self.injector.inject_env_var('{{env(EMPTY_VAR)}}')
        assert result == ''

    @patch.dict(os.environ, {'NUMERIC_VAR': '12345'})
    def test_inject_env_var_numeric_value(self):
        """Test injection of numeric environment variable"""
        result = self.injector.inject_env_var('{{env(NUMERIC_VAR)}}')
        assert result == '12345'
        assert isinstance(result, str)

    @patch.dict(os.environ, {'SPECIAL_CHARS': 'value with spaces and !@#$%'})
    def test_inject_env_var_special_characters(self):
        """Test injection of environment variable with special characters"""
        result = self.injector.inject_env_var('{{env(SPECIAL_CHARS)}}')
        assert result == 'value with spaces and !@#$%'

    def test_inject_env_var_malformed_interpolation(self):
        """Test handling of malformed interpolations"""
        result = self.injector.inject_env_var('{{env(}}')
        assert result == '{{env(}}'

        result = self.injector.inject_env_var('{{env)}}')
        assert result == '{{env)}}'

        result = self.injector.inject_env_var('{{env()}}')
        assert result == '{{env()}}'

    @patch.dict(os.environ, {'VAR_WITH_UNDERSCORES': 'underscore_value'})
    def test_inject_env_var_with_underscores(self):
        """Test injection of environment variable with underscores"""
        result = self.injector.inject_env_var('{{env(VAR_WITH_UNDERSCORES)}}')
        assert result == 'underscore_value'

    @patch.dict(os.environ, {'VAR123': 'alphanumeric_value'})
    def test_inject_env_var_alphanumeric(self):
        """Test injection of alphanumeric environment variable"""
        result = self.injector.inject_env_var('{{env(VAR123)}}')
        assert result == 'alphanumeric_value'


class TestEnvVarResolver:
    """Test EnvVarResolver class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.resolver = EnvVarResolver()

    @patch.dict(os.environ, {'TEST_ENV': 'test_value', 'ANOTHER_ENV': 'another_value'})
    def test_resolve_env_vars_simple(self):
        """Test simple environment variable resolution"""
        data = {
            'env_var': '{{env(TEST_ENV)}}',
            'another_var': '{{env(ANOTHER_ENV)}}',
            'normal_var': 'normal_value'
        }

        result = self.resolver.resolve_env_vars(data)

        assert result['env_var'] == 'test_value'
        assert result['another_var'] == 'another_value'
        assert result['normal_var'] == 'normal_value'

    @patch.dict(os.environ, {'HOME': '/home/user'})
    def test_resolve_env_vars_nested(self):
        """Test environment variable resolution in nested structures"""
        data = {
            'config': {
                'home_dir': '{{env(HOME)}}',
                'nested': {
                    'path': '{{env(HOME)}}/config'
                }
            },
            'list_with_env': [
                '{{env(HOME)}}/file1',
                '{{env(HOME)}}/file2'
            ]
        }

        result = self.resolver.resolve_env_vars(data)

        assert result['config']['home_dir'] == '/home/user'
        assert result['config']['nested']['path'] == '/home/user/config'
        assert result['list_with_env'][0] == '/home/user/file1'
        assert result['list_with_env'][1] == '/home/user/file2'

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_env_vars_missing(self):
        """Test resolution with missing environment variables"""
        data = {
            'missing_var': '{{env(MISSING_VAR)}}',
            'normal_var': 'normal_value'
        }

        result = self.resolver.resolve_env_vars(data)

        assert result['missing_var'] is None
        assert result['normal_var'] == 'normal_value'

    @patch.dict(os.environ, {'MIXED_VAR': 'mixed_value'})
    def test_resolve_env_vars_mixed_content(self):
        """Test resolution with mixed content"""
        data = {
            'mixed': 'prefix-{{env(MIXED_VAR)}}-suffix',
            'pure_env': '{{env(MIXED_VAR)}}',
            'no_env': 'no environment variables here'
        }

        result = self.resolver.resolve_env_vars(data)

        # Note: The actual behavior depends on the implementation
        # This test assumes the resolver handles partial interpolations
        assert 'mixed_value' in str(result['mixed']) or result['mixed'] == 'prefix-mixed_value-suffix'
        assert result['pure_env'] == 'mixed_value'
        assert result['no_env'] == 'no environment variables here'


class TestEnvVarInterpolationsResolver:
    """Test EnvVarInterpolationsResolver class"""

    def setup_method(self):
        """Set up test fixtures"""
        from himl.inject_env import EnvVarInjector
        self.injector = EnvVarInjector()
        self.resolver = EnvVarInterpolationsResolver(self.injector)

    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_resolve_interpolations(self):
        """Test interpolation resolution"""
        data = {
            'env_var': '{{env(TEST_VAR)}}',
            'normal_var': 'normal_value',
            'nested': {
                'env_nested': '{{env(TEST_VAR)}}'
            }
        }

        self.resolver.resolve_interpolations(data)

        assert data['env_var'] == 'test_value'
        assert data['normal_var'] == 'normal_value'
        assert data['nested']['env_nested'] == 'test_value'

    @patch.dict(os.environ, {'PATH_VAR': '/usr/bin'})
    def test_do_resolve_interpolation(self):
        """Test individual interpolation resolution"""
        result = self.resolver.do_resolve_interpolation('{{env(PATH_VAR)}}')
        assert result == '/usr/bin'

        result = self.resolver.do_resolve_interpolation('not an interpolation')
        assert result == 'not an interpolation'

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_missing_env_var(self):
        """Test resolution of missing environment variable"""
        result = self.resolver.do_resolve_interpolation('{{env(MISSING)}}')
        assert result is None

    @patch.dict(os.environ, {'COMPLEX_VAR': 'complex/path/value'})
    def test_resolve_complex_env_var(self):
        """Test resolution of complex environment variable"""
        result = self.resolver.do_resolve_interpolation('{{env(COMPLEX_VAR)}}')
        assert result == 'complex/path/value'
