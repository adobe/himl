# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pytest
import sys
from unittest.mock import patch, MagicMock

from himl.secret_resolvers import (
    SecretResolver, SSMSecretResolver, S3SecretResolver,
    VaultSecretResolver, SopsSecretResolver, AggregatedSecretResolver
)


class TestSecretResolver:
    """Test base SecretResolver class"""

    def test_get_param_or_exception_success(self):
        """Test successful parameter retrieval"""
        resolver = SecretResolver()
        params = {'key': 'value', 'number': 42}

        assert resolver.get_param_or_exception('key', params) == 'value'
        assert resolver.get_param_or_exception('number', params) == 42

    def test_get_param_or_exception_missing(self):
        """Test exception when parameter is missing"""
        resolver = SecretResolver()
        params = {'key': 'value'}

        with pytest.raises(Exception) as exc_info:
            resolver.get_param_or_exception('missing_key', params)

        assert "Could not find required key" in str(exc_info.value)
        assert "missing_key" in str(exc_info.value)

    def test_supports_not_implemented(self):
        """Test that supports method raises NotImplementedError"""
        resolver = SecretResolver()

        with pytest.raises(NotImplementedError):
            resolver.supports('any_type')

    def test_resolve_not_implemented(self):
        """Test that resolve method raises NotImplementedError"""
        resolver = SecretResolver()

        with pytest.raises(NotImplementedError):
            resolver.resolve('any_type', {})


class TestSSMSecretResolver:
    """Test SSMSecretResolver class"""

    def test_supports_with_boto3(self):
        """Test supports method when boto3 is available"""
        with patch.dict(sys.modules, {'boto3': MagicMock()}):
            resolver = SSMSecretResolver()
            assert resolver.supports('ssm') is True
            assert resolver.supports('s3') is False

    def test_supports_without_boto3(self):
        """Test supports method when boto3 is not available"""
        with patch.dict(sys.modules, {}, clear=True):
            resolver = SSMSecretResolver()
            assert resolver.supports('ssm') is False

    @patch('himl.simplessm.SimpleSSM')
    def test_resolve_success(self, mock_simple_ssm):
        """Test successful SSM secret resolution"""
        # Setup mocks
        mock_ssm_instance = MagicMock()
        mock_ssm_instance.get.return_value = 'secret_value'
        mock_simple_ssm.return_value = mock_ssm_instance

        resolver = SSMSecretResolver(default_aws_profile='default')
        secret_params = {
            'path': '/my/secret/path',
            'aws_profile': 'test-profile',
            'region_name': 'us-west-2'
        }

        result = resolver.resolve('ssm', secret_params)

        assert result == 'secret_value'
        mock_simple_ssm.assert_called_once_with('test-profile', 'us-west-2')
        mock_ssm_instance.get.assert_called_once_with('/my/secret/path')

    @patch('himl.simplessm.SimpleSSM')
    def test_resolve_with_default_profile(self, mock_simple_ssm):
        """Test SSM resolution with default profile"""
        mock_ssm_instance = MagicMock()
        mock_ssm_instance.get.return_value = 'secret_value'
        mock_simple_ssm.return_value = mock_ssm_instance

        resolver = SSMSecretResolver(default_aws_profile='default-profile')
        secret_params = {'path': '/my/secret/path'}

        result = resolver.resolve('ssm', secret_params)

        assert result == 'secret_value'
        mock_simple_ssm.assert_called_once_with('default-profile', 'us-east-1')

    def test_resolve_missing_profile(self):
        """Test SSM resolution without AWS profile"""
        resolver = SSMSecretResolver()
        secret_params = {'path': '/my/secret/path'}

        with pytest.raises(Exception) as exc_info:
            resolver.resolve('ssm', secret_params)

        assert "Could not find the aws_profile" in str(exc_info.value)

    def test_resolve_missing_path(self):
        """Test SSM resolution without path"""
        resolver = SSMSecretResolver(default_aws_profile='default')
        secret_params = {'aws_profile': 'test-profile'}

        with pytest.raises(Exception) as exc_info:
            resolver.resolve('ssm', secret_params)

        assert "Could not find required key" in str(exc_info.value)


