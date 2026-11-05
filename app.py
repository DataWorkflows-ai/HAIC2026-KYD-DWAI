"""
Know Your District — district profile dashboard for Hawaii legislative offices.

Presentation only. Calculations, routing, and guardrails live in scripts/agent.py.

Run locally:
    python3 -m streamlit run app.py
"""

import math

import streamlit as st
from scripts.agent import answer, get_district, build_profile

st.set_page_config(
    page_title="Know Your District",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1200px; }
    .kyd-header {
        border-bottom: 2px solid #0B5563;
        padding-bottom: 0.75rem;
        margin-bottom: 1.25rem;
    }
    /* Higher specificity so Streamlit's p rules do not override */
    div[data-testid="stMarkdownContainer"] p.kyd-kicker,
    p.kyd-kicker {
        color: #0B5563 !important;
        font-size: 14px !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600 !important;
        margin: 0;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-title,
    p.kyd-title {
        color: #0B1F33 !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        margin: 0.15rem 0 0.2rem 0;
        line-height: 1.2;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-context,
    p.kyd-context {
        color: #3D4A57 !important;
        font-size: 16px !important;
        margin: 0;
        line-height: 1.4;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-section,
    p.kyd-section {
        color: #0B1F33 !important;
        font-size: 20px !important;
        font-weight: 650 !important;
        margin: 1.25rem 0 0.5rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #E3E8ED;
    }
    .kyd-card {
        background: #FFFFFF;
        border: 1px solid #E3E8ED;
        border-radius: 6px;
        padding: 0.9rem 1rem 0.85rem 1rem;
        min-height: 0;
        height: auto;
        margin-bottom: 0.6rem;
        overflow: visible;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-card-label,
    p.kyd-card-label {
        color: #1A2332 !important;
        font-size: 17px !important;
        font-weight: 550 !important;
        line-height: 1.35;
        margin: 0 0 0.4rem 0;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-card-value,
    p.kyd-card-value {
        color: #0B1F33 !important;
        font-size: 30px !important;
        font-weight: 700 !important;
        line-height: 1.2;
        margin: 0;
        word-break: break-word;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-card-moe,
    p.kyd-card-moe {
        color: #3A4553 !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        margin: 0.3rem 0 0 0;
        line-height: 1.3;
    }
    div[data-testid="stMarkdownContainer"] p.kyd-card-note,
    p.kyd-card-note {
        color: #3A4553 !important;
        font-size: 14px !important;
        font-weight: 450 !important;
        margin: 0.35rem 0 0 0;
        line-height: 1.35;
    }
    div[data-testid="stMarkdownContainer"] .kyd-footer,
    .kyd-footer {
        color: #3A4553 !important;
        font-size: 14px !important;
        border-top: 1px solid #E3E8ED;
        padding-top: 0.75rem;
        margin-top: 1.5rem;
        line-height: 1.4;
    }
    div[data-testid="stSidebar"] { background-color: #F4F7F8; }
    div[data-testid="stSidebar"] * {
        font-size: 15px !important;
    }
    div[data-testid="stSidebar"] h1,
    div[data-testid="stSidebar"] h2,
    div[data-testid="stSidebar"] h3,
    div[data-testid="stSidebar"] .stMarkdown p {
        font-size: 16px !important;
        color: #0B1F33 !important;
    }
    div[data-testid="stSidebar"] button {
        font-size: 15px !important;
        color: #0B1F33 !important;
        white-space: normal !important;
        height: auto !important;
        min-height: 2.4rem;
        padding: 0.45rem 0.6rem !important;
        text-align: left;
        line-height: 1.3;
    }
    div[data-testid="stSidebar"] label,
    div[data-testid="stSidebar"] .stSelectbox label,
    div[data-testid="stSidebar"] .stRadio label {
        font-size: 15px !important;
        color: #1A2332 !important;
    }
    @media (max-width: 900px) {
        p.kyd-title { font-size: 26px !important; }
        p.kyd-card-value { font-size: 26px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: district selection and question
# ---------------------------------------------------------------------------
st.sidebar.markdown("**Know Your District**")
st.sidebar.caption("Hawaii legislative districts")

chamber = st.sidebar.radio("Chamber", ["House", "Senate"], horizontal=True)
max_dist = 51 if chamber == "House" else 25
district = st.sidebar.selectbox("District", list(range(1, max_dist + 1)))

st.sidebar.divider()
st.sidebar.markdown("**Ask a question**")
question = st.sidebar.text_area(
    "Question",
    placeholder="e.g. What is the poverty rate in HD 22?",
    label_visibility="collapsed",
    height=80,
)
if st.sidebar.button("Ask", use_container_width=True) and question.strip():
    st.session_state["last_question"] = question.strip()

st.sidebar.markdown("**Example questions**")
examples = [
    "Profile HD 22",
    "How many seniors live alone in HD 30?",
    "What is the uninsured rate in HD 12?",
    "kūpuna poverty in HD 45",
    "What share of households have no vehicle in SD 12?",
]
for ex in examples:
    if st.sidebar.button(ex, key=f"ex_{ex}", use_container_width=True):
        st.session_state["last_question"] = ex

# ---------------------------------------------------------------------------
# Helpers — display only; same field names and MOE rules as agent.py
# ---------------------------------------------------------------------------
def _num(val):
    if val is None:
        return None
    s = str(val).replace(",", "").replace("%", "").replace("±", "").replace("$", "").strip()
    if s in ("", "(X)", "None", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def money_parts(data, field):
    est = _num(data.get(f"{field}_estimate"))
    moe = _num(data.get(f"{field}_moe"))
    value = f"${est:,.0f}" if est is not None else "N/A"
    moe_str = f"±${moe:,.0f}" if moe is not None else ""
    return value, moe_str

def percent_parts(data, field):
    pct = data.get(f"{field}_percent")
    moe = data.get(f"{field}_percent_moe")
    if pct in (None, "(X)"):
        return "N/A", ""
    moe_str = str(moe).strip() if moe and str(moe) not in ("(X)", "None", "") else ""
    if moe_str and not moe_str.startswith("±"):
        moe_str = f"±{moe_str}"
    return str(pct), moe_str

def count_parts(data, field):
    est = data.get(f"{field}_estimate")
    moe = data.get(f"{field}_moe")
    n = _num(est)
    m = _num(moe)
    value = f"{int(n):,}" if n is not None else "N/A"
    moe_str = f"±{int(m):,}" if m is not None else ""
    return value, moe_str

def rent_burden_parts(data):
    p1 = _num(data.get("rent_30_to_34_9_percent"))
    p2 = _num(data.get("rent_35_plus_percent"))
    m1 = _num(data.get("rent_30_to_34_9_percent_moe"))
    m2 = _num(data.get("rent_35_plus_percent_moe"))
    if p1 is None or p2 is None:
        return "N/A", ""
    total = p1 + p2
    if m1 is not None and m2 is not None:
        moe = math.sqrt(m1 ** 2 + m2 ** 2)
        return f"{total:.1f}%", f"±{moe:.1f}"
    return f"{total:.1f}%", ""

def card(label, value, moe, note):
    moe_html = f'<p class="kyd-card-moe">{moe}</p>' if moe else ""
    note_html = f'<p class="kyd-card-note">{note}</p>' if note else ""
    st.markdown(
        f"""
        <div class="kyd-card">
          <p class="kyd-card-label">{label}</p>
          <p class="kyd-card-value">{value}</p>
          {moe_html}
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
data = get_district(chamber.lower(), district)

st.markdown(
    f"""
    <div class="kyd-header">
      <p class="kyd-kicker">Hawaii legislative district</p>
      <p class="kyd-title">{chamber} District {district}</p>
      <p class="kyd-context">ACS 2020–2024 five-year estimates, via DBEDT. Figures are survey estimates with margins of error.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not data:
    st.error(f"No data for {chamber} District {district}.")
else:
    # People
    st.markdown('<p class="kyd-section">People</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        v, m = count_parts(data, "pop_16_plus")
        card("Population 16 and over", v, m, "People · DP03")
    with c2:
        v, m = percent_parts(data, "pct_people_poverty")
        card("People below the poverty line", v, m, "People · DP03")
    with c3:
        v, m = percent_parts(data, "householders_65plus_living_alone")
        card("People age 65+ living alone", v, m, "Households · DP02")

    c4, c5, c6 = st.columns(3)
    with c4:
        v, m = percent_parts(data, "with_disability")
        card("Population with a disability", v, m, "People · DP02")
    with c5:
        v, m = percent_parts(data, "limited_english")
        card("Speak English less than “very well”", v, m, "People age 5+ · DP02")
    with c6:
        v, m = percent_parts(data, "pct_65plus_poverty")
        card("People age 65+ below poverty", v, m, "People 65+ · DP03")

    # Access
    st.markdown('<p class="kyd-section">Access</p>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    with a1:
        v, m = percent_parts(data, "pct_no_health_insurance")
        card("People without health insurance", v, m, "Civilian noninstitutionalized population · DP03")
    with a2:
        v, m = percent_parts(data, "no_vehicle")
        card("Households with no vehicle available", v, m, "Occupied housing units · DP04")
    with a3:
        v, m = percent_parts(data, "snap_benefits")
        card("Households reporting SNAP", v, m, "ACS survey estimate, not DHS enrollment · DP03")

    # Economic Conditions
    st.markdown('<p class="kyd-section">Economic Conditions</p>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        v, m = money_parts(data, "median_hh_income")
        card("Median household income", v, m, "Households · DP03")
    with e2:
        v, m = percent_parts(data, "in_labor_force")
        card("Labor force participation", v, m, "Population 16+ · DP03")
    with e3:
        v, m = percent_parts(data, "employed")
        card("Employment rate", v, m, "Population 16+ · DP03")

    e4, e5, e6 = st.columns(3)
    with e4:
        v, m = rent_burden_parts(data)
        card("Renters spending 30%+ of income on rent", v, m, "Renter households · DP04")
    with e5:
        v, m = percent_parts(data, "pct_children_under5_poverty")
        card("Related children under 5 in poverty", v, m, "Related children under 5 · DP03")
    with e6:
        v, m = money_parts(data, "per_capita_income")
        card("Per capita income", v, m, "People · DP03")

    # Sources
    with st.expander("Sources and margins of error"):
        st.markdown(build_profile(chamber.lower(), district))
        st.caption(
            "Margins of error are ACS 90% confidence intervals. "
            "Percent margins are used for percent figures. "
            "Rent burden combines the 30.0–34.9% and 35%+ GRAPI bands; its margin is the square root of the sum of the squared percent margins. "
            "SNAP is the share of households that reported receiving SNAP on the ACS survey, not administrative enrollment published by DHS."
        )

# Answer
if "last_question" in st.session_state:
    st.divider()
    st.subheader("Answer")
    st.caption(st.session_state["last_question"])
    with st.spinner("Looking up…"):
        result = answer(st.session_state["last_question"])
    st.markdown(result)

st.markdown(
    """
    <div class="kyd-footer">
      Data: U.S. Census ACS 2020–2024 five-year estimates via the Hawaii State Data Center (DBEDT).
      Aggregates only; no individual data. This tool is not an official State of Hawaii publication.
    </div>
    """,
    unsafe_allow_html=True,
)
