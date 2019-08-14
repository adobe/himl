# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import sys

PY3 = sys.version_info >= (3, 0)

if PY3:
    iteritems = lambda d: iter(d.items())
    integer_types = (int,)
    string_types = (str,)
    primitive_types = (str, int, bool)
else:
    iteritems = lambda d: d.iteritems()
    integer_types = (int, long)
    string_types = (str, unicode)
    primitive_types = (str, unicode, int, long, bool)
