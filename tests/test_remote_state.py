# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import json
from unittest.mock import patch, MagicMock

from himl.remote_state import S3TerraformRemoteStateRetriever


class TestS3TerraformRemoteStateRetriever:
    """Test S3TerraformRemoteStateRetriever class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.retriever = S3TerraformRemoteStateRetriever()

    @patch('boto3.session.Session')
    def test_get_s3_client_success(self, mock_session):
        """Test successful S3 client creation and object retrieval"""
        # Mock the S3 client and response
        mock_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_client
        mock_session.return_value = mock_session_instance

        # Mock S3 response
        terraform_state = {
            'version': 4,
            'terraform_version': '1.0.0',
            'outputs': {
                'vpc_id': {'value': 'vpc-12345'},
                'subnet_ids': {'value': ['subnet-1', 'subnet-2']}
            }
        }
        mock_client.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=json.dumps(terraform_state).encode()))
        }

        result = S3TerraformRemoteStateRetriever.get_s3_client(
            'my-terraform-bucket',
            'path/to/terraform.tfstate',
            'my-aws-profile'
        )

        assert result == terraform_state
        mock_session.assert_called_once_with(profile_name='my-aws-profile')
        mock_session_instance.client.assert_called_once_with('s3')
        mock_client.get_object.assert_called_once_with(
            Bucket='my-terraform-bucket',
            Key='path/to/terraform.tfstate'
        )

    @patch.object(S3TerraformRemoteStateRetriever, 'get_s3_client')
    def test_get_dynamic_data_empty_states(self, mock_get_s3_client):
        """Test dynamic data retrieval with empty remote states list"""
        result = self.retriever.get_dynamic_data([])

        expected = {'outputs': {}}
        assert result == expected
        mock_get_s3_client.assert_not_called()