class TestS3SecretResolver:
    """Test S3SecretResolver class"""

    def test_supports_with_boto3(self):
        """Test supports method when boto3 is available"""
        with patch.dict(sys.modules, {'boto3': MagicMock()}):
            resolver = S3SecretResolver()
            assert resolver.supports('s3') is True
            assert resolver.supports('ssm') is False

    @patch('himl.simples3.SimpleS3')
    def test_resolve_success(self, mock_simple_s3):
        """Test successful S3 secret resolution"""
        mock_s3_instance = MagicMock()
        mock_s3_instance.get.return_value = 'file_content'
        mock_simple_s3.return_value = mock_s3_instance

        resolver = S3SecretResolver(default_aws_profile='default')
        secret_params = {
            'bucket': 'my-bucket',
            'path': 'path/to/file.txt',
            'aws_profile': 'test-profile',
            'region_name': 'us-west-2',
            'base64encode': 'false'
        }

        result = resolver.resolve('s3', secret_params)

        assert result == 'file_content'
        mock_simple_s3.assert_called_once_with('test-profile', 'us-west-2')
        mock_s3_instance.get.assert_called_once_with('my-bucket', 'path/to/file.txt', False)

    @patch('himl.simples3.SimpleS3')
    def test_resolve_with_base64_encoding(self, mock_simple_s3):
        """Test S3 resolution with base64 encoding"""
        mock_s3_instance = MagicMock()
        mock_s3_instance.get.return_value = 'encoded_content'
        mock_simple_s3.return_value = mock_s3_instance

        resolver = S3SecretResolver(default_aws_profile='default')
        secret_params = {
            'bucket': 'my-bucket',
            'path': 'path/to/file.txt',
            'aws_profile': 'test-profile',
            'base64encode': 'true'
        }

        result = resolver.resolve('s3', secret_params)

        assert result == 'encoded_content'
        mock_s3_instance.get.assert_called_once_with('my-bucket', 'path/to/file.txt', True)

    def test_resolve_missing_bucket(self):
        """Test S3 resolution without bucket"""
        resolver = S3SecretResolver(default_aws_profile='default')
        secret_params = {'path': 'path/to/file.txt', 'aws_profile': 'test-profile'}

        with pytest.raises(Exception) as exc_info:
            resolver.resolve('s3', secret_params)

        assert "Could not find required key" in str(exc_info.value)


class TestVaultSecretResolver:
    """Test VaultSecretResolver class"""

    def test_supports_with_hvac(self):
        """Test supports method when hvac is available"""
        with patch.dict(sys.modules, {'hvac': MagicMock()}):
            resolver = VaultSecretResolver()
            assert resolver.supports('vault') is True
            assert resolver.supports('ssm') is False

    @patch('himl.simplevault.SimpleVault')
    def test_resolve_token_policy(self, mock_simple_vault):
        """Test Vault token policy resolution"""
        mock_vault_instance = MagicMock()
        mock_vault_instance.get_token.return_value = 'vault_token'
        mock_simple_vault.return_value = mock_vault_instance

        resolver = VaultSecretResolver()
        secret_params = {'token_policy': 'my_policy'}

        result = resolver.resolve('vault', secret_params)

        assert result == 'vault_token'
        mock_vault_instance.get_token.assert_called_once_with('my_policy')

    @patch('himl.simplevault.SimpleVault')
    def test_resolve_path(self, mock_simple_vault):
        """Test Vault path resolution"""
        mock_vault_instance = MagicMock()
        mock_vault_instance.get_path.return_value = {'key': 'value'}
        mock_simple_vault.return_value = mock_vault_instance

        resolver = VaultSecretResolver()
        secret_params = {'path': '/secret/path'}

        result = resolver.resolve('vault', secret_params)

        assert result == {'key': 'value'}
        mock_vault_instance.get_path.assert_called_once_with('/secret/path')

    @patch('himl.simplevault.SimpleVault')
    def test_resolve_key(self, mock_simple_vault):
        """Test Vault key resolution"""
        mock_vault_instance = MagicMock()
        mock_vault_instance.get_key.return_value = 'secret_value'
        mock_simple_vault.return_value = mock_vault_instance

        resolver = VaultSecretResolver()
        secret_params = {'key': '/secret/path/key_name'}

        result = resolver.resolve('vault', secret_params)

        assert result == 'secret_value'
        mock_vault_instance.get_key.assert_called_once_with('/secret/path', 'key_name')


