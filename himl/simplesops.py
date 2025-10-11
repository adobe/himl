# Copyright (c), Edoardo Tenani <e.tenani@arduino.cc>, 2018-2020
# Simplified BSD License (see LICENSES/BSD-2-Clause.txt or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function
from functools import lru_cache

import os
import logging
import yaml

from subprocess import Popen, PIPE

logger = logging.getLogger(__name__)

# From https://github.com/getsops/sops/blob/master/cmd/sops/codes/codes.go
# Should be manually updated
SOPS_ERROR_CODES = {
    1: "ErrorGeneric",
    2: "CouldNotReadInputFile",
    3: "CouldNotWriteOutputFile",
    4: "ErrorDumpingTree",
    5: "ErrorReadingConfig",
    6: "ErrorInvalidKMSEncryptionContextFormat",
    7: "ErrorInvalidSetFormat",
    8: "ErrorConflictingParameters",
    21: "ErrorEncryptingMac",
    23: "ErrorEncryptingTree",
    24: "ErrorDecryptingMac",
    25: "ErrorDecryptingTree",
    49: "CannotChangeKeysFromNonExistentFile",
    51: "MacMismatch",
    52: "MacNotFound",
    61: "ConfigFileNotFound",
    85: "KeyboardInterrupt",
    91: "InvalidTreePathFormat",
    100: "NoFileSpecified",
    128: "CouldNotRetrieveKey",
    111: "NoEncryptionKeyFound",
    200: "FileHasNotBeenModified",
    201: "NoEditorFound",
    202: "FailedToCompareVersions",
    203: "FileAlreadyEncrypted",
}


class SopsError(Exception):
    """Extend Exception class with sops specific information"""

    def __init__(self, filename, exit_code, message, decryption=True):
        self.filename = filename
        self.exit_code = exit_code
        self.stderr = message
        self.decryption = decryption

        if exit_code in SOPS_ERROR_CODES:
            exception_name = SOPS_ERROR_CODES[exit_code]
            formatted_message = "error with file %s: %s exited with code %d: %s" % (
                filename,
                exception_name,
                exit_code,
                message,
            )
        else:
            formatted_message = (
                "could not %s file %s; Unknown sops error code: %s; message: %s"
                % (
                    "decrypt" if decryption else "encrypt",
                    filename,
                    exit_code,
                    message,
                )
            )
        super(SopsError, self).__init__(formatted_message)


class Sops:
    """Utility class to perform sops CLI actions"""

    @staticmethod
    @lru_cache(maxsize=2048)
    def decrypt(
        encrypted_file: str,
        decode_output: bool = True,
        rstrip: bool = True,
    ):
        command = ["sops"]
        env = os.environ.copy()

        command.extend(["--decrypt", encrypted_file])
        process = Popen(
            command,
            stdin=None,
            stdout=PIPE,
            stderr=PIPE,
            env=env,
        )
        (output_bytes, err) = process.communicate()
        exit_code = process.returncode

        if decode_output:
            # output is binary, we want UTF-8 string
            output: str = output_bytes.decode("utf-8", errors="surrogate_or_strict")
            # the process output is the decrypted secret; be cautious
        else:
            output = output_bytes.decode("utf-8", errors="surrogate_or_strict")
        if exit_code != 0:
            raise SopsError(encrypted_file, exit_code, err, decryption=True)

        if rstrip:
            output = output.rstrip()
        return yaml.full_load(output)

    def get_keys(self, secret_file, secret_key):
        result = Sops.decrypt(secret_file)
        secret_key_path = secret_key.strip("[]")
        keys = [key.strip("'") for key in secret_key_path.split("']['")]
        try:
            for key in keys:
                result = result[key]
        except KeyError:
            raise SopsError(secret_file, 128, "Encountered KeyError parsing yaml for key: %s" % secret_key,
                            decryption=True)
        return result


class SimpleSops:
    def __init__(self):
        pass

    def get(self, secret_file, secret_key):
        try:
            logger.info(
                "Resolving sops secret %s from file %s", secret_key, secret_file
            )
            return Sops().get_keys(secret_file=secret_file, secret_key=secret_key)
        except SopsError as e:
            raise Exception(
                "Error while trying to read sops value for file %s, key: %s - %s"
                % (secret_file, secret_key, e)
            )
