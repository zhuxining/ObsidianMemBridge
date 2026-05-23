import pytest

from membridge.core import Bridge, create_bridge


def test_create_bridge_returns_bridge():
    bridge = create_bridge("notes", "memory")

    assert isinstance(bridge, Bridge)
    assert bridge.source == "notes"
    assert bridge.target == "memory"
    assert bridge.describe() == "MemBridge: notes -> memory"


def test_create_bridge_uses_default_target():
    bridge = create_bridge("notes")

    assert bridge.target == "memory"


def test_create_bridge_rejects_empty_source():
    with pytest.raises(ValueError):
        create_bridge("   ")
