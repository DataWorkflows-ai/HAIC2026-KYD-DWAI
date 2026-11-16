# Hawaii DOE Smarter Balanced and HSA Science results, SY 2024-25

Downloaded for the HAIC 2026 Know Your District project. Public Excel files only; no login was required. Official source publishes English Language Arts and Mathematics in a single workbook, not two separate files.

## Source page

- https://hawaiipublicschools.org/academics/types-of-testing/

That page lists “2025 results” with two Excel links (ELA/Mathematics combined, and HSA-Science). It also links the Hawaiʻi Smarter Balanced Portal at https://smarterbalanced.alohahsap.org/, which is a practice-test and resources site, not the results download page. The workbooks below came from the DOE types-of-testing page.

## Terms of use

Files are content of the official Hawaiʻi State Department of Education website and are subject to the Department’s Terms of Use:

- https://hawaiipublicschools.org/useful-links/terms-of-use/

Key points from that page (retrieved 2026-11-15): the site may be used for authorized purposes only and is provided as a public service, “as is,” without warranties. “Duplication or use of any CONTENT from this WEBSITE for commercial purposes or in any manner likely to give the impression of official approval by the state of Hawaiʻi is prohibited.” Copyright © 1995-2025 Department of Education, state of Hawaiʻi.

## Files

### SBA2024-25.xlsx

- Source URL: https://hawaiipublicschools.org/wp-content/uploads/SBA2024-25.xlsx
- Link text on the source page: 2025 results, English Language Arts/Mathematics (EXCEL)
- Download time: Sunday, Nov 15, 2026, 9:52 PM HST
- Size: 108,631 bytes
- SHA256: 7099effea90feffa7887c5e87e6a13e977e0225ac7987096a802fcb429c7e50f
- Title in the workbook: 2024-2025 Smarter Balanced Assessment, English Language Arts & Mathematics
- Subjects: English Language Arts and Mathematics in the same file (side-by-side columns)
- Geography: state, complex area, complex, and school (four sheets). Not legislative or county-council districts.
- Broken out by complex area: yes. The COMPLEX AREA sheet has all 16 complex areas, including a “Charter” grouping. The COMPLEX and SCHOOLS sheets also carry a Complex Area column.
- Broken out by school name: yes. The SCHOOLS sheet has a School Name column for 295 schools.
- Grade coverage: yes, grades 3–8 and 11, plus an All Grades total, at every geography level (state, complex area, complex, and school). School rows include only the grades that school serves (for example an elementary school has grades 3–5; a high school has grade 11).
- School code for joins: yes. SCHOOLS has a School Code column. All 295 codes are 3-digit numeric HIDOE school codes, range 100–569, unique, one per school name. Suitable to join to school location files that use the same HIDOE school code.
- Suppression: an asterisk `*` means data is unavailable or suppressed to protect student identities under FERPA (footnote on the COMPLEX and SCHOOLS sheets). STATE and COMPLEX AREA have no suppressed cells. COMPLEX has 2 suppressed rows (8 cells): Hāna complex, grades 4 and 6. SCHOOLS has 130 suppressed rows (500 asterisk cells).
- Charter: listed as its own complex area (38 charter schools in this file).

Sheets and columns:

1. STATE (15 rows total; 8 data rows). Columns: Grade; English Language Arts N Tested, N Proficient, Met/Exceeded Achievement Standard; Mathematics N Tested, N Proficient, Met/Exceeded Achievement Standard. Grades: 3, 4, 5, 6, 7, 8, 11, All Grades.
2. COMPLEX AREA (135 rows total; 128 data rows = 16 complex areas × 8 grade rows). Columns: Complex Area; Grade; ELA N Tested, Met/Exceeded Achievement Standard; Mathematics N Tested, Met/Exceeded Achievement Standard. Identifier cells are left blank after the first row of each complex area (forward-fill to read). Every complex area has grades 3–8, 11, and All Grades.
3. COMPLEX (353 rows total; 344 data rows = 43 complexes × 8 grade rows; 1 blank row; 1 FERPA footnote). Columns: Complex Area; Complex; Grade; then the same ELA and Mathematics rate columns as COMPLEX AREA (no N Proficient). Every complex has grades 3–8, 11, and All Grades, with the two Hāna suppressions noted above.
4. SCHOOLS (1,290 rows total; 1,281 data rows; 1 blank row; 1 FERPA footnote). Columns: Complex Area; Complex; School Code; School Name; Grade; ELA N Tested, Met/Exceeded Achievement Standard; Mathematics N Tested, Met/Exceeded Achievement Standard. 295 schools. Grade-row counts: Grade 3 (207), 4 (207), 5 (207), 6 (151), 7 (89), 8 (89), 11 (70), All Grades (261).

