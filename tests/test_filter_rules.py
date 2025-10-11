# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pytest
from himl.filter_rules import FilterRules


class TestFilterRules:
    """Test FilterRules class"""

    def test_initialization(self):
        """Test FilterRules initialization"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'values': ['key1', 'key2']}
            }
        ]
        levels = ['env', 'region', 'cluster']

        filter_rules = FilterRules(rules, levels)

        assert filter_rules.rules == rules
        assert filter_rules.levels == levels

    def test_simple_value_filter(self):
        """Test filtering with simple value selector"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'values': ['keep_me', 'also_keep']}
            }
        ]
        levels = ['env', 'region']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'region': 'us-east-1',
            'keep_me': 'value1',
            'also_keep': 'value2',
            'remove_me': 'value3',
            'remove_this_too': 'value4'
        }

        filter_rules.run(output)

        # Should keep level keys and specified keys
        assert 'env' in output
        assert 'region' in output
        assert 'keep_me' in output
        assert 'also_keep' in output
        assert 'remove_me' not in output
        assert 'remove_this_too' not in output

    def test_regex_filter(self):
        """Test filtering with regex selector"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'regex': 'keep_.*'}
            }
        ]
        levels = ['env', 'region']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'region': 'us-east-1',
            'keep_me': 'value1',
            'keep_this': 'value2',
            'remove_me': 'value3',
            'also_remove': 'value4'
        }

        filter_rules.run(output)

        assert 'env' in output
        assert 'region' in output
        assert 'keep_me' in output
        assert 'keep_this' in output
        assert 'remove_me' not in output
        assert 'also_remove' not in output

    def test_combined_values_and_regex_filter(self):
        """Test filtering with both values and regex"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {
                    'values': ['explicit_keep'],
                    'regex': 'pattern_.*'
                }
            }
        ]
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'explicit_keep': 'value1',
            'pattern_match': 'value2',
            'pattern_another': 'value3',
            'remove_me': 'value4'
        }

        filter_rules.run(output)

        assert 'env' in output
        assert 'explicit_keep' in output
        assert 'pattern_match' in output
        assert 'pattern_another' in output
        assert 'remove_me' not in output

    def test_regex_selector_match(self):
        """Test regex matching in selector"""
        rules = [
            {
                'selector': {'cluster': 'cluster.*'},
                'keys': {'values': ['keep_me']}
            }
        ]
        levels = ['env', 'cluster']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'cluster': 'cluster1',
            'keep_me': 'value1',
            'remove_me': 'value2'
        }

        filter_rules.run(output)

        assert 'env' in output
        assert 'cluster' in output
        assert 'keep_me' in output
        assert 'remove_me' not in output

    def test_multiple_selector_conditions(self):
        """Test multiple conditions in selector"""
        rules = [
            {
                'selector': {
                    'env': 'dev',
                    'region': 'us-.*'
                },
                'keys': {'values': ['keep_me']}
            }
        ]
        levels = ['env', 'region']
        filter_rules = FilterRules(rules, levels)

        # Should match - both conditions satisfied
        output = {
            'env': 'dev',
            'region': 'us-east-1',
            'keep_me': 'value1',
            'remove_me': 'value2'
        }

        filter_rules.run(output)

        assert 'keep_me' in output
        assert 'remove_me' not in output

    def test_selector_no_match(self):
        """Test when selector doesn't match"""
        rules = [
            {
                'selector': {'env': 'prod'},
                'keys': {'values': ['keep_me']}
            }
        ]
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',  # Doesn't match selector
            'keep_me': 'value1',
            'remove_me': 'value2'
        }

        filter_rules.run(output)

        # Since selector doesn't match, all non-level keys should be removed
        assert 'env' in output
        assert 'keep_me' not in output
        assert 'remove_me' not in output

    def test_multiple_rules(self):
        """Test multiple filter rules"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'values': ['dev_specific']}
            },
            {
                'selector': {'cluster': 'cluster1'},
                'keys': {'values': ['cluster_specific']}
            }
        ]
        levels = ['env', 'cluster']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'cluster': 'cluster1',
            'dev_specific': 'value1',
            'cluster_specific': 'value2',
            'remove_me': 'value3'
        }

        filter_rules.run(output)

        assert 'env' in output
        assert 'cluster' in output
        assert 'dev_specific' in output
        assert 'cluster_specific' in output
        assert 'remove_me' not in output

    def test_missing_selector_key(self):
        """Test selector with missing key in output"""
        rules = [
            {
                'selector': {'missing_key': 'value'},
                'keys': {'values': ['keep_me']}
            }
        ]
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'keep_me': 'value1',
            'remove_me': 'value2'
        }

        filter_rules.run(output)

        # Selector should not match due to missing key
        assert 'env' in output
        assert 'keep_me' not in output
        assert 'remove_me' not in output

    def test_invalid_selector_type(self):
        """Test invalid selector type"""
        rules = [
            {
                'selector': 'invalid_selector',  # Should be dict
                'keys': {'values': ['keep_me']}
            }
        ]
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {'env': 'dev', 'keep_me': 'value1'}

        with pytest.raises(Exception) as exc_info:
            filter_rules.run(output)

        assert "Filter selector must be a dictionary" in str(exc_info.value)

    def test_empty_rules(self):
        """Test with empty rules list"""
        rules = []
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'remove_me': 'value1',
            'also_remove': 'value2'
        }

        filter_rules.run(output)

        # With no rules, all non-level keys should be removed
        assert 'env' in output
        assert 'remove_me' not in output
        assert 'also_remove' not in output

    def test_match_method_direct(self):
        """Test match method directly"""
        filter_rules = FilterRules([], [])

        output = {'env': 'dev', 'region': 'us-east-1'}

        # Exact match
        assert filter_rules.match(output, {'env': 'dev'}) is True

        # Regex match
        assert filter_rules.match(output, {'region': 'us-.*'}) is True

        # No match
        assert filter_rules.match(output, {'env': 'prod'}) is False

        # Missing key
        assert filter_rules.match(output, {'missing': 'value'}) is False

    def test_complex_regex_patterns(self):
        """Test complex regex patterns"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'regex': '^(keep|save)_.*$'}
            }
        ]
        levels = ['env']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'keep_this': 'value1',
            'save_that': 'value2',
            'keep_me_too': 'value3',
            'remove_this': 'value4',
            'also_remove': 'value5'
        }

        filter_rules.run(output)

        assert 'env' in output
        assert 'keep_this' in output
        assert 'save_that' in output
        assert 'keep_me_too' in output
        assert 'remove_this' not in output
        assert 'also_remove' not in output

    def test_preserve_level_keys(self):
        """Test that level keys are always preserved"""
        rules = [
            {
                'selector': {'env': 'dev'},
                'keys': {'values': []}  # Empty values list
            }
        ]
        levels = ['env', 'region', 'cluster']
        filter_rules = FilterRules(rules, levels)

        output = {
            'env': 'dev',
            'region': 'us-east-1',
            'cluster': 'web',
            'remove_me': 'value1'
        }

        filter_rules.run(output)

        # Level keys should always be preserved
        assert 'env' in output
        assert 'region' in output
        assert 'cluster' in output
        assert 'remove_me' not in output
