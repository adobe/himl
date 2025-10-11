# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import pytest

from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from himl.simples3 import SimpleS3
from himl.simplessm import SimpleSSM
from himl.simplesops import SimpleSops, Sops, SopsError
from himl.simplevault import SimpleVault


class TestSimpleS3:
    """Test SimpleS3 class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.s3 = SimpleS3('test-profile', 'us-east-1')

    @patch('boto3.session.Session')
    def test_get_success(self, mock_session):
        """Test successful S3 object retrieval"""
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        mock_client.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=b'file content'))
        }

        result = self.s3.get('my-bucket', 'path/to/file.txt')

        assert result == b'file content'
        mock_session.assert_called_once_with(profile_name='test-profile')
        mock_client.get_object.assert_called_once_with(Bucket='my-bucket', Key='path/to/file.txt')

    @patch('boto3.session.Session')
    def test_get_with_base64_encoding(self, mock_session):
        """Test S3 retrieval with base64 encoding"""
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        mock_client.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=b'binary content'))
        }

        result = self.s3.get('my-bucket', 'path/to/file.bin', base64Encode=True)

        # Should return base64 encoded string
        import base64
        expected = base64.b64encode(b'binary content').decode('utf-8')
        assert result == expected

    @patch('boto3.session.Session')
    def test_get_client_error(self, mock_session):
        """Test S3 client error handling"""
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        mock_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'GetObject'
        )

        with pytest.raises(Exception) as exc_info:
            self.s3.get('my-bucket', 'nonexistent/file.txt')

        assert 'Error while trying to read S3 value' in str(exc_info.value)
        assert 'NoSuchKey' in str(exc_info.value)

    def test_parse_data_no_encoding(self):
        """Test parse_data without encoding"""
        result = self.s3.parse_data(b'test content', False)
        assert result == b'test content'

    def test_parse_data_with_base64(self):
        """Test parse_data with base64 encoding"""
        import base64
        test_data = b'test content'
        result = self.s3.parse_data(test_data, True)
        expected = base64.b64encode(test_data).decode('utf-8')
        assert result == expected


class TestSimpleSSM:
    """Test SimpleSSM class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.ssm = SimpleSSM('test-profile', 'us-east-1')

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    def test_get_success(self, mock_boto_client):
        """Test successful SSM parameter retrieval"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        mock_client.get_parameter.return_value = {
            'Parameter': {'Value': 'secret_value'}
        }

        result = self.ssm.get('/my/secret/key')

        assert result == 'secret_value'
        mock_boto_client.assert_called_once_with('ssm', region_name='us-east-1')
        mock_client.get_parameter.assert_called_once_with(Name='/my/secret/key', WithDecryption=True)

    @patch.dict(os.environ, {'AWS_PROFILE': 'original-profile'})
    @patch('boto3.client')
    def test_get_preserves_original_profile(self, mock_boto_client):
        """Test that original AWS profile is preserved"""
        # Create SSM instance after environment is patched
        ssm = SimpleSSM('test-profile', 'us-east-1')

        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        mock_client.get_parameter.return_value = {
            'Parameter': {'Value': 'secret_value'}
        }

        ssm.get('/my/secret/key')

        # Original profile should be restored
        assert os.environ.get('AWS_PROFILE') == 'original-profile'

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    def test_get_removes_profile_when_none_initially(self, mock_boto_client):
        """Test that AWS_PROFILE is removed when none was set initially"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        mock_client.get_parameter.return_value = {
            'Parameter': {'Value': 'secret_value'}
        }

        self.ssm.get('/my/secret/key')

        # AWS_PROFILE should not be in environment
        assert 'AWS_PROFILE' not in os.environ

    @patch('boto3.client')
    def test_get_client_error(self, mock_boto_client):
        """Test SSM client error handling"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        mock_client.get_parameter.side_effect = ClientError(
            {'Error': {'Code': 'ParameterNotFound'}},
            'GetParameter'
        )

        with pytest.raises(Exception) as exc_info:
            self.ssm.get('/nonexistent/parameter')

        assert 'Error while trying to read SSM value' in str(exc_info.value)
        assert 'ParameterNotFound' in str(exc_info.value)


class TestSimpleSops:
    """Test SimpleSops class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sops = SimpleSops()

    @patch.object(Sops, 'get_keys')
    def test_get_success(self, mock_get_keys):
        """Test successful SOPS secret retrieval"""
        mock_get_keys.return_value = 'decrypted_value'

        result = self.sops.get('/path/to/secrets.yaml', 'my_key')

        assert result == 'decrypted_value'
        mock_get_keys.assert_called_once_with(secret_file='/path/to/secrets.yaml', secret_key='my_key')

    @patch.object(Sops, 'get_keys')
    def test_get_sops_error(self, mock_get_keys):
        """Test SOPS error handling"""
        mock_get_keys.side_effect = SopsError('/path/to/secrets.yaml', 1, 'Decryption failed', True)

        with pytest.raises(Exception) as exc_info:
            self.sops.get('/path/to/secrets.yaml', 'my_key')

        assert 'Error while trying to read sops value' in str(exc_info.value)


