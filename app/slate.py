"""Seed slate generator — deterministic fixture construction.

Builds the demo slate: 3 campaigns, each with a shared master chain
(source -> shot_plan -> keyframe -> clip) and a 40-territory fan-out of
localisable leaves (copy_{territory} -> package_{territory}, which also
consumes the shared clip). Territory variants share upstream nodes, which is
exactly what makes reuse dramatic when a scoped rule change lands.

Fully deterministic: same call => same specs => same fingerprints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.schemas import (
    CampaignSpec,
    ErrorClass,
    NodeKind,
    NodeRunRecord,
    NodeSpec,
    ProviderCallRecord,
    TerritoryVariant,
)

TERRITORIES: list[tuple[str, str]] = [
    ("us", "en-US"), ("ca", "en-CA"), ("mx", "es-MX"), ("br", "pt-BR"),
    ("gb", "en-GB"), ("ie", "en-IE"), ("de", "de-DE"), ("fr", "fr-FR"),
    ("es", "es-ES"), ("it", "it-IT"), ("nl", "nl-NL"), ("be", "nl-BE"),
    ("se", "sv-SE"), ("no", "nb-NO"), ("dk", "da-DK"), ("fi", "fi-FI"),
    ("pl", "pl-PL"), ("at", "de-AT"), ("ch", "de-CH"), ("pt", "pt-PT"),
    ("gr", "el-GR"), ("cz", "cs-CZ"), ("hu", "hu-HU"), ("ro", "ro-RO"),
    ("jp", "ja-JP"), ("kr", "ko-KR"), ("cn", "zh-CN"), ("tw", "zh-TW"),
    ("hk", "zh-HK"), ("sg", "en-SG"), ("in", "en-IN"), ("au", "en-AU"),
    ("nz", "en-NZ"), ("za", "en-ZA"), ("ae", "ar-AE"), ("sa", "ar-SA"),
    ("il", "he-IL"), ("tr", "tr-TR"), ("eg", "ar-EG"), ("ng", "en-NG"),
]

EU_TERRITORIES = ["de", "fr", "es", "it", "nl", "be", "se", "pl", "at", "pt", "gr", "cz", "hu", "ro", "ie", "dk", "fi"]

CAMPAIGNS: list[tuple[str, str]] = [
    ("campaign_a", "Aurora Sneaker Launch"),
    ("campaign_b", "Northwind Travel Winter"),
    ("campaign_c", "Lumen Bank Rebrand"),
]


def build_seed_specs() -> list[NodeSpec]:
    specs: list[NodeSpec] = []
    for campaign_id, name in CAMPAIGNS:
        specs += [
            NodeSpec(
                node_id=f"{campaign_id}.source",
                campaign_id=campaign_id,
                kind=NodeKind.SOURCE,
                inputs={"prompt": f"Campaign brief: {name}. 15-second product spot."},
                recipe={"model": "reasoning", "seed": 7},
            ),
            NodeSpec(
                node_id=f"{campaign_id}.shot_plan",
                campaign_id=campaign_id,
                kind=NodeKind.SHOT_PLAN,
                inputs={"prompt": f"Shot plan for {name}: 3 shots, product hero, lifestyle close."},
                recipe={"model": "reasoning", "seed": 7},
                parents=[f"{campaign_id}.source"],
            ),
            NodeSpec(
                node_id=f"{campaign_id}.keyframe",
                campaign_id=campaign_id,
                kind=NodeKind.KEYFRAME,
                inputs={"prompt": f"Key visual for {name}."},
                recipe={"model": "image", "seed": 11},
                parents=[f"{campaign_id}.shot_plan"],
            ),
            NodeSpec(
                node_id=f"{campaign_id}.clip",
                campaign_id=campaign_id,
                kind=NodeKind.CLIP,
                inputs={"prompt": f"6-second master clip for {name}."},
                recipe={"model": "video", "duration_seconds": 6.0, "seed": 13},
                parents=[f"{campaign_id}.keyframe"],
            ),
        ]
        for territory, locale in TERRITORIES:
            specs += [
                NodeSpec(
                    node_id=f"{campaign_id}.copy.{territory}",
                    campaign_id=campaign_id,
                    territory=territory,
                    kind=NodeKind.COPY,
                    inputs={
                        "prompt": f"Localise end-card copy for {name} in {locale}.",
                        "disclaimer": "",
                    },
                    recipe={"model": "text", "locale": locale, "seed": 17},
                    parents=[f"{campaign_id}.shot_plan"],
                ),
                NodeSpec(
                    node_id=f"{campaign_id}.package.{territory}",
                    campaign_id=campaign_id,
                    territory=territory,
                    kind=NodeKind.PACKAGE,
                    inputs={"format": "9x16", "runtime_seconds": 15},
                    recipe={"encoder": "ffmpeg", "seed": 19},
                    parents=[f"{campaign_id}.clip", f"{campaign_id}.copy.{territory}"],
                ),
            ]
    return specs


def build_seed_campaigns() -> list[CampaignSpec]:
    return [
        CampaignSpec(
            campaign_id=cid,
            name=name,
            brief=f"{name}: flagship 15-second spot, 40 territory variants.",
            territories=[TerritoryVariant(territory=t, locale=loc) for t, loc in TERRITORIES],
            interpretation_mode="fallback_deterministic",
        )
        for cid, name in CAMPAIGNS
    ]


def seed_historical_builds() -> tuple[list[NodeRunRecord], list[ProviderCallRecord]]:
    """Generate realistic synthetic history (FR-8.7).
    Labeled as seeded (is_seeded=True) so analytics are populated on first launch.
    """
    now = datetime.now(timezone.utc)
    runs: list[NodeRunRecord] = []
    calls: list[ProviderCallRecord] = []

    # Build 1: Master campaign builds (yesterday)
    t1 = now - timedelta(days=1)
    b1 = "build_seed_001"

    # Campaign A master chain + first 5 territories
    kinds_costs = [
        ("source", NodeKind.SOURCE, Decimal("0.001"), "gemini-3-pro", "text"),
        ("shot_plan", NodeKind.SHOT_PLAN, Decimal("0.002"), "gemini-3-pro", "text"),
        ("keyframe", NodeKind.KEYFRAME, Decimal("0.04"), "imagen-4", "image"),
        ("clip", NodeKind.CLIP, Decimal("0.35"), "veo-3.1-fast", "video"),
    ]

    for suffix, kind, cost, model, modality in kinds_costs:
        run_id = f"seed_run_{b1}_{suffix}"
        node_id = f"campaign_a.{suffix}"
        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory="master",
                build_id=b1,
                run_id=run_id,
                node_id=node_id,
                node_kind=kind,
                fingerprint="a" * 64,
                status="ok",
                cache_hit=False,
                attempt=1,
                error_class=ErrorClass.NONE,
                is_seeded=True,
                started_at=t1,
                ended_at=t1 + timedelta(seconds=4),
                duration_ms=4000,
                cost_usd=cost,
            )
        )
        calls.append(
            ProviderCallRecord(
                run_id=run_id,
                build_id=b1,
                model=model,
                modality=modality,
                cost_usd=cost,
                media_seconds=6.0 if modality == "video" else 0.0,
                latency_ms=3500,
                is_seeded=True,
                called_at=t1,
            )
        )

    # Injected transient timeout attempt on clip for demo lineage
    parent_fail_id = f"seed_run_{b1}_clip_fail"
    runs.append(
        NodeRunRecord(
            tenant="demo",
            campaign_id="campaign_a",
            territory="master",
            build_id=b1,
            run_id=parent_fail_id,
            node_id="campaign_a.clip",
            node_kind=NodeKind.CLIP,
            fingerprint="a" * 64,
            status="failed",
            cache_hit=False,
            attempt=1,
            error_class=ErrorClass.TRANSIENT,
            is_seeded=True,
            started_at=t1 - timedelta(seconds=10),
            ended_at=t1 - timedelta(seconds=8),
            duration_ms=2000,
            cost_usd=Decimal("0"),
        )
    )

    # 40 territory variants for Campaign A in Build 1
    for terr, _ in TERRITORIES:
        run_copy = f"seed_run_{b1}_copy_{terr}"
        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory=terr,
                build_id=b1,
                run_id=run_copy,
                node_id=f"campaign_a.copy.{terr}",
                node_kind=NodeKind.COPY,
                fingerprint="b" * 64,
                status="ok",
                cache_hit=False,
                attempt=1,
                is_seeded=True,
                started_at=t1,
                cost_usd=Decimal("0.0005"),
            )
        )
        calls.append(
            ProviderCallRecord(
                run_id=run_copy,
                build_id=b1,
                model="gemini-3.1-flash",
                modality="text",
                cost_usd=Decimal("0.0005"),
                is_seeded=True,
                called_at=t1,
            )
        )

        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory=terr,
                build_id=b1,
                run_id=f"seed_run_{b1}_pkg_{terr}",
                node_id=f"campaign_a.package.{terr}",
                node_kind=NodeKind.PACKAGE,
                fingerprint="c" * 64,
                status="ok",
                cache_hit=False,
                attempt=1,
                is_seeded=True,
                started_at=t1,
                cost_usd=Decimal("0"),
            )
        )

    # Build 2: Incremental rebuild of EU territories (6 hours ago)
    t2 = now - timedelta(hours=6)
    b2 = "build_seed_002"

    for terr in ["de", "fr", "es", "it"]:
        run_copy_b2 = f"seed_run_{b2}_copy_{terr}"
        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory=terr,
                build_id=b2,
                run_id=run_copy_b2,
                node_id=f"campaign_a.copy.{terr}",
                node_kind=NodeKind.COPY,
                fingerprint="d" * 64,
                status="ok",
                cache_hit=False,  # Rebuilt
                attempt=1,
                is_seeded=True,
                started_at=t2,
                cost_usd=Decimal("0.0005"),
            )
        )
        calls.append(
            ProviderCallRecord(
                run_id=run_copy_b2,
                build_id=b2,
                model="gemini-3.1-flash",
                modality="text",
                cost_usd=Decimal("0.0005"),
                is_seeded=True,
                called_at=t2,
            )
        )
        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory=terr,
                build_id=b2,
                run_id=f"seed_run_{b2}_pkg_{terr}",
                node_id=f"campaign_a.package.{terr}",
                node_kind=NodeKind.PACKAGE,
                fingerprint="e" * 64,
                status="ok",
                cache_hit=False,
                attempt=1,
                is_seeded=True,
                started_at=t2,
                cost_usd=Decimal("0"),
            )
        )

    # Clean nodes in Build 2 reused from cache (demonstrating avoided spend)
    for terr in ["us", "ca", "gb", "jp"]:
        runs.append(
            NodeRunRecord(
                tenant="demo",
                campaign_id="campaign_a",
                territory=terr,
                build_id=b2,
                run_id=f"seed_run_{b2}_reused_{terr}",
                node_id=f"campaign_a.package.{terr}",
                node_kind=NodeKind.PACKAGE,
                fingerprint="c" * 64,
                status="ok",
                cache_hit=True,  # Cache hit!
                attempt=1,
                is_seeded=True,
                started_at=t2,
                cost_usd=Decimal("0.35"),  # Avoided clip cost
            )
        )

    return runs, calls
