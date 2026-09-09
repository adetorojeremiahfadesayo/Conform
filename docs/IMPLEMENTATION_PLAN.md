# CONFORM Submission Remediation — Implementation Plan

**Prepared:** September 5, 2026  
**Deadline:** September 9, 2026 at 2:00 PM PDT / 10:00 PM WAT  
**Target:** Agentic Cinema — ClickHouse Partner Track

## 1. Purpose

This plan addresses four blocking findings from the submission-readiness audit:

1. Establish clean, permitted implementation provenance.
2. Remove silent frontend simulation and fabricated-success behaviour.
3. Make the headline preset complete a real backend-driven workflow.
4. Put the Google ADK agent in the judge-facing workflow without bypassing human approval.

The goal is one truthful, reliable, end-to-end demonstration. Expanding feature count is secondary.

## 2. Non-negotiable constraints

- Submitted implementation artifacts must be created with tools permitted by the hackathon.
- Do not copy source code, tests, prompts, generated assets, or UI components from legacy
  checkouts, external backups, or unrelated projects.
- High-level product strategy may guide the clean implementation, but the code must be rebuilt.
- Only Google Cloud AI tools and the selected partner's permitted AI features may be used.
- ClickHouse must be used at runtime through the official `mcp-clickhouse` server connected to a
  ClickHouse Cloud or self-hosted cluster.
- No generative provider call may occur before explicit human approval.
- An integration failure must remain a visible failure. It must never become a simulated success.
- All displayed hashes, counts, costs, statuses, releases, and verification verdicts must originate
  from backend records or deterministic frontend formatting of those records.

## 3. Collaboration boundary

### Entrant and permitted Google tooling

- Create and implement the clean repository.
- Generate all submitted source code, tests, prompts, assets, and deployment configuration.
- Configure Google Cloud, ClickHouse Cloud, MCP, storage, deployment, and Devpost.
- Preserve implementation-provenance evidence.

### Architecture & Quality Assurance

- Provide planning, architecture critique, acceptance criteria, and review checklists.
- Perform read-only audits of completed stages.
- Report defects and rule risks without writing untracked implementation code.

## 4. Minimum competitive vertical slice

The clean implementation should initially contain only this journey:

1. A production lead opens one campaign with 40 territory variants.
2. They select the EU disclaimer-change preset.
3. A live Google ADK agent interprets the request and invokes typed deterministic tools.
4. The backend calculates the exact blast radius, reuse count, cost, and graph hash.
5. The workflow stops at `AWAITING_APPROVAL` with zero provider calls.
6. The user explicitly approves the quoted spend.
7. The ADK workflow resumes and rebuilds only the dirty nodes.
8. Build and provider events are recorded in ClickHouse.
9. An analyst query reads the build history through the official ClickHouse MCP server.
10. The release is re-read from storage and verified byte-exact.
11. A controlled one-byte corruption causes verification to fail visibly.

Do not add secondary campaigns or optional views until this path is working live.

## 5. Target architecture

```text
React UI
  |
  | typed HTTP requests and build-event stream
  v
FastAPI workflow API
  |
  +--> Google ADK agent
  |      |
  |      +--> interpret_change
  |      +--> evaluate_project_rules
  |      +--> compute_blast_radius
  |      +--> quote_rebuild
  |      +--> build_dirty_subtree      [only after human approval]
  |      +--> verify_release
  |      +--> query_slate_history
  |
  +--> deterministic Python core
  |      JCS + SHA-256, DAG, rules, cost, approval validation, verification
  |
  +--> Vertex AI providers
  |      Gemini first; optional media providers only if the vertical slice needs them
  |
  +--> content-addressed artifact storage
  |
  +--> ClickHouse writes
  |
  +--> official mcp-clickhouse read path
```

The ADK agent chooses and sequences typed tools. It must not calculate hashes, costs, dirty sets,
or verification verdicts. Those remain deterministic.

## 6. Workstream A — Clean implementation provenance

**Owner:** entrant with permitted Google tooling  
**Priority:** blocking  
**Target completion:** September 5

