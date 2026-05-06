import { useState } from "react";
import "./ClaimClusters.css";

const scoreColor = (score) => {
  if (score >= 0.6) return "var(--green)";
  if (score >= 0.4) return "var(--amber)";
  return "var(--red)";
};

const statusConfig = {
  "high-signal": { label: "HIGH SIGNAL", class: "tag-green" },
  "medium": { label: "MEDIUM SIGNAL", class: "tag-amber" },
  "low": { label: "LOW SIGNAL", class: "tag-cyan" },
  "misinformation": { label: "MISINFORMATION", class: "tag-red" },
};

const platformIcon = {
  twitter: "𝕏",
  reddit: "ʀ",
  facebook: "ƒ",
  forums: "⊞",
  tiktok: "♪",
};

export default function ClaimClusters({ clusters = [], claims = [], loading = false }) {
  const [selected, setSelected] = useState(null);
  const [sortBy, setSortBy] = useState("final_score");

  if (loading && clusters.length === 0) {
    return (
      <div className="clusters-layout">
        <div className="detail-empty">
          <div className="empty-icon animate-pulse">⬡</div>
          <div className="empty-title display">Analyzing Clusters...</div>
        </div>
      </div>
    );
  }

  const sorted = [...clusters].sort((a, b) => {
    if (sortBy === "final_score") return (b.final_score || 0) - (a.final_score || 0);
    if (sortBy === "frequency") return (b.claim_ids?.length || 0) - (a.claim_ids?.length || 0);
    return 0;
  });

  const selectedCluster = selected ? clusters.find(c => c.cluster_id === selected) : null;
  const clusterClaims = selectedCluster ? claims.filter(c => selectedCluster.claim_ids.includes(c.claim_id)) : [];

  return (
    <div className="clusters-layout">
      {/* Left: Cluster list */}
      <div className="clusters-list panel">
        <div className="panel-header">
          <span className="panel-title">Claim Clusters · {clusters.length} Identified</span>
          <select
            style={{ width: "auto", padding: "3px 8px", fontSize: 10 }}
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="final_score">Sort: Score</option>
            <option value="frequency">Sort: Frequency</option>
          </select>
        </div>

        <div className="clusters-scroll">
          {sorted.length === 0 ? (
            <div className="detail-empty" style={{ height: "auto", padding: 40 }}>
              <div className="empty-icon">⬡</div>
              <div className="empty-title display">No Clusters Yet</div>
              <div className="empty-sub">Once investigation starts, AI will group similar claims into clusters here.</div>
            </div>
          ) : (
            sorted.map((cluster) => {
              const status = statusConfig[cluster.status] || statusConfig.low;
              const isSelected = selected === cluster.cluster_id;
              const isMisinfo = cluster.status === "misinformation";
              const clusterClaimsPreview = claims.filter(c => cluster.claim_ids.includes(c.claim_id)).slice(0, 2);

              return (
                <div
                  key={cluster.cluster_id}
                  className={`cluster-item ${isSelected ? "selected" : ""} ${isMisinfo ? "misinfo" : ""}`}
                  onClick={() => setSelected(isSelected ? null : cluster.cluster_id)}
                >
                  <div className="cluster-item-header">
                    <div className="cluster-id mono">{cluster.cluster_id}</div>
                    <span className={`tag ${status.class}`}>{status.label}</span>
                  </div>

                  <div className="cluster-label display">{cluster.label}</div>

                  <div className="cluster-claims-preview">
                    {clusterClaimsPreview.map((c, i) => (
                      <div key={i} className="claim-preview-item">
                        <span className="claim-quote">"</span>{c.statement}<span className="claim-quote">"</span>
                      </div>
                    ))}
                    {cluster.claim_ids.length > 2 && (
                      <div className="mono" style={{ fontSize: 10, color: "var(--text-dim)" }}>
                        +{cluster.claim_ids.length - 2} more claims
                      </div>
                    )}
                  </div>

                  <div className="cluster-metrics-row">
                    <div className="cluster-metric">
                      <span className="cm-value" style={{ color: "var(--cyan)" }}>{cluster.claim_ids.length}</span>
                      <span className="cm-label">claims</span>
                    </div>
                    <div className="cluster-metric">
                      <span className="cm-value" style={{ color: "var(--teal)" }}>{Object.keys(cluster.platform_breakdown || {}).length}</span>
                      <span className="cm-label">sources</span>
                    </div>
                    <div className="cluster-metric">
                      <span className="cm-value" style={{ color: scoreColor(cluster.final_score) }}>
                        {((cluster.final_score || 0) * 100).toFixed(0)}%
                      </span>
                      <span className="cm-label">score</span>
                    </div>
                  </div>

                  <div className="cluster-score-bars">
                    <div className="score-bar-row">
                      <span className="sbar-label">CROWD</span>
                      <div className="score-bar flex-1">
                        <div className="score-bar-fill" style={{
                          width: `${(cluster.crowd_score || 0) * 100}%`,
                          background: "var(--cyan)",
                        }} />
                      </div>
                      <span className="sbar-val">{(cluster.crowd_score || 0).toFixed(2)}</span>
                    </div>
                    <div className="score-bar-row">
                      <span className="sbar-label">FINAL</span>
                      <div className="score-bar flex-1">
                        <div className="score-bar-fill" style={{
                          width: `${(cluster.final_score || 0) * 100}%`,
                          background: scoreColor(cluster.final_score),
                        }} />
                      </div>
                      <span className="sbar-val" style={{ color: scoreColor(cluster.final_score) }}>
                        {(cluster.final_score || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {isMisinfo && (
                    <div className="misinfo-warning">
                      🚨 {cluster.misinfo_reason}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right: Detail panel */}
      <div className="cluster-detail panel">
        {selectedCluster ? (
          <ClusterDetail cluster={selectedCluster} claims={clusterClaims} />
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

function ClusterDetail({ cluster, claims }) {
  const status = statusConfig[cluster.status] || statusConfig.low;
  const isMisinfo = cluster.status === "misinformation";

  return (
    <div className="detail-content animate-in">
      <div className="panel-header">
        <div>
          <span className="panel-title">{cluster.cluster_id} · Detailed Analysis</span>
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
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{cluster.misinfo_reason}</div>
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
                {((cluster.crowd_score || 0) * 100).toFixed(0)}
              </div>
              <div className="score-card-label">CROWD SCORE</div>
              <div className="score-card-sub">Frequency · Diversity · Recency</div>
            </div>
            <div className="score-arrow">=</div>
            <div className="score-card final">
              <div className="score-big" style={{
                color: scoreColor(cluster.final_score),
                fontSize: 40,
              }}>
                {((cluster.final_score || 0) * 100).toFixed(0)}
              </div>
              <div className="score-card-label">FINAL SCORE</div>
              <div className="score-card-sub">Composite Intelligence Score</div>
            </div>
          </div>
        </div>

        {/* Claim list */}
        <div className="detail-section">
          <div className="section-label">Extracted Claims ({claims.length})</div>
          <div className="claims-list">
            {claims.map((c, i) => (
              <div key={i} className="claim-item">
                <div className="claim-num mono">{String(i + 1).padStart(2, "0")}</div>
                <div className="claim-text">
                  <div style={{ fontWeight: 500 }}>"{c.statement}"</div>
                  <div className="mono" style={{ fontSize: 9, color: "var(--text-dim)", marginTop: 4 }}>
                    Type: {c.claim_type} · Confidence: {c.confidence?.toFixed(2)} · Lang: {c.language}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Source breakdown */}
        <div className="detail-section">
          <div className="section-label">Source Distribution</div>
          <div className="sources-grid">
            {Object.entries(cluster.platform_breakdown || {}).map(([platform, count], i) => (
              <div key={i} className="source-item">
                <div className="source-icon">{platformIcon[platform.toLowerCase()] || "○"}</div>
                <div className="source-name">{platform}</div>
                <div className="source-count" style={{ color: "var(--cyan)" }}>{count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
