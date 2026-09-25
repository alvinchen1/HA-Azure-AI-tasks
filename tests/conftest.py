"""Fixtures for the Azure AI Tasks tests."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load this custom integration.

    Request this explicitly from tests that start Home Assistant; it pulls in
    the async `hass` fixture, so it must not be autouse or the plain unit tests
    would drag a whole HA instance in with them.
    """
    yield