### A1. Preserve only non-implementation strategy

- Treat this plan and the product problem statement as strategy.
- Do not transfer implementation code, tests, prompts, UI assets, or generated designs.
- Keep the current checkout separate and exclude it from the submitted repository.

### A2. Create the clean repository

- Create a new empty public repository during the contest period.
- Add Apache-2.0 `LICENSE` at the repository root.
- Confirm the license is detected in the repository About panel.
- Add a secret-safe `.gitignore` before creating local credentials.
- Make the empty scaffold the first commit.

### A3. Record provenance

Create `PROVENANCE.md` containing:

- repository creation date;
- entrant and team members;
- implementation tools used;
- confirmation that prior implementation artifacts were not copied;
- a link or transcript reference for any organizer clarification;
- a short list of third-party non-AI libraries and their licenses.

Preserve commit history and relevant permitted-tool session logs.

### A4. Provenance gate

Workstreams B–D may be designed in parallel, but submitted implementation begins only in the clean
repository. If provenance cannot be defended honestly, stop and ask the organizer before submission.

### Acceptance criteria

- The submitted repository has an auditable empty starting point.
- No submitted file is copied from legacy prototype trees.
- Every implementation tool used is permitted by the event rules.
- `PROVENANCE.md` is accurate and complete.
- The public repository and Apache-2.0 license are visible without authentication.

## 7. Workstream B — Real backend-driven headline preset

**Owner:** entrant with permitted Google tooling  
**Priority:** P0  
**Target completion:** September 6

### B1. Define the preset as data

Use a stable identifier rather than depending on fragile prose parsing:

```json
{
  "preset_id": "eu_disclaimer_2026",
  "campaign_id": "campaign_aurora"
}
```

The server resolves this identifier into a validated typed change. A separate endpoint may accept
custom natural-language changes through Gemini.

### B2. Implement the deterministic scenario

- Seed one campaign with 40 territory variants.
- Share upstream nodes and fan out at localisable copy/package nodes.
- Define the demo project rule and its territory scope explicitly.
- Calculate fingerprints, graph hash, dirty nodes, reused nodes, cost, and duration deterministically.
- Return findings containing node ID, territory, rule ID, and reason.
- Persist the change and estimate so page refreshes do not invent a new result.

### B3. Required API contract

```text
POST /api/presets/{preset_id}/changes
POST /api/changes/{change_id}/estimate
GET  /api/changes/{change_id}
GET  /api/changes/{change_id}/graph
POST /api/changes/{change_id}/approve
POST /api/changes/{change_id}/build
GET  /api/builds/{build_id}
GET  /api/releases/{release_id}/verify
```

Every response must use a typed error envelope on failure.

### B4. Backend tests

- Known preset produces a validated change and never returns 422.
- Unknown preset returns a typed 404.
- The same graph and preset produce identical fingerprints and estimate.
- Estimate contains the expected dirty and reused node IDs.
- Provider-call count remains zero before approval.
- Build without approval returns 409.
- Approval is bound to the estimate's graph hash.
- A changed graph invalidates the approval.

### Acceptance criteria

- The UI preset completes against the real API with no fallback branch.
- The displayed dirty count, reuse count, cost, findings, and graph match the API response.
- Replaying the same preset produces stable deterministic results.
- Server and browser logs contain no unhandled errors.

## 8. Workstream C — Remove fabricated success and silent fallback

**Owner:** entrant with permitted Google tooling  
**Priority:** P0  
**Target completion:** September 6

### C1. Use explicit operation states

Every network-backed action must follow:

```text
idle -> loading -> succeeded
               -> failed
```

Failures must preserve the last valid state and show an actionable error. They must not unlock the
next workflow stage.

### C2. Remove synthetic evidence

Remove or prohibit:

- advancement after a failed change request;
- approval after a failed approval request;
- completion animations that run independently of the build result;
- fake scanning totals or random progress presented as backend work;
- generated placeholder hashes presented as artifact hashes;
- fixed release IDs or artifact counts;
- verification success after a failed verification request;
- “Calling Vertex AI” unless a recorded provider-call event confirms it;
- “live API attached” unless a health/readiness check confirms it.

