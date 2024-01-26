from typing import Tuple, Union
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.auth_method.schemas import AuthMethodBase
from keystoneauth1.exceptions.auth_plugins import NoMatchingPlugin
from keystoneauth1.exceptions.connection import ConnectFailure
from keystoneauth1.exceptions.http import NotFound, Unauthorized
from pytest_cases import parametrize, parametrize_with_cases

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Openstack, Project, TrustedIDP
from src.providers.openstack import connect_to_provider
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@parametrize(
    exception=[
        "invalid_url",
        "expired_token",
        "wrong_auth_type",
        "wrong_idp_name",
        "wrong_protocol",
        "invalid_project_id",
        "timeout",
    ]
)
def case_exception(
    exception: str,
) -> Union[ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound]:
    if exception == "invalid_url" or exception == "timeout":
        return ConnectFailure()
    elif (
        exception == "expired_token"
        or exception == "wrong_protocol"
        or exception == "invalid_project_id"
    ):
        return Unauthorized()
    elif exception == "wrong_auth_type":
        return NoMatchingPlugin("fake")
    elif exception == "wrong_idp_name":
        return NotFound()


@pytest.fixture
def configurations() -> Tuple[Openstack, Issuer, Project, str]:
    project_id = uuid4()
    start_date, end_date = random_start_end_dates()
    sla = SLA(
        doc_uuid=uuid4(),
        start_date=start_date,
        end_date=end_date,
        projects=[project_id],
    )
    user_group = UserGroup(name=random_lower_string(), slas=[sla])
    relationship = AuthMethodBase(
        idp_name=random_lower_string(), protocol=random_lower_string()
    )
    issuer = Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        relationship=relationship,
        user_groups=[user_group],
    )
    trusted_idp = TrustedIDP(
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
    return provider_conf, issuer, project, region_name


@patch("src.providers.openstack.connect")
@parametrize_with_cases("exception", cases=".")
def test_fail_connection(
    mock_func,
    exception: Union[ConnectFailure, Unauthorized, NoMatchingPlugin, NotFound],
    configurations: Tuple[Openstack, Issuer, Project, str],
) -> None:
    mock_func.side_effect = exception
    (provider_conf, issuer, project, region_name) = configurations
    assert not connect_to_provider(
        provider_conf=provider_conf,
        idp=issuer,
        project_id=project.id,
        region_name=region_name,
    )


def test_connection(configurations: Tuple[Openstack, Issuer, Project, str]) -> None:
    (provider_conf, issuer, project, region_name) = configurations
    conn = connect_to_provider(
        provider_conf=provider_conf,
        idp=issuer,
        project_id=project.id,
        region_name=region_name,
    )
    assert conn.auth.get("auth_url") == provider_conf.auth_url
    assert conn.auth.get("identity_provider") == issuer.relationship.idp_name
    assert conn.auth.get("protocol") == issuer.relationship.protocol
    assert conn.auth.get("access_token") == issuer.token
    assert conn.auth.get("project_id") == project.id
    assert conn._compute_region == region_name