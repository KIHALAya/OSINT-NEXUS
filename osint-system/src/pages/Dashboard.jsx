import { useState } from "react";
import TopNav from "../components/TopNav";
import "./Dashboard.css";

const mockCases = [
  {
    id: "CASE-2024-0847",
    subject: "Amira Benali",
    age: 14,
    lastSeen: "2024-01-15",
    location: "Casablanca",
    status: "active",
    priority: "critical",
    leads: 2,
    posts: 163,
    progress: 67,
  },
  {
    id: "CASE-2024-0831",
    subject: "Karim Idrissi",
    age: 17,
    lastSeen: "2024-01-10",
    location: "Rabat",
    status: "active",
    priority: "high",
    leads: 1,
    posts: 84,
    progress: 42,
  },
  {
    id: "CASE-2024-0812",
    subject: "Fatima Zohra El Amrani",
    age: 22,
    lastSeen: "2024-01-05",
    location: "Marrakech",
    status: "monitoring",
    priority: "medium",
    leads: 3,
    posts: 210,
    progress: 55,
  },
  {
    id: "CASE-2023-1190",
    subject: "Omar Tazi",
    age: 35,
    lastSeen: "2023-12-20",
    location: "Tangier",
    status: "closed",
    priority: "resolved",
    leads: 5,
    posts: 420,
    progress: 100,
  },
];

const priorityConfig = {
  critical: { label: "CRITICAL", class: "tag-red" },
  high: { label: "HIGH", class: "tag-amber" },
  medium: { label: "MEDIUM", class: "tag-cyan" },
  resolved: { label: "RESOLVED", class: "tag-green" },
};

const statusConfig = {
  active: { label: "ACTIVE", color: "var(--green)" },
  monitoring: { label: "MONITORING", color: "var(--amber)" },
  closed: { label: "CLOSED", color: "var(--text-dim)" },
};

export default function Dashboard({ navigate }) {
  const [filter, setFilter] = useState("all");

  const filtered = mockCases.filter(c => filter === "all" || c.status === filter);

  return (
    <div className="dashboard">
      <TopNav navigate={navigate} currentPage="dashboard" />

      <div className="dashboard-body">
        {/* Hero stats */}
        <div className="dashboard-stats">
          <div className="stat-card">
            <div className="stat-value cyan">4</div>
            <div className="stat-label">Active Cases</div>
            <div className="stat-sub">↑ 2 this week</div>
          </div>
          <div className="stat-card">
            <div className="stat-value amber">877</div>
            <div className="stat-label">Posts Ingested</div>
            <div className="stat-sub">Last 24h: 163</div>
          </div>
          <div className="stat-card">
            <div className="stat-value green">11</div>
            <div className="stat-label">Active Leads</div>
            <div className="stat-sub">3 high-priority</div>
          </div>
          <div className="stat-card">
            <div className="stat-value red">7</div>
            <div className="stat-label">Misinfo Filtered</div>
            <div className="stat-sub">Prevented spread</div>
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

          <div className="cases-grid">
            {filtered.map((c, i) => {
              const priority = priorityConfig[c.priority];
              const status = statusConfig[c.status];
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
                      <span>Age {c.age}</span>
                      <span>·</span>
                      <span>{c.location}</span>
                      <span>·</span>
                      <span>Last seen {c.lastSeen}</span>
                    </div>
                  </div>

                  <div className="case-metrics">
                    <div className="metric">
                      <div className="metric-value" style={{ color: "var(--cyan)" }}>{c.posts}</div>
                      <div className="metric-label">POSTS</div>
                    </div>
                    <div className="metric">
                      <div className="metric-value" style={{ color: "var(--green)" }}>{c.leads}</div>
                      <div className="metric-label">LEADS</div>
                    </div>
                    <div className="metric">
                      <div className="metric-value" style={{ color: "var(--amber)" }}>{c.progress}%</div>
                      <div className="metric-label">CONFIDENCE</div>
                    </div>
                  </div>

                  <div className="case-progress">
                    <div className="score-bar">
                      <div
                        className="score-bar-fill"
                        style={{
                          width: `${c.progress}%`,
                          background: c.progress > 60 ? "var(--green)" : c.progress > 40 ? "var(--amber)" : "var(--cyan)",
                        }}
                      />
                    </div>
                  </div>

                  <div className="case-card-footer">
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
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
