# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
import os

import hvac


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


logger = logging.getLogger(__name__)


class SimpleVault:
    def __init__(self):
        pass

    def get_vault_client(self):
        url = os.getenv('VAULT_ADDR')
        namespace = os.getenv('VAULT_NAMESPACE')
        verify = not strtobool(os.getenv('VAULT_SKIP_VERIFY', 'false'))

        logger.info("Vault using url: {}, namespace: {}".format(url, namespace))
        if not verify:
            logger.warning("Using insecure vault endpoint, verify: {}".format(verify))

        client = hvac.Client(
            url=url,
            namespace=namespace,
            verify=verify,
        )

        authenticated = client.is_authenticated()

        if not authenticated:
            logger.info("Vault not authenticated, trying LDAP fallback")

            password = os.getenv('VAULT_PASSWORD')
            username = os.getenv('VAULT_USERNAME')
            try:
                client.auth.ldap.login(
                    username=username,
                    password=password,
                )
                assert client.is_authenticated()
                logger.info("Vault LDAP authenticated")
            except Exception:
                raise Exception("Error authenticating Vault over LDAP")

        return client

    def get_token(self, policy):
        role = os.getenv('VAULT_ROLE')
        client = self.get_vault_client()
        logger.info("Generating token for policy: {} using role: {}".format(policy, role))

        token = client.create_token(
            policies=[policy],
            role=role,
            lease='24h',
        )

        return token['auth']['client_token']

    def get_path(self, path):
        mount_point = os.getenv('VAULT_MOUNT_POINT', 'kv')
        client = self.get_vault_client()
        result = client.secrets.kv.v2.read_secret_version(mount_point=mount_point, path=path)
        secret_data = result['data']['data']

        return secret_data

    def get_key(self, path, key):
        secret_data = self.get_path(path)
        secret_key_value = secret_data[key]

        return secret_key_value
