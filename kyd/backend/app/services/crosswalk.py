"""Cross-program eligibility estimates: from SNAP participation and income ladders to other programs.

Each estimate applies ONE published eligibility rule to district-level ACS counts:
  - categorical / adjunctive rules: a SNAP household automatically meets another program's income test
    (free school meals, Lifeline, WIC, Hawaiʻi LIHEAP) → count SNAP households (or members) of the right kind;
  - income rules: a program's income limit as a share of poverty → people under that poverty ratio.

Every figure carries its rule, the rule's citation, the formula, the observation ids it was built from,
a low/high range where the method is approximate, and a confidence label. Population-level and
informational only: never an individual eligibility determination; the administering agency decides.
"""
from __future__ import annotations

from .cache import cached
from .repo import repo

INPUTS = ["snap_hh_count", "snap_hh_children", "snap_persons_est", "households", "pct_ssi_hh", "pct_under5",
          "pop_below_125fpl", "pop_below_138fpl", "pop_below_150fpl", "pop_below_185fpl"]

ACS_THRESHOLD_CAVEAT = ("Income figures use Census poverty thresholds, which are national. Hawaiʻi programs use the "
                        "higher HHS Hawaiʻi poverty guidelines, so income-based counts likely understate the eligible pool.")
SNAP_ACS_CAVEAT = ("SNAP households are ACS survey counts, which typically run below DHS administrative caseloads "
                   "(see Sources & Methods cross-checks).")

RULES = {
    "school_meals": {
        "name": "Free school meals (direct certification)",
        "rule": "Children in SNAP households are directly certified for free school meals, with no application.",
        "source": {"title": "Hawaiʻi Child Nutrition Programs — Direct Certification",
                   "url": "https://hcnp.hawaii.gov/wp-content/uploads/2019/07/Direct-Certification-2019.pdf"},
    },
    "lifeline": {
        "name": "Lifeline phone/internet discount",
        "rule": "A household qualifies if a member receives SNAP (or Medicaid, SSI, public housing, VA pension), "
                "or if household income is at or below 135% of the poverty guidelines.",
        "source": {"title": "47 CFR § 54.409 — Consumer qualification for Lifeline",
                   "url": "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-54/subpart-E/section-54.409"},
    },
    "liheap": {
        "name": "LIHEAP energy assistance (Hawaiʻi)",
        "rule": "Hawaiʻi treats households receiving SNAP, SSI, TANF, GA or AABD as categorically income-eligible. "
                "Categorical eligibility removes the income test; it does not guarantee a benefit.",
        "source": {"title": "Hawaiʻi DHS LIHEAP Detailed Model Plan FFY 2026, §1.4a",
                   "url": "https://humanservices.hawaii.gov/wp-content/uploads/2025/07/Model-Plan-Packet-2026.pdf"},
    },
    "wic": {
        "name": "WIC (women, infants and children)",
        "rule": "Members of SNAP households are adjunctively income-eligible for WIC. WIC also needs a "
                "categorical status (pregnant, postpartum, infant, child under 5) and nutritional risk.",
        "source": {"title": "7 CFR § 246.7(d)(2)(vi) — Adjunct or automatic income eligibility",
                   "url": "https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-A/part-246/subpart-C/section-246.7"},
    },
    "med_quest": {
        "name": "Med-QUEST (Medicaid) — income test",
        "rule": "Adults 19–64 qualify with income up to 138% of the Hawaiʻi poverty guidelines; children and "
                "pregnant people have higher limits; aged, blind and disabled applicants have a lower limit.",
        "source": {"title": "Med-QUEST Division — MAGI and non-MAGI income standards",
                   "url": "https://medquest.hawaii.gov/"},
    },
}


def _ids(obs: dict, *keys) -> list[str]:
    return [obs[k].obs_id for k in keys if k in obs]


