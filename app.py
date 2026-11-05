"""
Know Your District — district-first profile tool for Hawaii legislators.

Run locally:
    python3 -m streamlit run app.py
"""

import streamlit as st
from scripts.agent import answer, get_district, build_profile

st.set_page_config(page_title="Know Your District", page_icon="🏝️", layout="wide")

st.sidebar.title("Know Your District")
st.sidebar.caption("Hawaii legislative districts")

chamber = st.sidebar.radio("Chamber", ["House", "Senate"], horizontal=True)
max_dist = 51 if chamber == "House" else 25
district = st.sidebar.selectbox("District", list(range(1, max_dist + 1)))

st.sidebar.divider()
question = st.sidebar.text_input("Or ask a question", placeholder="e.g. Profile HD 22")
if st.sidebar.button("Go") and question.strip():
    st.session_state["last_question"] = question

st.title(f"{chamber} District {district}")

data = get_district(chamber.lower(), district)
if not data:
    st.error(f"No data for {chamber} District {district}.")
else:
    def metric_display(field, is_money=False):
        """Return 'value ±moe' string for visible display."""
        if is_money:
            est = data.get(f"{field}_estimate")
            moe = data.get(f"{field}_moe")
            try:
                val = f"${int(float(str(est).replace(',',''))):,}"
            except (TypeError, ValueError):
                val = "N/A"
            moe_str = str(moe).strip() if moe and str(moe) not in ("(X)", "None", "") else ""
            if moe_str and not moe_str.startswith("±"):
                moe_str = f"±{moe_str}"
            return f"{val} {moe_str}".strip()
        else:
            pct = data.get(f"{field}_percent")
            moe = data.get(f"{field}_percent_moe")
            if pct in (None, "(X)"):
                return "N/A"
            moe_str = str(moe).strip() if moe and str(moe) not in ("(X)", "None", "") else ""
            if moe_str and not moe_str.startswith("±"):
                moe_str = f"±{moe_str}"
            return f"{pct} {moe_str}".strip()

    cols = st.columns(5)
    metrics = [
        ("Poverty", "pct_people_poverty", False),
        ("Uninsured", "pct_no_health_insurance", False),
        ("65+ Alone", "householders_65plus_living_alone", False),
        ("Disability", "with_disability", False),
        ("No Vehicle", "no_vehicle", False),
    ]
    for col, (label, field, is_money) in zip(cols, metrics):
        col.metric(label, metric_display(field, is_money))

    cols2 = st.columns(4)
    metrics2 = [
        ("Limited English", "limited_english", False),
        ("SNAP (Census)", "snap_benefits", False),
        ("Median Income", "median_hh_income", True),
        ("Labor Force", "in_labor_force", False),
    ]
    for col, (label, field, is_money) in zip(cols2, metrics2):
        col.metric(label, metric_display(field, is_money))

    with st.expander("Sources and margins of error"):
        st.markdown(build_profile(chamber.lower(), district))

if "last_question" in st.session_state:
    st.divider()
    st.subheader("Answer")
    with st.spinner("Looking up…"):
        result = answer(st.session_state["last_question"])
    st.markdown(result)

st.divider()
st.caption("Data: U.S. Census ACS 2020–2024 5-year via DBEDT. Aggregates only, no individual data.")
