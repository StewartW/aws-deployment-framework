# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates or updates an ALIAS for an account
"""

import os
from sts import STS
from aws_xray_sdk.core import patch_all

patch_all()

ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")


def create_account_alias(account, iam_client):
    print(
        f"Ensuring Account: {account.get('account_full_name')} has alias {account.get('alias')}"
    )
    try:
        iam_client.create_account_alias(AccountAlias=account.get("alias"))
    except iam_client.exceptions.EntityAlreadyExistsException:
        pass
    return account


def lambda_handler(event, _):
    if event.get("alias"):
        print(
            f"Ensuring Account: {event.get('account_full_name')} has alias {event.get('alias')}"
        )
        sts = STS()
        account_id = event.get("Id")
        role = sts.assume_cross_account_role(
            f"arn:aws:iam::{account_id}:role/{ADF_ROLE_NAME}",
            "adf_account_alias_config",
        )
        create_account_alias(event, role.client("iam"))
    else:
        print(
            f"Ensuring Account: {event.get('account_full_name')} does not need an alias"
        )
    return event
