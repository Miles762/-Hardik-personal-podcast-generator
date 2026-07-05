"""API schemas for the internal analytics dashboard (PRD 10, 11.6).

Revision (user-requested): the seeded concept is removed. Every metric shown is a
real captured value, so there is no ``source`` field and no seeded trend series.
"""

from __future__ import annotations

from pydantic import BaseModel


class Tile(BaseModel):
    label: str
    value: float
    unit: str = ""


class NameValue(BaseModel):
    name: str
    value: float


class DashboardResponse(BaseModel):
    product: list[Tile]
    user: list[Tile]
    operational: list[Tile]
    top_interests: list[NameValue]
    voice_distribution: list[NameValue]
