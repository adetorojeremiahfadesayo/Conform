"""Deploy CONFORM with private persistent artifacts and an authenticated MCP sidecar."""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from app.config import load_config
from app.store.artifacts import GCSArtifactStore, build_store


def main() -> None:
    config = load_config()
    project = config.google_cloud_project
    bucket = f"conform-{project}-artifacts"
    local = build_store(config)
    remote = GCSArtifactStore(replace(config, artifact_bucket=bucket), "vertex")
    count = 0
    for path in local._root.glob("*/*"):
        if not path.is_file() or len(path.name) != 64:
            continue
        data = path.read_bytes()
        if data.startswith((b"OFFLINE", b"STUB")):
            continue
        content_type = "video/mp4" if data[4:8] == b"ftyp" else "application/json"
        remote.put(path.name, data, content_type)
        count += 1
    print(f"Uploaded {count} usable cache objects to private GCS", flush=True)
    env = {
        "GOOGLE_CLOUD_PROJECT": project, "GOOGLE_CLOUD_REGION": config.google_cloud_region,
        "VERTEX_TEXT_MODEL": config.vertex_text_model,
        "VERTEX_REASONING_MODEL": config.vertex_reasoning_model,
        "VERTEX_VIDEO_MODEL": "veo-3.1-fast-generate-001",
        "VERTEX_IMAGE_MODEL": config.vertex_image_model,
        "CLICKHOUSE_HOST": config.clickhouse_host, "CLICKHOUSE_PORT": str(config.clickhouse_port),
        "CLICKHOUSE_USER": "conform_judge",
        "CLICKHOUSE_DATABASE": config.clickhouse_database, "ARTIFACT_BUCKET": bucket,
        "BUILD_BUDGET_USD": config.build_budget_usd, "JUDGE_MODE": "true",
        "CLICKHOUSE_MCP_QUERY_TIMEOUT": "60",
    }
    with tempfile.TemporaryDirectory(prefix="conform-deploy-") as tmp:
        values = Path(tmp) / "runtime.json"
        values.write_text(json.dumps(env), encoding="utf-8")
        gcloud = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        subprocess.run([gcloud, "run", "deploy", "conform", "--source", ".", "--project", project,
                        "--region", config.google_cloud_region, "--allow-unauthenticated",
                        "--service-account", f"conform-judge@{project}.iam.gserviceaccount.com",
                        "--update-secrets", "CLICKHOUSE_PASSWORD=conform-clickhouse-judge-password:latest",
                        "--env-vars-file", str(values), "--memory", "2Gi", "--cpu", "2",
                        "--min-instances", "1", "--max-instances", "1", "--concurrency", "1",
                        "--timeout", "300", "--quiet"], check=True)


if __name__ == "__main__":
    main()
