from uuid import uuid4

import pytest
from pytest_cases import case, parametrize, parametrize_with_cases

from src.models.provider import Project, Provider, Region, TrustedIDP
from tests.schemas.utils import random_lower_string, random_provider_type, random_url


@pytest.fixture
def identity_provider() -> TrustedIDP:
    return TrustedIDP(
        protocol=random_lower_string(),
        name=random_lower_string(),
        endpoint=random_url(),
    )


@pytest.fixture
def project() -> Project:
    return Project(id=uuid4(), sla=uuid4())


@pytest.fixture
def region() -> Region:
    return Region(name=random_lower_string())


@case(tags=["valid"])
@parametrize(attr=["regions"])  # TODO: Add BlockStorageVolMap
def case_valid_attr(attr: bool) -> bool:
    return attr


@case(tags=["invalid"])
@parametrize(
    attr=[
        "auth_url",
        "identity_providers_none",
        "identity_providers_single",
        "projects_none",
        "projects_single",
        "regions_none",
        "regions_single",
    ]
)
def case_invalid_attr(attr: bool) -> bool:
    return attr


@parametrize_with_cases("attr", cases=".", has_tag="valid")
def test_provider_schema(
    attr: str, identity_provider: TrustedIDP, project: Project, region: Region
) -> None:
    """Create an SLA with or without regions."""
    d = {
        "name": random_lower_string(),
        "type": random_provider_type(),
        "auth_url": random_url(),
        "identity_providers": [identity_provider],
        "projects": [project],
    }
    if attr == "regions":
        d["regions"] = [region]
    item = Provider(**d)
    assert item.name == d.get("name")
    assert item.type == d.get("type").value
    assert item.auth_url == d.get("auth_url")
    projects = d.get("projects", [])
    assert len(item.projects) == len(projects)
    assert item.projects == projects
    identity_providers = d.get("identity_providers", [])
    assert len(item.identity_providers) == len(identity_providers)
    assert item.identity_providers == identity_providers
    regions = d.get("regions", [])
    assert len(item.regions) == len(regions)
    assert item.regions == regions


@parametrize_with_cases("attr", cases=".", has_tag="invalid")
def test_provider_invalid_schema(
    attr: str, identity_provider: TrustedIDP, project: Project, region: Region
) -> None:
    """SLA with invalid projects list.

    Duplicated values.
    None value: if the projects key is omitted as in the previous test, by default it
    is an empty list.
    """
    d = {
        "name": random_lower_string(),
        "type": random_provider_type(),
        "auth_url": None if attr == "auth_url" else random_url(),
        "projects": [project],
    }
    if attr.endswith("_none"):
        attr = attr[: -len("_none")]
        d[attr] = None
    elif attr == "identity_providers_single":
        d["identity_providers"] = identity_provider
    elif attr == "projects_single":
        d["projects"] = project
    elif attr == "regions_single":
        d["regions"] = region
    with pytest.raises(ValueError):
        Provider(**d)
