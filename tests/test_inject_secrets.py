# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pytest
from unittest.mock import patch

from himl.inject_secrets import SecretInjector


class TestSecretInjector:
    """Test SecretInjector class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.injector = SecretInjector(default_aws_profile='test-profile')

    def test_is_interpolation(self):
        """Test interpolation detection"""
        assert self.injector.is_interpolation('{{ssm.path(/my/secret)}}')
        assert self.injector.is_interpolation('{{vault.path(/secret)}}')
        assert not self.injector.is_interpolation('not an interpolation')
        assert not self.injector.is_interpolation('{{incomplete')
        assert not self.injector.is_interpolation('incomplete}}')

    def test_split_dot_not_within_parentheses(self):
        """Test splitting on dots outside parentheses"""
        # Test simple case
        result = self.injector.split_dot_not_within_parentheses('ssm.path(/my/secret)')
        assert result == ['ssm', 'path(/my/secret)']

        # Test complex case with multiple parameters
        result = self.injector.split_dot_not_within_parentheses('ssm.path(/my/secret).aws_profile(test)')
        assert result == ['ssm', 'path(/my/secret)', 'aws_profile(test)']

        # Test with dots inside parentheses (should not split)
        result = self.injector.split_dot_not_within_parentheses('ssm.path(/my.secret.path)')
        assert result == ['ssm', 'path(/my.secret.path)']

    def test_inject_secret_non_interpolation(self):
        """Test that non-interpolations are returned unchanged"""
        result = self.injector.inject_secret('normal string')
        assert result == 'normal string'

        result = self.injector.inject_secret('{{incomplete')
        assert result == '{{incomplete'

    @patch.object(SecretInjector, 'split_dot_not_within_parentheses')
    def test_inject_secret_insufficient_parts(self, mock_split):
        """Test handling of insufficient parts after splitting"""
        mock_split.return_value = ['ssm']  # Only one part

        result = self.injector.inject_secret('{{ssm}}')
        assert result == '{{ssm}}'

    def test_inject_secret_ssm_format(self):
        """Test SSM secret format parsing"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='secret_value'):

            result = self.injector.inject_secret('{{ssm.path(/my/secret).aws_profile(test)}}')

            assert result == 'secret_value'
            self.injector.resolver.resolve.assert_called_once_with(
                'ssm',
                {
                    'ssm': None,
                    'path': '/my/secret',
                    'aws_profile': 'test'
                }
            )

    def test_inject_secret_vault_format(self):
        """Test Vault secret format parsing"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value={'key': 'value'}):

            result = self.injector.inject_secret('{{vault.path(/secret/path)}}')

            assert result == {'key': 'value'}
            self.injector.resolver.resolve.assert_called_once_with(
                'vault',
                {
                    'vault': None,
                    'path': '/secret/path'
                }
            )

    def test_inject_secret_s3_format(self):
        """Test S3 secret format parsing"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='file_content'):

            result = self.injector.inject_secret('{{s3.bucket(my-bucket).path(file.txt).base64encode(true)}}')

            assert result == 'file_content'
            self.injector.resolver.resolve.assert_called_once_with(
                's3',
                {
                    's3': None,
                    'bucket': 'my-bucket',
                    'path': 'file.txt',
                    'base64encode': 'true'
                }
            )

    def test_inject_secret_sops_format(self):
        """Test SOPS secret format parsing"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='decrypted_value'):

            result = self.injector.inject_secret('{{sops.secret_file(/path/to/secrets.yaml).secret_key(my_key)}}')

            assert result == 'decrypted_value'
            self.injector.resolver.resolve.assert_called_once_with(
                'sops',
                {
                    'sops': None,
                    'secret_file': '/path/to/secrets.yaml',
                    'secret_key': 'my_key'
                }
            )

    def test_inject_secret_unsupported_type(self):
        """Test handling of unsupported secret types"""
        with patch.object(self.injector.resolver, 'supports', return_value=False):

            result = self.injector.inject_secret('{{unsupported.path(/secret)}}')

            assert result == '{{unsupported.path(/secret)}}'

    def test_inject_secret_parameter_without_parentheses(self):
        """Test parsing parameters without parentheses"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='secret_value'):

            result = self.injector.inject_secret('{{ssm.path(/my/secret).decrypt}}')

            assert result == 'secret_value'
            self.injector.resolver.resolve.assert_called_once_with(
                'ssm',
                {
                    'ssm': None,
                    'path': '/my/secret',
                    'decrypt': None
                }
            )

    def test_inject_secret_caching(self):
        """Test that secret injection uses caching"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='secret_value') as mock_resolve:

            # Call the same secret twice
            secret_interpolation = '{{ssm.path(/my/secret)}}'
            result1 = self.injector.inject_secret(secret_interpolation)
            result2 = self.injector.inject_secret(secret_interpolation)

            assert result1 == 'secret_value'
            assert result2 == 'secret_value'

            # Due to LRU cache, resolve should only be called once
            assert mock_resolve.call_count == 1

    def test_inject_secret_complex_path(self):
        """Test injection with complex paths containing special characters"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='secret_value'):

            result = self.injector.inject_secret('{{ssm.path(/app/env-prod/db.password)}}')

            assert result == 'secret_value'
            self.injector.resolver.resolve.assert_called_once_with(
                'ssm',
                {
                    'ssm': None,
                    'path': '/app/env-prod/db.password'
                }
            )

    def test_inject_secret_multiple_parameters(self):
        """Test injection with multiple parameters"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', return_value='secret_value'):

            result = self.injector.inject_secret(
                '{{ssm.path(/my/secret).aws_profile(prod).region_name(us-west-2)}}'
            )

            assert result == 'secret_value'
            self.injector.resolver.resolve.assert_called_once_with(
                'ssm',
                {
                    'ssm': None,
                    'path': '/my/secret',
                    'aws_profile': 'prod',
                    'region_name': 'us-west-2'
                }
            )

    def test_inject_secret_resolver_exception(self):
        """Test handling of resolver exceptions"""
        with patch.object(self.injector.resolver, 'supports', return_value=True), \
             patch.object(self.injector.resolver, 'resolve', side_effect=Exception('Resolver error')):

            with pytest.raises(Exception) as exc_info:
                self.injector.inject_secret('{{ssm.path(/my/secret)}}')

            assert 'Resolver error' in str(exc_info.value)

    def test_inject_secret_empty_interpolation(self):
        """Test handling of empty interpolation"""
        result = self.injector.inject_secret('{{}}')
        assert result == '{{}}'  # Should remain unchanged

    def test_inject_secret_malformed_interpolation(self):
        """Test handling of malformed interpolations"""
        result = self.injector.inject_secret('{{ssm.path(}}')
        assert result == '{{ssm.path(}}'  # Should remain unchanged due to malformed parentheses