### HSA-Science2024-25.xlsx

- Source URL: https://hawaiipublicschools.org/wp-content/uploads/HSA-Science2024-25.xlsx
- Link text on the source page: 2025 results, HSA-Science (EXCEL)
- Download time: Sunday, Nov 15, 2026, 9:52 PM HST
- Size: 46,510 bytes
- SHA256: b4932b0840f9edc0d74c01a98a355e3b8a356201e29a24807c573502797a31c5
- Title in the workbook: 2024-2025 Hawaii State Assessment, Science (Grades 5 and 8) & End of Course Biology (High School)
- Subject: Science only (HSA Science in grades 5 and 8; Biology end-of-course exam reported as High School)
- Geography: state, complex area, complex, and school (four sheets). Not legislative or county-council districts.
- Broken out by complex area: yes. The COMPLEX AREA sheet has all 16 complex areas, including “Charter.” The COMPLEX and SCHOOLS sheets also carry a Complex Area column.
- Broken out by school name: yes. The SCHOOLS sheet has a School Name column for 293 schools.
- Grade coverage: no, this file does not cover grades 3–8 and 11. It covers Grade 5, Grade 8, and High School (Biology EOC), plus an All Grades total. It does not include grades 3, 4, 6, or 7, and high school is labeled “High School,” not “Grade 11.”
- School code for joins: yes. SCHOOLS has a School Code column. All 293 codes are 3-digit numeric HIDOE school codes, range 100–568, unique, one per school name. Same coding system as the SBA file.
- Suppression: same FERPA asterisk footnote on COMPLEX and SCHOOLS. STATE, COMPLEX AREA, and COMPLEX have no suppressed cells (the COMPLEX footnote is present but unused). SCHOOLS has 54 suppressed rows (108 asterisk cells).
- Charter: listed as its own complex area (36 charter schools in this file). Two charter schools appear in the SBA file but not here: Kamalani Academy (school code 553, grades 3–8) and Kūlia Academy (school code 569, grades 6–8). No schools appear only in the Science file.
- All Grades rows on the SCHOOLS sheet appear only for the 46 schools that have more than one tested science grade.

Sheets and columns:

1. STATE (11 rows total; 4 data rows). Columns: Grade; N Tested; N Proficient; Met/Exceeded Achievement Standard. Grades: 5, 8, High School, All Grades.
2. COMPLEX AREA (71 rows total; 64 data rows = 16 complex areas × 4 grade rows). Columns: Complex Area; Grade; N Tested; Met/Exceeded Achievement Standard. Every complex area has Grade 5, Grade 8, High School, and All Grades.
3. COMPLEX (181 rows total; 172 data rows = 43 complexes × 4 grade rows; 1 blank row; 1 FERPA footnote). Columns: Complex Area; Complex; Grade; N Tested; Met/Exceeded Achievement Standard. Every complex has the same four grade rows.
4. SCHOOLS (418 rows total; 409 data rows; 1 blank row; 1 FERPA footnote). Columns: Complex Area; Complex; School Code; School Name; Grade; N Tested; Met/Exceeded Achievement Standard. 293 schools. Grade-row counts: Grade 5 (206), Grade 8 (87), High School (70), All Grades (46).

## Gaps

- There is no separate official 2025 ELA-only or Math-only xlsx. Both subjects are in SBA2024-25.xlsx.
- HSA Science does not cover grades 3–8 and 11; it covers grades 5 and 8 plus high-school Biology EOC.
- Results are at DOE complex-area / complex / school geography, not State House, State Senate, or county-council districts. School Code can be used to join schools to other location files.
- Older-year workbooks (2022–2024) are also linked on the same source page and were not downloaded.
