#!/usr/bin/env python3
# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import argparse
import logging
import os
import sys
import yaml
from .config_generator import ConfigProcessor

logger = logging.getLogger(__name__)


class Loader(yaml.SafeLoader):
    """
    Overloading the default YAML Loader by adding the custom include tag
    """

    ROOT_DIR = os.path.abspath(os.curdir)

    def __init__(self, stream):

        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        """
        Method implementing the custom include tag logic that will grab a value from a yaml key in a specified folder
        at a specified path
        :param node: String containing the path and key variables
        :return: String values representing the extracted value for the specified path, key combination under node
        """
        path, key = self.construct_yaml_str(node).split(" ")
        filename = os.path.join(self.ROOT_DIR, path)

        with open(filename, 'r') as f:
            yaml_structure = yaml.load(f, Loader)
            return self.__traverse_path(path=key, yaml_dict=yaml_structure)

    def __traverse_path(self, path: str, yaml_dict: dict):
        """
        Method for safe traversing a yaml dictionary to extract a value from a key path
        :param path: String representing the keys needed to traverse the dictionary
        :param yaml_dict: YAML dictionary
        :return: String representing the value for the key path specified
        """
        keys = path.split(".")

        current_key = keys.pop(0)

        if current_key in yaml_dict:
            if len(keys) == 0:
                return yaml_dict[current_key]
            else:
                if isinstance(yaml_dict[current_key], dict):
                    return self.__traverse_path(path=".".join(keys), yaml_dict=yaml_dict[current_key])
                else:
                    raise Exception("{1}[{0}] is not traversable.".format(current_key, yaml_dict))
        else:
            raise Exception("Key not found for {0} in dictionary {1}.".format(current_key, yaml_dict))


def merge_configs(directories, levels, output_dir):
    """
    Method for running the merge configuration logic under different formats
    :param directories: list of paths for leaf directories
    :param levels: list of hierarchy levels to traverse
    :param output_dir: where to save the generated configs
    """
    config_processor = ConfigProcessor()
    merge_logic(config_processor, directories, levels, output_dir)


def merge_logic(config_processor, directories, levels, output_dir):
    """
    Method implementing the merge config logic
    :param config_processor: the HIML config Processor
    :param directories: list of paths for directories to run the config merge logic
    :param levels: list of hierarchy levels to traverse
    :param output_dir: where to save the generated configs
    """
    for path in directories:

        # use the HIML deep merge functionality
        output = dict(
            config_processor.process(path=path, output_format="yaml", print_data=False, multi_line_string=True))

        # exchange the levels to which to run for with the values extracted from the yaml structure
        level_values = [output.get(level) for level in levels]

        # create the publish path and all level_values except the last one
        publish_path = os.path.join(output_dir, '') + '/'.join(level_values[:-1])
        if not os.path.exists(publish_path):
            os.makedirs(publish_path)

        # create the yaml file for output using the publish_path and last level_values element
        filename = "{0}/{1}.yaml".format(publish_path, level_values[-1])
        logger.info("Found input config directory: %s", path)
        logger.info("Storing generated config to: %s", filename)
        with open(filename, "w+") as f:
            f.write(yaml.dump(output))


def is_leaf_directory(dir, leaf_directories):
    return any(dir.startswith(leaf) for leaf in leaf_directories)


def get_leaf_directories(src, leaf_directories):
    """
    Method for doing a deep search of directories matching either the desired
    leaf directorie.
    :param src: the source path to start looking from
    :return: the list of absolute paths
    """
    directories = []

    for root, dirs, files in os.walk(src):
        for dr in dirs:
            # if directory is hidden skip
            if dr.startswith('.') or root.split("/")[1].startswith("."):
                continue
            elif is_leaf_directory(dr, leaf_directories):
                directory = root + "/" + dr
                directories.append(directory)
            else:
                continue

    if len(directories) == 0:
        sys.exit("No leaf directories found")

    return directories


def parser_options(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='The configs directory')

    parser.add_argument('--output-dir', dest='output_dir', type=str,
                        help='output directory, where generated configs will be saved', required=True)
    parser.add_argument('--levels', dest='hierarchy_levels', nargs='+',
                        help='hierarchy levels, for instance: env, region, cluster', required=True)
    parser.add_argument('--leaf-directories', dest='leaf_directories', nargs='+',
                        help='leaf directories, for instance: cluster', required=True)
    return parser.parse_args(args)


def run(args=None):
    opts = parser_options(args)

    # load the !include tag
    Loader.add_constructor('!include', Loader.include)

    # override the Yaml FullLoader with our custom loader
    yaml.FullLoader = Loader

    # extract the list of absolute paths for leaf directories
    dirs = get_leaf_directories(opts.path, opts.leaf_directories)

    # merge the configs using HIML
    merge_configs(dirs, opts.hierarchy_levels, opts.output_dir)
