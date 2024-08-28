from typing import List

from app.services import service_registry


def get_azure_client():
    try:
        from azure.core.credentials import TokenCredential
        from msgraph import GraphServiceClient
    except ImportError:
        raise ImportError(
            """azure-identity and msgraph are required for AzureUserStore.
            pip install azure-identity msgraph-sdk
            """
        )

    credential = service_registry().get(TokenCredential)
    scopes = ["https://graph.microsoft.com/.default"]
    return GraphServiceClient(credentials=credential, scopes=scopes)


async def get_users_by_filter(
    client, filter: str, select: List[str] = None, expand: List[str] = None
):
    from kiota_abstractions.base_request_configuration import RequestConfiguration
    from msgraph.generated.users.users_request_builder import (
        UsersRequestBuilder,
    )

    qp = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
        select=select,
        filter=filter,
        expand=expand,
        count=True,
    )

    request_configuration = RequestConfiguration(query_parameters=qp)
    request_configuration.headers.add("ConsistencyLevel", "eventual")

    users = await client.users.get(request_configuration)
    return users


async def get_organization(select: List[str], client):
    from kiota_abstractions.base_request_configuration import RequestConfiguration
    from msgraph.generated.organization.organization_request_builder import (
        OrganizationRequestBuilder,
    )

    qp = OrganizationRequestBuilder.OrganizationRequestBuilderGetQueryParameters(
        select=select,
    )
    request_configuration = RequestConfiguration(query_parameters=qp)
    request_configuration.headers.add("ConsistencyLevel", "eventual")

    organization = await client.organization.get(request_configuration)
    return organization
