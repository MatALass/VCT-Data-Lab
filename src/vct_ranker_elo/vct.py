from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VctEvent:
    event_id: int
    region: str
    name: str
    stage: str
    url_slug: str

    @property
    def stats_url(self) -> str:
        return f"https://www.vlr.gg/event/stats/{self.event_id}/{self.url_slug}"


# Périmètre strict demandé : VCT 2026 Stage 1 uniquement.
# Les pages overview /event/<id>/... sont volontairement converties en /event/stats/<id>/...
# car c'est la table de stats joueurs qui contient les métriques exploitables.
VCT_2026_STAGE_1_EVENTS: tuple[VctEvent, ...] = (
    VctEvent(2860, "Americas", "VCT 2026 Americas Stage 1", "Stage 1", "vct-2026-americas-stage-1"),
    VctEvent(2863, "EMEA", "VCT 2026 EMEA Stage 1", "Stage 1", "vct-2026-emea-stage-1"),
    VctEvent(2775, "Pacific", "VCT 2026 Pacific Stage 1", "Stage 1", "vct-2026-pacific-stage-1"),
    VctEvent(2864, "China", "VCT 2026 China Stage 1", "Stage 1", "vct-2026-china-stage-1"),
)

VCT_REGIONS = ["All", "Americas", "EMEA", "Pacific", "China"]


def events_for_region(region: str) -> list[VctEvent]:
    if region == "All":
        return list(VCT_2026_STAGE_1_EVENTS)
    return [event for event in VCT_2026_STAGE_1_EVENTS if event.region == region]
