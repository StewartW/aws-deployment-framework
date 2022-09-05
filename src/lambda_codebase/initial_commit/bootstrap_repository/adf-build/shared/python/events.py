"""
Standardised class for pushing events from within the ADF Namespace
"""


import os
import boto3


class ADFEvents:
    def __init__(
        self, client: boto3.client, service, namespace="ADF", eventbus_arn=None
    ) -> None:
        """
        Client: Any Boto3 EventBridge client
        Service: The name of the Service e.g AccountManagement.EnableSupport
        namespace: Defaults to ADF
        eventbus_arn: Optionally specify a custom EventBridge ARN. If no ARN is specified, and no ENV variable set, will default to ADF-Event-Bus

        """
        self.events = client
        self.source = f"{namespace}.{service}"
        self.eventbus_arn = (
            os.environ.get("ADF_EVENTBUS_ARN", "ADF-Event-Bus")
            if eventbus_arn is None
            else eventbus_arn
        )

    # This dict isn't mutated. So it's safe to default to this
    def put_event(self, detailType, detail, resources=[]): # pylint: disable=W0102
        payload = {
            "Source": self.source,
            "Resources": resources,
            "DetailType": detailType,
            "Detail": detail,
            "EventBusName": self.eventbus_arn,
        }
        trace_id = os.getenv("_X_AMZN_TRACE_ID")
        if trace_id:
            payload["TraceHeader"] = trace_id
        self.events.put_events(Entries=[payload])
