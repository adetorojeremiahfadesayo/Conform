"""Deploy the authenticated CONFORM studio; never expose its control API publicly."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from app.config import load_config


def main() -> None:
    config = load_config()
    project = config.google_cloud_project
    bucket = f"conform-{project}-artifacts"
    environment = {
        "GOOGLE_CLOUD_PROJECT": project,
        "GOOGLE_CLOUD_REGION": config.google_cloud_region,
        "VERTEX_TEXT_MODEL": config.vertex_text_model,
        "VERTEX_REASONING_MODEL": config.vertex_reasoning_model,
        "VERTEX_VIDEO_MODEL": "veo-3.1-fast-generate-001",
        "VERTEX_IMAGE_MODEL": config.vertex_image_model,
        "CLICKHOUSE_HOST": config.clickhouse_host,
        "CLICKHOUSE_PORT": str(config.clickhouse_port),
        "CLICKHOUSE_USER": config.clickhouse_user,
        "CLICKHOUSE_PASSWORD": config.clickhouse_password,
        "CLICKHOUSE_DATABASE": config.clickhouse_database,
        "ARTIFACT_BUCKET": bucket,
        "BUILD_BUDGET_USD": config.build_budget_usd,
        "JUDGE_MODE": "false",
    }
    with tempfile.TemporaryDirectory(prefix="conform-studio-") as tmp:
        values = Path(tmp) / "runtime.json"
        values.write_text(json.dumps(environment), encoding="utf-8")
        gcloud = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
        subprocess.run(
            [
                gcloud,
                "run",
                "deploy",
                "conform-studio",
                "--source",
                ".",
                "--project",
                project,
                "--region",
                config.google_cloud_region,
                "--no-allow-unauthenticated",
                "--service-account",
                f"conform-run@{project}.iam.gserviceaccount.com",
                "--env-vars-file",
                str(values),
                "--memory",
                "2Gi",
                "--cpu",
                "2",
                "--min-instances",
                "0",
                "--max-instances",
                "1",
                "--concurrency",
                "1",
                "--timeout",
                "300",
                "--quiet",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
