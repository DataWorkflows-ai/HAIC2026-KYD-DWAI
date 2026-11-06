"""
Know Your District — district profile dashboard for Hawaii legislative offices.

Presentation only. Calculations, routing, and guardrails live in scripts/agent.py.
Comparison ranking lives in scripts/comparison.py.

Run locally:
    python3 -m streamlit run app.py
"""

import math

import plotly.graph_objects as go
import streamlit as st
from scripts.agent import answer, get_district, build_profile
from scripts.comparison import MEASURES, comparison_csv, programs_for, rank_districts
from scripts.map_data import (
    MISSING_COLOR,
    TEAL_BINS,
    ZOOM_AREAS,
    bin_label,
    locate_district,
    map_frame,
)

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
    .kyd-map-block {
        margin: 0.4rem 0 1.1rem 0;
    }
    .kyd-map-note {
        color: #1A2332 !important;
        font-size: 15px !important;
        line-height: 1.55 !important;
        margin: 0.85rem 0 !important;
    }
    div[data-testid="stPlotlyChart"] {
        overflow: hidden;
    }
    @media (max-width: 900px) {
        p.kyd-title { font-size: 26px !important; }
        p.kyd-card-value { font-size: 26px !important; }
        .kyd-legend { gap: 0.45rem 0.8rem; }
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

# Apply a pending chamber change before the radio is created. Setting a
# widget key after the widget has already been instantiated raises
# StreamlitWidgetAlreadyInstantiatedError.
if "requested_chamber" in st.session_state:
    st.session_state["profile_chamber"] = st.session_state.pop("requested_chamber")

chamber = st.sidebar.radio("Chamber", ["House", "Senate"], horizontal=True, key="profile_chamber")
max_dist = 51 if chamber == "House" else 25
if "requested_district" in st.session_state:
    req = st.session_state.pop("requested_district")
    if 1 <= req <= max_dist:
        st.session_state["profile_district"] = req
district = st.sidebar.selectbox("District", list(range(1, max_dist + 1)), key="profile_district")

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
        card(
            "Households with a person age 65+ living alone",
            v, m,
            "Share of total households · DP02. Not the share of seniors who live alone.",
        )

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

    with st.expander("Sources and margins of error"):
        st.markdown(build_profile(chamber.lower(), district))
        st.caption(
            "Margins of error are ACS 90% confidence intervals. "
            "Percent margins are used for percent figures. "
            "Rent burden combines the 30.0–34.9% and 35%+ GRAPI bands; its margin is the square root of the sum of the squared percent margins. "
            "SNAP is the share of households that reported receiving SNAP on the ACS survey, not administrative enrollment published by DHS. "
            "Households with a person age 65+ living alone is the share of total households (DP02), not the share of seniors who live alone."
        )

# ---------------------------------------------------------------------------
# District comparison — one chamber, one measure, no composite score
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="kyd-section">District comparison</p>', unsafe_allow_html=True)
st.caption(
    "Ranks districts within one chamber by one verified measure, highest percentage first. "
    "This is a comparison of survey estimates, not an eligibility ranking, an enrollment-gap ranking, or a need score."
)

measure_labels = {key: meta["label"] for key, meta in MEASURES.items()}
cmp_chamber = st.radio("Chamber to compare", ["House", "Senate"], horizontal=True, key="cmp_chamber")
cmp_measure = st.selectbox(
    "Measure",
    options=list(MEASURES.keys()),
    format_func=lambda k: measure_labels[k],
    key="cmp_measure",
)

ranked, missing_count = rank_districts(cmp_chamber.lower(), cmp_measure)
meta = MEASURES[cmp_measure]

st.markdown(
    f"**{meta['label']}** — {cmp_chamber} districts. "
    f"Denominator: {meta['denominator']}. Source: {meta['table']}, ACS 2020–2024 5-year."
)
if missing_count:
    st.warning(f"{missing_count} district(s) have no estimate for this measure and are excluded. Missing data is not treated as zero.")
else:
    st.caption("No missing estimates for this measure. Missing data would be excluded, never treated as zero.")

st.info(
    "Overlapping margins of error mean an apparent difference between districts may not be statistically meaningful. "
    "A flag marks estimates whose margin of error exceeds 30% of the estimate. "
    "Map colors are quantile bins of the statewide comparison. They do not establish statistically significant differences or enrollment gaps."
)

# Table first so a row selection is known before the map is drawn.
st.markdown(
    '<p class="kyd-map-note">Select a district row to locate it on the map. '
    "Use Open profile to view its statistics.</p>",
    unsafe_allow_html=True,
)

table_rows = []
if ranked:
    for r in ranked:
        est = f"{int(r['estimate']):,}" if r["estimate"] is not None else ""
        est_moe = f"±{int(r['estimate_moe']):,}" if r["estimate_moe"] is not None else ""
        table_rows.append({
            "District": r["district"],
            "Percent": r["percent_display"],
            "Percent MOE": r["percent_moe_display"],
            "Estimate": est,
            "Estimate MOE": est_moe,
            "Denominator": r["denominator"],
            "Source": r["source_table"],
            "Year": r["year"],
            "Uncertainty flag": r["uncertainty_flag"],
        })
    table_event = st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"cmp_table_{cmp_chamber}_{cmp_measure}",
    )
    selected_rows = []
    if table_event is not None and getattr(table_event, "selection", None) is not None:
        selected_rows = list(getattr(table_event.selection, "rows", []) or [])
    located = int(table_rows[selected_rows[0]]["District"]) if selected_rows else None
