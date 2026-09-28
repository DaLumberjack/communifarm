"""Shared pytest fixtures for Communifarm."""

from __future__ import annotations

import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_socket
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_socket import enable_socket

from custom_components.communifarm.const import DOMAIN
from custom_components.communifarm.domain.models import (
    CommunifarmState,
    EntityBinding,
    Environment,
    EnvironmentalProfile,
    ProductionBatch,
    Site,
)

pytest_plugins = "pytest_homeassistant_custom_component"

# Windows ProactorEventLoop needs AF_INET socketpair; PHCC only allows UNIX sockets.
if sys.platform == "win32":
    pytest_socket.disable_socket = lambda *args, **kwargs: enable_socket()  # type: ignore[assignment]
    enable_socket()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in tests."""
    return None


@pytest.fixture
def sample_state() -> CommunifarmState:
    """Return a seeded Communifarm domain state."""
    site = Site(name="Test Site", id="site_test")
    environment = Environment(name="Test Tent", site_id=site.id, id="env_test")
    batch = ProductionBatch(
        name="Batch 1", environment_id=environment.id, id="batch_test"
    )
    profile = EnvironmentalProfile(temperature_target=22.0, humidity_target=60.0)
    bindings = [
        EntityBinding(
            role="temperature_source",
            entity_entry_id="entry_temp",
            entity_id="sensor.mock_temperature",
        ),
        EntityBinding(
            role="humidity_source",
            entity_entry_id="entry_hum",
            entity_id="sensor.mock_humidity",
        ),
        EntityBinding(
            role="switch_actuator",
            entity_entry_id="entry_switch",
            entity_id="switch.mock_exhaust",
        ),
        EntityBinding(
            role="lc_stir_plate",
            entity_entry_id="entry_stir",
            entity_id="switch.mock_lc_stir_plate",
        ),
    ]
    return CommunifarmState(
        site=site,
        environment=environment,
        profile=profile,
        batch=batch,
        bindings=bindings,
    )


@pytest.fixture
def mock_config_entry(sample_state: CommunifarmState) -> MockConfigEntry:
    """Return a mock config entry with seeded state."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Site / Test Tent",
        data={"state": sample_state.to_dict()},
        unique_id="communifarm_single",
    )


@pytest.fixture
def bypass_dashboard() -> Generator[AsyncMock, None, None]:
    """Bypass lovelace provisioning side effects."""
    with patch(
        "custom_components.communifarm.dashboard.provisioner._async_save_lovelace",
        new_callable=AsyncMock,
    ) as mocked:
        yield mocked
