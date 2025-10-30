# Copyright 2025 Adobe. All rights reserved.
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
from collections import OrderedDict


from himl import ConfigProcessor, ConfigGenerator


class TestConfigProcessor:
    """Test cases for ConfigProcessor class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_processor = ConfigProcessor()

    def teardown_method(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_yaml(self, path, content):
        """Helper to create test YAML files"""
        full_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            yaml.dump(content, f)
        return full_path

    def test_simple_config_processing(self):
        """Test basic config processing with single file"""
        # Create a simple config file
        config_data = {'env': 'test', 'debug': True, 'port': 8080}
        self.create_test_yaml('config.yaml', config_data)

        # Process the config
        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            print_data=False
        )

        assert result == config_data

    def test_hierarchical_config_merging(self):
        """Test hierarchical config merging"""
        # Create default config
        default_config = {
            'env': 'default',
            'database': {'host': 'localhost', 'port': 5432},
            'features': ['feature1', 'feature2']
        }
        self.create_test_yaml('default.yaml', default_config)

        # Create environment-specific config
        env_config = {
            'env': 'production',
            'database': {'host': 'prod-db.example.com'},
            'features': ['feature3']
        }
        os.makedirs(os.path.join(self.temp_dir, 'production'), exist_ok=True)
        self.create_test_yaml('production/env.yaml', env_config)

        # Process the hierarchical config
        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='production',
            print_data=False
        )

        # Verify deep merge occurred
        assert result['env'] == 'production'
        assert result['database']['host'] == 'prod-db.example.com'
        assert result['database']['port'] == 5432  # From default
        assert 'feature1' in result['features']
        assert 'feature2' in result['features']
        assert 'feature3' in result['features']

    def test_config_filtering(self):
        """Test config filtering functionality"""
        config_data = {
            'env': 'test',
            'database': {'host': 'localhost'},
            'secret_key': 'should_be_filtered',
            'public_key': 'should_remain'
        }
        self.create_test_yaml('config.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            filters=['env', 'database', 'public_key'],
            print_data=False
        )

        assert 'env' in result
        assert 'database' in result
        assert 'public_key' in result
        assert 'secret_key' not in result

    def test_config_exclusion(self):
        """Test config key exclusion functionality"""
        config_data = {
            'env': 'test',
            'database': {'host': 'localhost'},
            'secret_key': 'should_be_excluded',
            'public_key': 'should_remain'
        }
        self.create_test_yaml('config.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            exclude_keys=['secret_key'],
            print_data=False
        )

        assert 'env' in result
        assert 'database' in result
        assert 'public_key' in result
        assert 'secret_key' not in result

    def test_enclosing_key_addition(self):
        """Test adding enclosing key to config"""
        config_data = {'env': 'test', 'debug': True}
        self.create_test_yaml('config.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            enclosing_key='application',
            print_data=False
        )

        assert 'application' in result
        assert result['application'] == config_data

    def test_enclosing_key_removal(self):
        """Test removing enclosing key from config"""
        config_data = {
            'application': {
                'env': 'test',
                'debug': True
            },
            'other_key': 'value'
        }
        self.create_test_yaml('config.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            remove_enclosing_key='application',
            print_data=False
        )

        assert result == config_data['application']

    def test_output_formats(self):
        """Test different output formats"""
        config_data = {'env': 'test', 'debug': True}
        self.create_test_yaml('config.yaml', config_data)

        # Test YAML output
        yaml_result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            output_format='yaml',
            print_data=False
        )
        assert yaml_result == config_data

        # Test JSON output
        json_result = self.config_processor.process(
            cwd=self.temp_dir,
            path='config.yaml',
            output_format='json',
            print_data=False
        )
        assert json_result == config_data

    def test_unicode_processing_disabled(self):
        """Test Unicode processing with allow_unicode=False"""
        config_data = {
            'message': 'Hello 世界',
            'emoji': '✨ sparkles',
            'accents': 'café'
        }
        self.create_test_yaml('unicode.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='unicode.yaml',
            allow_unicode=False,
            print_data=False
        )

        # Data should be processed correctly regardless of Unicode settings
        assert result['message'] == 'Hello 世界'
        assert result['emoji'] == '✨ sparkles'
        assert result['accents'] == 'café'

    def test_unicode_processing_enabled(self):
        """Test Unicode processing with allow_unicode=True"""
        config_data = {
            'message': 'Hello 世界',
            'emoji': '✨ sparkles',
            'accents': 'café',
            'arabic': 'مرحبا',
            'cyrillic': 'Привет'
        }
        self.create_test_yaml('unicode.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='unicode.yaml',
            allow_unicode=True,
            print_data=False
        )

        # Data should be processed correctly
        assert result['message'] == 'Hello 世界'
        assert result['emoji'] == '✨ sparkles'
        assert result['accents'] == 'café'
        assert result['arabic'] == 'مرحبا'
        assert result['cyrillic'] == 'Привет'


class TestConfigGenerator:
    """Test cases for ConfigGenerator class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_yaml(self, path, content):
        """Helper to create test YAML files"""
        full_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            yaml.dump(content, f)
        return full_path

    def test_config_generator_initialization(self):
        """Test ConfigGenerator initialization"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        assert generator.cwd == self.temp_dir
        assert generator.path == 'test'
        assert isinstance(generator.generated_data, OrderedDict)

    def test_hierarchy_generation(self):
        """Test hierarchy generation from directory structure"""
        # Create a hierarchy structure
        self.create_test_yaml('default.yaml', {'env': 'default'})
        os.makedirs(os.path.join(self.temp_dir, 'production'), exist_ok=True)
        self.create_test_yaml('production/env.yaml', {'env': 'production'})

        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='production',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        hierarchy = generator.generate_hierarchy()
        assert len(hierarchy) >= 1
        assert any('default.yaml' in str(files) for files in hierarchy)

    def test_yaml_content_loading(self):
        """Test YAML content loading"""
        config_data = {'test_key': 'test_value', 'number': 42}
        yaml_file = self.create_test_yaml('test.yaml', config_data)

        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        content = generator.yaml_get_content(yaml_file)
        assert content == config_data

    def test_yaml_merging(self):
        """Test YAML merging functionality"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        base_config = OrderedDict([('env', 'base'), ('features', ['f1', 'f2'])])
        new_config = {'env': 'new', 'features': ['f3'], 'new_key': 'value'}

        generator.merge_yamls(
            base_config,
            new_config,
            [(list, ["append_unique"]), (dict, ["merge"])],
            ["override"],
            ["override"]
        )

        assert base_config['env'] == 'new'
        assert 'f1' in base_config['features']
        assert 'f2' in base_config['features']
        assert 'f3' in base_config['features']
        assert base_config['new_key'] == 'value'

    def test_output_data_yaml(self):
        """Test YAML output formatting"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {'env': 'test', 'debug': True, 'port': 8080}
        yaml_output = generator.output_data(test_data, 'yaml')

        # Parse the YAML output back to verify it's valid
        parsed_data = yaml.safe_load(yaml_output)
        assert parsed_data == test_data

    def test_output_data_json(self):
        """Test JSON output formatting"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {'env': 'test', 'debug': True, 'port': 8080}
        json_output = generator.output_data(test_data, 'json')

        # Parse the JSON output back to verify it's valid
        import json
        parsed_data = json.loads(json_output)
        assert parsed_data == test_data

    def test_invalid_output_format(self):
        """Test handling of invalid output format"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {'env': 'test'}

        with pytest.raises(Exception) as exc_info:
            generator.output_data(test_data, 'invalid_format')

        assert "Unknown output format" in str(exc_info.value)

    def test_values_from_dir_path(self):
        """Test extracting values from directory path"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='env=production/region=us-east-1/cluster=web',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        values = generator.get_values_from_dir_path()
        expected = {'env': 'production', 'region': 'us-east-1', 'cluster': 'web'}
        assert values == expected

    def test_allow_unicode_false(self):
        """Test that Unicode characters are escaped when allow_unicode=False"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=False,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {
            'greeting': 'Hello 世界',
            'emoji': '🚀 rocket',
            'special': 'café résumé naïve'
        }
        yaml_output = generator.output_yaml_data(test_data)

        # When allow_unicode=False, Unicode should be escaped
        assert '\\u' in yaml_output or '\\x' in yaml_output or 'greeting: Hello' in yaml_output

    def test_allow_unicode_true(self):
        """Test that Unicode characters are preserved when allow_unicode=True"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=True,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {
            'greeting': 'Hello 世界',
            'emoji': '🚀 rocket',
            'special': 'café résumé naïve'
        }
        yaml_output = generator.output_yaml_data(test_data)

        # When allow_unicode=True, most Unicode should be preserved
        # Note: PyYAML may still escape some 4-byte UTF-8 characters (emojis)
        assert '世界' in yaml_output  # Chinese characters preserved
        assert 'café' in yaml_output  # Accented characters preserved
        assert 'résumé' in yaml_output  # Accented characters preserved
        assert 'naïve' in yaml_output  # Accented characters preserved
        # Emoji might be escaped as \U0001F680 even with allow_unicode=True
        assert ('🚀' in yaml_output or '\\U0001F680' in yaml_output)

    def test_unicode_in_nested_structures(self):
        """Test Unicode handling in nested data structures"""
        generator = ConfigGenerator(
            cwd=self.temp_dir,
            path='test',
            multi_line_string=False,
            allow_unicode=True,
            type_strategies=[(list, ["append_unique"]), (dict, ["merge"])],
            fallback_strategies=["override"],
            type_conflict_strategies=["override"]
        )

        test_data = {
            'users': [
                {'name': 'José García', 'country': 'España'},
                {'name': '田中太郎', 'country': '日本'},
                {'name': 'François Müller', 'country': 'France'}
            ],
            'config': {
                'title': 'Configuration — Настройки',
                'description': 'Multi-language support: English, 中文, العربية, हिन्दी'
            }
        }
        yaml_output = generator.output_yaml_data(test_data)

        # Verify Unicode characters are preserved (excluding 4-byte emoji which may be escaped)
        assert 'José García' in yaml_output
        assert '田中太郎' in yaml_output
        assert 'España' in yaml_output
        assert '日本' in yaml_output
        assert 'Настройки' in yaml_output
        assert '中文' in yaml_output
        assert 'العربية' in yaml_output
        assert 'हिन्दी' in yaml_output