@cached
def estimate(geo_id: str) -> dict:
    r = repo()
    if not r.geography(geo_id):
        raise KeyError(geo_id)
    obs = {o.indicator: o for o in r.observations([geo_id], INPUTS) if o.value is not None}
    v = {k: o.value for k, o in obs.items()}
    out = []

    def add(pid, unit, est, low, high, formula, inputs, confidence, assumptions):
        out.append({"program_id": pid, **RULES[pid], "unit": unit, "estimate": round(est) if est is not None else None,
                    "low": round(low) if low is not None else None, "high": round(high) if high is not None else None,
                    "formula": formula, "input_obs_ids": inputs, "confidence": confidence, "assumptions": assumptions})

    if "snap_hh_children" in v:
        add("school_meals", "households", v["snap_hh_children"], None, None,
            "SNAP households with children under 18 (S2201_C03_009)", _ids(obs, "snap_hh_children"), "high",
            ["Counts households, not children; a household may have several school-age children.", SNAP_ACS_CAVEAT])

    if "snap_hh_count" in v:
        income = None
        if "pop_below_125fpl" in v and "pop_below_150fpl" in v:
            a, b = v["pop_below_125fpl"], v["pop_below_150fpl"]
            income = a + (b - a) * (135 - 125) / (150 - 125)
        add("lifeline", "households", v["snap_hh_count"], v["snap_hh_count"], None,
            "SNAP households (S2201_C03_001) qualify categorically; the income route (≤135% FPL) adds more",
            _ids(obs, "snap_hh_count", "pop_below_125fpl", "pop_below_150fpl"), "high",
            ["Lower bound: counts only the SNAP route. Medicaid, SSI and housing routes are not added because "
             "households overlap and ACS does not report the overlap."]
            + ([f"Income route: about {round(income):,} people live below 135% of poverty "
                "(interpolated between the 125% and 150% lines)."] if income else []) + [SNAP_ACS_CAVEAT])

    if "snap_hh_count" in v and "households" in v and "pct_ssi_hh" in v:
        ssi = v["households"] * v["pct_ssi_hh"] / 100
        snap = v["snap_hh_count"]
        add("liheap", "households", max(snap, ssi), max(snap, ssi), min(v["households"], snap + ssi),
            "Range: larger of SNAP or SSI households (full overlap) to their sum (no overlap); TANF, GA and AABD "
            "households are mostly already in SNAP", _ids(obs, "snap_hh_count", "households", "pct_ssi_hh"), "medium",
            ["SSI households = total households × share with SSI (DP03_0070).", SNAP_ACS_CAVEAT])

    if "snap_persons_est" in v and "pct_under5" in v:
        snap_kids = v["snap_persons_est"] * v["pct_under5"] / 100
        inc = v["pop_below_185fpl"] * v["pct_under5"] / 100 if "pop_below_185fpl" in v else None
        lo, hi = (min(snap_kids, inc), max(snap_kids, inc)) if inc is not None else (snap_kids, None)
        add("wic", "children under 5", snap_kids, lo, hi,
            "Estimate: people in SNAP households × district share under 5 (adjunctive route). Range also uses "
            "people below 185% FPL × share under 5 (income route)",
            _ids(obs, "snap_persons_est", "pct_under5", "pop_below_185fpl"), "low",
            ["Assumes SNAP households have the district's age mix; they skew younger, so the low end likely "
             "understates.", "Excludes pregnant and postpartum people, who are also WIC-eligible.",
             "WIC also requires nutritional risk, which nearly all income-eligible applicants meet.", ACS_THRESHOLD_CAVEAT])

    if "pop_below_138fpl" in v:
        add("med_quest", "people", v["pop_below_138fpl"], v.get("pop_below_125fpl"), v.get("pop_below_150fpl"),
            "People below 138% of poverty, interpolated between the S1701 125% and 150% lines",
            _ids(obs, "pop_below_125fpl", "pop_below_138fpl", "pop_below_150fpl"), "medium",
            ["All ages counted at the adult limit: children and pregnant people qualify at higher incomes, so their "
             "eligible count is higher than shown.", "Many in this group already have Med-QUEST; this is the "
             "income-eligible pool, not the uninsured gap.", ACS_THRESHOLD_CAVEAT])

    return {"geo_id": geo_id, "estimates": out,
            "note": "Population-level estimates from published eligibility rules. Informational only; the "
                    "administering agency determines eligibility."}
