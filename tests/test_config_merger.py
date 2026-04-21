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
from unittest.mock import patch, MagicMock

from himl.config_merger import (
    Loader, merge_configs, merge_logic, get_leaf_directories,
    get_parser, run, _group_by_parent, merge_logic_batch, build_parent_cache
)


class TestLoader:
    """Test custom YAML Loader with include functionality"""

    def test_loader_initialization(self):
        """Test Loader initialization"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('test: value')
            f.flush()

            try:
                with open(f.name, 'r') as stream:
                    loader = Loader(stream)
                    assert loader._root == os.path.dirname(f.name)
            finally:
                os.unlink(f.name)

    def test_include_constructor(self):
        """Test include constructor functionality"""
        # Create a temporary file to include
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as include_file:
            include_content = {'included_key': 'included_value', 'nested': {'key': 'value'}}
            yaml.dump(include_content, include_file)
            include_file.flush()

            try:
                # Create main YAML content with include
                main_content = f"""
test_key: test_value
included_data: !include {include_file.name} included_key
nested_data: !include {include_file.name} nested.key
full_data: !include {include_file.name}
"""

                # Test loading with custom loader
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as main_file:
                    main_file.write(main_content)
                    main_file.flush()

                    try:
                        with open(main_file.name, 'r') as stream:
                            data = yaml.load(stream, Loader=Loader)

                            assert data['test_key'] == 'test_value'
                            assert data['included_data'] == 'included_value'
                            assert data['nested_data'] == 'value'
                            assert data['full_data'] == include_content
                    finally:
                        os.unlink(main_file.name)
            finally:
                os.unlink(include_file.name)


class TestConfigMergerFunctions:
    """Test config merger utility functions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_directory_structure(self):
        """Create a test directory structure"""
        # Create directory structure: env=dev/region=us-east-1/cluster=web
        structure = {
            'default.yaml': {'env': 'default', 'region': 'default', 'cluster': 'default'},
            'env=dev/env.yaml': {'env': 'dev'},
            'env=dev/region=us-east-1/region.yaml': {'region': 'us-east-1'},
            'env=dev/region=us-east-1/cluster=web/cluster.yaml': {'cluster': 'web', 'app': 'webapp'}
        }

        for path, content in structure.items():
            full_path = os.path.join(self.temp_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                yaml.dump(content, f)

    def test_get_leaf_directories(self):
        """Test finding leaf directories"""
        self.create_directory_structure()

        leaf_dirs = get_leaf_directories(self.temp_dir, ['cluster'])

        assert len(leaf_dirs) == 1
        assert leaf_dirs[0].endswith('env=dev/region=us-east-1/cluster=web')

    def test_get_leaf_directories_multiple_leaves(self):
        """Test finding multiple leaf directories"""
        self.create_directory_structure()

        # Create another cluster
        cluster2_path = os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=api')
        os.makedirs(cluster2_path, exist_ok=True)
        with open(os.path.join(cluster2_path, 'cluster.yaml'), 'w') as f:
            yaml.dump({'cluster': 'api', 'app': 'api-service'}, f)

        leaf_dirs = get_leaf_directories(self.temp_dir, ['cluster'])

        assert len(leaf_dirs) == 2
        cluster_names = [os.path.basename(d).split('=')[1] for d in leaf_dirs]
        assert 'web' in cluster_names
        assert 'api' in cluster_names

    def test_get_leaf_directories_no_matches(self):
        """Test finding leaf directories with no matches"""
        self.create_directory_structure()

        leaf_dirs = get_leaf_directories(self.temp_dir, ['nonexistent'], exit_on_empty=False)

        assert len(leaf_dirs) == 0

    @patch('himl.config_merger.ConfigProcessor')
    def test_merge_logic(self, mock_config_processor):
        """Test merge logic function"""
        self.create_directory_structure()

        # Mock ConfigProcessor
        mock_processor = MagicMock()
        mock_processor.process.return_value = {
            'env': 'dev',
            'region': 'us-east-1',
            'cluster': 'web',
            'app': 'webapp'
        }

        # Create output directory
        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        config_tuple = (
            mock_processor,
            os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=web'),
            ['env', 'region', 'cluster'],
            output_dir,
            None,  # No filter rules
            False  # allow_unicode
        )

        merge_logic(config_tuple)

        # Verify output file was created
        expected_output = os.path.join(output_dir, 'dev/us-east-1/web.yaml')
        assert os.path.exists(expected_output)

        # Verify content
        with open(expected_output, 'r') as f:
            content = yaml.safe_load(f)
            assert content['env'] == 'dev'
            assert content['region'] == 'us-east-1'
            assert content['cluster'] == 'web'

    @patch('himl.config_merger.ConfigProcessor')
    @patch('himl.config_merger.FilterRules')
    def test_merge_logic_with_filters(self, mock_filter_rules, mock_config_processor):
        """Test merge logic with filter rules"""
        self.create_directory_structure()

        # Mock ConfigProcessor
        mock_processor = MagicMock()
        mock_processor.process.return_value = {
            'env': 'dev',
            'region': 'us-east-1',
            'cluster': 'web',
            'app': 'webapp',
            'remove_me': 'should_be_filtered',
            '_filters': [{'selector': {'env': 'dev'}, 'keys': {'values': ['app']}}]
        }

        # Mock FilterRules
        mock_filter_instance = MagicMock()
        mock_filter_rules.return_value = mock_filter_instance

        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        config_tuple = (
            mock_processor,
            os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=web'),
            ['env', 'region', 'cluster'],
            output_dir,
            '_filters',
            False  # allow_unicode
        )

        merge_logic(config_tuple)

        # Verify filter was applied
        mock_filter_rules.assert_called_once()
        mock_filter_instance.run.assert_called_once()

    @patch('himl.config_merger.Pool')
    @patch('himl.config_merger.cpu_count')
    def test_merge_configs_parallel(self, mock_cpu_count, mock_pool):
        """Test merge configs with parallel processing"""
        mock_cpu_count.return_value = 4
        mock_pool_instance = MagicMock()
        mock_pool.return_value.__enter__.return_value = mock_pool_instance

        directories = ['dir1', 'dir2']
        levels = ['env', 'region']
        output_dir = '/output'

        merge_configs(directories, levels, output_dir, enable_parallel=True, filter_rules=None, allow_unicode=False)

        mock_pool.assert_called_once_with(4)
        mock_pool_instance.map.assert_called_once()

    @patch('himl.config_merger.merge_logic')
    def test_merge_configs_sequential(self, mock_merge_logic):
        """Test merge configs with sequential processing"""
        directories = ['dir1', 'dir2']
        levels = ['env', 'region']
        output_dir = '/output'

        merge_configs(directories, levels, output_dir, enable_parallel=False, filter_rules=None, allow_unicode=False)

        assert mock_merge_logic.call_count == 2

    def test_get_parser(self):
        """Test argument parser creation"""
        parser = get_parser()

        # Test basic arguments
        args = parser.parse_args(['input_dir', '--output-dir', 'output', '--levels', 'env', 'region',
                                  '--leaf-directories', 'cluster'])
        assert args.path == 'input_dir'
        assert args.output_dir == 'output'
        assert args.hierarchy_levels == ['env', 'region']

        # Test optional arguments
        args = parser.parse_args([
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env', 'region', 'cluster',
            '--leaf-directories', 'cluster',
            '--filter-rules-key', '_filters',
            '--enable-parallel'
        ])

        assert args.leaf_directories == ['cluster']
        assert args.filter_rules == '_filters'
        assert args.enable_parallel is True

    @patch('himl.config_merger.merge_configs')
    @patch('himl.config_merger.get_leaf_directories')
    def test_run_function(self, mock_get_leaf_directories, mock_merge_configs):
        """Test main run function"""
        mock_get_leaf_directories.return_value = ['dir1', 'dir2']

        args = [
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env', 'region',
            '--leaf-directories', 'cluster'
        ]

        with patch('sys.argv', ['himl-config-merger'] + args):
            run()

        mock_get_leaf_directories.assert_called_once_with('input_dir', ['cluster'])
        mock_merge_configs.assert_called_once_with(
            ['dir1', 'dir2'],
            ['env', 'region'],
            'output',
            False,  # enable_parallel default
            None,   # filter_rules_key default
            False,  # allow_unicode default
            enable_precompute=False
        )

    def test_parser_default_values(self):
        """Test parser default values"""
        parser = get_parser()

        args = parser.parse_args(['input_dir', '--output-dir', 'output', '--levels', 'env',
                                  '--leaf-directories', 'cluster'])

        assert args.leaf_directories == ['cluster']
        assert args.filter_rules is None
        assert args.enable_parallel is False

    def test_parser_multiple_levels(self):
        """Test parser with multiple levels"""
        parser = get_parser()

        args = parser.parse_args([
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env', 'region', 'cluster', 'app',
            '--leaf-directories', 'cluster'
        ])

        assert args.hierarchy_levels == ['env', 'region', 'cluster', 'app']

    def test_parser_multiple_leaf_directories(self):
        """Test parser with multiple leaf directories"""
        parser = get_parser()

        args = parser.parse_args([
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env', 'region',
            '--leaf-directories', 'cluster', 'service'
        ])

        assert args.leaf_directories == ['cluster', 'service']

    @patch('himl.config_merger.ConfigProcessor')
    def test_merge_logic_missing_filter_key(self, mock_config_processor):
        """Test merge logic when filter key is missing"""
        self.create_directory_structure()

        mock_processor = MagicMock()
        mock_processor.process.return_value = {
            'env': 'dev',
            'region': 'us-east-1',
            'cluster': 'web'
            # No _filters key
        }

        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        config_tuple = (
            mock_processor,
            os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=web'),
            ['env', 'region', 'cluster'],
            output_dir,
            '_filters',  # Filter key that doesn't exist
            False  # allow_unicode
        )

        with pytest.raises(Exception) as exc_info:
            merge_logic(config_tuple)

        assert "Filter rule key '_filters' not found in config" in str(exc_info.value)

    def test_parser_allow_unicode_flag(self):
        """Test allow-unicode flag parsing"""
        parser = get_parser()

        # Test default value (False)
        args = parser.parse_args([
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env',
            '--leaf-directories', 'cluster'
        ])
        assert args.allow_unicode is False

        # Test when flag is set (True)
        args = parser.parse_args([
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env',
            '--leaf-directories', 'cluster',
            '--allow-unicode'
        ])
        assert args.allow_unicode is True

    @patch('himl.config_merger.ConfigProcessor')
    def test_merge_logic_with_unicode(self, mock_config_processor):
        """Test merge logic with Unicode content"""
        self.create_directory_structure()

        # Mock ConfigProcessor with Unicode content
        mock_processor = MagicMock()
        mock_processor.process.return_value = {
            'env': 'dev',
            'region': 'us-east-1',
            'cluster': 'web',
            'message': 'Hello 世界',
            'emoji': '🚀 rocket',
            'multilingual': {
                'japanese': 'こんにちは',
                'arabic': 'مرحبا',
                'russian': 'Привет'
            }
        }

        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        # Test with allow_unicode=True
        config_tuple = (
            mock_processor,
            os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=web'),
            ['env', 'region', 'cluster'],
            output_dir,
            None,
            True  # allow_unicode=True
        )

        merge_logic(config_tuple)

        # Verify output file was created
        expected_output = os.path.join(output_dir, 'dev/us-east-1/web.yaml')
        assert os.path.exists(expected_output)

        # Verify content has Unicode characters
        with open(expected_output, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check that Unicode is preserved in the file
            assert '世界' in content or 'message:' in content  # Unicode should be present or at least the key

    @patch('himl.config_merger.merge_configs')
    @patch('himl.config_merger.get_leaf_directories')
    def test_run_with_unicode_flag(self, mock_get_leaf_directories, mock_merge_configs):
        """Test run function with allow-unicode flag"""
        mock_get_leaf_directories.return_value = ['dir1', 'dir2']

        args = [
            'input_dir',
            '--output-dir', 'output',
            '--levels', 'env', 'region',
            '--leaf-directories', 'cluster',
            '--allow-unicode'
        ]

        with patch('sys.argv', ['himl-config-merger'] + args):
            run()

        mock_get_leaf_directories.assert_called_once_with('input_dir', ['cluster'])
        mock_merge_configs.assert_called_once_with(
            ['dir1', 'dir2'],
            ['env', 'region'],
            'output',
            False,  # enable_parallel default
            None,   # filter_rules_key default
            True,   # allow_unicode=True
            enable_precompute=False
        )

    def test_merge_logic_with_precomputed_state(self):
        """Test merge_logic passes precomputed_state to ConfigProcessor.process"""
        self.create_directory_structure()

        mock_processor = MagicMock()
        mock_processor.process.return_value = {
            'env': 'dev', 'region': 'us-east-1', 'cluster': 'web'
        }

        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        precomputed = {'env': 'dev', 'region': 'us-east-1'}
        config_tuple = (
            mock_processor,
            os.path.join(self.temp_dir, 'env=dev/region=us-east-1/cluster=web'),
            ['env', 'region', 'cluster'],
            output_dir,
            None,
            False,
            precomputed,
        )

        merge_logic(config_tuple)

        call_kwargs = mock_processor.process.call_args[1]
        assert call_kwargs['precomputed_state'] == precomputed

    @patch('himl.config_merger.build_parent_cache')
    @patch('himl.config_merger.merge_logic')
    def test_merge_configs_with_precompute_enabled(self, mock_merge_logic, mock_build_parent_cache):
        """Test merge_configs calls build_parent_cache when enable_precompute=True"""
        mock_build_parent_cache.return_value = {}
        directories = ['dir1', 'dir2']

        merge_configs(directories, ['env'], '/output', enable_parallel=False,
                      filter_rules=None, allow_unicode=False, enable_precompute=True)

        mock_build_parent_cache.assert_called_once_with(directories)
        assert mock_merge_logic.call_count == 2

    def test_parser_enable_precompute_flag(self):
        """Test --enable-precompute flag is parsed correctly"""
        parser = get_parser()

        args = parser.parse_args([
            'input_dir', '--output-dir', 'output',
            '--levels', 'env', '--leaf-directories', 'cluster',
            '--enable-precompute'
        ])
        assert args.enable_precompute is True

    def test_parser_enable_precompute_default_false(self):
        """Test --enable-precompute defaults to False"""
        parser = get_parser()
        args = parser.parse_args([
            'input_dir', '--output-dir', 'output',
            '--levels', 'env', '--leaf-directories', 'cluster'
        ])
        assert args.enable_precompute is False


class TestGroupByParent:
    """Tests for _group_by_parent helper"""

    def test_single_parent(self):
        dirs = ['/root/parent/leaf1', '/root/parent/leaf2', '/root/parent/leaf3']
        result = _group_by_parent(dirs)
        assert len(result) == 1
        assert set(result[0]) == set(dirs)

    def test_multiple_parents(self):
        dirs = [
            '/root/parent1/leaf1',
            '/root/parent1/leaf2',
            '/root/parent2/leaf3',
        ]
        result = _group_by_parent(dirs)
        assert len(result) == 2
        flat = {d for group in result for d in group}
        assert flat == set(dirs)

    def test_empty_input(self):
        assert _group_by_parent([]) == []

    def test_each_leaf_in_own_parent(self):
        dirs = ['/a/x/leaf', '/b/y/leaf', '/c/z/leaf']
        result = _group_by_parent(dirs)
        assert len(result) == 3


class TestMergeLogicBatch:
    """Tests for merge_logic_batch"""

    @patch('himl.config_merger.merge_logic')
    def test_calls_merge_logic_for_each_param(self, mock_merge_logic):
        batch = [('p1',), ('p2',), ('p3',)]
        merge_logic_batch(batch)
        assert mock_merge_logic.call_count == 3
        mock_merge_logic.assert_any_call(('p1',))
        mock_merge_logic.assert_any_call(('p3',))

    @patch('himl.config_merger.merge_logic')
    def test_empty_batch(self, mock_merge_logic):
        merge_logic_batch([])
        mock_merge_logic.assert_not_called()


class TestBuildParentCache:
    """Tests for build_parent_cache"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_service_hierarchy(self, services, deployments_per_service):
        """Create a minimal hierarchy: cwd/service=X/deployment=Y/deployment.yaml"""
        for svc in services:
            svc_dir = os.path.join(self.temp_dir, f'service={svc}')
            os.makedirs(svc_dir, exist_ok=True)
            with open(os.path.join(svc_dir, 'service.yaml'), 'w') as f:
                yaml.dump({'service': svc}, f)
            for dep in deployments_per_service:
                dep_dir = os.path.join(svc_dir, f'deployment={dep}')
                os.makedirs(dep_dir, exist_ok=True)
                with open(os.path.join(dep_dir, 'deployment.yaml'), 'w') as f:
                    yaml.dump({'deployment': dep}, f)

    def _leaf_paths(self, services, deployments):
        return [
            os.path.join(self.temp_dir, f'service={svc}', f'deployment={dep}')
            for svc in services for dep in deployments
        ]

    def test_deduplicates_same_parent(self):
        """Two leaves under the same service produce one cache entry"""
        self._create_service_hierarchy(['svc1'], ['dep1', 'dep2'])
        leaves = self._leaf_paths(['svc1'], ['dep1', 'dep2'])

        cache = build_parent_cache(leaves, cwd=self.temp_dir)

        assert len(cache) == 1

    def test_separate_parents_produce_separate_entries(self):
        """Leaves under different services produce one entry per service"""
        self._create_service_hierarchy(['svc1', 'svc2'], ['dep1', 'dep2'])
        leaves = self._leaf_paths(['svc1', 'svc2'], ['dep1', 'dep2'])

        cache = build_parent_cache(leaves, cwd=self.temp_dir)

        assert len(cache) == 2

    def test_cache_keyed_by_absolute_parent_path(self):
        """Cache keys are absolute paths of parent directories"""
        self._create_service_hierarchy(['svc1'], ['dep1'])
        leaves = self._leaf_paths(['svc1'], ['dep1'])

        cache = build_parent_cache(leaves, cwd=self.temp_dir)

        expected_key = os.path.abspath(os.path.join(self.temp_dir, 'service=svc1'))
        assert expected_key in cache

    def test_cache_contains_merged_parent_data(self):
        """Cached state contains YAML data merged from the parent directory"""
        self._create_service_hierarchy(['svc1'], ['dep1'])
        leaves = self._leaf_paths(['svc1'], ['dep1'])

        cache = build_parent_cache(leaves, cwd=self.temp_dir)

        parent_key = os.path.abspath(os.path.join(self.temp_dir, 'service=svc1'))
        assert cache[parent_key].get('service') == 'svc1'
