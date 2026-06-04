# Copyright 2025 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pytest
from himl.interpolation import (
    InterpolationResolver, EscapingResolver, InterpolationValidator,
    FromDictInjector, FullBlobInjector, DictIterator,
    is_interpolation, is_escaped_interpolation, is_full_interpolation,
    is_fully_escaped_interpolation, remove_white_spaces,
    replace_parent_working_directory, collect_pending_keys
)


class TestInterpolationUtilities:
    """Test utility functions for interpolation"""

    def test_is_interpolation(self):
        """Test interpolation detection"""
        assert is_interpolation("{{env.name}}")
        assert is_interpolation("prefix {{env.name}} suffix")
        assert not is_interpolation("no interpolation")
        assert not is_interpolation("{{`escaped`}}")
        assert not is_interpolation(123)
        assert not is_interpolation(None)

    def test_is_escaped_interpolation(self):
        """Test escaped interpolation detection"""
        assert is_escaped_interpolation("{{`escaped`}}")
        assert is_escaped_interpolation("prefix {{`escaped`}} suffix")
        assert not is_escaped_interpolation("{{normal}}")
        assert not is_escaped_interpolation("no interpolation")

    def test_is_full_interpolation(self):
        """Test full interpolation detection"""
        assert is_full_interpolation("{{env.name}}")
        assert not is_full_interpolation("prefix {{env.name}} suffix")
        assert not is_full_interpolation("{{`escaped`}}")
        assert not is_full_interpolation("no interpolation")

    def test_is_fully_escaped_interpolation(self):
        """Test fully escaped interpolation detection"""
        assert is_fully_escaped_interpolation("{{`escaped`}}")
        assert not is_fully_escaped_interpolation("prefix {{`escaped`}} suffix")
        assert not is_fully_escaped_interpolation("{{normal}}")

    def test_remove_white_spaces(self):
        """Test whitespace removal"""
        assert remove_white_spaces("  hello   world  ") == "helloworld"
        assert remove_white_spaces("no spaces") == "nospaces"
        assert remove_white_spaces("") == ""

    def test_replace_parent_working_directory(self):
        """Test CWD replacement"""
        result = replace_parent_working_directory("{{cwd}}/config", "/home/user")
        assert result == "/home/user/config"

        result = replace_parent_working_directory("no cwd here", "/home/user")
        assert result == "no cwd here"


class TestFromDictInjector:
    """Test FromDictInjector class"""

    def test_simple_interpolation_resolve(self):
        """Test simple value interpolation"""
        injector = FromDictInjector()
        data = {'env': {'name': 'production'}, 'port': 8080}

        result = injector.resolve("{{env.name}}", data)
        assert result == "production"

        result = injector.resolve("Environment: {{env.name}}", data)
        assert result == "Environment: production"

    def test_numeric_interpolation_resolve(self):
        """Test numeric value interpolation"""
        injector = FromDictInjector()
        data = {'config': {'port': 8080, 'enabled': True}}

        result = injector.resolve("{{config.port}}", data)
        assert result == 8080

        result = injector.resolve("{{config.enabled}}", data)
        assert result is True

    def test_nested_interpolation_resolve(self):
        """Test deeply nested interpolation"""
        injector = FromDictInjector()
        data = {
            'app': {
                'database': {
                    'connection': {
                        'host': 'db.example.com'
                    }
                }
            }
        }

        result = injector.resolve("{{app.database.connection.host}}", data)
        assert result == "db.example.com"

    def test_missing_key_interpolation(self):
        """Test interpolation with missing keys"""
        injector = FromDictInjector()
        data = {'env': {'name': 'production'}}

        result = injector.resolve("{{missing.key}}", data)
        assert result == "{{missing.key}}"  # Should remain unchanged

    def test_multiple_interpolations(self):
        """Test multiple interpolations in one string"""
        injector = FromDictInjector()
        data = {'env': 'prod', 'region': 'us-east-1'}

        result = injector.resolve("{{env}}-{{region}}", data)
        assert result == "prod-us-east-1"

    def test_parse_leaves(self):
        """Test parse_leaves method"""
        injector = FromDictInjector()
        data = {
            'level1': {
                'level2': {
                    'value': 'test'
                },
                'simple': 'value'
            },
            'root': 'root_value'
        }

        injector.parse_leaves(data, "")

        assert 'level1.level2.value' in injector.results
        assert injector.results['level1.level2.value'] == 'test'
        assert 'level1.simple' in injector.results
        assert injector.results['level1.simple'] == 'value'
        assert 'root' in injector.results
        assert injector.results['root'] == 'root_value'


