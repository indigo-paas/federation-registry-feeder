from uuid import uuid4

import pytest

from src.models.identity_provider import SLA, Issuer, UserGroup
from src.models.provider import Project, TrustedIDP
from src.providers.core import (
    get_identity_provider_info_for_project,
    get_identity_provider_with_auth_method,
)
from tests.schemas.utils import random_lower_string, random_start_end_dates, random_url


@pytest.fixture
def sla() -> SLA:
    start_date, end_date = random_start_end_dates()
    return SLA(doc_uuid=uuid4(), start_date=start_date, end_date=end_date)


@pytest.fixture
def user_group(sla: SLA) -> UserGroup:
    return UserGroup(name=random_lower_string(), slas=[sla])


@pytest.fixture
def issuer(user_group: UserGroup) -> Issuer:
    return Issuer(
        issuer=random_url(),
        group_claim=random_lower_string(),
        token=random_lower_string(),
        user_groups=[user_group],
    )


def test_get_ipd_with_auth_method(issuer: Issuer) -> None:
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    user_group = issuer.user_groups[0]
    sla = user_group.slas[0]
    item = get_identity_provider_with_auth_method(
        auth_methods=[idp],
        issuer=issuer,
        user_group=user_group,
        sla=sla,
        project=uuid4().hex,
    )
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.relationship
    assert item.relationship.idp_name == idp.idp_name
    assert item.relationship.protocol == idp.protocol


def test_fail_update_issuer(issuer: Issuer) -> None:
    idp = TrustedIDP(
        endpoint=random_url(),
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    user_group = issuer.user_groups[0]
    sla = user_group.slas[0]
    with pytest.raises(ValueError):
        get_identity_provider_with_auth_method(
            auth_methods=[idp],
            issuer=issuer,
            user_group=user_group,
            sla=sla,
            project=uuid4().hex,
        )


def test_retrieve_idp_for_target_project(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=issuer.user_groups[0].slas[0].doc_uuid)
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    item, token = get_identity_provider_info_for_project(
        issuers=[issuer], trusted_issuers=[idp], project=project
    )
    assert token == issuer.token
    assert item.endpoint == issuer.endpoint
    assert item.group_claim == issuer.group_claim
    assert item.relationship
    assert item.relationship.idp_name == idp.idp_name
    assert item.relationship.protocol == idp.protocol
    assert item.user_groups[0].sla.project == project.id


def test_no_matching_sla(issuer: Issuer) -> None:
    project = Project(id=uuid4(), sla=uuid4())
    idp = TrustedIDP(
        endpoint=issuer.endpoint,
        name=random_lower_string(),
        protocol=random_lower_string(),
    )
    with pytest.raises(ValueError):
        get_identity_provider_info_for_project(
            issuers=[issuer], trusted_issuers=[idp], project=project
        )
