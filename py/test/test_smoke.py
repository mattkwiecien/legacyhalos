import pytest


def test_smoke():
    try:
        import legacyhalos
    except:
        raise pytest.fail("Failed to import legacyhalos")