else:
    located = None
    st.caption("No districts to list for this measure.")

# ---------------------------------------------------------------------------
# Comparison map — same chamber, measure, and values as the table
# ---------------------------------------------------------------------------
st.markdown('<div id="map-anchor"></div>', unsafe_allow_html=True)
geojson, map_rows, edges, map_missing = map_frame(cmp_chamber.lower(), cmp_measure)

located_info = locate_district(geojson, located) if located else None
if located_info:
    view = located_info["view"]
    group_text = ", ".join(located_info["groups"]) or "its boundary"
    st.markdown(
        f'<p class="kyd-map-note">Showing {cmp_chamber} District {located} on {group_text}. '
        "The statewide color bins are unchanged. This locates the district; it does not open the profile.</p>",
        unsafe_allow_html=True,
    )
else:
    zoom_choice = st.selectbox("Map area", list(ZOOM_AREAS.keys()), key="map_area")
    view = ZOOM_AREAS[zoom_choice]

valued = [r for r in map_rows if not r["missing"] and r["bin"] is not None]
missing_rows = [r for r in map_rows if r["missing"] or r["bin"] is None]
n_bins = max((r["bin"] for r in valued), default=-1) + 1
colors = TEAL_BINS[: max(n_bins, 1)]


def _scale(cols):
    n = len(cols)
    scale = []
    for i, color in enumerate(cols):
        scale.append([i / n, color])
        scale.append([(i + 1) / n, color])
    return scale


def _hover(row):
    est = f"{int(row['estimate']):,}" if row["estimate"] is not None else "No estimate"
    est_moe = f"±{int(row['estimate_moe']):,}" if row["estimate_moe"] is not None else ""
    flag = row["uncertainty_flag"] or ""
    if flag == "MOE exceeds 30% of estimate":
        flag = "Uncertainty: MOE exceeds 30% of the estimate"
    elif flag == "missing":
        flag = "No estimate for this measure. Not shown as zero."
    return [
        cmp_chamber,
        est,
        est_moe,
        row["denominator"] or "—",
        row["source_table"] or "—",
        row["year"] or "—",
        flag,
        row["bin_label"],
    ]


