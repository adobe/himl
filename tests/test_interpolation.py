# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from pytest import mark
from himl.interpolation import DictIterator


@mark.parametrize(
    "start, end, func",
    [
        (
            {"test": [1, 3, 2], "another": {"thing": "is", "some": "data"}},
            {"test": [1, 3, 2], "another": {"thing": "is", "some": "data"}},
            lambda x: x,
        ),
        (
            {"test": [1, 3, 2], "another": {"thing": "is", "some": "data"}},
            {"test": [1, 3, 2], "another": {"thing": "isis", "some": "datadata"}},
            lambda x: 2 * x,
        ),
        (
            [["a", "set"], ["of", "test"], ["data", "for", "testing"], [1, 2, 3]],
            [["a_", "set_"], ["of_", "test_"], ["data_", "for_", "testing_"], [1, 2, 3]],
            lambda x: x + "_",
        ),
    ],
)
def test_dict_iterator(start, end, func):
    looper = DictIterator()
    assert looper.loop_all_items(start, func) == end
