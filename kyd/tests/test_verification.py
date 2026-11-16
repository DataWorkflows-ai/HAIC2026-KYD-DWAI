"""The source checks pass on the real files AND fail when a source changes shape.
Each mutation test copies a source, breaks it the way a new report edition could, and asserts
that a FAIL is raised (a silent pass would mean wrong numbers could reach the app)."""
import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parents[1] / "verify"
sys.path.insert(0, str(VERIFY))
import bessd, census, core, crosscheck, databook  # noqa: E401,E402


def run(*mods) -> dict[str, core.Check]:
    rep = core.Report()
    for m in mods:
        m.run(rep)
    return {c.id: c for c in rep.checks}


def fails(checks) -> list[str]:
    return [k for k, c in checks.items() if c.status == "fail"]


def test_real_sources_have_no_failures():
    assert fails(run(census, databook, bessd, crosscheck)) == []


def test_every_typed_databook_figure_is_checked():
    ids = run(databook)
    assert sum(1 for k, c in ids.items() if c.kind == "transcription") >= 90


# ── Census: a variable keeps its name but changes meaning ─────────────────────
@pytest.fixture
def census_copy(tmp_path, monkeypatch):
    for p in core.RAW.glob("*_districts.json"):
        shutil.copy(p, tmp_path / p.name)
    monkeypatch.setattr(census, "RAW", tmp_path)
    return tmp_path


def _edit(path: Path, fn):
    d = json.loads(path.read_text())
    fn(d["response"]["data"])
    path.write_text(json.dumps(d))


def test_census_swapped_poverty_thresholds_fail(census_copy):
    def swap(data):
        h = data[0]
        i, j = h.index("S1701_C01_041E"), h.index("S1701_C01_042E")
        h[i], h[j] = h[j], h[i]                     # 185% and 200% columns trade places
    _edit(census_copy / "S1701_house_districts.json", swap)
    assert "census.S1701.poverty_ladder.house" in fails(run(census))


def test_census_percent_column_reassigned_fails(census_copy):
    def shift(data):
        h = data[0]
        i, j = h.index("S2201_C04_001E"), h.index("S2201_C02_001E")
        h[i], h[j] = h[j], h[i]
    _edit(census_copy / "S2201_senate_districts.json", shift)
    f = fails(run(census))
    assert "census.S2201.rate_identity.senate" in f and "census.S2201.vs_DP03.C04_001E.senate" in f


def test_census_dropped_variable_and_missing_district_fail(census_copy):
    def drop(data):
        h = data[0]
        h[h.index("S1810_C03_001E")] = "S1810_C03_001EX"
        del data[5]
    _edit(census_copy / "S1810_house_districts.json", drop)
    f = fails(run(census))
    assert "census.S1810.house.codes" in f and "census.S1810.house.districts" in f


def test_census_new_vintage_fails(census_copy):
    p = census_copy / "DP05_senate_districts.json"
    d = json.loads(p.read_text())
    d["response"]["dataAPIURI"] = d["response"]["dataAPIURI"].replace("/2024/", "/2025/")
    p.write_text(json.dumps(d))
    assert "census.DP05.senate.vintage" in fails(run(census))


# ── Databook: next edition moves a table, or a number is typed wrong ─────────
def test_databook_table_moved_fails(monkeypatch):
    real = databook.pages()
    monkeypatch.setattr(databook, "pages", lambda: [""] + real)        # a new page inserted up front
    f = fails(run(databook))
    assert any(k.startswith("dhs.databook2025.anchor.p27") for k in f)
    assert any(k.startswith("dhs.databook2025.medquest.sfy") for k in f)


def test_databook_typo_in_code_fails(monkeypatch):
    sys.path.insert(0, str(core.REPO / "scripts"))
    import medquest, tanf_underenrollment
    rows = [dict(r) for r in medquest.ENROLLMENT]
    rows[-1]["oahu"] += 10
    monkeypatch.setattr(medquest, "ENROLLMENT", rows)
    monkeypatch.setitem(tanf_underenrollment.TANF_STATEWIDE, "filipino", 18)
    f = fails(run(databook))
    assert "dhs.databook2025.medquest.sfy2025" in f
    assert "dhs.databook2025.tanf.race_ethnicity.filipino" in f


# ── BESSD: the CSV drifts from the workbook ──────────────────────────────────
def test_bessd_csv_edit_fails(tmp_path, monkeypatch):
    src = core.PROCESSED / "bessd_sfy2026_caseload_by_island.csv"
    rows = list(csv.DictReader(src.open()))
    rows[3]["tanf"] = str(float(rows[3]["tanf"]) + 7)
    out = tmp_path / src.name
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    monkeypatch.setattr(bessd, "CSV", out)
    f = fails(run(bessd))
    assert "dhs.bessd_sfy2026.csv_matches_workbook" in f and "dhs.bessd_sfy2026.row_totals" in f
