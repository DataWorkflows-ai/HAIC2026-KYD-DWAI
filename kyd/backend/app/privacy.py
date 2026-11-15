"""PII scrubbing before anything is persisted (§8.3). Uses Microsoft Presidio when
it is installed and falls back to regexes otherwise. Scrubbing is on by default."""
from __future__ import annotations
import re

_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<SSN>"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "<EMAIL>"),
    (re.compile(r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "<PHONE>"),
    (re.compile(r"\b\d{1,5}\s+\w+(\s\w+)?\s(St|Street|Ave|Avenue|Rd|Road|Pl|Place|Way|Dr|Drive|Hwy|Loop)\b", re.I), "<ADDRESS>"),
]

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _an, _anon = AnalyzerEngine(), AnonymizerEngine()
except Exception:  # Presidio is optional in dev
    _an = _anon = None


def scrub(text: str | None) -> str | None:
    if not text:
        return text
    if _an is not None:
        res = _an.analyze(text=text, language="en")
        return _anon.anonymize(text=text, analyzer_results=res).text
    for pat, tok in _PATTERNS:
        text = pat.sub(tok, text)
    return text
