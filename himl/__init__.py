# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from .config_generator import ConfigGenerator, ConfigProcessor
from .main import ConfigRunner

# Make imports available at package level
__all__ = ['ConfigGenerator', 'ConfigProcessor', 'ConfigRunner', '__version__']

try:
    from ._version import version as __version__
except ImportError:
    # Fallback for development installs
    __version__ = "unknown"
    try:
        from importlib.metadata import version
        __version__ = version("himl")
    except ImportError:
        try:
            # Fallback for Python < 3.8
            from importlib_metadata import version as fallback_version
            __version__ = fallback_version("himl")
        except ImportError:
            pass
