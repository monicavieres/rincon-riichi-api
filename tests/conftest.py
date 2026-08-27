"""Shared pytest fixtures and client."""

import pytest
from fastapi.testclient import TestClient

from rincon_riichi_api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
