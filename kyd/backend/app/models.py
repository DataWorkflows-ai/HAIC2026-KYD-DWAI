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


class ProgramMatch(BaseModel):
    program: Program
    score: float
    eligible_proxy: Observation | None = None
    uptake_proxy: Observation | None = None
    gap_note: str | None = None
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


class AgentAnswer(BaseModel):
    text: str
    route: Literal["S1", "S2", "REFUSED"]
    intent: str | None = None
    geo_ids: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    programs: list[ProgramMatch] = Field(default_factory=list)
    escalation_reasons: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)   # tool calls, for "show the math"
