import { useState, useEffect } from "react";
import TopNav from "../components/TopNav";
import ClaimClusters from "../components/ClaimClusters";
import Leads from "../components/Leads";
import KnowledgeGraph from "../components/KnowledgeGraph";
import AgentChat from "../components/AgentChat";
import CommunityIntelligence from "../components/CommunityIntelligence";
import { mockCase, mockStats } from "../data/mockData";
import "./CaseView.css";

const TABS = [
  { id: "clusters", label: "CLAIM CLUSTERS", icon: "⬡" },
  { id: "leads", label: "LEADS", icon: "⚡" },
  { id: "graph", label: "KNOWLEDGE GRAPH", icon: "🕸" },
  { id: "chat", label: "AGENT CHAT", icon: "🤖" },
  { id: "pipeline", label: "INTELLIGENCE PIPELINE", icon: "📡" },
];

export default function CaseView({ navigate, caseData }) {
  const [activeTab, setActiveTab] = useState("clusters");
  const cas = caseData || mockCase;
  const caseId = cas.id;

  const [leads, setLeads] = useState([]);
  const [claims, setClaims] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!caseId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [leadsResp, claimsResp, postsResp, clustersResp] = await Promise.all([
          fetch(`http://localhost:8000/api/cases/${caseId}/leads`),
          fetch(`http://localhost:8000/api/cases/${caseId}/claims`),
          fetch(`http://localhost:8000/api/cases/${caseId}/posts`),
          fetch(`http://localhost:8000/api/cases/${caseId}/clusters`)
        ]);

        if (!leadsResp.ok || !claimsResp.ok || !postsResp.ok || !clustersResp.ok) {
          throw new Error("Failed to fetch case data");
        }

        const [leadsData, claimsData, postsData, clustersData] = await Promise.all([
          leadsResp.json(),
          claimsResp.json(),
          postsResp.json(),
          clustersResp.json()
        ]);

        setLeads(leadsData);
        setClaims(claimsData);
        setPosts(postsData);
        setClusters(clustersData);
      } catch (err) {
        console.error("Fetch error:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Poll every 30 seconds for updates during investigation
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [caseId]);

  // Derive stats from real data
  const stats = {
    totalPosts: posts.length,
    clustersFormed: clusters.length,
    highSignalLeads: leads.filter(l => l.priority === "urgent" || l.priority === "high").length,
    misinfoFiltered: 0, // Not yet tracked in DB
    processingSteps: loading && posts.length === 0 ? [{ step: "Fetching data...", status: "pending" }] : [
      { step: "Data Ingested", status: posts.length > 0 ? "done" : "pending" },
      { step: "Claims Extracted", status: claims.length > 0 ? "done" : "pending" },
      { step: "Clustering Complete", status: clusters.length > 0 ? "done" : "pending" }
    ]
  };

  return (
    <div className="case-view">
      <TopNav navigate={navigate} currentPage="case" caseData={cas} />

      <div className="case-body">
        {/* Case header */}
        <div className="case-header-bar">
          <div className="case-subject-info">
            <div className="subject-avatar">
              {cas.subject?.split(" ").map(w => w[0]).join("").slice(0, 2)}
            </div>
            <div>
              <div className="case-subject-name display">{cas.subject}</div>
              <div className="case-subject-meta">
                <span className="mono" style={{ fontSize: 10, color: "var(--text-dim)" }}>{cas.id}</span>
                <span>·</span>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>Age {cas.age}</span>
                <span>·</span>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{cas.location}</span>
                <span>·</span>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>Last seen {cas.lastSeen}</span>
              </div>
            </div>
          </div>

          <div className="case-quick-stats">
            <div className="cqs-item">
              <span className="cqs-val cyan">{stats.totalPosts}</span>
              <span className="cqs-label">Posts Ingested</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val amber">{stats.clustersFormed}</span>
              <span className="cqs-label">Clusters</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val green">{stats.highSignalLeads}</span>
              <span className="cqs-label">Active Leads</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val red">{stats.misinfoFiltered}</span>
              <span className="cqs-label">Misinfo Blocked</span>
            </div>
          </div>

          <div className="case-priority-badge">
            <span className={`tag tag-${cas.priority === 'critical' ? 'red' : 'amber'}`} style={{ fontSize: 11, padding: "4px 10px" }}>
              ● {cas.priority?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Pipeline status mini */}
        <div className="pipeline-mini">
          {stats.processingSteps.map((step, i) => (
            <div key={i} className="pm-step">
              <div className={`pm-dot ${step.status}`}></div>
              <span className="pm-label">{step.step}</span>
            </div>
          ))}
        </div>

        {/* Tab navigation */}
        <div className="tab-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.id === "clusters" && clusters.length > 0 && (
                <span className="tab-badge">{clusters.length}</span>
              )}
              {tab.id === "leads" && leads.length > 0 && (
                <span className={`tab-badge ${leads.some(l => l.priority === 'urgent') ? 'urgent' : ''}`}>{leads.length}</span>
              )}
              {tab.id === "chat" && (
                <span className="tab-badge active-badge">LIVE</span>
              )}
            </button>
          ))}
        </div>

        {error && <div className="error-banner" style={{ margin: "20px 0", padding: 15, background: "rgba(255,0,0,0.1)", border: "1px solid red", color: "red" }}>Error: {error}</div>}

        {/* Tab content */}
        <div className="tab-content animate-in" key={activeTab}>
          {activeTab === "clusters" && <ClaimClusters clusters={clusters} claims={claims} loading={loading} />}
          {activeTab === "leads" && <Leads leads={leads} loading={loading} />}
          {activeTab === "graph" && <KnowledgeGraph caseId={caseId} />}
          {activeTab === "chat" && <AgentChat caseId={caseId} />}
          {activeTab === "pipeline" && <CommunityIntelligence posts={posts} />}
        </div>
      </div>
    </div>
  );
}
