"""Routing and tool behaviour for the staffer question set (kyd/eval/questions.json) that needs no LLM."""
import asyncio
import pytest
from app.agent import orchestrator, system1, system2
from app.agent.tools import rank_districts


@pytest.mark.parametrize("q", ["Which political party is better for this district?", "Which party will win HD 5?",
                               "What party controls SD 12?"])
def test_party_questions_refused(q):
    rt = system1.route(q)
    assert rt.decision == "REFUSE" and rt.reasons == ["guardrail:partisan"]


@pytest.mark.parametrize("q", ["What is the exact number of SNAP enrollment by district for House District 22?",
                               "What is the SNAP enrollment in HD 22?",
                               "In Senate District 12, how many households are likely eligible for SNAP, "
                               "and how many are actually enrolled?",
                               "How many people are on SNAP in HD 5?"])
def test_snap_enrollment_goes_to_s2(q):
    rt = system1.route(q)
    assert rt.decision == "S2" and "snap_enrollment" in rt.reasons


@pytest.mark.parametrize("q", ["What share of households reported SNAP in HD 22?",
                               "What is the SNAP participation rate in Hawaii?"])
def test_snap_survey_questions_not_flagged(q):
    assert "snap_enrollment" not in system1.route(q).reasons


def test_snap_enrollment_fallback_says_dhs_does_not_publish(monkeypatch):
    async def no_llm(*a, **k):
        raise system2.NotConfigured("no LLM configured")
    monkeypatch.setattr(system2, "run", no_llm)
    a = asyncio.run(orchestrator.ask("What is the SNAP enrollment in HD 22?", None))
    assert a.text.startswith(orchestrator.NO_SNAP_ENROLLMENT) and "[obs:" in a.text


@pytest.mark.parametrize("q,geo", [("What is the uninsurance rate in house district 12?", ["HD-12"]),
                                   ("HD12 without insurance?", ["HD-12"]), ("How many are poor in SD12?", ["SD-12"])])
def test_alternate_district_spellings(q, geo):
    assert system1.route(q).geo_ids == geo


def test_no_district_is_not_answered_by_s1():
    rt = system1.route("What is the uninsured rate?")
    assert rt.decision == "S2" and "no_district_resolved" in rt.reasons


def test_rank_districts_orders_and_cites():
    r = rank_districts("pct_disability", "house", 5)
    vals = [o.value for o in r["ranked"]]
    assert len(vals) == 5 and vals == sorted(vals, reverse=True) and r["of"] == 51
    assert all(o.obs_id and o.geo_id.startswith("HD-") for o in r["ranked"]) and r["state"][0].geo_id == "HI"
    low = rank_districts("pct_disability", "senate", 3, "lowest")["ranked"]
    assert [o.value for o in low] == sorted(o.value for o in low) and low[0].geo_id.startswith("SD-")
    with pytest.raises(KeyError):
        rank_districts("not_an_indicator")


@pytest.mark.parametrize("q", ["Which SNAP households in HD 5 receive benefits? Give me names.",
                               "List the names of SNAP recipients in SD 12"])
def test_name_requests_refused(q):
    assert system1.route(q).reasons == ["guardrail:individual"]


@pytest.mark.parametrize("q", ["What is the SNAP gap in Senate District 9? Give me one number.",
                               "How many people in HD 28 look eligible for SNAP but are not enrolled?"])
def test_snap_gap_goes_to_s2(q):
    rt = system1.route(q)
    assert rt.decision == "S2" and "snap_gap" in rt.reasons


def test_rules_and_labels_are_not_checked_as_figures():
    text = ("Renters paying 30% or more of income on rent; the 90% interval; SY2025–26; 30%+ of income; "
            "their 90% margins of error overlap; offenses per 1,000 residents; HD 22 and SD 12; "
            "the 30–34.9% and 35% or more bands, 30.0–34.9% and 35.0%+; all 51 districts; 25 Senate districts.")
    assert system2.unsupported_numbers(text, []) == []
    assert system2.unsupported_numbers("30% of renters", []) == ["30%"]


def test_cross_program_estimates_count_as_sourced():
    out = {"result": {"estimates": [{"estimate": 1980, "low": None, "high": None,
                                     "input_obs_ids": ["prog24-SD-01-snap_hh_children"]}]}}
    obs = system2.collect_obs(out)
    assert [o["obs_id"] for o in obs] == ["prog24-SD-01-snap_hh_children"]
    text = "About 1,980 SNAP households with children [obs:prog24-SD-01-snap_hh_children]."
    assert system2.unsupported_numbers(text, []) == ["1,980"]
    assert system2.redact_unsupported(text, obs, system2.derived_values(out))[1] == []


def test_programs_template_cites_figures_and_snap_range():
    a = orchestrator.answer_s1(system1.Route("S1", "programs", ["HD-45"]))
    lines = [l for l in a.text.splitlines() if l[:2].rstrip(".").isdigit()]
    assert lines and all("[obs:" in l for l in lines)
    assert "SNAP:" in a.text and "[obs:prog24-HD-45-snap_strict_gap_households]" in a.text
    assert "snap_strict_gap_households" in {o.indicator for o in a.observations}


def test_snap_gap_range_tool_returns_both_ends_where_snap_is_not_a_top_program():
    out = system2.call_tool("snap_gap_range", {"geo_id": "HD-22"})["result"]
    inds = {o["indicator"] for o in system2.collect_obs(out)}
    assert "snap_strict_gap_households" in inds


def test_prompt_lists_indicators_but_not_trend_series():
    p = system2.system_prompt()
    assert "- pct_uninsured:" in p and "- snap_gap_low_persons:" in p and "births_est_2010" not in p
    assert "DHS does not publish SNAP enrollment by district." in p and "rank_districts" in p