Decorative animation is allowed only when it is clearly decorative and does not represent system
state or evidence.

### C3. Truthful runtime status

Display separate status for:

- Google ADK;
- Vertex AI;
- ClickHouse writer;
- ClickHouse MCP reader;
- artifact storage;
- deployment build/version.

Use at least these states:

```text
checking | live_verified | fallback_demo | unavailable | error
```

`live_verified` requires a successful lightweight readiness check, not merely the presence of an
environment variable or installed package.

### C4. Event-driven build display

- Stream server build events using SSE, WebSocket, or bounded polling.
- Every event includes build ID, run ID, node ID, attempt, status, provider mode, and timestamp.
- Render progress from completed backend nodes, not elapsed timers.
- Clearly distinguish `cache_hit`, `provider_call`, `retry`, `failed`, and `verified` events.

### C5. Frontend tests

- A 422 change response leaves the user on the proposal screen.
- A failed estimate cannot display `ESTIMATE READY`.
- A failed approval keeps the build button disabled.
- A failed build cannot create or display a release.
- A failed verification produces an error, never green success.
- Fallback mode never displays a live-provider-call message.
- Counts shown in graph, approval, build, analytics, and release views remain consistent.

### Acceptance criteria

- Disconnecting each integration individually produces an explicit, correctly labelled failure.
- No catch handler converts an error into success.
- No random value contributes to a displayed operational fact.
- A judge can identify which integrations are live without opening developer tools.

## 9. Workstream D — Demonstrate the live Google ADK agent

**Owner:** entrant with permitted Google tooling  
**Priority:** P0  
**Target completion:** September 7

### D1. Agent responsibilities

The ADK agent may:

- interpret the user's change request into a typed contract;
- select deterministic tools;
- explain returned findings and estimates;
- resume an approved workflow;
- query build history through the ClickHouse MCP tool.

The ADK agent may not:

- calculate a hash, dirty set, cost, or pass/fail verdict;
- approve spending for the user;
- call a provider before approval;
- silently substitute a local scripted workflow for a failed live ADK run.

### D2. Typed ADK tools

Implement narrow tools such as:

```text
interpret_change(change_text | preset_id)
evaluate_project_rules(change_id)
compute_blast_radius(change_id)
quote_rebuild(change_id)
get_approval_status(change_id)
build_dirty_subtree(change_id)
verify_release(release_id)
query_slate_history(question | guarded_sql)
```

Tool outputs are typed contracts. Tool errors remain explicit typed errors.

### D3. Pause-and-resume approval protocol

1. Start an ADK run and assign an agent run/session ID.
2. Let the agent interpret, evaluate, calculate, and quote.
3. Persist the run as `AWAITING_APPROVAL`.
4. End or suspend agent execution without calling a provider.
5. Show an explicit human approval control in the UI.
6. Record actor, timestamp, estimate ID, and graph hash on approval.
7. Resume the same workflow only after approval.
8. Revalidate the graph hash before the first provider call.

Do not expose an `auto_approve` option in the judge-facing UI or demo API.

### D4. Judge-facing agent trace

Display:

- agent run/session ID;
- live/fallback/error mode;
- ordered tool calls;
- concise typed outputs;
- approval pause;
- provider calls after approval;
- ClickHouse MCP query and returned rows;
- final release ID and verification result.

The displayed trace must originate from stored audit events.

### D5. ADK tests

- A live ADK run invokes the expected deterministic tools.
- The run stops at `AWAITING_APPROVAL` when approval is absent.
- Provider-call count is zero at the pause.
- Agent attempts to build early receive a typed rejection.
- Explicit approval resumes the correct run.
- Stale approval blocks the resumed build.
- A failed live ADK run is labelled failed, not deterministic success.
- `google_adk_live` is reported only after the real ADK Runner returns successfully.
- The UI tool trace equals the persisted audit trace.

### Acceptance criteria

- The active judge-facing UI exercises the ADK endpoint.
- The demo visibly shows the agent pause for a person.
- No automatic or simulated approval occurs.
- The post-approval build and verification results are real backend records.

