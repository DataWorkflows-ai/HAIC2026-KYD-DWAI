"""
Streamlit app for the HAIC 2026 Know Your District agent.

Run locally:
    streamlit run app.py

Mitchell can deploy this directly (Streamlit Community Cloud, etc.).
End users: legislators and their offices.
"""

import streamlit as st
from scripts.agent import answer

st.set_page_config(page_title="Know Your District", page_icon="🏝️")

st.title("Know Your District")
st.caption("HAIC 2026 – Socio-economic summaries for Hawaii legislative districts")

st.markdown(
    "Ask a question about a Hawaii House or Senate district. "
    "Answers use ACS 2020-2024 5-year data and include citations and official program links."
)

# Example questions
examples = [
    "How many kūpuna in House District 22 live below the poverty line?",
    "Which House districts have the highest share of residents without health insurance?",
    "What share of households in House District 19 spend more than 30% of their income on rent?",
    "How many children under 5 in House District 45 live in low-income households?",
    "In Senate District 12, how many households are likely eligible for SNAP?",
]

selected = st.selectbox("Example questions", [""] + examples)
question = st.text_input("Or type your own question", value=selected)

if st.button("Get answer") or question:
    if question.strip():
        with st.spinner("Looking up the data…"):
            result = answer(question)
        st.markdown(result)
    else:
        st.info("Enter a question or choose an example above.")

st.divider()
st.caption(
    "Data: ACS 2020-2024 5-year estimates (DP03, DP04) from the Hawaii State Data Center. "
    "Program links point to official state pages. Margins of error and data limitations apply."
)
