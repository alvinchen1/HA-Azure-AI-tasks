"""Tests for the dual-mode Azure OpenAI endpoint builder.

Azure has two OpenAI surfaces. Classic resources must keep working exactly as
they did (this is a HACS integration - other people's installs point at
*.openai.azure.com), while Foundry "v1" resources need the new path shape.
"""
from unittest.mock import MagicMock

import pytest

from custom_components.azure_ai_tasks.ai_task import (
    API_VERSION_CHAT,
    AzureAITaskEntity,
    _endpoint_root,
    _is_v1_endpoint,
)

CLASSIC = "https://my-resource.openai.azure.com"
V1_HOST = "https://my-resource.services.ai.azure.com"


def _entity(endpoint: str) -> AzureAITaskEntity:
    """Build an entity without touching Home Assistant setup."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry"
    return AzureAITaskEntity(
        name="Azure AI Tasks",
        endpoint=endpoint,
        api_key="secret",
        chat_model="gpt-4o",
        image_model="",
        hass=MagicMock(),
        config_entry=config_entry,
    )


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (CLASSIC, False),
        (f"{CLASSIC}/", False),
        ("https://my-resource.cognitiveservices.azure.com", False),
        (V1_HOST, True),
        (f"{V1_HOST}/openai/v1", True),
        # A classic host someone pasted with the v1 path is honoured as v1.
        (f"{CLASSIC}/openai/v1", True),
        ("", False),
    ],
)
def test_is_v1_endpoint(endpoint: str, expected: bool) -> None:
    """The surface is detected from host or path."""
    assert _is_v1_endpoint(endpoint) is expected


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (CLASSIC, CLASSIC),
        (f"{V1_HOST}/openai/v1", V1_HOST),
        (f"{V1_HOST}/openai/v1/responses", V1_HOST),
    ],
)
def test_endpoint_root_strips_path(endpoint: str, expected: str) -> None:
    """Any pasted path is stripped so we never append a second one."""
    assert _endpoint_root(endpoint) == expected


def test_classic_request_is_unchanged() -> None:
    """Classic: deployment in the path, api-version query, model not forced."""
    entity = _entity(CLASSIC)
    assert entity._is_v1 is False

    url, params, payload = entity._build_request(
        "gpt-4o", "chat/completions", API_VERSION_CHAT, {"messages": []}
    )

    assert url == f"{CLASSIC}/openai/deployments/gpt-4o/chat/completions"
    assert params == {"api-version": API_VERSION_CHAT}
    assert payload == {"messages": []}


def test_v1_request_drops_deployment_and_api_version() -> None:
    """v1: flat path, no api-version, model carried in the body."""
    entity = _entity(V1_HOST)
    assert entity._is_v1 is True

    url, params, payload = entity._build_request(
        "gpt-4o", "chat/completions", API_VERSION_CHAT, {"messages": []}
    )

    assert url == f"{V1_HOST}/openai/v1/chat/completions"
    assert params is None
    assert payload == {"messages": [], "model": "gpt-4o"}


def test_v1_base_with_path_is_not_doubled() -> None:
    """A pasted /openai/v1 base does not produce /openai/v1/openai/v1/..."""
    entity = _entity(f"{V1_HOST}/openai/v1/")

    url, _params, _payload = entity._build_request(
        "dall-e-3", "images/generations", "2024-10-21", {"prompt": "a cat"}
    )

    assert url == f"{V1_HOST}/openai/v1/images/generations"


@pytest.mark.parametrize(
    "path", ["chat/completions", "images/generations", "images/edits"]
)
def test_all_operations_route_on_both_surfaces(path: str) -> None:
    """Every operation the integration uses works on both surfaces."""
    classic_url, classic_params, _ = _entity(CLASSIC)._build_request(
        "m", path, "2024-10-21", {}
    )
    v1_url, v1_params, v1_payload = _entity(V1_HOST)._build_request(
        "m", path, "2024-10-21", {}
    )

    assert classic_url == f"{CLASSIC}/openai/deployments/m/{path}"
    assert classic_params == {"api-version": "2024-10-21"}
    assert v1_url == f"{V1_HOST}/openai/v1/{path}"
    assert v1_params is None
    assert v1_payload == {"model": "m"}


def test_build_request_does_not_mutate_caller_payload() -> None:
    """The model injection must not leak back into the caller's dict."""
    original = {"prompt": "hello"}
    _url, _params, payload = _entity(V1_HOST)._build_request(
        "gpt-image-1", "images/generations", "2024-10-21", original
    )

    assert original == {"prompt": "hello"}
    assert payload["model"] == "gpt-image-1"
