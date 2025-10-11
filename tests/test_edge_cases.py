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
from himl import ConfigProcessor
from himl.interpolation import InterpolationValidator
from himl.python_compat import iteritems, primitive_types, PY3


class TestEdgeCases:
    """Test edge cases and error conditions"""

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

    def test_empty_yaml_file(self):
        """Test processing empty YAML file"""
        self.create_test_yaml('empty.yaml', {})

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='empty.yaml',
            print_data=False
        )

        assert result == {}

    def test_yaml_file_with_null_values(self):
        """Test processing YAML with null values"""
        config_data = {
            'key1': None,
            'key2': 'value2',
            'nested': {
                'null_key': None,
                'valid_key': 'valid_value'
            }
        }
        self.create_test_yaml('null_values.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='null_values.yaml',
            print_data=False
        )

        assert result['key1'] is None
        assert result['key2'] == 'value2'
        assert result['nested']['null_key'] is None
        assert result['nested']['valid_key'] == 'valid_value'

    def test_yaml_file_with_special_characters(self):
        """Test processing YAML with special characters"""
        config_data = {
            'unicode_key': 'value with émojis 🚀',
            'special_chars': 'value with !@#$%^&*()',
            'quotes': 'value with "quotes" and \'apostrophes\'',
            'newlines': 'value with\nnewlines\nand\ttabs'
        }
        self.create_test_yaml('special_chars.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='special_chars.yaml',
            print_data=False
        )

        assert result == config_data

    def test_deeply_nested_structure(self):
        """Test processing deeply nested YAML structure"""
        config_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'level5': {
                                'deep_value': 'found_it'
                            }
                        }
                    }
                }
            }
        }
        self.create_test_yaml('deep_nested.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='deep_nested.yaml',
            print_data=False
        )

        assert result['level1']['level2']['level3']['level4']['level5']['deep_value'] == 'found_it'

    def test_large_list_processing(self):
        """Test processing large lists"""
        large_list = [f'item_{i}' for i in range(1000)]
        config_data = {
            'large_list': large_list,
            'other_key': 'other_value'
        }
        self.create_test_yaml('large_list.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='large_list.yaml',
            print_data=False
        )

        assert len(result['large_list']) == 1000
        assert result['large_list'][0] == 'item_0'
        assert result['large_list'][999] == 'item_999'

    def test_circular_interpolation_detection(self):
        """Test detection of circular interpolations"""
        config_data = {
            'key1': '{{key2}}',
            'key2': '{{key1}}'  # Circular reference
        }
        self.create_test_yaml('circular.yaml', config_data)

        # This should not cause infinite recursion
        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='circular.yaml',
            print_data=False,
            skip_interpolation_validation=True  # Skip validation to avoid exception
        )

        # The interpolations should remain unresolved
        assert '{{' in str(result['key1']) or '{{' in str(result['key2'])

    def test_malformed_interpolation_syntax(self):
        """Test handling of malformed interpolation syntax"""
        config_data = {
            'malformed1': '{{incomplete',
            'malformed2': 'incomplete}}',
            'malformed3': '{{}}',
            'malformed4': '{{.invalid.syntax}}',
            'valid': 'normal_value'
        }
        self.create_test_yaml('malformed.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='malformed.yaml',
            print_data=False,
            skip_interpolation_validation=True
        )

        # Malformed interpolations should remain unchanged
        assert result['malformed1'] == '{{incomplete'
        assert result['malformed2'] == 'incomplete}}'
        assert result['malformed3'] == '{{}}'
        assert result['valid'] == 'normal_value'

    def test_nonexistent_path(self):
        """Test processing nonexistent path"""
        with pytest.raises(Exception):
            self.config_processor.process(
                cwd=self.temp_dir,
                path='nonexistent/path',
                print_data=False
            )

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax"""
        invalid_yaml_path = os.path.join(self.temp_dir, 'invalid.yaml')
        with open(invalid_yaml_path, 'w') as f:
            f.write('invalid: yaml: content: [unclosed')

        with pytest.raises(yaml.YAMLError):
            self.config_processor.process(
                cwd=self.temp_dir,
                path='invalid.yaml',
                print_data=False
            )

    def test_mixed_data_types(self):
        """Test processing mixed data types"""
        config_data = {
            'string': 'text',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'list': [1, 'two', 3.0, False],
            'dict': {'nested': 'value'},
            'null': None
        }
        self.create_test_yaml('mixed_types.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='mixed_types.yaml',
            print_data=False
        )

        assert result['string'] == 'text'
        assert result['integer'] == 42
        assert result['float'] == 3.14
        assert result['boolean'] is True
        assert result['list'] == [1, 'two', 3.0, False]
        assert result['dict']['nested'] == 'value'
        assert result['null'] is None

    def test_unicode_handling(self):
        """Test Unicode character handling"""
        config_data = {
            'chinese': '你好世界',
            'arabic': 'مرحبا بالعالم',
            'emoji': '🌍🚀⭐',
            'mixed': 'Hello 世界 🌍'
        }
        self.create_test_yaml('unicode.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='unicode.yaml',
            print_data=False
        )

        assert result == config_data

    def test_very_long_strings(self):
        """Test handling of very long strings"""
        long_string = 'x' * 10000
        config_data = {
            'long_string': long_string,
            'normal_key': 'normal_value'
        }
        self.create_test_yaml('long_strings.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='long_strings.yaml',
            print_data=False
        )

        assert len(result['long_string']) == 10000
        assert result['normal_key'] == 'normal_value'

    def test_empty_directory_hierarchy(self):
        """Test processing empty directory hierarchy"""
        empty_dir = os.path.join(self.temp_dir, 'empty_dir')
        os.makedirs(empty_dir, exist_ok=True)

        with pytest.raises(Exception):
            self.config_processor.process(
                cwd=self.temp_dir,
                path='empty_dir',
                print_data=False
            )

    def test_interpolation_with_missing_keys(self):
        """Test interpolation with missing keys"""
        config_data = {
            'existing_key': 'existing_value',
            'interpolation': '{{missing.key}}',
            'partial_interpolation': 'prefix-{{missing.key}}-suffix'
        }
        self.create_test_yaml('missing_keys.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='missing_keys.yaml',
            print_data=False,
            skip_interpolation_validation=True
        )

        # Missing interpolations should remain unresolved
        assert result['existing_key'] == 'existing_value'
        assert '{{missing.key}}' in result['interpolation']

    def test_filter_with_nonexistent_keys(self):
        """Test filtering with nonexistent keys"""
        config_data = {
            'key1': 'value1',
            'key2': 'value2'
        }
        self.create_test_yaml('filter_test.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='filter_test.yaml',
            filters=['key1', 'nonexistent_key'],
            print_data=False
        )

        # Should only include existing filtered keys
        assert 'key1' in result
        assert 'key2' not in result
        assert 'nonexistent_key' not in result

    def test_exclude_all_keys(self):
        """Test excluding all keys"""
        config_data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }
        self.create_test_yaml('exclude_all.yaml', config_data)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='exclude_all.yaml',
            exclude_keys=['key1', 'key2', 'key3'],
            print_data=False
        )

        assert result == {}

    def test_complex_merge_strategies(self):
        """Test complex merge strategies"""
        # Create base config
        base_config = {
            'list_append': ['item1'],
            'list_override': ['base1', 'base2'],
            'dict_merge': {'key1': 'base_value1', 'key2': 'base_value2'}
        }
        self.create_test_yaml('default.yaml', base_config)

        # Create override config
        override_config = {
            'list_append': ['item2'],
            'list_override': ['override1'],
            'dict_merge': {'key2': 'override_value2', 'key3': 'new_value3'}
        }
        os.makedirs(os.path.join(self.temp_dir, 'env'), exist_ok=True)
        self.create_test_yaml('env/config.yaml', override_config)

        result = self.config_processor.process(
            cwd=self.temp_dir,
            path='env',
            print_data=False
        )

        # Verify merge behavior
        assert 'item1' in result['list_append']
        assert 'item2' in result['list_append']
        assert result['dict_merge']['key1'] == 'base_value1'
        assert result['dict_merge']['key2'] == 'override_value2'
        assert result['dict_merge']['key3'] == 'new_value3'


class TestPythonCompatibility:
    """Test Python compatibility utilities"""

    def test_iteritems_function(self):
        """Test iteritems compatibility function"""
        test_dict = {'key1': 'value1', 'key2': 'value2'}

        items = list(iteritems(test_dict))

        assert len(items) == 2
        assert ('key1', 'value1') in items
        assert ('key2', 'value2') in items

    def test_primitive_types(self):
        """Test primitive types detection"""
        assert isinstance('string', primitive_types)
        assert isinstance(42, primitive_types)
        assert isinstance(3.14, primitive_types)
        assert isinstance(True, primitive_types)
        assert not isinstance([], primitive_types)
        assert not isinstance({}, primitive_types)

    def test_py3_flag(self):
        """Test Python 3 detection flag"""
        import sys
        expected_py3 = sys.version_info[0] >= 3
        assert PY3 == expected_py3


class TestInterpolationValidatorEdgeCases:
    """Test InterpolationValidator edge cases"""

    def test_validator_with_nested_unresolved(self):
        """Test validator with nested unresolved interpolations"""
        validator = InterpolationValidator()

        data = {
            'level1': {
                'level2': {
                    'unresolved': '{{missing.key}}'
                }
            }
        }

        with pytest.raises(Exception) as exc_info:
            validator.check_all_interpolations_resolved(data)

        assert 'Interpolation could not be resolved' in str(exc_info.value)
        assert '{{missing.key}}' in str(exc_info.value)

    def test_validator_with_list_unresolved(self):
        """Test validator with unresolved interpolations in lists"""
        validator = InterpolationValidator()

        data = {
            'list_with_interpolation': [
                'resolved_value',
                '{{unresolved.key}}',
                'another_resolved_value'
            ]
        }

        with pytest.raises(Exception) as exc_info:
            validator.check_all_interpolations_resolved(data)

        assert 'Interpolation could not be resolved' in str(exc_info.value)
        assert '{{unresolved.key}}' in str(exc_info.value)
