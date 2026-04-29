import { useState } from "react";
import { mockLeads, mockClaimClusters } from "../data/mockData";
import "./Leads.css";

const priorityConfig = {
  urgent: { label: "URGENT", class: "tag-red", order: 0 },
  high: { label: "HIGH", class: "tag-amber", order: 1 },
  medium: { label: "MEDIUM", class: "tag-cyan", order: 2 },
  low: { label: "LOW", class: "tag-dim", order: 3 },
};

export default function Leads() {
  const [assigned, setAssigned] = useState({});
  const [expanded, setExpanded] = useState(null);

  const sorted = [...mockLeads].sort((a, b) =>
    (priorityConfig[a.priority]?.order ?? 9) - (priorityConfig[b.priority]?.order ?? 9)
  );

  return (
    <div className="leads-container">
      <div className="leads-header-bar">
        <div>
          <h2 className="display" style={{ fontSize: 18, letterSpacing: "0.08em" }}>
            VALIDATED LEADS
          </h2>
          <div className="mono" style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 2 }}>
            Crowd-validated · AI-verified · Traceable evidence chains
          </div>
        </div>
        <div className="leads-summary">
          <div className="ls-stat">
            <span style={{ color: "var(--red)", fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700 }}>
              {sorted.filter(l => l.priority === "urgent").length}
            </span>
            <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>URGENT</span>
          </div>
          <div className="ls-stat">
            <span style={{ color: "var(--amber)", fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700 }}>
              {sorted.filter(l => l.priority === "high" || l.priority === "medium").length}
            </span>
            <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>OTHER</span>
          </div>
          <div className="ls-stat">
            <span style={{ color: "var(--green)", fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700 }}>
              {sorted.length}
            </span>
            <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>TOTAL</span>
          </div>
        </div>
      </div>

      <div className="leads-list">
        {sorted.map((lead, i) => {
          const priority = priorityConfig[lead.priority];
          const cluster = mockClaimClusters.find(c => c.id === lead.claimId);
          const isExpanded = expanded === lead.id;
          const isAssigned = assigned[lead.id];

          return (
            <div
              key={lead.id}
              className={`lead-card animate-in ${isExpanded ? "expanded" : ""}`}
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="lead-main" onClick={() => setExpanded(isExpanded ? null : lead.id)}>
                <div className="lead-header">
                  <div className="lead-id-group">
                    <span className="lead-id mono">{lead.id}</span>
                    <span className={`tag ${priority.class}`}>{priority.label}</span>
                    {isAssigned && <span className="tag tag-green">ASSIGNED</span>}
                  </div>
                  <div className="lead-confidence">
                    <div className="conf-value" style={{
                      color: lead.confidence >= 0.6 ? "var(--green)" : lead.confidence >= 0.4 ? "var(--amber)" : "var(--red)"
                    }}>
                      {(lead.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="conf-label mono">CONFIDENCE</div>
                  </div>
                </div>

                <h3 className="lead-title display">{lead.title}</h3>

                {cluster && (
                  <div className="lead-source-cluster">
                    <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>SOURCE CLUSTER</span>
                    <span className="mono" style={{ fontSize: 10, color: "var(--cyan)" }}>{cluster.id}</span>
                    <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{cluster.label}</span>
                  </div>
                )}

                <div className="lead-confidence-bar">
                  <div className="score-bar" style={{ height: 4 }}>
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${lead.confidence * 100}%`,
                        background: lead.confidence >= 0.6 ? "var(--green)" : lead.confidence >= 0.4 ? "var(--amber)" : "var(--red)",
                      }}
                    />
                  </div>
                </div>

                <div className="lead-expand-hint mono">
                  {isExpanded ? "▲ COLLAPSE" : "▼ VIEW EVIDENCE & ACTIONS"}
                </div>
              </div>

              {isExpanded && (
                <div className="lead-detail animate-in">
                  <div className="divider" style={{ marginBottom: 14 }} />

                  <div className="lead-detail-grid">
                    <div>
                      <div className="section-mini-label">Supporting Evidence</div>
                      <ul className="evidence-list-simple">
                        {lead.evidence.map((e, i) => (
                          <li key={i} className="evidence-simple-item">
                            <span className="ev-bullet">◆</span>
                            <span>{e}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <div className="section-mini-label">Required Action</div>
                      <div className="action-box">
                        <div className="action-icon">⚡</div>
                        <div className="action-text">{lead.actionRequired}</div>
                      </div>

                      <div style={{ marginTop: 12 }}>
                        <div className="section-mini-label">Traceability</div>
                        <div className="trace-chain">
                          <div className="trace-node">Community Posts ({cluster?.frequency})</div>
                          <div className="trace-arrow">→</div>
                          <div className="trace-node">Cluster {lead.claimId}</div>
                          <div className="trace-arrow">→</div>
                          <div className="trace-node">AI Verified</div>
                          <div className="trace-arrow">→</div>
                          <div className="trace-node highlight">{lead.id}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="lead-actions">
                    <button
                      className={`btn ${isAssigned ? "btn-ghost" : "btn-primary"}`}
                      onClick={() => setAssigned(prev => ({ ...prev, [lead.id]: !prev[lead.id] }))}
                    >
                      {isAssigned ? "✓ ASSIGNED" : "ASSIGN TO INVESTIGATOR"}
                    </button>
                    <button className="btn btn-secondary">REQUEST DEEPER ANALYSIS</button>
                    <button className="btn btn-ghost">EXPORT REPORT</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Placeholder for misinformation leads */}
        <div className="misinfo-leads-section">
          <div className="section-mini-label" style={{ marginBottom: 10 }}>
            Filtered Misinformation (1 cluster excluded from leads)
          </div>
          <div className="misinfo-lead-card">
            <span className="tag tag-red" style={{ marginRight: 8 }}>MISINFO</span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              CC-003 · Rabat Sighting — Image reuse detected, bot amplification confirmed. Excluded from active leads.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