## 10. Integration checkpoint

Run the entire journey in a clean browser session:

1. Confirm every status is `live_verified`.
2. Select the headline preset.
3. Observe the live ADK tool trace.
4. Confirm the workflow stops before spend.
5. Compare UI estimate values with the API response.
6. Approve explicitly.
7. Observe real provider/cache/retry events.
8. Confirm ClickHouse receives the events.
9. Ask a canned question through MCP and display the executed SQL and returned rows.
10. Verify the release successfully.
11. Corrupt one byte and verify that the same release fails.
12. Refresh and confirm the build, release, and audit history persist.

The checkpoint fails if any screen uses locally generated operational data.

## 11. Four-day delivery schedule

### September 5 — Provenance and clean foundation

- Resolve the organizer/provenance question.
- Create the clean public repository and initial commit.
- Add license, provenance record, minimal contracts, and deterministic core skeleton.
- Define the one campaign and one preset.

### September 6 — Real vertical slice and truthful UI

- Implement the preset-to-estimate backend path.
- Implement approval invariants.
- Build the frontend on real API state only.
- Add failure-state and cross-screen consistency tests.

### September 7 — ADK, ClickHouse MCP, and deployment

- Connect the live Google ADK workflow.
- Implement pause-and-resume approval.
- Connect ClickHouse writes and official MCP reads.
- Deploy to Cloud Run with server-side secrets.
- Verify every public status as `live_verified`.

### September 8 — Stabilise, record, and submit

- Run backend tests, frontend tests, lint, production build, and cold-clone rehearsal.
- Run the exact live demo repeatedly.
- Record a narrated or clearly subtitled video under three minutes.
- Ensure the video visibly proves live ADK, Vertex, ClickHouse MCP, approval, rebuild, and tamper detection.
- Complete Devpost fields and submit early.

### September 9 — Buffer only

- Fix only submission-blocking issues.
- Do not add features.
- Confirm public URLs and submit before 10:00 PM WAT.

## 12. Scope cuts

Cut in this order if time is short:

1. Additional campaigns.
2. Free-form analyst questions; retain one or two canned MCP-backed questions.
3. Rich analytics charts; retain build totals and one savings comparison.
4. Music and voice generation.
5. Image/video generation if the core proof can use a smaller permitted Gemini text artifact.
6. Release-to-release diff view.

Never cut:

- clean implementation provenance;
- live Google ADK participation;
- live ClickHouse MCP use;
- blast radius before spend;
- explicit human approval;
- incremental rebuild and proven cache reuse;
- truthful failure/mode labelling;
- release verification;
- public repository, hosted URL, and functioning demo video.

## 13. Final acceptance matrix

| Area | Required evidence | Pass condition |
|---|---|---|
| Provenance | Repository history and `PROVENANCE.md` | No prohibited implementation artifacts or tools |
| Preset | Browser and API trace | Preset completes without fallback or 422 |
| Truthfulness | Failure-injection tests | No error path advances to success |
| ADK | Stored tool trace | Live ADK run pauses and resumes around human approval |
| Pre-spend gate | Provider-call log | Zero provider calls before approval |
| Incremental build | Build records | Only dirty nodes generate; clean nodes are cache hits |
| ClickHouse | Live status and MCP query | Events written and read via official MCP server |
| Verification | Stored artifact test | Clean release passes; one-byte corruption fails |
| Consistency | Cross-screen assertions | Counts and costs agree everywhere |
| Deployment | Public cold-browser test | Hosted application loads and completes the journey |
| Repository | Cold-clone test | Setup works from documented instructions |
| Video | Public YouTube/Vimeo URL | Under 3:00 and shows the real functioning workflow |

## 14. Definition of done

The remediation is complete only when a judge can open the public URL in a new browser, execute the
headline scenario, observe a live Google ADK agent stop for approval, approve it, see only the dirty
nodes rebuild, query the resulting ClickHouse history through the official MCP server, and verify then
tamper with the resulting release—all without encountering simulated operational evidence.

