import { useState } from "react";
import "./Leads.css";

const priorityConfig = {
  urgent: { label: "URGENT", class: "tag-red", order: 0 },
  high: { label: "HIGH", class: "tag-amber", order: 1 },
  medium: { label: "MEDIUM", class: "tag-cyan", order: 2 },
  low: { label: "LOW", class: "tag-dim", order: 3 },
};

export default function Leads({ leads = [], loading = false }) {
  const [assigned, setAssigned] = useState({});
  const [expanded, setExpanded] = useState(null);

  if (loading && leads.length === 0) {
    return (
      <div className="leads-container">
        <div className="detail-empty">
          <div className="empty-icon animate-pulse">⚡</div>
          <div className="empty-title display">Fetching Validated Leads...</div>
        </div>
      </div>
    );
  }

  const sorted = [...leads].sort((a, b) =>
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
        {sorted.length === 0 ? (
          <div className="detail-empty">
            <div className="empty-icon">⚡</div>
            <div className="empty-title display">No Leads Generated Yet</div>
            <div className="empty-sub">Investigation in progress. Leads will appear once high-confidence clusters are identified.</div>
          </div>
        ) : (
          sorted.map((lead, i) => {
            const priority = priorityConfig[lead.priority] || priorityConfig.medium;
            const isExpanded = expanded === lead.lead_id;
            const isAssigned = assigned[lead.lead_id];

            return (
              <div
                key={lead.lead_id}
                className={`lead-card animate-in ${isExpanded ? "expanded" : ""}`}
                style={{ animationDelay: `${i * 0.08}s` }}
              >
                <div className="lead-main" onClick={() => setExpanded(isExpanded ? null : lead.lead_id)}>
                  <div className="lead-header">
                    <div className="lead-id-group">
                      <span className="lead-id mono">{lead.lead_id}</span>
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

                  <div className="lead-source-cluster">
                    <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>SOURCE CLUSTER</span>
                    <span className="mono" style={{ fontSize: 10, color: "var(--cyan)" }}>{lead.cluster_id}</span>
                    <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{lead.claim_count} Claims from {lead.unique_sources} Sources</span>
                  </div>

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
                          {lead.evidence && lead.evidence.map((e, i) => (
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
                          <div className="action-text">{lead.action_required}</div>
                        </div>

                        <div style={{ marginTop: 12 }}>
                          <div className="section-mini-label">Traceability</div>
                          <div className="trace-chain">
                            <div className="trace-node">Community Posts</div>
                            <div className="trace-arrow">→</div>
                            <div className="trace-node">Cluster {lead.cluster_id}</div>
                            <div className="trace-arrow">→</div>
                            <div className="trace-node">AI Verified</div>
                            <div className="trace-arrow">→</div>
                            <div className="trace-node highlight">{lead.lead_id}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="lead-actions">
                      <button
                        className={`btn ${isAssigned ? "btn-ghost" : "btn-primary"}`}
                        onClick={() => setAssigned(prev => ({ ...prev, [lead.lead_id]: !prev[lead.lead_id] }))}
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
          })
        )}

        <div className="misinfo-leads-section">
          <div className="section-mini-label" style={{ marginBottom: 10 }}>
            Filtered Misinformation
          </div>
          <div className="misinfo-lead-card">
            <span style={{ fontSize: 12, color: "var(--text-dim)" }}>
              AI models automatically exclude clusters with low truth-scores from the leads view.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
