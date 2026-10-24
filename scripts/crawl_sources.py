#!/usr/bin/env python3
"""Collect public source data for the HAIC 2026 Know Your District challenge.

The crawler is deliberately conservative:
* source pages are configured explicitly below;
* only direct data/report file links are downloaded;
* HTML crawling is limited to the same requested site sections;
* every request is checked against robots.txt and rate-limited per host.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (compatible; HAIC2026KYDDataCrawler/1.0; "
    "+https://github.com/DataWorkflows-ai/HAIC2026-KYD-DWAI)"
)
REQUEST_TIMEOUT = 45
REQUEST_INTERVAL_SECONDS = 1.0
LFS_THRESHOLD_BYTES = 50 * 1024 * 1024
TOTAL_DOWNLOAD_BUDGET_BYTES = 2 * 1024 * 1024 * 1024

FILE_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".geojson",
    ".gis",
    ".gz",
    ".json",
    ".kmz",
    ".pdf",
    ".shp",
    ".txt",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".xml",
    ".zip",
}

PAGE_SKIP_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".png",
    ".svg",
    ".webp",
}


@dataclass(frozen=True)
class SourceConfig:
    name: str
    start_url: str
    publisher: str
    output_subdir: str
    crawl_prefixes: tuple[str, ...]
    max_depth: int


SOURCES = (
    SourceConfig(
        name="tax_annual_reports",
        start_url="https://tax.hawaii.gov/stats/a5_1annual/",
        publisher="Hawaii Department of Taxation",
        output_subdir="tax.hawaii.gov/annual-reports",
        crawl_prefixes=("https://tax.hawaii.gov/stats/a5_1annual/",),
        max_depth=2,
    ),
    SourceConfig(
        name="tax_individual_income",
        start_url="https://tax.hawaii.gov/stats/a5_1annual/a5_5ind_inc/",
        publisher="Hawaii Department of Taxation",
        output_subdir="tax.hawaii.gov/individual-income",
        crawl_prefixes=("https://tax.hawaii.gov/stats/a5_1annual/a5_5ind_inc/",),
        max_depth=2,
    ),
    SourceConfig(
        name="tax_monthly_tax_reports",
        start_url="https://tax.hawaii.gov/stats/a5_3txcolrpt/",
        publisher="Hawaii Department of Taxation",
        output_subdir="tax.hawaii.gov/monthly-tax-reports",
        crawl_prefixes=("https://tax.hawaii.gov/stats/a5_3txcolrpt/",),
        max_depth=2,
    ),
    SourceConfig(
        name="dbedt_economic",
        start_url="https://dbedt.hawaii.gov/economic/",
        publisher="Hawaii DBEDT Research & Economic Analysis Division",
        output_subdir="dbedt.hawaii.gov/economic",
        crawl_prefixes=("https://dbedt.hawaii.gov/economic/",),
        max_depth=2,
    ),
    SourceConfig(
        name="census_hawaii_acs",
        start_url="https://census.hawaii.gov/acs/",
        publisher="Hawaii State Data Center",
        output_subdir="census.hawaii.gov/acs",
        crawl_prefixes=("https://census.hawaii.gov/acs/",),
        max_depth=2,
    ),
)


class PoliteSession:
    def __init__(self, user_agent: str, interval_seconds: float) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.user_agent = user_agent
        self.interval_seconds = interval_seconds
        self.last_request_by_host: dict[str, float] = {}
        self.robots_by_host: dict[str, RobotFileParser | None] = {}
        self.robot_errors: dict[str, str] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"
        if host_key not in self.robots_by_host:
            robots_url = urljoin(host_key, "/robots.txt")
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                self._wait(parsed.netloc)
                response = self.session.get(robots_url, timeout=REQUEST_TIMEOUT)
                if response.status_code >= 400:
                    parser = None
                    self.robot_errors[host_key] = f"robots.txt returned HTTP {response.status_code}"
                else:
                    parser.parse(response.text.splitlines())
            except requests.RequestException as exc:
                parser = None
                self.robot_errors[host_key] = f"robots.txt unavailable: {exc}"
            self.robots_by_host[host_key] = parser

        parser = self.robots_by_host[host_key]
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def get(self, url: str, *, stream: bool = False) -> requests.Response:
        parsed = urlparse(url)
        self._wait(parsed.netloc)
        return self.session.get(url, timeout=REQUEST_TIMEOUT, stream=stream)

    def _wait(self, host: str) -> None:
        now = time.monotonic()
        last_request = self.last_request_by_host.get(host)
        if last_request is not None:
            elapsed = now - last_request
            if elapsed < self.interval_seconds:
                time.sleep(self.interval_seconds - elapsed)
        self.last_request_by_host[host] = time.monotonic()


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path)
    if path != "/" and path.endswith("/index.html"):
        path = path[: -len("index.html")]
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, fragment="").geturl()


def file_extension(url: str) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    suffix = Path(path).suffix
    if suffix in FILE_EXTENSIONS:
        return suffix
    query = parse_qs(parsed.query)
    for key in ("file", "filename", "download"):
        for value in query.get(key, []):
            suffix = Path(value.lower()).suffix
            if suffix in FILE_EXTENSIONS:
                return suffix
    return suffix


def is_file_url(url: str) -> bool:
    return file_extension(url) in FILE_EXTENSIONS


def is_probable_html_page(url: str) -> bool:
    suffix = Path(unquote(urlparse(url).path).lower()).suffix
    return suffix not in FILE_EXTENSIONS and suffix not in PAGE_SKIP_EXTENSIONS


def is_in_prefix(url: str, prefixes: Iterable[str]) -> bool:
    normalized = normalize_url(url)
    return any(normalized.startswith(prefix) for prefix in prefixes)


def safe_page_name(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    if path.endswith("/"):
        path = path[:-1]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", path)
    if parsed.query:
        query_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.query)
        slug = f"{slug}_{query_slug}"
    return f"{slug or 'index'}.md"


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if name:
        return sanitize_filename(name)

    query = parse_qs(parsed.query)
    for key in ("file", "filename", "download"):
        for value in query.get(key, []):
            name = Path(value).name
            if name:
                return sanitize_filename(name)

    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    ext = file_extension(url)
    return f"download-{digest}{ext if ext in FILE_EXTENSIONS else ''}"


def sanitize_filename(name: str) -> str:
    name = name.replace("\\", "_").replace("/", "_").strip()
    name = re.sub(r"\s+", " ", name)
    return name or "download"


def output_dir_for(source: SourceConfig, page_url: str, raw_dir: Path) -> Path:
    base = raw_dir / source.output_subdir
    if source.name != "dbedt_economic":
        return base

    parsed = urlparse(page_url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) >= 2 and parts[0] == "economic":
        return base / parts[1]
    return base / "index"


def title_for_page(soup: BeautifulSoup, url: str) -> str:
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())
    heading = soup.find(["h1", "h2"])
    if heading:
        return " ".join(heading.get_text(" ", strip=True).split())
    return url


def html_to_markdown(soup: BeautifulSoup, page_url: str) -> str:
    for unwanted in soup(["script", "style", "noscript", "svg"]):
        unwanted.decompose()

    title = title_for_page(soup, page_url)
    lines: list[str] = [f"# {title}", "", f"Source: {page_url}", ""]

    main = soup.find("main") or soup.find(id="content") or soup.find(class_="entry-content") or soup.body or soup
    for element in main.find_all(["h1", "h2", "h3", "p", "li", "th", "td", "a"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if not text:
            continue
        if element.name in {"h1", "h2", "h3"}:
            level = {"h1": "#", "h2": "##", "h3": "###"}[element.name]
            lines.extend(["", f"{level} {text}", ""])
        elif element.name == "li":
            lines.append(f"- {text}")
        elif element.name == "a":
            href = element.get("href")
            if href:
                lines.append(f"- [{text}]({urljoin(page_url, href)})")
        else:
            lines.append(text)

    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        key = line.strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(line)
    return "\n".join(deduped).strip() + "\n"


def extract_links(soup: BeautifulSoup, page_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = normalize_url(urljoin(page_url, html.unescape(href)))
        text = " ".join(anchor.get_text(" ", strip=True).split())
        links.append((absolute, text))
    return links


def infer_period(title: str, url: str) -> str:
    text = f"{title} {unquote(url)}"
    patterns = [
        r"\bFY\s?20\d{2}\b",
        r"\b20\d{2}\s?[-/]\s?20\d{2}\b",
        r"\b(19|20)\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+20\d{2}\b",
        r"\b20\d{2}\s+Q[1-4]\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.group(0) for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return "; ".join(dict.fromkeys(matches))


def should_prioritize(url: str, title: str) -> bool:
    text = f"{title} {unquote(url)}".lower()
    priority_terms = (
        "legislative",
        "district",
        "tract",
        "zip",
        "zcta",
        "county",
        "acs",
        "census",
        "income",
        "poverty",
        "housing",
    )
    if any(term in text for term in priority_terms):
        return True
    year_matches = [int(match.group(0)) for match in re.finditer(r"\b20\d{2}\b", text)]
    return bool(year_matches and max(year_matches) >= datetime.now(timezone.utc).year - 10)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def choose_destination(directory: Path, filename: str, digest: str, existing_hashes: dict[str, Path]) -> tuple[Path, bool]:
    if digest in existing_hashes:
        return existing_hashes[digest], True

    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    if not destination.exists():
        return destination, False

    current_hash = sha256_file(destination)
    if current_hash == digest:
        existing_hashes[digest] = destination
        return destination, True

    stem = destination.stem
    suffix = destination.suffix
    destination = directory / f"{stem}__{digest[:8]}{suffix}"
    return destination, False


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_file(
    *,
    session: PoliteSession,
    source: SourceConfig,
    file_url: str,
    page_url: str,
    title: str,
    raw_dir: Path,
    manifest_rows: list[dict[str, str]],
    failures: list[dict[str, str]],
    existing_hashes: dict[str, Path],
    downloaded_at: str,
    total_downloaded: list[int],
) -> None:
    if not should_prioritize(file_url, title) and total_downloaded[0] >= TOTAL_DOWNLOAD_BUDGET_BYTES:
        failures.append(
            {
                "url": file_url,
                "source_page": page_url,
                "reason": "Skipped because the 2 GB download budget was reached and the link was not priority data",
            }
        )
        return

    if not session.can_fetch(file_url):
        failures.append({"url": file_url, "source_page": page_url, "reason": "Disallowed by robots.txt"})
        return

    try:
        response = session.get(file_url, stream=True)
        if response.status_code >= 400:
            failures.append(
                {
                    "url": file_url,
                    "source_page": page_url,
                    "reason": f"HTTP {response.status_code}",
                }
            )
            response.close()
            return

        tmp_dir = raw_dir / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / hashlib.sha256(file_url.encode("utf-8")).hexdigest()
        hasher = hashlib.sha256()
        size = 0
        with tmp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                hasher.update(chunk)
                handle.write(chunk)
        response.close()
    except requests.RequestException as exc:
        failures.append({"url": file_url, "source_page": page_url, "reason": f"Request failed: {exc}"})
        return

    digest = hasher.hexdigest()
    destination, duplicate = choose_destination(
        output_dir_for(source, page_url, raw_dir),
        filename_from_url(file_url),
        digest,
        existing_hashes,
    )
    if duplicate:
        tmp_path.unlink(missing_ok=True)
    else:
        shutil.move(str(tmp_path), destination)
        existing_hashes[digest] = destination
        total_downloaded[0] += size

    manifest_rows.append(
        {
            "local_path": destination.as_posix(),
            "source_url": file_url,
            "source_page": page_url,
            "publisher": source.publisher,
            "title": title,
            "year/period": infer_period(title, file_url),
            "file_type": file_extension(file_url).lstrip("."),
            "size_bytes": str(size),
            "sha256": digest,
            "downloaded_at": downloaded_at,
        }
    )


def crawl_source(
    *,
    source: SourceConfig,
    session: PoliteSession,
    raw_dir: Path,
    manifest_rows: list[dict[str, str]],
    failures: list[dict[str, str]],
    existing_hashes: dict[str, Path],
    downloaded_at: str,
    total_downloaded: list[int],
) -> None:
    queue: list[tuple[str, int]] = [(normalize_url(source.start_url), 0)]
    seen_pages: set[str] = set()
    queued_pages: set[str] = {normalize_url(source.start_url)}

    while queue:
        page_url, depth = queue.pop(0)
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)

        if not session.can_fetch(page_url):
            failures.append({"url": page_url, "source_page": page_url, "reason": "Disallowed by robots.txt"})
            continue

        try:
            response = session.get(page_url)
        except requests.RequestException as exc:
            failures.append({"url": page_url, "source_page": page_url, "reason": f"Request failed: {exc}"})
            continue

        if response.status_code >= 400:
            failures.append({"url": page_url, "source_page": page_url, "reason": f"HTTP {response.status_code}"})
            continue

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            if is_file_url(page_url):
                download_file(
                    session=session,
                    source=source,
                    file_url=page_url,
                    page_url=page_url,
                    title=page_url,
                    raw_dir=raw_dir,
                    manifest_rows=manifest_rows,
                    failures=failures,
                    existing_hashes=existing_hashes,
                    downloaded_at=downloaded_at,
                    total_downloaded=total_downloaded,
                )
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        page_dir = raw_dir / source.output_subdir / "_pages"
        write_text(page_dir / safe_page_name(page_url), html_to_markdown(soup, page_url))

        for link_url, link_title in extract_links(soup, page_url):
            title = link_title or filename_from_url(link_url)
            if is_file_url(link_url):
                download_file(
                    session=session,
                    source=source,
                    file_url=link_url,
                    page_url=page_url,
                    title=title,
                    raw_dir=raw_dir,
                    manifest_rows=manifest_rows,
                    failures=failures,
                    existing_hashes=existing_hashes,
                    downloaded_at=downloaded_at,
                    total_downloaded=total_downloaded,
                )
                continue

            if depth >= source.max_depth:
                continue
            if not is_probable_html_page(link_url):
                continue
            if not is_in_prefix(link_url, source.crawl_prefixes):
                continue
            if link_url in queued_pages:
                continue
            queued_pages.add(link_url)
            queue.append((link_url, depth + 1))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "local_path",
        "source_url",
        "source_page",
        "publisher",
        "title",
        "year/period",
        "file_type",
        "size_bytes",
        "sha256",
        "downloaded_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_failures(path: Path, failures: list[dict[str, str]], robot_errors: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["url", "source_page", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for failure in failures:
            writer.writerow(failure)
        for host, reason in robot_errors.items():
            writer.writerow({"url": f"{host}/robots.txt", "source_page": "", "reason": reason})


def write_lfs_attributes(path: Path, manifest_rows: list[dict[str, str]]) -> None:
    large_paths = [
        row["local_path"]
        for row in manifest_rows
        if row["size_bytes"].isdigit() and int(row["size_bytes"]) > LFS_THRESHOLD_BYTES
    ]
    if not large_paths:
        return

    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    for local_path in sorted(set(large_paths)):
        pattern = f"/{local_path} filter=lfs diff=lfs merge=lfs -text"
        if pattern not in lines:
            lines.append(pattern)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def clean_previous_outputs(raw_dir: Path, manifest_path: Path, failures_path: Path) -> None:
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    manifest_path.unlink(missing_ok=True)
    failures_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--clean", action="store_true", help="Delete existing data/raw and manifests before crawling")
    args = parser.parse_args()

    repo_root = args.repo_root
    raw_dir = repo_root / "data" / "raw"
    manifest_path = repo_root / "data" / "MANIFEST.csv"
    failures_path = repo_root / "data" / "CRAWL_FAILURES.csv"

    if args.clean:
        clean_previous_outputs(raw_dir, manifest_path, failures_path)

    session = PoliteSession(USER_AGENT, REQUEST_INTERVAL_SECONDS)
    manifest_rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    existing_hashes: dict[str, Path] = {}
    downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total_downloaded = [0]

    for source in SOURCES:
        print(f"Crawling {source.start_url}", flush=True)
        crawl_source(
            source=source,
            session=session,
            raw_dir=raw_dir,
            manifest_rows=manifest_rows,
            failures=failures,
            existing_hashes=existing_hashes,
            downloaded_at=downloaded_at,
            total_downloaded=total_downloaded,
        )

    write_manifest(manifest_path, manifest_rows)
    write_failures(failures_path, failures, session.robot_errors)
    write_lfs_attributes(repo_root / ".gitattributes", manifest_rows)

    tmp_dir = raw_dir / ".tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    print(f"Wrote {len(manifest_rows)} manifest rows to {manifest_path}")
    print(f"Wrote {len(failures) + len(session.robot_errors)} failure/skip rows to {failures_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
