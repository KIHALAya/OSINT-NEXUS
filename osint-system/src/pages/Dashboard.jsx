import { useState, useEffect } from "react";
import TopNav from "../components/TopNav";
import "./Dashboard.css";

const priorityConfig = {
  critical: { label: "CRITICAL", class: "tag-red" },
  high: { label: "HIGH", class: "tag-amber" },
  medium: { label: "MEDIUM", class: "tag-cyan" },
  low: { label: "LOW", class: "tag-dim" },
  resolved: { label: "RESOLVED", class: "tag-green" },
};

const statusConfig = {
  active: { label: "ACTIVE", color: "var(--green)" },
  monitoring: { label: "MONITORING", color: "var(--amber)" },
  closed: { label: "CLOSED", color: "var(--text-dim)" },
};

export default function Dashboard({ navigate }) {
  const [filter, setFilter] = useState("all");
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/cases")
      .then(r => r.json())
      .then(data => {
        setCases(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Dashboard fetch error:", err);
        setLoading(false);
      });
  }, []);

  const filtered = cases.filter(c => filter === "all" || c.status === filter);

  return (
    <div className="dashboard">
      <TopNav navigate={navigate} currentPage="dashboard" />

      <div className="dashboard-body">
        {/* Hero stats */}
        <div className="dashboard-stats">
          <div className="stat-card">
            <div className="stat-value cyan">{cases.filter(c => c.status === 'active').length}</div>
            <div className="stat-label">Active Cases</div>
            <div className="stat-sub">Across all platforms</div>
          </div>
          <div className="stat-card">
            <div className="stat-value amber">{cases.length}</div>
            <div className="stat-label">Total Cases</div>
            <div className="stat-sub">Since deployment</div>
          </div>
          <div className="stat-card">
            <div className="stat-value green">AI</div>
            <div className="stat-label">Agent Ready</div>
            <div className="stat-sub">Proactive ingestion ON</div>
          </div>
          <div className="stat-card">
            <div className="stat-value red">1.5</div>
            <div className="stat-label">Gemini Flash</div>
            <div className="stat-sub">Video intelligence active</div>
          </div>
        </div>

        {/* Cases section */}
        <div className="cases-section">
          <div className="cases-header">
            <div>
              <h1 className="cases-title display">INVESTIGATION CASES</h1>
              <div className="cases-subtitle mono">Community Intelligence · AI-Verified Leads</div>
            </div>
            <div className="cases-actions">
              <div className="filter-tabs">
                {["all", "active", "monitoring", "closed"].map(f => (
                  <button
                    key={f}
                    className={`filter-tab ${filter === f ? "active" : ""}`}
                    onClick={() => setFilter(f)}
                  >
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
              <button className="btn btn-primary" onClick={() => navigate("new-case")}>
                + NEW CASE
              </button>
            </div>
          </div>

          {loading ? (
            <div className="detail-empty">
              <div className="empty-icon animate-pulse">⬡</div>
              <div className="empty-title display">Loading Active Cases...</div>
            </div>
          ) : (
            <div className="cases-grid">
              {filtered.length === 0 ? (
                <div className="detail-empty" style={{ gridColumn: "1 / -1" }}>
                  <div className="empty-icon">📂</div>
                  <div className="empty-title display">No cases found</div>
                  <div className="empty-sub">Click "+ NEW CASE" to start an investigation.</div>
                </div>
              ) : (
                filtered.map((c, i) => {
                  const priority = priorityConfig[c.priority.toLowerCase()] || priorityConfig.medium;
                  const status = statusConfig[c.status.toLowerCase()] || statusConfig.active;
                  return (
                    <div
                      key={c.id}
                      className="case-card animate-in"
                      style={{ animationDelay: `${i * 0.05}s` }}
                      onClick={() => navigate("case", c)}
                    >
                      <div className="case-card-header">
                        <div className="case-id mono">{c.id}</div>
                        <div className="case-priority">
                          <span className={`tag ${priority.class}`}>{priority.label}</span>
                        </div>
                      </div>

                      <div className="case-subject">
                        <div className="subject-name display">{c.subject}</div>
                        <div className="subject-meta">
                          <span>Age {c.age || 'N/A'}</span>
                          <span>·</span>
                          <span>{c.location || 'Unknown'}</span>
                          <span>·</span>
                          <span>{c.lastSeen || 'N/A'}</span>
                        </div>
                      </div>

                      <div className="case-card-footer" style={{ marginTop: 20 }}>
                        <div className="case-status" style={{ color: status.color }}>
                          <span className="status-indicator" style={{ background: status.color }}></span>
                          {status.label}
                        </div>
                        <span style={{ color: "var(--cyan)", fontSize: 12, fontFamily: "var(--font-mono)" }}>
                          VIEW →
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
