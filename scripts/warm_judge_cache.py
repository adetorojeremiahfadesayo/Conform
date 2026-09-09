"""Explicitly approved preparation of real Google media for the judge preset.

Run only with --approve-spend. Keeps existing immutable cache entries and
records provider evidence. This is operational setup, outside the core.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from app.agents.coordinator import Coordinator
from app.config import load_config
from app.core.builder import run_build
from app.core.fingerprint import hash_graph
from app.domain.schemas import Approval
from app.providers.vertex import VertexVideoProvider


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approve-spend", action="store_true")
    args = parser.parse_args()
    if not args.approve_spend:
        parser.error("--approve-spend is required; up to three six-second silent Veo clips")
    config = load_config()
    coord = Coordinator(config)
    # Explicit six-second, single-output calls. Use Google's documented Veo endpoint.
    video_config = replace(config, vertex_video_model="veo-3.1-fast-generate-001",
                           google_cloud_region="us-central1")
    coord.providers["clip"] = VertexVideoProvider(video_config)
    approval = Approval(change_id="change_judge_media_warmup", actor="producer (simulated)",
                        graph_hash=hash_graph(list(coord.graph.nodes.values())))
    nodes = [nid for nid in coord.graph.nodes if nid.endswith(".clip")]
    result = run_build(graph=coord.graph, dirty_node_ids=nodes, approval=approval,
                       providers=coord.providers, store=coord.store, existing_releases=[])
    coord.writer.write_runs(result.runs)
    coord.writer.write_provider_calls(result.provider_calls)
    if result.release:
        coord.writer.write_artifacts(result.release.artifacts)
    Path("output").mkdir(exist_ok=True)
    Path("output/judge_media_warmup.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({"rebuilt": result.nodes_rebuilt, "reused": result.nodes_reused,
                      "artifacts": len(result.release.artifacts) if result.release else 0}))


if __name__ == "__main__":
    main()
