import { useState } from "react";
import { mockClaimClusters } from "../data/mockData";
import "./ClaimClusters.css";

const scoreColor = (score) => {
  if (score >= 0.6) return "var(--green)";
  if (score >= 0.4) return "var(--amber)";
  return "var(--red)";
};

const statusConfig = {
  "high-signal": { label: "HIGH SIGNAL", class: "tag-green" },
  "medium-signal": { label: "MEDIUM SIGNAL", class: "tag-amber" },
  "low-signal": { label: "LOW SIGNAL", class: "tag-cyan" },
  "misinformation": { label: "MISINFORMATION", class: "tag-red" },
};

const platformIcon = {
  twitter: "𝕏",
  reddit: "ʀ",
  facebook: "ƒ",
  forums: "⊞",
  tiktok: "♪",
};

export default function ClaimClusters() {
  const [selected, setSelected] = useState(null);
  const [sortBy, setSortBy] = useState("finalScore");

  const sorted = [...mockClaimClusters].sort((a, b) => {
    if (sortBy === "finalScore") return b.finalScore - a.finalScore;
    if (sortBy === "frequency") return b.frequency - a.frequency;
    if (sortBy === "recent") return a.recentActivity.localeCompare(b.recentActivity);
    return 0;
  });

  const selectedCluster = selected ? mockClaimClusters.find(c => c.id === selected) : null;

  return (
    <div className="clusters-layout">
      {/* Left: Cluster list */}
      <div className="clusters-list panel">
        <div className="panel-header">
          <span className="panel-title">Claim Clusters · {mockClaimClusters.length} Identified</span>
          <select
            style={{ width: "auto", padding: "3px 8px", fontSize: 10 }}
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="finalScore">Sort: Score</option>
            <option value="frequency">Sort: Frequency</option>
            <option value="recent">Sort: Recent</option>
          </select>
        </div>

        <div className="clusters-scroll">
          {sorted.map((cluster) => {
            const status = statusConfig[cluster.status];
            const isSelected = selected === cluster.id;
            const isMisinfo = cluster.status === "misinformation";

            return (
              <div
                key={cluster.id}
                className={`cluster-item ${isSelected ? "selected" : ""} ${isMisinfo ? "misinfo" : ""}`}
                onClick={() => setSelected(isSelected ? null : cluster.id)}
              >
                <div className="cluster-item-header">
                  <div className="cluster-id mono">{cluster.id}</div>
                  <span className={`tag ${status.class}`}>{status.label}</span>
                </div>

                <div className="cluster-label display">{cluster.label}</div>

                <div className="cluster-claims-preview">
                  {cluster.claims.slice(0, 2).map((c, i) => (
                    <div key={i} className="claim-preview-item">
                      <span className="claim-quote">"</span>{c}<span className="claim-quote">"</span>
                    </div>
                  ))}
                  {cluster.claims.length > 2 && (
                    <div className="mono" style={{ fontSize: 10, color: "var(--text-dim)" }}>
                      +{cluster.claims.length - 2} more claims
                    </div>
                  )}
                </div>

                <div className="cluster-metrics-row">
                  <div className="cluster-metric">
                    <span className="cm-value" style={{ color: "var(--cyan)" }}>{cluster.frequency}</span>
                    <span className="cm-label">posts</span>
                  </div>
                  <div className="cluster-metric">
                    <span className="cm-value" style={{ color: "var(--teal)" }}>{cluster.uniqueSources}</span>
                    <span className="cm-label">sources</span>
                  </div>
                  <div className="cluster-metric">
                    <span className="cm-value" style={{ color: scoreColor(cluster.finalScore) }}>
                      {(cluster.finalScore * 100).toFixed(0)}%
                    </span>
                    <span className="cm-label">score</span>
                  </div>
                  <div className="cluster-metric">
                    <span className="cm-value" style={{ color: "var(--text-dim)", fontSize: 11 }}>
                      {cluster.recentActivity}
                    </span>
                    <span className="cm-label">latest</span>
                  </div>
                </div>

                <div className="cluster-score-bars">
                  <div className="score-bar-row">
                    <span className="sbar-label">CROWD</span>
                    <div className="score-bar flex-1">
                      <div className="score-bar-fill" style={{
                        width: `${cluster.crowdScore * 100}%`,
                        background: "var(--cyan)",
                      }} />
                    </div>
                    <span className="sbar-val">{cluster.crowdScore.toFixed(2)}</span>
                  </div>
                  <div className="score-bar-row">
                    <span className="sbar-label">AI VER</span>
                    <div className="score-bar flex-1">
                      <div className="score-bar-fill" style={{
                        width: `${cluster.aiVerificationScore * 100}%`,
                        background: "var(--purple)",
                      }} />
                    </div>
                    <span className="sbar-val">{cluster.aiVerificationScore.toFixed(2)}</span>
                  </div>
                  <div className="score-bar-row">
                    <span className="sbar-label">FINAL</span>
                    <div className="score-bar flex-1">
                      <div className="score-bar-fill" style={{
                        width: `${cluster.finalScore * 100}%`,
                        background: scoreColor(cluster.finalScore),
                      }} />
                    </div>
                    <span className="sbar-val" style={{ color: scoreColor(cluster.finalScore) }}>
                      {cluster.finalScore.toFixed(2)}
                    </span>
                  </div>
                </div>

                {isMisinfo && (
                  <div className="misinfo-warning">
                    🚨 {cluster.misinfoReason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Right: Detail panel */}
      <div className="cluster-detail panel">
        {selectedCluster ? (
          <ClusterDetail cluster={selectedCluster} />
        ) : (
          <div className="detail-empty">
            <div className="empty-icon">⬡</div>
            <div className="empty-title display">Select a Claim Cluster</div>
            <div className="empty-sub">Click any cluster to view detailed analysis, evidence chains, and AI verification results</div>
          </div>
        )}
      </div>
    </div>
  );
}

function ClusterDetail({ cluster }) {
  const status = statusConfig[cluster.status];
  const isMisinfo = cluster.status === "misinformation";

  return (
    <div className="detail-content animate-in">
      <div className="panel-header">
        <div>
          <span className="panel-title">{cluster.id} · Detailed Analysis</span>
        </div>
        <span className={`tag ${status.class}`}>{status.label}</span>
      </div>

      <div className="detail-scroll">
        <div className="detail-section">
          <h2 className="detail-heading display">{cluster.label}</h2>
          {isMisinfo && (
            <div className="misinfo-alert">
              <div className="misinfo-icon">🚨</div>
              <div>
                <div style={{ fontWeight: 600, color: "var(--red)", marginBottom: 2 }}>MISINFORMATION DETECTED</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{cluster.misinfoReason}</div>
                {cluster.botAmplification && (
                  <div style={{ fontSize: 11, color: "var(--red-dim)", marginTop: 4 }}>
                    ⚠ Bot amplification detected — 75% of sharing accounts are new
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Score breakdown */}
        <div className="detail-section">
          <div className="section-label">Score Breakdown</div>
          <div className="score-breakdown">
            <div className="score-card">
              <div className="score-big" style={{ color: "var(--cyan)" }}>
                {(cluster.crowdScore * 100).toFixed(0)}
              </div>
              <div className="score-card-label">CROWD SCORE</div>
              <div className="score-card-sub">Frequency · Diversity · Recency</div>
            </div>
            <div className="score-arrow">×</div>
            <div className="score-card">
              <div className="score-big" style={{ color: "var(--purple)" }}>
                {(cluster.aiVerificationScore * 100).toFixed(0)}
              </div>
              <div className="score-card-label">AI VERIFICATION</div>
              <div className="score-card-sub">OSINT · Image Match · Consistency</div>
            </div>
            <div className="score-arrow">=</div>
            <div className="score-card final">
              <div className="score-big" style={{
                color: cluster.finalScore >= 0.6 ? "var(--green)" : cluster.finalScore >= 0.4 ? "var(--amber)" : "var(--red)",
                fontSize: 40,
              }}>
                {(cluster.finalScore * 100).toFixed(0)}
              </div>
              <div className="score-card-label">FINAL SCORE</div>
              <div className="score-card-sub">Composite Intelligence Score</div>
            </div>
          </div>
        </div>

        {/* Claim list */}
        <div className="detail-section">
          <div className="section-label">Extracted Claims ({cluster.claims.length})</div>
          <div className="claims-list">
            {cluster.claims.map((c, i) => (
              <div key={i} className="claim-item">
                <div className="claim-num mono">{String(i + 1).padStart(2, "0")}</div>
                <div className="claim-text">"{c}"</div>
              </div>
            ))}
          </div>
        </div>

        {/* Source breakdown */}
        <div className="detail-section">
          <div className="section-label">Source Distribution</div>
          <div className="sources-grid">
            {cluster.sources.map((s, i) => (
              <div key={i} className="source-item">
                <div className="source-icon">{platformIcon[s.platform] || "○"}</div>
                <div className="source-name">{s.platform}</div>
                <div className="source-count" style={{ color: "var(--cyan)" }}>{s.count}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Evidence */}
        {cluster.evidence.length > 0 && (
          <div className="detail-section">
            <div className="section-label">Supporting Evidence</div>
            <div className="evidence-list">
              {cluster.evidence.map((e, i) => (
                <div key={i} className={`evidence-item ${e.verified ? "verified" : "unverified"}`}>
                  <span className="evidence-badge">{e.verified ? "✓ VERIFIED" : "? UNVERIFIED"}</span>
                  <span className="evidence-content">{e.content}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Contradictions */}
        {cluster.contradictions.length > 0 && (
          <div className="detail-section">
            <div className="section-label">Contradictions Detected</div>
            <div className="contradictions-list">
              {cluster.contradictions.map((c, i) => (
                <div key={i} className={`contradiction-item severity-${c.severity}`}>
                  <span className="contra-severity">{c.severity.toUpperCase()}</span>
                  <span>{c.content}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="detail-section">
          <div className="section-label">Activity Timeline</div>
          <div className="timeline-list">
            {cluster.timeline.map((t, i) => (
              <div key={i} className="timeline-item">
                <div className="timeline-time mono">{t.time}</div>
                <div className="timeline-dot"></div>
                <div className="timeline-event">{t.event}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