class TestSopsSecretResolver:
    """Test SopsSecretResolver class"""

    def test_supports(self):
        """Test supports method"""
        resolver = SopsSecretResolver()
        assert resolver.supports('sops') is True
        assert resolver.supports('vault') is False

    @patch('himl.simplesops.SimpleSops')
    def test_resolve_success(self, mock_simple_sops):
        """Test successful SOPS secret resolution"""
        mock_sops_instance = MagicMock()
        mock_sops_instance.get.return_value = 'decrypted_value'
        mock_simple_sops.return_value = mock_sops_instance

        resolver = SopsSecretResolver()
        secret_params = {
            'secret_file': '/path/to/secrets.yaml',
            'secret_key': 'my_key'
        }

        result = resolver.resolve('sops', secret_params)

        assert result == 'decrypted_value'
        mock_sops_instance.get.assert_called_once_with(
            secret_file='/path/to/secrets.yaml',
            secret_key='my_key'
        )

    def test_resolve_missing_file(self):
        """Test SOPS resolution without secret file"""
        resolver = SopsSecretResolver()
        secret_params = {'secret_key': 'my_key'}

        with pytest.raises(Exception) as exc_info:
            resolver.resolve('sops', secret_params)

        assert "Could not find required key" in str(exc_info.value)


class TestAggregatedSecretResolver:
    """Test AggregatedSecretResolver class"""

    def test_initialization(self):
        """Test AggregatedSecretResolver initialization"""
        resolver = AggregatedSecretResolver(default_aws_profile='test-profile')
        assert len(resolver.secret_resolvers) == 4
        assert any(isinstance(r, SSMSecretResolver) for r in resolver.secret_resolvers)
        assert any(isinstance(r, S3SecretResolver) for r in resolver.secret_resolvers)
        assert any(isinstance(r, VaultSecretResolver) for r in resolver.secret_resolvers)
        assert any(isinstance(r, SopsSecretResolver) for r in resolver.secret_resolvers)

    def test_supports_delegated(self):
        """Test that supports method delegates to individual resolvers"""
        with patch.dict(sys.modules, {'boto3': MagicMock(), 'hvac': MagicMock()}):
            resolver = AggregatedSecretResolver()
            assert resolver.supports('ssm') is True
            assert resolver.supports('s3') is True
            assert resolver.supports('vault') is True
            assert resolver.supports('sops') is True
            assert resolver.supports('unknown') is False

    @patch('himl.simplessm.SimpleSSM')
    def test_resolve_delegated(self, mock_simple_ssm):
        """Test that resolve method delegates to appropriate resolver"""
        mock_ssm_instance = MagicMock()
        mock_ssm_instance.get.return_value = 'secret_value'
        mock_simple_ssm.return_value = mock_ssm_instance

        with patch.dict(sys.modules, {'boto3': MagicMock()}):
            resolver = AggregatedSecretResolver(default_aws_profile='default')
            secret_params = {'path': '/my/secret', 'aws_profile': 'test'}

            result = resolver.resolve('ssm', secret_params)

            assert result == 'secret_value'

    def test_resolve_unsupported_type(self):
        """Test resolve with unsupported secret type"""
        resolver = AggregatedSecretResolver()

        with pytest.raises(Exception) as exc_info:
            resolver.resolve('unsupported_type', {})

        assert "Could not resolve secret type" in str(exc_info.value)
        assert "unsupported_type" in str(exc_info.value)
