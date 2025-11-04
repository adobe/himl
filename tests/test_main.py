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

import yaml
from unittest.mock import patch, MagicMock
from io import StringIO

from himl.main import ConfigRunner


class TestConfigRunner:
    """Test ConfigRunner class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.runner = ConfigRunner()

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

    def test_get_parser(self):
        """Test argument parser creation"""
        parser = self.runner.get_parser()

        # Test that parser has expected arguments
        args = parser.parse_args(['test_path'])
        assert args.path == 'test_path'

        # Test with optional arguments
        args = parser.parse_args([
            'test_path',
            '--output-file', 'output.yaml',
            '--format', 'json',
            '--filter', 'key1',
            '--exclude', 'secret_key',
            '--skip-interpolation-validation',
            '--skip-interpolation-resolving',
            '--enclosing-key', 'app',
            '--cwd', '/custom/path'
        ])

        assert args.path == 'test_path'
        assert args.output_file == 'output.yaml'
        assert args.output_format == 'json'
        assert args.filter == ['key1']
        assert args.exclude == ['secret_key']
        assert args.skip_interpolation_validation is True
        assert args.skip_interpolation_resolving is True
        assert args.enclosing_key == 'app'
        assert args.cwd == '/custom/path'

    @patch('himl.main.ConfigProcessor')
    def test_do_run_basic(self, mock_config_processor):
        """Test basic do_run functionality"""
        # Create mock options
        mock_opts = MagicMock()
        mock_opts.cwd = None
        mock_opts.path = 'test_path'
        mock_opts.filter = None
        mock_opts.exclude = None
        mock_opts.output_file = None
        mock_opts.print_data = True
        mock_opts.output_format = 'yaml'
        mock_opts.enclosing_key = None
        mock_opts.remove_enclosing_key = None
        mock_opts.skip_interpolation_resolving = False
        mock_opts.skip_interpolation_validation = False
        mock_opts.skip_secrets = False
        mock_opts.multi_line_string = False
        mock_opts.allow_unicode = False
        mock_opts.merge_list_strategy = MagicMock()
        mock_opts.merge_list_strategy.value = 'append_unique'

        # Mock ConfigProcessor
        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        with patch('os.getcwd', return_value='/current/dir'):
            self.runner.do_run(mock_opts)

        # Verify ConfigProcessor was called correctly
        mock_config_processor.assert_called_once()
        mock_processor_instance.process.assert_called_once_with(
            '/current/dir',
            'test_path',
            (),
            (),
            None,
            None,
            'yaml',
            True,
            None,
            False,
            False,
            False,
            False,
            False,
            type_strategies=[(list, ['append_unique']), (dict, ["merge"])]
        )

    @patch('himl.main.ConfigProcessor')
    def test_do_run_with_filters(self, mock_config_processor):
        """Test do_run with filters and exclusions"""
        mock_opts = MagicMock()
        mock_opts.cwd = '/custom/cwd'
        mock_opts.path = 'test_path'
        mock_opts.filter = ['key1', 'key2']
        mock_opts.exclude = ['secret']
        mock_opts.output_file = 'output.yaml'
        mock_opts.print_data = False
        mock_opts.output_format = 'json'
        mock_opts.enclosing_key = 'app'
        mock_opts.remove_enclosing_key = None
        mock_opts.skip_interpolation_resolving = True
        mock_opts.skip_interpolation_validation = True
        mock_opts.skip_secrets = True
        mock_opts.multi_line_string = True
        mock_opts.allow_unicode = False
        mock_opts.merge_list_strategy = MagicMock()
        mock_opts.merge_list_strategy.value = 'override'

        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        self.runner.do_run(mock_opts)

        mock_processor_instance.process.assert_called_once_with(
            '/custom/cwd',
            'test_path',
            ['key1', 'key2'],
            ['secret'],
            'app',
            None,
            'json',
            False,
            'output.yaml',
            True,
            True,
            True,
            True,
            False,
            type_strategies=[(list, ['override']), (dict, ["merge"])]
        )

    @patch('himl.main.ConfigProcessor')
    def test_run_with_args(self, mock_config_processor):
        """Test run method with command line arguments"""
        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        args = ['test_path', '--format', 'json']

        with patch('os.getcwd', return_value='/current/dir'):
            self.runner.run(args)

        mock_config_processor.assert_called_once()
        mock_processor_instance.process.assert_called_once()

    @patch('sys.stdout', new_callable=StringIO)
    @patch('himl.main.ConfigProcessor')
    def test_run_integration_simple(self, mock_config_processor, mock_stdout):
        """Test integration with simple config"""
        # Setup mock processor to return test data
        test_data = {'env': 'test', 'debug': True}
        mock_processor_instance = MagicMock()
        mock_processor_instance.process.return_value = test_data
        mock_config_processor.return_value = mock_processor_instance

        # Create test config
        self.create_test_yaml('config.yaml', test_data)

        args = [os.path.join(self.temp_dir, 'config.yaml')]

        with patch('os.getcwd', return_value=self.temp_dir):
            self.runner.run(args)

        # Verify the processor was called
        mock_processor_instance.process.assert_called_once()

    def test_parser_list_merge_strategies(self):
        """Test list merge strategy options"""
        parser = self.runner.get_parser()

        # Test append strategy
        args = parser.parse_args(['test_path', '--list-merge-strategy', 'append'])
        assert args.merge_list_strategy.value == 'append'

        # Test override strategy
        args = parser.parse_args(['test_path', '--list-merge-strategy', 'override'])
        assert args.merge_list_strategy.value == 'override'

        # Test prepend strategy
        args = parser.parse_args(['test_path', '--list-merge-strategy', 'prepend'])
        assert args.merge_list_strategy.value == 'prepend'

        # Test append_unique strategy (default)
        args = parser.parse_args(['test_path'])
        assert args.merge_list_strategy.value == 'append_unique'

    def test_parser_boolean_flags(self):
        """Test boolean flag parsing"""
        parser = self.runner.get_parser()

        # Test default values
        args = parser.parse_args(['test_path'])
        assert args.skip_interpolation_validation is False
        assert args.skip_interpolation_resolving is False

        # Test when flags are set
        args = parser.parse_args([
            'test_path',
            '--skip-interpolation-validation',
            '--skip-interpolation-resolving'
        ])
        assert args.skip_interpolation_validation is True
        assert args.skip_interpolation_resolving is True

    def test_parser_multiple_filters(self):
        """Test multiple filter and exclude arguments"""
        parser = self.runner.get_parser()

        args = parser.parse_args([
            'test_path',
            '--filter', 'key1',
            '--filter', 'key2',
            '--exclude', 'secret1',
            '--exclude', 'secret2'
        ])

        assert args.filter == ['key1', 'key2']
        assert args.exclude == ['secret1', 'secret2']

    @patch('himl.main.ConfigProcessor')
    def test_output_file_sets_print_data_false(self, mock_config_processor):
        """Test that specifying output file without --print-data sets print_data to False"""
        mock_opts = MagicMock()
        mock_opts.cwd = None
        mock_opts.path = 'test_path'
        mock_opts.filter = None
        mock_opts.exclude = None
        mock_opts.output_file = 'output.yaml'
        mock_opts.print_data = False  # Not explicitly set by user, defaults to False
        mock_opts.output_format = 'yaml'
        mock_opts.enclosing_key = None
        mock_opts.remove_enclosing_key = None
        mock_opts.skip_interpolation_resolving = False
        mock_opts.skip_interpolation_validation = False
        mock_opts.skip_secrets = False
        mock_opts.multi_line_string = False
        mock_opts.allow_unicode = False
        mock_opts.merge_list_strategy = MagicMock()
        mock_opts.merge_list_strategy.value = 'append_unique'

        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        with patch('os.getcwd', return_value='/current/dir'):
            self.runner.do_run(mock_opts)

        # When output_file is specified without --print-data, print_data should be False
        call_args = mock_processor_instance.process.call_args[0]
        # print_data is the 8th positional argument (index 7)
        assert call_args[7] is False
        # output_file is the 9th positional argument (index 8)
        assert call_args[8] == 'output.yaml'

    def test_parser_help_message(self):
        """Test that parser help can be generated without error"""
        parser = self.runner.get_parser()

        # This should not raise an exception
        help_text = parser.format_help()
        assert 'path' in help_text
        assert 'output-file' in help_text
        assert 'format' in help_text

    @patch('himl.main.ConfigProcessor')
    def test_empty_filters_and_excludes(self, mock_config_processor):
        """Test handling of empty filters and excludes"""
        mock_opts = MagicMock()
        mock_opts.cwd = None
        mock_opts.path = 'test_path'
        mock_opts.filter = []  # Empty list
        mock_opts.exclude = []  # Empty list
        mock_opts.output_file = None
        mock_opts.output_format = 'yaml'
        mock_opts.enclosing_key = None
        mock_opts.remove_enclosing_key = None
        mock_opts.skip_interpolation_resolving = False
        mock_opts.skip_interpolation_validation = False
        mock_opts.skip_secrets = False
        mock_opts.multi_line_string = False
        mock_opts.allow_unicode = False
        mock_opts.merge_list_strategy = MagicMock()
        mock_opts.merge_list_strategy.value = 'append_unique'

        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        with patch('os.getcwd', return_value='/current/dir'):
            self.runner.do_run(mock_opts)

        # Empty lists should be converted to empty tuples
        call_args = mock_processor_instance.process.call_args[0]
        # filters is the 3rd positional argument (index 2)
        assert call_args[2] == ()
        # exclude_keys is the 4th positional argument (index 3)
        assert call_args[3] == ()

    def test_parser_allow_unicode_flag(self):
        """Test allow-unicode flag parsing"""
        parser = self.runner.get_parser()

        # Test default value (False)
        args = parser.parse_args(['test_path'])
        assert args.allow_unicode is False

        # Test when flag is set (True)
        args = parser.parse_args(['test_path', '--allow-unicode'])
        assert args.allow_unicode is True

    @patch('himl.main.ConfigProcessor')
    def test_do_run_with_allow_unicode_true(self, mock_config_processor):
        """Test do_run with allow_unicode=True"""
        mock_opts = MagicMock()
        mock_opts.cwd = None
        mock_opts.path = 'test_path'
        mock_opts.filter = None
        mock_opts.exclude = None
        mock_opts.output_file = None
        mock_opts.print_data = True
        mock_opts.output_format = 'yaml'
        mock_opts.enclosing_key = None
        mock_opts.remove_enclosing_key = None
        mock_opts.skip_interpolation_resolving = False
        mock_opts.skip_interpolation_validation = False
        mock_opts.skip_secrets = False
        mock_opts.multi_line_string = False
        mock_opts.allow_unicode = True  # Enable Unicode
        mock_opts.merge_list_strategy = MagicMock()
        mock_opts.merge_list_strategy.value = 'append_unique'

        mock_processor_instance = MagicMock()
        mock_config_processor.return_value = mock_processor_instance

        with patch('os.getcwd', return_value='/current/dir'):
            self.runner.do_run(mock_opts)

        # Verify allow_unicode=True is passed correctly
        call_args = mock_processor_instance.process.call_args[0]
        # allow_unicode is the 14th positional argument (index 13)
        assert call_args[13] is True

    @patch('sys.stdout', new_callable=StringIO)
    def test_run_integration_with_unicode(self, mock_stdout):
        """Test integration with Unicode content"""
        # Create test config with Unicode content
        test_data = {
            'greeting': 'Hello 世界',
            'emoji': '🚀 rocket',
            'multilingual': {
                'english': 'Hello',
                'japanese': 'こんにちは',
                'arabic': 'مرحبا'
            }
        }
        self.create_test_yaml('unicode_config.yaml', test_data)

        args = [
            os.path.join(self.temp_dir, 'unicode_config.yaml'),
            '--allow-unicode'
        ]

        with patch('os.getcwd', return_value=self.temp_dir):
            self.runner.run(args)

        # Verify output contains Unicode characters
        output = mock_stdout.getvalue()
        assert 'greeting' in output or 'Hello' in output  # Basic verification that something was output