class TestFullBlobInjector:
    """Test FullBlobInjector class"""

    def test_full_blob_injection(self):
        """Test full blob injection"""
        injector = FullBlobInjector()
        data = {
            'database': {
                'host': 'localhost',
                'port': 5432
            }
        }

        result = injector.resolve("{{database}}", data)
        assert result == data['database']

    def test_partial_interpolation_unchanged(self):
        """Test that partial interpolations are unchanged"""
        injector = FullBlobInjector()
        data = {'env': 'production'}

        result = injector.resolve("Environment: {{env}}", data)
        assert result == "Environment: {{env}}"

    def test_missing_key_unchanged(self):
        """Test that missing keys remain unchanged"""
        injector = FullBlobInjector()
        data = {'env': 'production'}

        result = injector.resolve("{{missing}}", data)
        assert result == "{{missing}}"

    def test_nested_blob_injection(self):
        """Test nested blob injection"""
        injector = FullBlobInjector()
        data = {
            'app': {
                'config': {
                    'database': {
                        'host': 'localhost',
                        'port': 5432
                    }
                }
            }
        }

        result = injector.resolve("{{app.config.database}}", data)
        assert result == data['app']['config']['database']


class TestInterpolationResolver:
    """Test InterpolationResolver class"""

    def test_resolve_interpolations(self):
        """Test interpolation resolution"""
        resolver = InterpolationResolver()
        data = {
            'env': 'production',
            'database_url': 'db-{{env}}.example.com',
            'config': {
                'environment': '{{env}}'
            }
        }

        result = resolver.resolve_interpolations(data)

        assert result['database_url'] == 'db-production.example.com'
        assert result['config']['environment'] == 'production'

    def test_complex_interpolation_resolution(self):
        """Test complex interpolation scenarios"""
        resolver = InterpolationResolver()
        data = {
            'env': 'prod',
            'region': 'us-east-1',
            'cluster': 'web',
            'full_name': '{{env}}-{{region}}-{{cluster}}',
            'nested': {
                'value': 'Environment is {{env}}'
            },
            'reference': {
                'to_nested': '{{nested}}'
            }
        }

        result = resolver.resolve_interpolations(data)

        assert result['full_name'] == 'prod-us-east-1-web'
        assert result['nested']['value'] == 'Environment is prod'
        assert result['reference']['to_nested'] == data['nested']


class TestInterpolationValidator:
    """Test InterpolationValidator class"""

    def test_valid_interpolations_pass(self):
        """Test that resolved interpolations pass validation"""
        validator = InterpolationValidator()
        data = {
            'env': 'production',
            'database_url': 'db-production.example.com'
        }

        # Should not raise an exception
        validator.check_all_interpolations_resolved(data)

    def test_unresolved_interpolations_fail(self):
        """Test that unresolved interpolations fail validation"""
        validator = InterpolationValidator()
        data = {
            'env': 'production',
            'database_url': 'db-{{unresolved}}.example.com'
        }

        with pytest.raises(Exception) as exc_info:
            validator.check_all_interpolations_resolved(data)

        assert "Interpolation could not be resolved" in str(exc_info.value)
        assert "{{unresolved}}" in str(exc_info.value)

    def test_escaped_interpolations_pass(self):
        """Test that escaped interpolations pass validation"""
        validator = InterpolationValidator()
        data = {
            'env': 'production',
            'template': 'Use {{`variable`}} for templating'
        }

        # Should not raise an exception
        validator.check_all_interpolations_resolved(data)


class TestEscapingResolver:
    """Test EscapingResolver class"""

    def test_resolve_escaping(self):
        """Test escaping resolution"""
        resolver = EscapingResolver()
        data = {
            'template': '{{`escaped_value`}}',
            'normal': 'normal_value'
        }

        result = resolver.resolve_escaping(data)

        # The actual escaping logic would be implemented in DictEscapingResolver
        # This test verifies the method can be called without error
        assert result is not None


