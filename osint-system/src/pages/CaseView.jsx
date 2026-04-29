import { useState } from "react";
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
              <span className="cqs-val cyan">{mockStats.totalPosts}</span>
              <span className="cqs-label">Posts Ingested</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val amber">{mockStats.clustersFormed}</span>
              <span className="cqs-label">Clusters</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val green">{mockStats.highSignalLeads}</span>
              <span className="cqs-label">Active Leads</span>
            </div>
            <div className="cqs-item">
              <span className="cqs-val red">{mockStats.misinfoFiltered}</span>
              <span className="cqs-label">Misinfo Blocked</span>
            </div>
          </div>

          <div className="case-priority-badge">
            <span className="tag tag-red" style={{ fontSize: 11, padding: "4px 10px" }}>
              ● {cas.priority?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Pipeline status mini */}
        <div className="pipeline-mini">
          {mockStats.processingSteps.map((step, i) => (
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
              {tab.id === "clusters" && (
                <span className="tab-badge">4</span>
              )}
              {tab.id === "leads" && (
                <span className="tab-badge urgent">2</span>
              )}
              {tab.id === "chat" && (
                <span className="tab-badge active-badge">LIVE</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="tab-content animate-in" key={activeTab}>
          {activeTab === "clusters" && <ClaimClusters />}
          {activeTab === "leads" && <Leads />}
          {activeTab === "graph" && <KnowledgeGraph />}
          {activeTab === "chat" && <AgentChat />}
          {activeTab === "pipeline" && <CommunityIntelligence />}
        </div>
      </div>
    </div>
  );
}
