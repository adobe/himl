# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import tempfile
import shutil
import pytest
import yaml
from unittest.mock import patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def yaml_creator(temp_dir):
    """Factory fixture for creating YAML files in temp directory"""
    def create_yaml(path, content):
        full_path = os.path.join(temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            yaml.dump(content, f)
        return full_path
    return create_yaml


@pytest.fixture
def sample_config():
    """Sample configuration data for testing"""
    return {
        'env': 'test',
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'testdb'
        },
        'features': ['feature1', 'feature2'],
        'debug': True
    }


@pytest.fixture
def hierarchical_config(yaml_creator):
    """Create a hierarchical config structure for testing"""
    # Default config
    default_config = {
        'env': 'default',
        'database': {'host': 'localhost', 'port': 5432},
        'features': ['default_feature'],
        'timeout': 30
    }
    yaml_creator('default.yaml', default_config)

    # Environment-specific config
    env_config = {
        'env': 'production',
        'database': {'host': 'prod-db.example.com'},
        'features': ['prod_feature'],
        'ssl_enabled': True
    }
    yaml_creator('production/env.yaml', env_config)

    # Region-specific config
    region_config = {
        'region': 'us-east-1',
        'database': {'region': 'us-east-1'},
        'cdn_endpoint': 'https://cdn-us-east-1.example.com'
    }
    yaml_creator('production/us-east-1/region.yaml', region_config)

    return {
        'default': default_config,
        'env': env_config,
        'region': region_config
    }


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing"""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test_access_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }):
        yield


@pytest.fixture
def mock_vault_env():
    """Mock Vault environment variables for testing"""
    with patch.dict(os.environ, {
        'VAULT_ADDR': 'https://vault.example.com',
        'VAULT_TOKEN': 'test_token',
        'VAULT_USERNAME': 'test_user',
        'VAULT_PASSWORD': 'test_password',
        'VAULT_ROLE': 'test_role',
        'VAULT_MOUNT_POINT': 'kv'
    }):
        yield


@pytest.fixture
def interpolation_config():
    """Configuration with interpolations for testing"""
    return {
        'env': 'production',
        'region': 'us-east-1',
        'app_name': 'myapp',
        'database_url': 'db-{{env}}.example.com',
        'full_name': '{{app_name}}-{{env}}-{{region}}',
        'config': {
            'environment': '{{env}}',
            'nested_interpolation': 'Environment is {{env}}'
        },
        'reference_config': '{{config}}'
    }


@pytest.fixture
def secret_config():
    """Configuration with secret interpolations for testing"""
    return {
        'database': {
            'password': '{{ssm.path(/app/db/password).aws_profile(prod)}}',
            'api_key': '{{vault.path(/secret/api).key(key)}}'
        },
        's3_config': {
            'credentials': '{{s3.bucket(secrets).path(creds.json).aws_profile(prod)}}'
        },
        'sops_secret': '{{sops.secret_file(/path/secrets.yaml).secret_key(db_password)}}'
    }


@pytest.fixture
def filter_config():
    """Configuration with filter rules for testing"""
    return {
        'env': 'dev',
        'cluster': 'cluster1',
        'region': 'us-east-1',
        'keep_this': 'should_remain',
        'remove_this': 'should_be_filtered',
        'keep_pattern_match': 'should_remain',
        'tags': {
            'cost_center': '123',
            'team': 'backend'
        },
        '_filters': [
            {
                'selector': {'env': 'dev'},
                'keys': {
                    'values': ['keep_this', 'tags'],
                    'regex': 'keep_pattern_.*'
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test"""
    # Store original environment
    original_env = os.environ.copy()

    # Clean up test-related environment variables
    test_vars = [
        'AWS_PROFILE', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
        'VAULT_ADDR', 'VAULT_TOKEN', 'VAULT_USERNAME', 'VAULT_PASSWORD',
        'VAULT_ROLE', 'VAULT_MOUNT_POINT'
    ]

    for var in test_vars:
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_terraform_state():
    """Mock Terraform state for testing"""
    return {
        'version': 4,
        'terraform_version': '1.0.0',
        'outputs': {
            'vpc_id': {
                'value': 'vpc-12345',
                'type': 'string'
            },
            'subnet_ids': {
                'value': ['subnet-1', 'subnet-2'],
                'type': ['list', 'string']
            },
            'database_config': {
                'value': {
                    'endpoint': 'db.example.com',
                    'port': 5432,
                    'database_name': 'myapp'
                },
                'type': ['object', {
                    'endpoint': 'string',
                    'port': 'number',
                    'database_name': 'string'
                }]
            }
        }
    }


# Pytest markers for categorizing tests
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "aws: mark test as requiring AWS credentials"
    )
    config.addinivalue_line(
        "markers", "vault: mark test as requiring Vault setup"
    )
    config.addinivalue_line(
        "markers", "sops: mark test as requiring SOPS setup"
    )


# Skip tests that require external dependencies if not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip tests based on available dependencies"""
    import sys

    # Skip AWS tests if boto3 is not available
    if 'boto3' not in sys.modules:
        skip_aws = pytest.mark.skip(reason="boto3 not available")
        for item in items:
            if "aws" in item.keywords:
                item.add_marker(skip_aws)

    # Skip Vault tests if hvac is not available
    if 'hvac' not in sys.modules:
        skip_vault = pytest.mark.skip(reason="hvac not available")
        for item in items:
            if "vault" in item.keywords:
                item.add_marker(skip_vault)

    # Skip SOPS tests if sops binary is not available
    import shutil
    if not shutil.which('sops'):
        skip_sops = pytest.mark.skip(reason="sops binary not available")
        for item in items:
            if "sops" in item.keywords:
                item.add_marker(skip_sops)
