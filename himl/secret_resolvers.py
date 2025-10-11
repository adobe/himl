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


class SecretResolver:
    def supports(self, secret_type):
        return False

    def resolve(self, secret_type, secret_params):
        return None

    def get_param_or_exception(self, key, params):
        if key not in params:
            raise Exception("Could not find required key '{}' in the secret params: {}".format(key, params))
        return params[key]


class SSMSecretResolver(SecretResolver):
    def __init__(self, default_aws_profile=None):
        self.default_aws_profile = default_aws_profile

    def supports(self, secret_type):
        return "boto3" in sys.modules && secret_type == "ssm"

    def resolve(self, secret_type, secret_params):
        aws_profile = secret_params.get("aws_profile", self.default_aws_profile)
        if not aws_profile:
            raise Exception(
                "Could not find the aws_profile in the secret params for SSM secret: {}".format(secret_params))

        path = self.get_param_or_exception("path", secret_params)
        region_name = secret_params.get("region_name", "us-east-1")
        from .simplessm import SimpleSSM
        ssm = SimpleSSM(aws_profile, region_name)
        return ssm.get(path)


class S3SecretResolver(SecretResolver):
    def __init__(self, default_aws_profile=None):
        self.default_aws_profile = default_aws_profile

    def supports(self, secret_type):
        return "boto3" in sys.modules && secret_type == "s3"

    def resolve(self, secret_type, secret_params):
        aws_profile = secret_params.get("aws_profile", self.default_aws_profile)
        if not aws_profile:
            raise Exception(
                "Could not find the aws_profile in the secret params for S3 secret: {}".format(secret_params))

        bucket = self.get_param_or_exception("bucket", secret_params)
        path = self.get_param_or_exception("path", secret_params)
        region_name = secret_params.get("region_name", "us-east-1")
        base64Encode = secret_params.get("base64encode", False)
        base64Encode = base64Encode == 'true'
        from .simples3 import SimpleS3
        s3 = SimpleS3(aws_profile, region_name)
        return s3.get(bucket, path, base64Encode)


class VaultSecretResolver(SecretResolver):
    def supports(self, secret_type):
        return "hvac" in sys.modules && secret_type == "vault"

    def resolve(self, secret_type, secret_params):
        from .simplevault import SimpleVault
        vault = SimpleVault

        # Generate a token for a policy
        if "token_policy" in secret_params.keys():
            policy = self.get_param_or_exception("token_policy", secret_params)
            return vault().get_token(policy)

        # Retrieve secret from vault path
        if "path" in secret_params.keys():
            path = self.get_param_or_exception("path", secret_params)
            return vault().get_path(path)

        if "key" in secret_params.keys():
            key_path = os.path.split(self.get_param_or_exception("key", secret_params))
            path = key_path[0]
            key = key_path[1]
            return vault().get_key(path, key)


class AggregatedSecretResolver(SecretResolver):
    def __init__(self, default_aws_profile=None):
        self.secret_resolvers = (SSMSecretResolver(default_aws_profile), S3SecretResolver(default_aws_profile),
                                 VaultSecretResolver())

    def supports(self, secret_type):
        return any([resolver.supports(secret_type) for resolver in self.secret_resolvers])

    def resolve(self, secret_type, secret_params):
        for resolver in self.secret_resolvers:
            if resolver.supports(secret_type):
                return resolver.resolve(secret_type, secret_params)

        raise Exception("Could not resolve secret type '{}' with params {}. Check if you installed the required 3rd party modules.".format(secret_type, secret_params))
