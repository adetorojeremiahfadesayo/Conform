import type { Estimate, GraphNode, NodeRun } from "../types";

interface Props {
  node: GraphNode;
  estimate: Estimate | null;
  runs: NodeRun[];
  onClose: () => void;
}

// Node inspector rail — the provenance view. Every node answers: what is it,
// what is its fingerprint, why is it dirty (reason code, verbatim from the
// engine), and what happened when it last ran (attempt chain with retries
// nested under their failed parents). Colour always carries a text label.
export function NodeInspector({ node, estimate, runs, onClose }: Props) {
  const dirtyEntry = estimate?.dirty_nodes.find((d) => d.node_id === node.node_id);
  const nodeRuns = runs.filter((r) => r.node_id === node.node_id);

  return (
    <aside className="inspector">
      <div className="inspector-head">
        <div>
          <p className="inspector-eyebrow">Node detail</p>
          <h3>{node.node_id}</h3>
          <div className="inspector-pills">
            <span className="badge">{node.kind}</span>
            <span className="badge">{node.territory}</span>
            <span className={`badge ${node.state === "dirty" ? "retry" : "ok"}`}>
              {node.state === "dirty" ? "DIRTY" : "CLEAN"}
            </span>
          </div>
        </div>
        <button onClick={onClose} aria-label="Close inspector" className="inspector-close">
          ✕
        </button>
      </div>

      <div className="inspector-body">
        <section>
          <p className="inspector-eyebrow">Fingerprint</p>
          <p className="mono break-all">{node.fingerprint}</p>
          <p className="dim" style={{ fontSize: 11 }}>
            SHA-256 over canonical(inputs ‖ recipe ‖ parent fingerprints). Same inputs + recipe
            ⇒ same fingerprint ⇒ the existing bytes are reused, never regenerated.
          </p>
        </section>

        {node.parents.length > 0 && (
          <section>
            <p className="inspector-eyebrow">Depends on</p>
            {node.parents.map((p) => (
              <p key={p} className="mono" style={{ fontSize: 11 }}>
                {p}
              </p>
            ))}
          </section>
        )}

        {dirtyEntry && (
          <section className="inspector-reason">
            <p className="inspector-eyebrow">Why it rebuilds</p>
            <p className="mono reason-code">{dirtyEntry.reason}</p>
            <p className="dim" style={{ fontSize: 11 }}>
              {dirtyEntry.depth === 0
                ? "Directly changed — this node's own spec or a scoped rule."
                : `Depth ${dirtyEntry.depth} — an upstream fingerprint changed, so this inherits the invalidation.`}
            </p>
          </section>
        )}

        {nodeRuns.length > 0 && (
          <section>
            <p className="inspector-eyebrow">Attempts (latest build)</p>
            {nodeRuns.map((r) => (
              <div
                key={r.run_id}
                className="attempt-card"
                style={r.parent_run_id ? { borderStyle: "dashed", marginLeft: 12 } : undefined}
              >
                <div className="inspector-pills">
                  <span className={`badge ${r.status}`}>{r.status}</span>
                  {r.cache_hit && <span className="badge cache">cache hit</span>}
                  {r.attempt > 1 && <span className="badge retry">attempt {r.attempt}</span>}
                  {r.error_class !== "none" && <span className="badge err">{r.error_class}</span>}
                </div>
                <p className="mono" style={{ fontSize: 10, marginTop: 6 }}>
                  run {r.run_id}
                  {r.parent_run_id ? ` ← parent ${r.parent_run_id}` : ""}
                </p>
                <p className="dim" style={{ fontSize: 11 }}>
                  cost ${r.cost_usd}
                </p>
              </div>
            ))}
          </section>
        )}

        {nodeRuns.length === 0 && (
          <p className="dim" style={{ fontSize: 12 }}>
            No build has run this node yet in the current session.
          </p>
        )}
      </div>
    </aside>
  );
}
