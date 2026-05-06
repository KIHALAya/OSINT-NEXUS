import "./CommunityIntelligence.css";

const platformIcon = {
  tiktok: "♪",
  reddit: "ʀ",
  twitter: "𝕏",
  facebook: "ƒ",
  forums: "⊞",
};

export default function CommunityIntelligence({ posts = [], loading = false }) {
  // Derive platform breakdown
  const counts = posts.reduce((acc, p) => {
    acc[p.source] = (acc[p.source] || 0) + 1;
    return acc;
  }, {});

  const platforms = Object.entries(counts).map(([name, count]) => ({
    name,
    count,
    percentage: Math.round((count / posts.length) * 100)
  }));

  return (
    <div className="ci-container">
      <div className="ci-bottom-grid">
        {/* Stats */}
        <div className="ci-section">
          <div className="ci-section-title">INGESTION STATS</div>
          <div className="stats-cards">
            <div className="ci-stat-card">
              <div className="ci-stat-val cyan">{posts.length}</div>
              <div className="ci-stat-label">Total Posts</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val amber">{posts.filter(p => p.bot_score > 0.4).length}</div>
              <div className="ci-stat-label">Bot Signals</div>
            </div>
            <div className="ci-stat-card">
              <div className="ci-stat-val green">{[...new Set(posts.map(p => p.author_id))].length}</div>
              <div className="ci-stat-label">Unique Authors</div>
            </div>
          </div>
        </div>

        {/* Platform breakdown */}
        <div className="ci-section">
          <div className="ci-section-title">PLATFORM BREAKDOWN</div>
          <div className="platform-bars">
            {platforms.length === 0 ? (
              <div className="mono" style={{ fontSize: 11, color: "var(--text-dim)" }}>Waiting for data...</div>
            ) : (
              platforms.map((p, i) => (
                <div key={i} className="platform-bar-row">
                  <div className="pb-label">{p.name.toUpperCase()}</div>
                  <div className="pb-bar-wrap">
                    <div
                      className="pb-bar"
                      style={{
                        width: `${p.percentage}%`,
                        background: ["var(--cyan)", "var(--teal)", "var(--purple)", "var(--amber)", "var(--green)"][i % 5],
                      }}
                    />
                  </div>
                  <div className="pb-count mono">{p.count}</div>
                  <div className="pb-pct mono">{p.percentage}%</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="ci-section" style={{ marginTop: 20 }}>
        <div className="ci-section-title">LIVE INGESTION FEED</div>
        <div className="raw-intel-list">
          {posts.length === 0 ? (
            <div className="detail-empty">
              <div className="empty-title display">No posts ingested yet</div>
            </div>
          ) : (
            posts.slice(0, 10).map((post, i) => (
              <div key={i} className={`raw-intel-item ${post.bot_score > 0.7 ? "flagged" : ""}`}>
                <div className="ri-source-badge">{post.source}</div>
                <div className="ri-claim">"{post.text.slice(0, 120)}{post.text.length > 120 ? '...' : ''}"</div>
                <div className="ri-metrics">
                  <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>
                    Eng: {post.engagement_score.toFixed(1)} · Bot: {post.bot_score.toFixed(2)}
                  </span>
                  <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>
                    {new Date(post.ingested_at).toLocaleTimeString()}
                  </span>
                </div>
                {post.bot_score > 0.7 && (
                  <span className="tag tag-red" style={{ fontSize: 8 }}>BOT SIGNAL</span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}