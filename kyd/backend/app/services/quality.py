"""Data-quality flags applied to every observation before it leaves the API (§9.2, §6.4)."""
from datetime import date
from ..config import settings
from ..models import Observation

Z90 = 1.645  # ACS MOEs are published at 90% confidence


def cv_of(value: float | None, moe: float | None) -> float | None:
    if value in (None, 0) or moe is None:
        return None
    return round((moe / Z90) / abs(value), 4)


def apply_flags(o: Observation, release_date: str | None = None, demo: bool = False) -> Observation:
    s = settings()
    o.cv = o.cv if o.cv is not None else cv_of(o.value, o.moe)
    flags = set(o.flags)
    if o.cv is not None and o.cv > s.cv_suppress:
        flags.add("suppressed_cv")         # UI greys the figure; the agent must caveat it
    elif o.cv is not None and o.cv > 0.15:
        flags.add("high_moe")
    if o.method == "apportioned":
        flags.add("apportioned")
    if release_date:
        try:
            if (date.today() - date.fromisoformat(release_date)).days > s.stale_after_days:
                flags.add("stale")
        except ValueError:
            pass
    if demo:
        flags.add("demo")
    o.flags = sorted(flags)
    return o


def significantly_different(a: Observation, b: Observation) -> bool:
    """Census Bureau significance test at 90% confidence."""
    if None in (a.value, b.value, a.moe, b.moe):
        return False
    se = ((a.moe / Z90) ** 2 + (b.moe / Z90) ** 2) ** 0.5
    return se > 0 and abs(a.value - b.value) / se > Z90
