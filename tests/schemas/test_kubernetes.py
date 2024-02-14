from typing import Any, Dict, List, Literal, Tuple

import pytest
from fed_reg.provider.enum import ProviderType
from pytest_cases import parametrize_with_cases

from src.models.provider import AuthMethod, Kubernetes, Project, Region
from tests.schemas.utils import random_lower_string, random_url


class CaseValidAttr:
    def case_regions(self, region: Region) -> Tuple[Literal["regions"], List[Region]]:
        return "regions", [region]

    # TODO: Add BlockStorageVolMap case


class CaseInvalidAttr:
    def case_type(self) -> Tuple[Literal["type"], Literal[ProviderType.OS]]:
        return "type", ProviderType.OS


def kubernetes_dict() -> Dict[str, Any]:
    """Dict with kubernetes provider minimal attributes."""
    return {
        "name": random_lower_string(),
        "type": ProviderType.K8S,
        "auth_url": random_url(),
    }


@parametrize_with_cases("key, value", cases=CaseValidAttr)
def test_kubernetes_schema(
    auth_method: AuthMethod, project: Project, key: str, value: Any
) -> None:
    """Valid Kubernetes provider schema."""
    d = kubernetes_dict()
    d["identity_providers"] = [auth_method]
    d["projects"] = [project]
    d[key] = value
    item = Kubernetes(**d)
    assert item.name == d.get("name")
    assert item.type == d.get("type").value
    assert item.auth_url == d.get("auth_url")
    projects = d.get("projects", [])
    assert len(item.projects) == len(projects)
    assert item.projects == projects
    identity_providers = d.get("identity_providers", [])
    assert len(item.identity_providers) == len(identity_providers)
    assert item.identity_providers == identity_providers
    regions = d.get("regions", [Region(name="default")])
    assert len(item.regions) == len(regions)
    assert item.regions == regions


@parametrize_with_cases("key, value", cases=CaseInvalidAttr)
def test_kubernetes_invalid_schema(
    auth_method: AuthMethod, project: Project, key: str, value: Any
) -> None:
    """Invalid Kubernetes provider schema.

    Invalid type.
    """
    d = kubernetes_dict()
    d["identity_providers"] = [auth_method]
    d["projects"] = [project]
    d[key] = value
    with pytest.raises(ValueError):
        Kubernetes(**d)
