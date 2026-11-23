"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_mission_goal() -> str:
    return "Ingest transactional CDC streams into Apache Iceberg bronze tables."
