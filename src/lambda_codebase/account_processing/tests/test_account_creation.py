"""
Tests the account creation lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from ..create_account import create_account


# pylint: disable=W0106
class SuccessTestCase(unittest.TestCase):
    def test_account_creation(self):
        test_account = {
            "account_full_name": "ADF Test Creation Account",
            "email": "test+account@domain.com",
        }
        iam_client = boto3.client("organizations")
        stubber = Stubber(iam_client)
        create_account_response = {
            "CreateAccountStatus": {"State": "IN_PROGRESS", "Id": "1234567890"}
        }
        describe_account_response = {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
                "AccountId": "9087564231",
                "Id": "1234567890",
            }
        }
        describe_account_response_complete = {
            "CreateAccountStatus": {
                "State": "SUCCEEDED",
                "AccountId": "9087564231",
                "Id": "1234567890",
            }
        }
        stubber.add_response(
            "create_account",
            create_account_response,
            {
                "Email": test_account.get("email"),
                "AccountName": test_account.get("account_full_name"),
                "RoleName": "OrganizationAccountAccessRole",
                "IamUserAccessToBilling": "DENY",
            },
        ),
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response,
            {"CreateAccountRequestId": "1234567890"},
        )
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response_complete,
            {"CreateAccountRequestId": "1234567890"},
        )

        stubber.activate()
        response = create_account(
            test_account, "OrganizationAccountAccessRole", iam_client
        )
        self.assertDictEqual(response, test_account)


class FailuteTestCase(unittest.TestCase):
    def test_account_creation_failure(self):
        test_account = {
            "account_full_name": "ADF Test Creation Account",
            "email": "test+account@domain.com",
        }
        iam_client = boto3.client("organizations")
        stubber = Stubber(iam_client)
        create_account_response = {
            "CreateAccountStatus": {"State": "IN_PROGRESS", "Id": "1234567890"}
        }
        describe_account_response = {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
                "AccountId": "9087564231",
                "Id": "1234567890",
            }
        }
        describe_account_response_complete = {
            "CreateAccountStatus": {
                "State": "FAILED",
                "AccountId": "9087564231",
                "Id": "1234567890",
                "FailureReason": "ACCOUNT_LIMIT_EXCEEDED",
            }
        }
        stubber.add_response(
            "create_account",
            create_account_response,
            {
                "Email": test_account.get("email"),
                "AccountName": test_account.get("account_full_name"),
                "RoleName": "OrganizationAccountAccessRole",
                "IamUserAccessToBilling": "DENY",
            },
        ),
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response,
            {"CreateAccountRequestId": "1234567890"},
        )
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response_complete,
            {"CreateAccountRequestId": "1234567890"},
        )

        stubber.activate()
        with self.assertRaises(Exception):
            create_account(test_account, "OrganizationAccountAccessRole", iam_client)
