# HAIC2026-KYD-DWAI

Raw public source-data library for the 2026 Hawaii Annual Innovation Challenge
(HAIC) use case **Know Your District: An AI Agent for Hawaii's Legislative
District Resident Profiles**.

This repository is only the data-collection and organization layer. It does not
build the AI agent.

## Challenge summary

The DBEDT/READ challenge asks teams to help legislators and public officials get
fast, sourced resident profiles for Hawaii House and Senate districts. Today,
economic, tax, housing, demographic, and program information is spread across
many public reports and tables. A future agent must answer in plain language,
cite every figure, identify the source year and geography, and say when data is
estimated, unavailable, outdated, or uncertain.

The official challenge rules are saved at:

- `docs/HAIC2026_Know_Your_District_Challenge_Rules.pdf`

## Data sources collected

The crawler is scoped to the public pages requested for this data library:

1. Department of Taxation annual reports:
   <https://tax.hawaii.gov/stats/a5_1annual/>
2. Department of Taxation individual income statistics:
   <https://tax.hawaii.gov/stats/a5_1annual/a5_5ind_inc/>
3. Department of Taxation current monthly tax reports:
   <https://tax.hawaii.gov/stats/a5_3txcolrpt/>
4. DBEDT Research & Economic Analysis:
   <https://dbedt.hawaii.gov/economic/>
5. Hawaii State Data Center American Community Survey:
   <https://census.hawaii.gov/acs/>

## Repository layout

```text
data/
  MANIFEST.csv              # Downloaded-file manifest with source metadata
  CRAWL_FAILURES.csv        # Skipped, blocked, 404, timeout, and rate-limit URLs
  raw/
    tax.hawaii.gov/
      annual-reports/
      individual-income/
      monthly-tax-reports/
    dbedt.hawaii.gov/
      economic/
    census.hawaii.gov/
      acs/
docs/
  HAIC2026_Know_Your_District_Challenge_Rules.pdf
scripts/
  crawl_sources.py          # Re-runnable crawler
  requirements.txt
```

Each source directory also contains `_pages/*.md` snapshots for crawled index
pages so that link lists and page tables are preserved even when the data is
shown directly on a page.

## What was collected

Counts below are unique downloaded data/report files, excluding `_pages`
markdown snapshots. The manifest may contain more rows than unique files when
the same file was linked from multiple source pages and de-duplicated by SHA-256.

| Source | Files | Size |
|---|---:|---:|
| Department of Taxation annual reports | 30 | 65,397,547 bytes |
| Department of Taxation individual income statistics | 27 | 78,439,959 bytes |
| Department of Taxation monthly tax reports | 188 | 19,169,297 bytes |
| DBEDT Research & Economic Analysis | 912 | 1,089,227,268 bytes |
| Hawaii State Data Center ACS | 50 | 14,167,530 bytes |
| **Total** | **1,207** | **1,266,401,601 bytes** |

Additional crawled index-page snapshots: 122 markdown files.

Downloaded file types:

| Type | Manifest rows |
|---|---:|
| PDF | 1,064 |
| XLSX | 642 |
| XLS | 59 |

## Manifest

`data/MANIFEST.csv` contains one row per downloaded source link:

- `local_path`
- `source_url`
- `source_page`
- `publisher`
- `title`
- `year/period`
- `file_type`
- `size_bytes`
- `sha256`
- `downloaded_at`

Identical files are stored once by SHA-256 hash. Repeated source links point to
the already saved local path in the manifest.

## Re-run the crawler

Use Python 3.12 or newer.

```bash
python3 -m pip install --user -r scripts/requirements.txt
python3 scripts/crawl_sources.py --clean
```

Crawler behavior:

- sends a normal identifying user agent;
- checks `robots.txt`;
- rate-limits requests to about one request per second per host;
- stays within the configured source sections for HTML crawling;
- downloads direct public data/report links, including direct file links on
  external hosts when they are linked from an in-scope page;
- stores page snapshots under `_pages/`;
- writes `data/MANIFEST.csv` and `data/CRAWL_FAILURES.csv`.

## Gaps and failures

Full details are in `data/CRAWL_FAILURES.csv`.

Summary:

| Reason | Count |
|---|---:|
| Skipped by DBEDT priority policy after a full DBEDT crawl exceeded the 2 GB guidance | 3,218 |
| HTTP 429 rate-limited file responses | 45 |
| HTTP 404 | 2 |
| `robots.txt` returned HTTP 404 | 1 |

The DBEDT site has enough linked files that a full depth-2 crawl exceeded the
requested size guidance before the ACS source could be collected. The committed
run therefore keeps recent and geography-relevant DBEDT files and records older
or lower-priority DBEDT links as skipped.

Observed 404 URLs:

- <https://dbedt.hawaii.gov/economic/unemployment/maui_weekly_unemployment_update>
- <https://dbedt.hawaii.gov/economic/2022-state-input-output-study/>

The HTTP 429 responses were direct files from `files.hawaii.gov` linked from
DBEDT tourism research pages, mostly Brand Health Index and traveler-profile PDF
links. They are listed individually in `data/CRAWL_FAILURES.csv`.

## Git LFS

No downloaded file exceeded 50 MB in this run, so no files needed Git LFS.
