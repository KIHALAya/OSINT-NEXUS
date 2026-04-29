import { mockStats } from "../data/mockData";
import "./CommunityIntelligence.css";

const STEPS = [
  { num: 1, id: "ingestion", label: "Community Ingestion", sub: "Reddit · Twitter · TikTok · Forums", icon: "📡" },
  { num: 2, id: "extraction", label: "Claim Extraction", sub: "AI Layer — Gemma", icon: "🧠" },
  { num: 3, id: "clustering", label: "Claim Clustering", sub: "Group similar claims", icon: "⬡" },
  { num: 4, id: "scoring", label: "Credibility Scoring", sub: "Crowd + Source + Consistency", icon: "📊" },
  { num: 5, id: "verification", label: "AI Verification", sub: "OSINT + Image + Contradiction", icon: "🔍" },
  { num: 6, id: "misinfo", label: "Misinfo Filtering", sub: "Bot detection · Image reuse", icon: "🚨" },
  { num: 7, id: "leads", label: "Lead Generation", sub: "Crowd-validated leads", icon: "⚡" },
  { num: 8, id: "graph", label: "Graph Update", sub: "Knowledge graph sync", icon: "🕸" },
];

export default function CommunityIntelligence() {
  return (
    <div className="ci-container">
      {/* Pipeline */}
      <div className="ci-section">
        <div className="ci-section-title">PROCESSING PIPELINE</div>
        <div className="pipeline-flow">
          {STEPS.map((step, i) => {
            const status = mockStats.processingSteps[i];
            return (
              <div key={step.id} className="pipeline-step">
                <div className={`step-card ${status?.status === "complete" ? "complete" : "pending"}`}>
                  <div className="step-icon">{step.icon}</div>
                  <div className="step-num mono">STEP {step.num}</div>
                  <div className="step-label display">{step.label}</div>
                  <div className="step-sub">{step.sub}</div>
                  {status && (
                    <div className={`step-status mono ${status.status}`}>
                      {status.status === "complete" ? `✓ ${status.time}` : "PENDING"}
                    </div>
                  )}
                </div>
                {i < STEPS.length - 1 && (
                  <div className="pipeline-arrow">→</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="ci-bottom-grid">
        {/* Stats */}
        <div className="ci-section">
          <div className="ci-section-title">INGESTION STATS</div>
          <div className="stats-cards">
            <div className="ci-stat-card">
              <div className="ci-stat-val cyan">{mockStats.totalPosts}</div>
              <div className="ci-stat-label">Total Posts</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val amber">{mockStats.claimsExtracted * 15}</div>
              <div className="ci-stat-label">Raw Claims</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val teal">{mockStats.clustersFormed}</div>
              <div className="ci-stat-label">Clusters</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val green">{mockStats.highSignalLeads}</div>
              <div className="ci-stat-label">High Leads</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val red">{mockStats.misinfoFiltered}</div>
              <div className="ci-stat-label">Misinfo</div>
            </div>
          </div>
        </div>

        {/* Platform breakdown */}
        <div className="ci-section">
          <div className="ci-section-title">PLATFORM BREAKDOWN</div>
          <div className="platform-bars">
            {mockStats.platformBreakdown.map((p, i) => (
              <div key={i} className="platform-bar-row">
                <div className="pb-label">{p.platform}</div>
                <div className="pb-bar-wrap">
                  <div
                    className="pb-bar"
                    style={{
                      width: `${p.percentage}%`,
                      background: ["var(--cyan)", "var(--teal)", "var(--purple)", "var(--amber)", "var(--green)"][i],
                    }}
                  />
                </div>
                <div className="pb-count mono">{p.count}</div>
                <div className="pb-pct mono">{p.percentage}%</div>
              </div>
            ))}
          </div>
        </div>

        {/* Raw intelligence sample */}
        <div className="ci-section">
          <div className="ci-section-title">RAW INTELLIGENCE SAMPLE</div>
          <div className="raw-intel-list">
            {[
              { claim: "Child seen near Morocco Mall", source: "twitter", engagement: 1200, reposts: 300, confidence: 0.4 },
              { claim: "Girl at morocco mall looks like her", source: "reddit", engagement: 340, reposts: 45, confidence: 0.35 },
              { claim: "Possible sighting Casablanca mall", source: "facebook", engagement: 89, reposts: 12, confidence: 0.3 },
              { claim: "Spotted in Rabat Agdal", source: "twitter", engagement: 4200, reposts: 890, confidence: 0.05, flagged: true },
              { claim: "Seen boarding train going north", source: "forums", engagement: 156, reposts: 28, confidence: 0.25 },
            ].map((item, i) => (
              <div key={i} className={`raw-intel-item ${item.flagged ? "flagged" : ""}`}>
                <div className="ri-source-badge">{item.source}</div>
                <div className="ri-claim">"{item.claim}"</div>
                <div className="ri-metrics">
                  <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>
                    ↑{item.engagement} · ↺{item.reposts}
                  </span>
                  <span className="mono" style={{
                    fontSize: 9,
                    color: item.confidence > 0.3 ? "var(--cyan)" : "var(--red-dim)",
                  }}>
                    {(item.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {item.flagged && (
                  <span className="tag tag-red" style={{ fontSize: 8 }}>MISINFO</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
