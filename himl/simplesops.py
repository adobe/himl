# Copyright (c), Edoardo Tenani <e.tenani@arduino.cc>, 2018-2020
# Simplified BSD License (see LICENSES/BSD-2-Clause.txt or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function

import os, logging

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
        if exit_code in SOPS_ERROR_CODES:
            exception_name = SOPS_ERROR_CODES[exit_code]
            message = "error with file %s: %s exited with code %d: %s" % (
                filename,
                exception_name,
                exit_code,
                message.decode("utf-8"),
            )
        else:
            message = (
                "could not %s file %s; Unknown sops error code: %s; message: %s"
                % (
                    "decrypt" if decryption else "encrypt",
                    filename,
                    exit_code,
                    message.decode("utf-8"),
                )
            )
        super(SopsError, self).__init__(message)


class Sops:
    """Utility class to perform sops CLI actions"""

    @staticmethod
    def decrypt(
        encrypted_file,
        secret_key=None,
        decode_output=True,
        rstrip=True,
    ):
        command = ["sops"]
        env = os.environ.copy()
        if secret_key is None:
            raise Exception(
                "Error while getting secret for %s: secret key not supplied"
                % encrypted_file
            )
        command.extend(["--extract", secret_key])
        command.extend(["--decrypt", encrypted_file])
        print(command)
        process = Popen(
            command,
            stdin=None,
            stdout=PIPE,
            stderr=PIPE,
            env=env,
        )
        (output, err) = process.communicate()
        exit_code = process.returncode

        if decode_output:
            # output is binary, we want UTF-8 string
            output = output.decode("utf-8", errors="surrogate_or_strict")
            # the process output is the decrypted secret; be cautious
        if exit_code != 0:
            raise SopsError(encrypted_file, exit_code, err, decryption=True)

        if rstrip:
            output = output.rstrip()

        return output


class SimpleSops:
    def __init__(self):
        pass

    def get(self, secret_file, secret_key):
        try:
            logger.info(
                "Resolving sops secret %s from file %s", secret_key, secret_file
            )
            return Sops.decrypt(encrypted_file=secret_file, secret_key=secret_key)
        except SopsError as e:
            raise Exception(
                "Error while trying to read sops value for file %s, key: %s - %s"
                % (secret_file, secret_key, e)
            )