fig = go.Figure()
if valued:
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=[r["district"] for r in valued],
        z=[r["bin"] for r in valued],
        featureidkey="properties.district",
        colorscale=_scale(colors),
        zmin=-0.5,
        zmax=n_bins - 0.5,
        showscale=False,
        marker_line_width=0.4,
        marker_line_color="#5C6B78",
        customdata=[_hover(r) for r in valued],
        hovertemplate=(
            "%{customdata[0]} District %{location}<br>"
            "Share: %{customdata[7]}<br>"
            "Estimate: %{customdata[1]} %{customdata[2]}<br>"
            "Denominator: %{customdata[3]}<br>"
            "Source: %{customdata[4]}<br>"
            "Year: %{customdata[5]}<br>"
            "%{customdata[6]}<extra></extra>"
        ),
        name="Estimate",
    ))
if missing_rows:
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=[r["district"] for r in missing_rows],
        z=[0] * len(missing_rows),
        featureidkey="properties.district",
        colorscale=[[0, MISSING_COLOR], [1, MISSING_COLOR]],
        showscale=False,
        marker_line_width=0.4,
        marker_line_color="#5C6B78",
        customdata=[_hover(r) for r in missing_rows],
        hovertemplate=(
            "%{customdata[0]} District %{location}<br>"
            "No estimate for this measure. Not shown as zero.<br>"
            "Source: %{customdata[4]}<extra></extra>"
        ),
        name="No estimate",
    ))
if located:
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=[located],
        z=[1],
        featureidkey="properties.district",
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        showscale=False,
        marker_line_width=3,
        marker_line_color="#0B1F33",
        hoverinfo="skip",
        name="Selected",
    ))
if located_info:
    others = [lb for lb in located_info["labels"] if not lb["selected"]]
    selected_lb = [lb for lb in located_info["labels"] if lb["selected"]]
    if others:
        fig.add_trace(go.Scattermap(
            lat=[lb["lat"] for lb in others],
            lon=[lb["lon"] for lb in others],
            mode="text",
            text=[str(lb["district"]) for lb in others],
            textfont={"size": 12, "color": "#0B1F33"},
            hoverinfo="skip",
            name="District numbers",
        ))
    if selected_lb:
        fig.add_trace(go.Scattermap(
            lat=[selected_lb[0]["lat"]],
            lon=[selected_lb[0]["lon"]],
            mode="markers+text",
            marker={"size": 30, "color": "#0B1F33"},
            text=[str(located)],
            textfont={"size": 14, "color": "#FFFFFF"},
            hoverinfo="skip",
            name="Selected district",
        ))
fig.update_layout(
    map_style="carto-positron",
    map_center=view["center"],
    map_zoom=view["zoom"],
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    height=560,
    uirevision=f"{cmp_chamber}-{cmp_measure}-{located or 'none'}",
)
map_event = st.plotly_chart(
    fig,
    use_container_width=True,
    on_select="rerun",
    selection_mode="points",
    key=f"map_{cmp_chamber}_{cmp_measure}",
)

# Color bins live in a normal Streamlit block below the chart.
# The required basemap credit stays inside the Plotly map.
st.caption("Color bins")
legend_cols = st.columns(n_bins + (1 if missing_rows else 0))
for i in range(n_bins):
    legend_cols[i].markdown(
        f'<span style="display:inline-block;width:14px;height:14px;background:{colors[i]};'
        f'border:1px solid #5C6B78;margin-right:6px;vertical-align:middle;"></span>'
        f'{bin_label(edges, i)}',
        unsafe_allow_html=True,
    )
if missing_rows:
    legend_cols[-1].markdown(
        f'<span style="display:inline-block;width:14px;height:14px;background:{MISSING_COLOR};'
        f'border:1px solid #5C6B78;margin-right:6px;vertical-align:middle;"></span>No estimate',
        unsafe_allow_html=True,
    )

if located:
    import streamlit.components.v1 as components
    components.html(
        """
        <script>
        const el = window.parent.document.getElementById("map-anchor");
        if (el) el.scrollIntoView({behavior: "smooth", block: "start"});
        </script>
        """,
        height=0,
    )

# Notices below the map, each in its own block.