class TestSops:
    """Test Sops utility class"""

    @patch('himl.simplesops.Popen')
    def test_decrypt_success(self, mock_popen):
        """Test successful SOPS decryption"""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'decrypted: content\n', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = Sops.decrypt('/path/to/encrypted.yaml')

        assert result == {'decrypted': 'content'}
        mock_popen.assert_called_once()

    def test_get_keys_simple(self):
        """Test get_keys with simple key"""
        sops = Sops()
        test_data = {'key1': 'value1', 'key2': 'value2'}

        with patch.object(Sops, 'decrypt', return_value=test_data):
            result = sops.get_keys('/path/to/file.yaml', 'key1')
            assert result == 'value1'

    def test_get_keys_nested(self):
        """Test get_keys with nested key"""
        sops = Sops()
        test_data = {
            'level1': {
                'level2': {
                    'key': 'nested_value'
                }
            }
        }

        with patch.object(Sops, 'decrypt', return_value=test_data):
            result = sops.get_keys('/path/to/file.yaml', "['level1']['level2']['key']")
            assert result == 'nested_value'

    def test_get_keys_missing_key(self):
        """Test get_keys with missing key"""
        sops = Sops()
        test_data = {'existing_key': 'value'}

        with patch.object(Sops, 'decrypt', return_value=test_data):
            with pytest.raises(SopsError):
                sops.get_keys('/path/to/file.yaml', 'missing_key')


class TestSimpleVault:
    """Test SimpleVault class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.vault = SimpleVault()

    @patch('hvac.Client')
    def test_get_vault_client_authenticated(self, mock_hvac_client):
        """Test getting authenticated Vault client"""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        result = self.vault.get_vault_client()

        assert result == mock_client
        mock_hvac_client.assert_called_once()

    @patch.dict(os.environ, {'VAULT_PASSWORD': 'test_pass', 'VAULT_USERNAME': 'test_user'})
    @patch('hvac.Client')
    def test_get_vault_client_ldap_fallback(self, mock_hvac_client):
        """Test Vault client with LDAP fallback authentication"""
        mock_client = MagicMock()
        mock_client.is_authenticated.side_effect = [False, True]  # First call fails, second succeeds
        mock_hvac_client.return_value = mock_client

        result = self.vault.get_vault_client()

        assert result == mock_client
        mock_client.auth.ldap.login.assert_called_once_with(
            username='test_user',
            password='test_pass'
        )

    @patch.dict(os.environ, {'VAULT_PASSWORD': 'test_pass', 'VAULT_USERNAME': 'test_user'})
    @patch('hvac.Client')
    def test_get_vault_client_ldap_failure(self, mock_hvac_client):
        """Test Vault client LDAP authentication failure"""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False
        mock_client.auth.ldap.login.side_effect = Exception('LDAP failed')
        mock_hvac_client.return_value = mock_client

        with pytest.raises(Exception) as exc_info:
            self.vault.get_vault_client()

        assert 'Error authenticating Vault over LDAP' in str(exc_info.value)

    @patch.dict(os.environ, {'VAULT_ROLE': 'test_role'})
    @patch.object(SimpleVault, 'get_vault_client')
    def test_get_token(self, mock_get_client):
        """Test token generation"""
        mock_client = MagicMock()
        mock_client.create_token.return_value = {
            'auth': {'client_token': 'generated_token'}
        }
        mock_get_client.return_value = mock_client

        result = self.vault.get_token('my_policy')

        assert result == 'generated_token'
        mock_client.create_token.assert_called_once_with(
            policies=['my_policy'],
            role='test_role',
            lease='24h'
        )

    @patch.dict(os.environ, {'VAULT_MOUNT_POINT': 'secret'})
    @patch.object(SimpleVault, 'get_vault_client')
    def test_get_path(self, mock_get_client):
        """Test path retrieval"""
        mock_client = MagicMock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {'data': {'key1': 'value1', 'key2': 'value2'}}
        }
        mock_get_client.return_value = mock_client

        result = self.vault.get_path('/my/secret/path')

        assert result == {'key1': 'value1', 'key2': 'value2'}
        mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            mount_point='secret',
            path='/my/secret/path'
        )

    @patch.object(SimpleVault, 'get_path')
    def test_get_key(self, mock_get_path):
        """Test key retrieval"""
        mock_get_path.return_value = {'key1': 'value1', 'key2': 'value2'}

        result = self.vault.get_key('/my/secret/path', 'key1')

        assert result == 'value1'
        mock_get_path.assert_called_once_with('/my/secret/path')


class TestSopsError:
    """Test SopsError exception class"""

    def test_sops_error_creation(self):
        """Test SopsError creation"""
        error = SopsError('/path/to/file', 1, 'Error message', True)

        assert error.filename == '/path/to/file'
        assert error.exit_code == 1
        assert error.stderr == 'Error message'
        assert error.decryption is True

    def test_sops_error_string_representation(self):
        """Test SopsError string representation"""
        error = SopsError('/path/to/file', 1, 'Error message', True)
        error_str = str(error)

        assert '/path/to/file' in error_str
        assert 'Error message' in error_str
