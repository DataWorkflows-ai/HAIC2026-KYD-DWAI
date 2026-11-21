"""API contracts. Every number travels inside an Observation, which carries its citation."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

Method = Literal["direct", "apportioned", "derived", "modeled"]


class Source(BaseModel):
    source_id: str
    publisher: str
    title: str
    url: str | None = None
    release_date: str | None = None
    license: str | None = None


class Observation(BaseModel):
    obs_id: str
    geo_id: str
    indicator: str
    label: str
    unit: str
    value: float | None
    moe: float | None = None
    cv: float | None = None
    vintage: str
    method: Method = "direct"
    method_note: str | None = None
    source_id: str
    flags: list[str] = Field(default_factory=list)   # suppressed_cv, high_moe, stale, apportioned, demo


class Geography(BaseModel):
    geo_id: str
    geo_type: Literal["state", "county", "sldu", "sldl"]
    name: str
    counties: list[str] = Field(default_factory=list)


class Program(BaseModel):
    program_id: str
    name: str
    agency: str
    level: str
    summary: str
    official_url: str
    populations: list[str] = Field(default_factory=list)
    proxy_indicators: list[str] = Field(default_factory=list)


class RangeEnd(BaseModel):
    persons: Observation
    share: Observation | None = None     # of people below the program's income limit
    grade: Literal["A", "B", "C"]        # A administrative count at district/ZIP; B survey or modelled; C allocated down
    basis: str                           # e.g. "survey-based", "benchmark-based"
    method: str


class GapRange(BaseModel):
    """People who look eligible but are not enrolled, shown as a range rather than one figure (spec §5.2)."""
    low: RangeEnd
    high: RangeEnd
    benchmark: list[Observation] = Field(default_factory=list)   # official participation rates behind the benchmark end
    is_not: str                                                  # one line on what the range does not mean
    note: str | None = None                                      # e.g. when the two methods disagree in this district


class ProgramMatch(BaseModel):
    program: Program
    score: float
    eligible_proxy: Observation | None = None
    uptake_proxy: Observation | None = None
    gap_note: str | None = None
    gap_range: GapRange | None = None
    rationale: list[str] = Field(default_factory=list)


class DistrictProfile(BaseModel):
    geography: Geography
    observations: list[Observation]
    comparisons: dict[str, list[Observation]] = Field(default_factory=dict)  # county / state
    peers: list[str] = Field(default_factory=list)
    data_as_of: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    geo_id: str | None = None          # UI context (selected district)
    chat_id: str | None = Field(default=None, max_length=40)   # saved chat to add to, or "new"


class Document(BaseModel):
    title: str
    body: str                          # Markdown


class AgentAnswer(BaseModel):
    text: str
    route: Literal["S1", "S2", "REFUSED"]
    intent: str | None = None
    geo_ids: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    programs: list[ProgramMatch] = Field(default_factory=list)
    escalation_reasons: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)   # tool calls, for "show the math"
    document: Document | None = None                  # long-form output, shown in the document panel
    chat_id: str | None = None                        # the saved chat this answer was added to
