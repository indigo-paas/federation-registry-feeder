from unittest.mock import patch

import pytest
from app.provider.schemas_extended import (
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityServiceCreate,
    NetworkServiceCreateExtended,
    ProjectCreate,
)
from app.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    IdentityServiceName,
    NetworkServiceName,
)
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import (
    Kubernetes,
    Openstack,
    PerRegionProps,
)
from src.providers.core import get_idp_project_and_region
from tests.schemas.utils import random_lower_string, random_url


@case(tags=["type"])
@parametrize(type=["openstack", "kubernetes"])
def case_provider_type(type: str) -> str:
    return type


@case(tags=["reg_props"])
@parametrize(with_reg_props=[True, False])
def case_with_reg_props(with_reg_props: str) -> str:
    return with_reg_props


@case(tags=["service"])
@parametrize(service=["block_storage", "compute", "network"])
def case_with_service(service: str) -> str:
    return service


@patch("src.providers.core.get_data_from_openstack")
@parametrize_with_cases("proj_with_reg_props", cases=".", has_tag="reg_props")
@parametrize_with_cases("service", cases=".", has_tag="service")
def test_retrieve_project_resources(
    mock_get_data,
    proj_with_reg_props: bool,
    service: str,
    issuer: Issuer,
    openstack_provider: Openstack,
) -> None:
    provider = openstack_provider
    provider.projects[0].sla = issuer.user_groups[0].slas[0].doc_uuid
    default_region_name = "RegionOne"
    provider.identity_providers[0].endpoint = issuer.endpoint

    mock_proj = ProjectCreate(uuid=provider.projects[0].id, name=random_lower_string())
    mock_identity = IdentityServiceCreate(
        endpoint=provider.auth_url, name=IdentityServiceName.OPENSTACK_KEYSTONE
    )
    mock_block_storage = BlockStorageServiceCreateExtended(
        endpoint=random_url(), name=BlockStorageServiceName.OPENSTACK_CINDER
    )
    mock_compute = ComputeServiceCreateExtended(
        endpoint=random_url(), name=ComputeServiceName.OPENSTACK_NOVA
    )
    mock_network = NetworkServiceCreateExtended(
        endpoint=random_url(), name=NetworkServiceName.OPENSTACK_NEUTRON
    )
    mock_get_data.return_value = (
        mock_proj,
        mock_block_storage if service == "block_storage" else None,
        mock_compute if service == "compute" else None,
        mock_identity,
        mock_network if service == "network" else None,
    )

    if proj_with_reg_props:
        provider.projects[0].per_region_props = [
            PerRegionProps(region_name=default_region_name)
        ]

    resp = get_idp_project_and_region(
        provider_conf=provider,
        project_conf=provider.projects[0],
        region_conf=provider.regions[0],
        issuers=[issuer],
    )
    assert resp

    idp, project, region = resp
    assert idp
    assert issuer.endpoint == idp.endpoint
    assert project
    assert mock_proj == project
    assert region
    assert mock_identity in region.identity_services
    if service == "block_storage":
        assert mock_block_storage in region.block_storage_services
    if service == "compute":
        assert mock_compute in region.compute_services
    if service == "network":
        assert mock_network in region.network_services


@parametrize_with_cases("provider_type", cases=".", has_tag="type")
def test_no_matching_idp_when_retrieving_project_resources(
    caplog: pytest.LogCaptureFixture,
    provider_type: str,
    issuer: Issuer,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    if provider_type == "openstack":
        provider = openstack_provider
    elif provider_type == "kubernetes":
        provider = kubernetes_provider

    resp = get_idp_project_and_region(
        provider_conf=provider,
        project_conf=provider.projects[0],
        region_conf=provider.regions[0],
        issuers=[issuer],
    )
    assert not resp

    msg = f"Skipping project {provider.projects[0].id}."
    assert caplog.text.strip("\n").endswith(msg)


@parametrize_with_cases("provider_type", cases=".", has_tag="type")
def test_no_conn_when_retrieving_project_resources(
    caplog: pytest.LogCaptureFixture,
    provider_type: str,
    issuer: Issuer,
    openstack_provider: Openstack,
    kubernetes_provider: Kubernetes,
) -> None:
    if provider_type == "openstack":
        provider = openstack_provider
    elif provider_type == "kubernetes":
        provider = kubernetes_provider

    provider.projects[0].sla = issuer.user_groups[0].slas[0].doc_uuid
    provider.identity_providers[0].endpoint = issuer.endpoint

    resp = get_idp_project_and_region(
        provider_conf=provider,
        project_conf=provider.projects[0],
        region_conf=provider.regions[0],
        issuers=[issuer],
    )
    assert not resp

    if provider_type == "openstack":
        msg = "Connection closed unexpectedly."
        assert caplog.text.strip("\n").endswith(msg)
