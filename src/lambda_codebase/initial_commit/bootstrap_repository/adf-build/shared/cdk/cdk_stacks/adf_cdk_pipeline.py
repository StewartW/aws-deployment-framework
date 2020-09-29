import os

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _codepipeline_actions,
    aws_codecommit as _codecommit,
    core,
    pipelines,
)
from cdk_constructs import adf_notifications

from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_STACK_PREFIX = os.environ.get("ADF_STACK_PREFIX", "")
ADF_PIPELINE_PREFIX = os.environ.get("ADF_PIPELINE_PREFIX", "")
ADF_DEFAULT_BUILD_TIMEOUT = 20
LOGGER = configure_logger(__name__)

PIPELINE_TYPE = "cdk"


def generate_cdk_pipeline(scope: core.Stack, stack_input):
    if stack_input["input"].get("params", {}).get("notification_endpoint"):
        stack_input["input"]["topic_arn"] = adf_notifications.Notifications(
            scope, "adf_notifications", stack_input["input"]
        ).topic_arn

    source_artifact = _codepipeline.Artifact()
    cloud_assembly_artifact = _codepipeline.Artifact()

    pipeline = pipelines.CdkPipeline(
        scope,
        "CDKPipeline",
        pipeline_name=f'{ADF_PIPELINE_PREFIX}{stack_input["input"].get("name")}',
        cloud_assembly_artifact=cloud_assembly_artifact,
        source_action=generate_source_stage_for_pipeline(scope, stack_input, source_artifact),
        synth_action=generate_synth_stage_for_pipeline(
            stack_input, source_artifact, cloud_assembly_artifact
        ),
    )
    # No target actions are created here. 
    # All this is really doing is create a repository and a pipeline to kick off the mutation process.

def generate_source_stage_for_pipeline(scope,
    stack_input, source_artifact: _codepipeline.Artifact
):
    _source_definition = stack_input["input"]["default_providers"]["source"]
    _source_name = _source_definition["provider"].lower()
    if "codecommit" in _source_name:
        return _codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit",
            output=source_artifact,
            branch=_source_definition.get("properties", {}).get("branch", "master"),
            repository=_codecommit.Repository.from_repository_name(scope, "pipeline-source-repo", repository_name=_source_definition.get("properties", {}).get("repository")
            or stack_input["input"]["name"],)

        )
    else:
        return None


def generate_synth_stage_for_pipeline(
    stack_input,
    source_artifact: _codepipeline.Artifact,
    cloud_assembly_artifact: _codepipeline.Artifact,
):
    _synth_definition = stack_input["input"]["default_providers"].get("synth", {})
    _synth_name = _synth_definition.get("provider", "simple-synth").lower()
    snyth_action = pipelines.SimpleSynthAction.standard_npm_synth(
        source_artifact=source_artifact,
        cloud_assembly_artifact=cloud_assembly_artifact,
        build_command="npm run build",
    )
    return snyth_action
