from typing import Tuple
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.provider.schemas_extended import (
    AuthMethodCreate,
    BlockStorageServiceCreateExtended,
    ComputeServiceCreateExtended,
    IdentityProviderCreateExtended,
    NetworkServiceCreateExtended,
    ProjectCreate,
    SLACreateExtended,
    UserGroupCreateExtended,
)
from app.service.enum import (
    BlockStorageServiceName,
    ComputeServiceName,
    NetworkServiceName,
)
from keystoneauth1.exceptions.connection import ConnectFailure
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.identity_provider import Issuer
from src.models.provider import AuthMethod, Openstack, Project
from src.providers.openstack import get_data_from_openstack
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@case(tags=["connection"])
@parametrize(item=["connection", "project", "block_storage", "compute", "network"])
def case_connection(item: str) -> str:
    return item


@case(tags=["item"])
@parametrize(item=["block_storage", "compute", "network"])
def case_absent_item(item: str) -> str:
    return item


@pytest.fixture
def configurations() -> (
    Tuple[Openstack, IdentityProviderCreateExtended, Project, str, str]
):
    project_id = uuid4()
    start_date, end_date = random_start_end_dates()
    sla = SLACreateExtended(
        doc_uuid=uuid4(), start_date=start_date, end_date=end_date, project=project_id
    )
    user_group = UserGroupCreateExtended(name=random_lower_string(), sla=sla)
    relationship = AuthMethodCreate(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )
    issuer = IdentityProviderCreateExtended(
        endpoint=random_url(),
        group_claim=random_lower_string(),
        relationship=relationship,
        user_groups=[user_group],
    )
    trusted_idp = AuthMethod(
        endpoint=issuer.endpoint,
        name=relationship.idp_name,
        protocol=relationship.protocol,
    )
    project = Project(id=project_id, sla=sla.doc_uuid)
    provider_conf = Openstack(
        name=random_lower_string(),
        auth_url=random_url(),
        identity_providers=[trusted_idp],
        projects=[project],
    )
    region_name = random_lower_string()
    token = random_lower_string()
    return provider_conf, issuer, project, region_name, token


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@patch("src.providers.openstack.connect_to_provider")
@parametrize_with_cases("fail_point", cases=".", has_tag="connection")
def test_no_connection(
    mock_conn: Mock,
    mock_project: Mock,
    mock_block_storage_service: Mock,
    mock_compute_service: Mock,
    mock_network_service: Mock,
    configurations: Tuple[Openstack, Issuer, Project, str],
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    fail_point: str,
) -> None:
    """Test no initial connection and connection loss during procedure"""
    block_storage_service_create.name = BlockStorageServiceName.OPENSTACK_CINDER
    compute_service_create.name = ComputeServiceName.OPENSTACK_NOVA
    network_service_create.name = NetworkServiceName.OPENSTACK_NEUTRON

    mock_project.return_value = project_create
    mock_block_storage_service.return_value = block_storage_service_create
    mock_compute_service.return_value = compute_service_create
    mock_network_service.return_value = network_service_create

    if fail_point == "connection":
        mock_conn.return_value = None
    elif fail_point == "project":
        mock_project.side_effect = ConnectFailure()
    elif fail_point == "block_storage":
        mock_block_storage_service.side_effect = ConnectFailure()
    elif fail_point == "compute":
        mock_compute_service.side_effect = ConnectFailure()
    elif fail_point == "network":
        mock_network_service.side_effect = ConnectFailure()

    (provider_conf, issuer, project_conf, region_name, token) = configurations
    resp = get_data_from_openstack(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=issuer,
        region_name=region_name,
        token=token,
    )
    assert not resp


@patch("src.providers.openstack.get_network_service")
@patch("src.providers.openstack.get_compute_service")
@patch("src.providers.openstack.get_block_storage_service")
@patch("src.providers.openstack.get_project")
@parametrize_with_cases("absent", cases=".", has_tag="item")
def test_retrieve_resources(
    mock_project: Mock,
    mock_block_storage_service: Mock,
    mock_compute_service: Mock,
    mock_network_service: Mock,
    configurations: Tuple[Openstack, Issuer, Project, str],
    project_create: ProjectCreate,
    block_storage_service_create: BlockStorageServiceCreateExtended,
    compute_service_create: ComputeServiceCreateExtended,
    network_service_create: NetworkServiceCreateExtended,
    absent: str,
) -> None:
    (provider_conf, issuer, project_conf, region_name, token) = configurations

    project_create.uuid = project_conf.id
    block_storage_service_create.name = BlockStorageServiceName.OPENSTACK_CINDER
    compute_service_create.name = ComputeServiceName.OPENSTACK_NOVA
    network_service_create.name = NetworkServiceName.OPENSTACK_NEUTRON

    mock_project.return_value = project_create
    mock_block_storage_service.return_value = (
        None if absent == "block_storage" else block_storage_service_create
    )
    mock_compute_service.return_value = (
        None if absent == "compute" else compute_service_create
    )
    mock_network_service.return_value = (
        None if absent == "network" else network_service_create
    )

    resp = get_data_from_openstack(
        provider_conf=provider_conf,
        project_conf=project_conf,
        identity_provider=issuer,
        region_name=region_name,
        token=token,
    )
    assert resp

    (
        proj,
        block_storage_service,
        compute_service,
        identity_service,
        network_service,
    ) = resp
    assert proj
    assert identity_service
    assert (
        not block_storage_service
        if absent == "block_storage"
        else block_storage_service
    )
    assert not compute_service if absent == "compute" else compute_service
    assert not network_service if absent == "network" else network_service