class TestCollectPendingKeys:
    """Tests for the collect_pending_keys helper"""

    # Note: is_interpolation requires >=2 chars inside {{}} due to the regex
    # pattern \{\{[^`].*?[^`]\}\} — use multi-char keys like {{env.name}}.

    def test_string_with_interpolation(self):
        pending = collect_pending_keys('{{env.name}}', 'mykey')
        assert pending == {'mykey'}

    def test_string_without_interpolation(self):
        pending = collect_pending_keys('plain_value', 'mykey')
        assert pending == set()

    def test_dict_with_interpolation(self):
        data = {'base': 'resolved', 'derived': '{{base_url}}', 'other': 'also_resolved'}
        pending = collect_pending_keys(data)
        assert pending == {'derived'}

    def test_list_with_interpolation(self):
        data = {'items': ['plain', '{{env.name}}', 'also_plain']}
        pending = collect_pending_keys(data)
        assert 'items.1' in pending
        assert 'items.0' not in pending
        assert 'items.2' not in pending

    def test_nested_dict(self):
        data = {'outer': {'inner': '{{ref.key}}'}}
        pending = collect_pending_keys(data)
        assert 'outer.inner' in pending

    def test_no_interpolations(self):
        data = {'aa': 'hello', 'bb': 42, 'cc': True}
        assert collect_pending_keys(data) == set()

    def test_empty_prefix(self):
        data = {'key': '{{val.x}}'}
        pending = collect_pending_keys(data)
        assert 'key' in pending

    def test_list_at_top_level(self):
        data = ['{{aa.bb}}', 'plain', '{{cc.dd}}']
        pending = collect_pending_keys(data)
        assert '0' in pending
        assert '1' not in pending
        assert '2' in pending


class TestDictIteratorLoopPendingItems:
    """Tests for DictIterator.loop_pending_items"""

    def test_resolves_pending_key(self):
        iterator = DictIterator()
        data = {'env': 'prod', 'url': '{{env}}-api.com'}
        resolver = InterpolationResolver()
        pending = {'url'}

        still_pending = iterator.loop_pending_items(
            data, lambda v: v.replace('{{env}}', 'prod'), pending
        )

        assert data['url'] == 'prod-api.com'
        assert 'url' not in still_pending

    def test_skips_missing_key_path(self):
        """KeyError for a missing path is silently skipped"""
        iterator = DictIterator()
        data = {'a': 'hello'}
        pending = {'nonexistent.path', 'also.missing'}

        result = iterator.loop_pending_items(data, lambda v: v, pending)

        assert isinstance(result, set)
        assert data == {'a': 'hello'}

    def test_handles_non_string_value_at_path(self):
        """When the value at a pending path is a dict, loop_all_items is used"""
        iterator = DictIterator()
        data = {'a': {'b': '{{c}}'}}
        pending = {'a'}

        result = iterator.loop_pending_items(data, lambda v: v, pending)

        assert isinstance(result, set)

    def test_resolves_list_element_pending_key(self):
        """_set_at_path uses int indexing when the pending key points to a list element (line 203)"""
        iterator = DictIterator()
        data = {'env': 'prod', 'items': ['plain', '{{env.name}}']}
        pending = {'items.1'}

        still_pending = iterator.loop_pending_items(
            data, lambda v: v.replace('{{env.name}}', 'prod'), pending
        )

        assert data['items'][1] == 'prod'
        assert 'items.1' not in still_pending


class TestInterpolationResolverWithPendingKeys:
    """Tests for InterpolationResolver.resolve_interpolations with pending_keys"""

    def test_resolve_with_pending_keys_returns_updated_set(self):
        resolver = InterpolationResolver()
        data = {'env': 'prod', 'url': '{{env}}-api.com', 'other': 'static'}
        pending = {'url'}

        still_pending = resolver.resolve_interpolations(data, pending_keys=pending)

        assert data['url'] == 'prod-api.com'
        assert isinstance(still_pending, set)
        assert 'url' not in still_pending

    def test_resolve_with_empty_pending_keys(self):
        resolver = InterpolationResolver()
        data = {'env': 'prod', 'url': '{{env}}-api.com'}
        pending = set()

        still_pending = resolver.resolve_interpolations(data, pending_keys=pending)

        assert still_pending == set()
        assert data['url'] == '{{env}}-api.com'  # untouched

    def test_resolve_without_pending_keys_returns_data(self):
        resolver = InterpolationResolver()
        data = {'env': 'prod', 'url': '{{env}}-api.com'}

        result = resolver.resolve_interpolations(data)

        assert result is data
        assert data['url'] == 'prod-api.com'
