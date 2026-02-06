from __future__ import annotations

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient

from shared.config import settings


def get_fully_qualified_namespace() -> str:
    # settings.SERVICEBUS_NAMESPACE is like: "opal-xxx-bus"
    # Service Bus client needs: "<namespace>.servicebus.windows.net"
    ns = settings.SERVICEBUS_NAMESPACE.strip()
    if ns.endswith(".servicebus.windows.net"):
        return ns
    return f"{ns}.servicebus.windows.net"


def get_client() -> ServiceBusClient:
    fqns = get_fully_qualified_namespace()
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return ServiceBusClient(fully_qualified_namespace=fqns, credential=credential)
