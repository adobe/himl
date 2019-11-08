# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import boto3
import logging
import os
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

class SimpleS3(object):
    def __init__(self, aws_profile, region_name):
        self.aws_profile = aws_profile
        self.region_name = region_name

    def get(self, bucket_name, bucket_key, base64Encode=False):
        try:
            logger.info("Resolving S3 object for bucket %s, key '%s' on profile %s in region %s", 
                bucket_name, bucket_key, self.aws_profile, self.region_name)
            client = self.get_s3_client()
            bucket_object = client.get_object(Bucket=bucket_name, Key=bucket_key)["Body"].read()
            return self.parse_data(bucket_object, base64Encode)
        except ClientError as e:
            raise Exception(
                'Error while trying to read S3 value for bucket_name %s, bucket_key: %s - %s' 
                % (bucket_name, bucket_key, e.response['Error']['Code']))

    def parse_data(self, bucket_object, base64Encode):
        if base64Encode:
            import base64
            encodedBytes = base64.b64encode(bucket_object)
            return str(encodedBytes, "utf-8")
        return bucket_object

    def get_s3_client(self):
        session = boto3.session.Session(profile_name=self.aws_profile)
        return session.client('s3')
