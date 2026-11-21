# Program gaps and HAIC requirement audit

Updated 2026-11-21 for the HAIC demo. All figures are aggregate public data. The app labels program gap rows as informational only; administering agencies decide individual eligibility.

## Where the demo requirements appear

| Requirement | Where in app |
|---|---|
| 76 legislators can ask district questions | Chat tab; suggested questions on Overview; `program_gaps` tool available to the agent |
| District profile population, age 65+, income/poverty, employment, housing | Overview tab headline and indicator table |
| County and state comparisons | Overview and Compare tabs; Program Gaps state anchors |
| Program recommendations with official sources | Programs tab and Program Gaps tab official links |
| Eligibility vs uptake | Program Gaps tab eligible/enrolled/gap/reach cards; SNAP, WIC, Med-QUEST, TANF, meals, Act 139 |
| Maps of boundaries and indicators | Map tab; new map-ready indicators include `snap_strict_gap_households`, `medquest_uninsured_eligible`, `wic_gap_est`, `act139_acs_upper_children` |
| Exportable summary with sources | Overview, Program Gaps, and school tables expose print/CSV export; `export_summary` includes program gaps |
| Unavailable or uncertain data labelled | Program Gaps cards include unavailable/caveat text; Figure popovers show source, vintage, method, MOE |
| Population-level, nonpartisan, public data only | Footer, Program Gaps disclaimer, source library, and agent guardrails |
| Crosswalk to 2022 boundaries | Sources & Methods; school rows list House/Senate district by campus location |
| Keep program info current | Sources tab/source library plus build-time verification suite |
| Outreach opportunity | Program Gaps largest gaps, SNAP strict district gap, and CEP-eligible non-participating school tables |

## Corrected data anchors

| Topic | Demo-safe value |
|---|---|
| SNAP statewide | USDA FY2022: 161,104 eligible people; 130,188 eligible participants; 30,916 gap; about 15,000-46,000 range |
| SNAP district | ACS B22003 poverty households not reporting SNAP; House 24 = 1,755 ±268 |
| TANF | Proxy denominator is 18,183 children under 50% FPL; reach range 18.7%-24.0% |
| WIC | FNS CY2023 44,888 eligible; Aug 2026 participants 25,804; about 19,100 not served |
| Med-QUEST | ACS C27016 uninsured-eligible gap 13,544 statewide; House 24 = 569 ±185 |
| School meals | October SY2025-26 is eligibility, not meals served; DOE non-charter 78,927 of 153,435 |
| CEP | HCNP workbook: 118 participating; 74 eligible not participating; 45,902 enrolled; 22,270 not certified |
| Act 139 | Range: HIDOE nearly 12,000 expected additional students to ACS upper bound about 36,500 children |
| Pahoa Elementary | House 4 / Senate 2 |

## Known caveats intentionally shown

- WIC district rows are allocated from state anchors because no public district or clinic caseload is published.
- TANF reach is a proxy range, not an official take-up rate.
- Med-QUEST reach mixes coverage and uninsured universes; the uninsured-eligible count is the solid district figure.
- Act 139 is a range, not a 24,000-child point gap.
- Utilities (H-HEAP, Lifeline) have no public district uptake gap in this package; they are listed as unavailable with outreach caveats.
