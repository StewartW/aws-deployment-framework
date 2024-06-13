# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy module used throughout the ADF.
"""

import glob
import os
import ast
import json
import boto3

from logger import configure_logger
from organization_policy_campaign import (
    OrganizationPolicyApplicationCampaign,
)
from errors import ParameterNotFoundError


from organizations import Organizations

from organization_policy_schema import OrgPolicySchema

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")
DEFAULT_ADF_POLICIES_DIR = "./adf-policies"


class OrganizationPolicy:
    adf_policies_dir: str

    def __init__(self, adf_policies_dir=None):
        self.adf_policies_dir = adf_policies_dir or DEFAULT_ADF_POLICIES_DIR

    @staticmethod
    def _find_all_legacy_policies(policy):
        _files = list(
            glob.iglob(
                f"./adf-bootstrap/**/{policy}.json",
                recursive=True,
            )
        )
        return [f.replace("./adf-bootstrap", ".") for f in _files]

    def _find_all_polices(self, policy):
        _files = list(
            glob.iglob(
                f"{self.adf_policies_dir}/{policy}/*.json",
                recursive=True,
            )
        )
        return [f.replace(f"{self.adf_policies_dir}", ".") for f in _files]

    @staticmethod
    def _trim_scp_file_name(policy):
        LOGGER.info("Policy is: %s" % policy)
        return policy[1:][:-8] if policy[1:][:-8] == "/" else policy[2:][:-9]

    @staticmethod
    def _trim_tagging_policy_file_name(policy):
        return policy[1:][:-19] if policy[1:][:-19] == "/" else policy[2:][:-20]

    @staticmethod
    def _is_govcloud(region: str) -> bool:
        """
        Evaluates the region to determine if it is part of GovCloud.

        :param region: a region (us-east-1, us-gov-west-1)
        :return: Returns True if the region is GovCloud, False otherwise.
        """
        return region.startswith("us-gov")

    def get_policy_body(self, path):
        with open(
            f"{self.adf_policies_dir}/{path}", mode="r", encoding="utf-8"
        ) as policy:
            return json.dumps(json.load(policy))

    def apply(
        self, organizations, parameter_store, config
    ):  # pylint: disable=R0912, R0915
        status = organizations.get_organization_info()
        if status.get("feature_set") != "ALL":
            LOGGER.info(
                "All Features are currently NOT enabled for this Organization, "
                "this is required to apply SCPs or Tagging Policies",
            )
            return

        supported_policies = {
            "scp": "SERVICE_CONTROL_POLICY",
            "tagging-policy": "TAG_POLICY",
        }

        if self._is_govcloud(REGION_DEFAULT):
            supported_policies = {
                "scp": "SERVICE_CONTROL_POLICY",
            }

        LOGGER.info(
            "Currently supported policy types: %s", supported_policies.values()
        )
        for _, policy_type in supported_policies.items():
            organizations.enable_organization_policies(policy_type)

        LOGGER.info("Building organization map")
        organization_mapping = organizations.get_organization_map(
            {
                "/": organizations.get_ou_root_id(),
            }
        )
        LOGGER.info("Organization map built!")

        self.apply_policies(
            boto3.client("organizations"),
            parameter_store,
            config,
            organization_mapping,
            supported_policies,
        )
        
    # pylint: disable=R0914
    def apply_policies(
        self,
        organizations,
        parameter_store,
        config,
        organization_mapping,
        supported_policies,
    ):
        LOGGER.info("V2 Method for applying policies")
        for policy, policy_type in supported_policies.items():
            _type = policy_type
            campaign = OrganizationPolicyApplicationCampaign(
                _type,
                organization_mapping,
                config.get("scp"),
                organizations,
            )
            _legacy_policies = OrganizationPolicy._find_all_legacy_policies(
                policy
            )
            LOGGER.info(
                "Discovered the following legacy policies: %s", _legacy_policies
            )
            try:
                current_stored_policy = ast.literal_eval(
                    parameter_store.fetch_parameter(policy)
                )
                for stored_policy in current_stored_policy:
                    path = (
                        OrganizationPolicy._trim_scp_file_name(stored_policy)
                        if policy == "scp"
                        else OrganizationPolicy._trim_tagging_policy_file_name(
                            stored_policy
                        )
                    )
                    if stored_policy not in _legacy_policies:
                        # Schedule Policy deletion
                        LOGGER.info(
                            "Scheduling policy: %s for deletion",
                            stored_policy,
                        )
                        campaign.delete_policy(f"adf-{policy}-{path}")
            except ParameterNotFoundError:
                LOGGER.debug(
                    "Parameter %s was not found in Parameter Store, continuing.",
                    policy,
                )
                pass
            for _policy in _legacy_policies:
                LOGGER.info("Loading policy: %s", _policy)
                proposed_policy = json.loads(
                    Organizations.get_policy_body(_policy)
                )

                path = (
                    OrganizationPolicy._trim_scp_file_name(_policy)
                    if policy == "scp"
                    else OrganizationPolicy._trim_tagging_policy_file_name(
                        _policy
                    )
                )
                proposed_policy_name = f"adf-{policy}-{path}"
                LOGGER.debug(proposed_policy)
                policy_instance = campaign.get_policy(
                    proposed_policy_name, proposed_policy
                )
                target = campaign.get_target(path)
                policy_instance.set_targets([target])

                LOGGER.info(target)

            _policies = self._find_all_polices(policy)
            LOGGER.info("Discovered the following policies: %s", _policies)
            for _policy in _policies:
                raw_policy_definition = json.loads(
                    self.get_policy_body(_policy)
                )
                policy_definition = OrgPolicySchema(
                    raw_policy_definition
                ).schema
                LOGGER.debug(policy_definition)
                proposed_policy = policy_definition.get("Policy")
                proposed_policy_name = policy_definition.get("PolicyName")
                campaign_policy = campaign.get_policy(
                    proposed_policy_name, proposed_policy
                )
                targets = policy_definition.get("Targets", [])
                campaign_policy.set_targets(
                    [campaign.get_target(t) for t in targets]
                )
            campaign.apply()
            parameter_store.put_parameter(policy, str(_legacy_policies))
