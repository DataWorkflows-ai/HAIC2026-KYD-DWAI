"""HPHA public housing properties by district."""
from app.services.hpha import properties


def test_statewide_inventory_matches_reconciliation():
    hi = properties("HI")
    assert len(hi["properties"]) == 86 and hi["units"] == 5920 and hi["state_units"] == 864


def test_house_and_senate_partition_the_inventory():
    for pre, n in (("HD", 51), ("SD", 25)):
        assert sum(properties(f"{pre}-{i:02d}")["units"] for i in range(1, n + 1)) == 5920
