# Live workflow and cache timing evidence

Checked against localhost on September 7-8, 2026. These are API measurements, not browser timings.

- Live ADK execution: `google_adk_live`, 17.2919 seconds, change `change_923cea5cf4f8`.
- Approved build: `build_ae00c3afc37c`, 2.0679 seconds, release `release_003`, 12 cache hits,
  no generation calls, telemetry recorded. All 12 artifact hashes verified.
- ClickHouse MCP readback failed with `MCP_UNREACHABLE` (connection refused).
- Inspected package bytes in the Vertex namespace: `OFFLINE PACKAGE` text, with the clip input
  recorded as zero bytes. Hash verification proves byte integrity, not playable media or live generation.
- After restarting the API, the first cached scan took 34.2425 seconds; total workflow 36.3958 seconds.
- Warm repeat: build `build_6467e80175ef`, cached scan 0.3609 seconds, build 1.9392 seconds,
  verification 0.0173 seconds; total scan/estimate/approval/build/verification 2.4090 seconds.
  All 12 artifacts reused, zero provider calls, telemetry recorded, verification passed.

Verdict: warm cached API workflow passes. Complete live media workflow remains unverified and package
generation is blocked by missing video inputs/fallback packaging. The four-second frontend minimum was
not measured in a browser during this check. Warm the server before presenting.
