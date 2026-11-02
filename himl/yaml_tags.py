# Copyright 2026 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from enum import Enum
from typing import cast

import yaml


class _DeleteMarker(Enum):
    DELETE = "delete"


DELETE = _DeleteMarker.DELETE


def construct_delete(loader, node):
    if not isinstance(node, yaml.ScalarNode) or node.value != "":
        raise yaml.constructor.ConstructorError(None, None, "!delete requires an empty scalar", node.start_mark)
    return DELETE


def loader_with_delete_tag(base_loader):
    loader = cast(type[yaml.SafeLoader], type("HimlDeleteLoader", (base_loader,), {}))
    loader.add_constructor("!delete", construct_delete)
    return loader