flagged = [r for r in valued if r["uncertainty_flag"] == "MOE exceeds 30% of estimate"]
if flagged:
    names = ", ".join(f"{cmp_chamber} {r['district']}" for r in flagged[:8])
    more = f" and {len(flagged) - 8} more" if len(flagged) > 8 else ""
    st.markdown(
        f'<p class="kyd-map-note">Uncertainty flag: the margin of error exceeds 30% of the estimate '
        f"for {len(flagged)} district(s) ({names}{more}). These are marked in the hover details and in the table.</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    '<p class="kyd-map-note">Boundaries: State of Hawaiʻi Office of Elections; Hawaiʻi Statewide GIS Program. '
    "2022 legislative districts as adopted by the Reapportionment Commission, retrieved 2026-11-05 "
    "from AdminBnd MapServer layers 33 (House) and 34 (Senate). "
    "The carto-positron basemap tiles are loaded from Carto; the polygons and data are local. "
    "If the tiles cannot load, the polygons still draw. "
    "Boundaries show district geography only, not the location of individual households, "
    "and a district statistic does not establish any individual's eligibility.</p>",
    unsafe_allow_html=True,
)

# Map selection opens the profile through the same pending-state path as the button.
# The dropdown below remains available if selection is not supported.
if map_event is not None and getattr(map_event, "selection", None) is not None:
    points = getattr(map_event.selection, "points", None) or []
    if points:
        point = points[0]
        loc = point.get("location") if isinstance(point, dict) else getattr(point, "location", None)
        if loc is not None:
            picked_map = int(loc)
            already = (
                st.session_state.get("map_opened_district") == picked_map
                and st.session_state.get("map_opened_chamber") == cmp_chamber
            )
            if not already:
                st.session_state["map_opened_district"] = picked_map
                st.session_state["map_opened_chamber"] = cmp_chamber
                st.session_state["requested_district"] = picked_map
                st.session_state["profile_opened"] = (
                    f"{cmp_chamber} District {picked_map}'s profile is now displayed at the top of the page."
                )
                if cmp_chamber != chamber:
                    st.session_state["requested_chamber"] = cmp_chamber
                st.rerun()

if ranked:
    st.download_button(
        "Download comparison as CSV",
        data=comparison_csv(ranked),
        file_name=f"{cmp_chamber.lower()}_{cmp_measure}_comparison.csv",
        mime="text/csv",
    )

    pick = st.selectbox(
        "Open a district profile from these results",
        options=[r["district"] for r in ranked],
        format_func=lambda d: f"{cmp_chamber} District {d}",
        key="open_profile",
    )
    if st.button("Open profile"):
        st.session_state["requested_district"] = pick
        st.session_state["profile_opened"] = (
            f"{cmp_chamber} District {pick}'s profile is now displayed at the top of the page."
        )
        if cmp_chamber != chamber:
            st.session_state["requested_chamber"] = cmp_chamber
        st.rerun()
    st.caption("Open profile shows the district's statistics. It is separate from locating a row on the map.")
    if st.session_state.get("profile_opened"):
        st.success(st.session_state["profile_opened"])

# ---------------------------------------------------------------------------
# Program information — only programs whose official pages were opened
# ---------------------------------------------------------------------------
st.markdown('<p class="kyd-section">Program information</p>', unsafe_allow_html=True)
st.caption(
    "Programs that may be relevant to the selected measure. A district statistic does not establish any individual's eligibility. "
    "District-level eligible-but-not-enrolled counts are not available in the current data. "
    "SNAP receipt and county enrollment are not subtracted from district estimates; the populations, units, and geographies are not interchangeable."
)

verified, unverified = programs_for(cmp_measure)
if verified:
    for prog in verified:
        st.markdown(
            f"**{prog['name']}**  \n"
            f"{prog['serves']}  \n"
            f"[Official page]({prog['url']}) · checked {prog['checked']}"
        )
else:
    st.markdown("No verified program page is linked to this measure.")

if unverified:
    st.warning("Official information that could not be verified on the date checked:")
    for item in unverified:
        st.markdown(f"**{item['name']}** — {item['note']} [Page]({item['url']}) · checked {item['checked']}")

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
