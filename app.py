"""
Know Your District — district-first profile tool for Hawaii legislators.

Run locally:
    python3 -m streamlit run app.py
"""

import streamlit as st
from scripts.agent import answer, get_district, build_profile

st.set_page_config(page_title="Know Your District", page_icon="🏝️", layout="wide")

# Sidebar: chamber + district picker
st.sidebar.title("Know Your District")
st.sidebar.caption("Hawaii legislative districts")

chamber = st.sidebar.radio("Chamber", ["House", "Senate"], horizontal=True)
max_dist = 51 if chamber == "House" else 25
district = st.sidebar.selectbox("District", list(range(1, max_dist + 1)))

st.sidebar.divider()
question = st.sidebar.text_input("Or ask a question", placeholder="e.g. Profile HD 22")
if st.sidebar.button("Go") and question.strip():
    st.session_state["last_question"] = question

# Main area
st.title(f"{chamber} District {district}")

data = get_district(chamber.lower(), district)
if not data:
    st.error(f"No data for {chamber} District {district}.")
else:
    # Metric cards
    def metric_val(field):
        pct = data.get(f"{field}_percent")
        moe = data.get(f"{field}_percent_moe")
        if pct in (None, "(X)"):
            return "N/A", ""
        moe_str = f" {moe}" if moe and str(moe) not in ("(X)", "None", "") else ""
        return str(pct), moe_str

    cols = st.columns(5)
    metrics = [
        ("Poverty", "pct_people_poverty"),
        ("Uninsured", "pct_no_health_insurance"),
        ("65+ Alone", "householders_65plus_living_alone"),
        ("Disability", "with_disability"),
        ("No Vehicle", "no_vehicle"),
    ]
    for col, (label, field) in zip(cols, metrics):
        val, moe = metric_val(field)
        col.metric(label, val, help=f"ACS 2020-2024 5-year. {moe}" if moe else "ACS 2020-2024 5-year")

    cols2 = st.columns(4)
    metrics2 = [
        ("Limited English", "limited_english"),
        ("SNAP (Census)", "snap_benefits"),
        ("Median Income", "median_hh_income"),
        ("Labor Force", "in_labor_force"),
    ]
    for col, (label, field) in zip(cols2, metrics2):
        if field == "median_hh_income":
            est = data.get(f"{field}_estimate")
            moe = data.get(f"{field}_moe")
            try:
                val = f"${int(float(str(est).replace(',',''))):,}"
            except (TypeError, ValueError):
                val = "N/A"
            moe_str = f" {moe}" if moe and str(moe) not in ("(X)", "None", "") else ""
            col.metric(label, val, help=f"ACS 2020-2024 DP03. {moe_str}" if moe_str else "ACS 2020-2024 DP03")
        else:
            val, moe = metric_val(field)
            col.metric(label, val, help=f"ACS 2020-2024 5-year. {moe}" if moe else "ACS 2020-2024 5-year")

    # Sources expander
    with st.expander("Sources and margins of error"):
        st.markdown(build_profile(chamber.lower(), district))

# Question answer area
if "last_question" in st.session_state:
    st.divider()
    st.subheader("Answer")
    with st.spinner("Looking up…"):
        result = answer(st.session_state["last_question"])
    st.markdown(result)

# Footer
st.divider()
st.caption("Data: U.S. Census ACS 2020–2024 5-year via DBEDT. Aggregates only, no individual data.")
