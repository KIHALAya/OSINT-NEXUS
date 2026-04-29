import { useState } from "react";
import "./KnowledgeGraph.css";

const nodes = [
  { id: "subject", label: "Amira Benali", type: "subject", x: 420, y: 230 },
  { id: "CC-001", label: "Morocco Mall\nSighting", type: "high", x: 180, y: 110 },
  { id: "CC-002", label: "Train Station\nMovement", type: "medium", x: 660, y: 110 },
  { id: "CC-003", label: "Rabat\nSighting", type: "misinfo", x: 150, y: 360 },
  { id: "CC-004", label: "Ain Diab\nBeach", type: "low", x: 680, y: 360 },
  { id: "E-001", label: "Mall CCTV\nRequested", type: "evidence", x: 50, y: 40 },
  { id: "E-002", label: "User Photo\n(Unverified)", type: "evidence-unverified", x: 70, y: 200 },
  { id: "CONTRA-001", label: "2022 Image\nReuse", type: "contradiction", x: 50, y: 420 },
];

const edges = [
  { from: "subject", to: "CC-001", label: "possible sighting", type: "sighting" },
  { from: "subject", to: "CC-002", label: "possible sighting", type: "sighting" },
  { from: "subject", to: "CC-003", label: "false claim", type: "misinfo" },
  { from: "subject", to: "CC-004", label: "low signal", type: "low" },
  { from: "CC-001", to: "E-001", label: "verified by", type: "evidence" },
  { from: "CC-001", to: "E-002", label: "supported by", type: "evidence" },
  { from: "CC-003", to: "CONTRA-001", label: "contradicted by", type: "contradiction" },
];

const nodeConfig = {
  subject: { fill: "rgba(0,200,255,0.15)", stroke: "rgba(0,200,255,0.8)", r: 36, labelColor: "#00c8ff" },
  high: { fill: "rgba(0,230,118,0.1)", stroke: "rgba(0,230,118,0.6)", r: 30, labelColor: "#00e676" },
  medium: { fill: "rgba(255,184,0,0.1)", stroke: "rgba(255,184,0,0.6)", r: 26, labelColor: "#ffb800" },
  misinfo: { fill: "rgba(255,59,92,0.1)", stroke: "rgba(255,59,92,0.6)", r: 26, labelColor: "#ff3b5c" },
  low: { fill: "rgba(100,150,190,0.08)", stroke: "rgba(100,150,190,0.3)", r: 22, labelColor: "#7ab8d4" },
  evidence: { fill: "rgba(156,107,255,0.1)", stroke: "rgba(156,107,255,0.5)", r: 20, labelColor: "#9c6bff" },
  "evidence-unverified": { fill: "rgba(255,184,0,0.08)", stroke: "rgba(255,184,0,0.3)", r: 18, labelColor: "#ffb800" },
  contradiction: { fill: "rgba(255,59,92,0.08)", stroke: "rgba(255,59,92,0.4)", r: 20, labelColor: "#ff3b5c" },
};

const edgeConfig = {
  sighting: { stroke: "rgba(0,200,255,0.4)", strokeDash: "none" },
  misinfo: { stroke: "rgba(255,59,92,0.4)", strokeDash: "5,4" },
  low: { stroke: "rgba(100,150,190,0.2)", strokeDash: "3,6" },
  evidence: { stroke: "rgba(156,107,255,0.3)", strokeDash: "none" },
  contradiction: { stroke: "rgba(255,59,92,0.5)", strokeDash: "8,3" },
};

function getNodeById(id) {
  return nodes.find(n => n.id === id);
}

export default function KnowledgeGraph() {
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState(null);

  const selectedNode = selected ? nodes.find(n => n.id === selected) : null;

  return (
    <div className="graph-container">
      <div className="graph-header">
        <div>
          <h2 className="display" style={{ fontSize: 16, letterSpacing: "0.1em" }}>
            KNOWLEDGE GRAPH
          </h2>
          <div className="mono" style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 2 }}>
            Claim clusters · Evidence chains · Contradictions
          </div>
        </div>
        <div className="graph-legend">
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--cyan)" }}></span> Subject</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--green)" }}></span> High Signal</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--amber)" }}></span> Medium</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--red)" }}></span> Misinfo</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--purple)" }}></span> Evidence</div>
        </div>
      </div>

      <div className="graph-layout">
        <div className="graph-svg-wrap">
          <svg viewBox="0 0 760 480" className="graph-svg">
            <defs>
              <filter id="glow-cyan">
                <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
                <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <filter id="glow-green">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <marker id="arrow-cyan" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
                <path d="M0,0 L0,6 L6,3 z" fill="rgba(0,200,255,0.5)" />
              </marker>
              <marker id="arrow-red" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
                <path d="M0,0 L0,6 L6,3 z" fill="rgba(255,59,92,0.5)" />
              </marker>
              <marker id="arrow-purple" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
                <path d="M0,0 L0,6 L6,3 z" fill="rgba(156,107,255,0.4)" />
              </marker>
            </defs>

            {/* Grid */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(0,100,160,0.06)" strokeWidth="0.5"/>
            </pattern>
            <rect width="760" height="480" fill="url(#grid)" />

            {/* Edges */}
            {edges.map((edge, i) => {
              const from = getNodeById(edge.from);
              const to = getNodeById(edge.to);
              if (!from || !to) return null;
              const cfg = edgeConfig[edge.type] || edgeConfig.sighting;
              const mx = (from.x + to.x) / 2;
              const my = (from.y + to.y) / 2;
              const markerEnd = edge.type === "evidence" || edge.type === "contradiction"
                ? edge.type === "contradiction" ? "url(#arrow-red)" : "url(#arrow-purple)"
                : "url(#arrow-cyan)";

              return (
                <g key={i}>
                  <line
                    x1={from.x} y1={from.y}
                    x2={to.x} y2={to.y}
                    stroke={cfg.stroke}
                    strokeWidth={1.5}
                    strokeDasharray={cfg.strokeDash === "none" ? "none" : cfg.strokeDash}
                    markerEnd={markerEnd}
                  />
                  <text
                    x={mx} y={my - 4}
                    textAnchor="middle"
                    fill="rgba(100,150,190,0.5)"
                    fontSize="7"
                    fontFamily="'Share Tech Mono'"
                    letterSpacing="0.05em"
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map((node) => {
              const cfg = nodeConfig[node.type] || nodeConfig.low;
              const isHovered = hovered === node.id;
              const isSelected = selected === node.id;
              const r = cfg.r + (isHovered || isSelected ? 4 : 0);
              const lines = node.label.split("\n");
              const filterAttr = isSelected || isHovered
                ? node.type === "subject" ? "url(#glow-cyan)" : "url(#glow-green)"
                : undefined;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHovered(node.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => setSelected(selected === node.id ? null : node.id)}
                  filter={filterAttr}
                >
                  <circle
                    r={r}
                    fill={cfg.fill}
                    stroke={cfg.stroke}
                    strokeWidth={isSelected ? 2 : 1.5}
                  />
                  {lines.map((line, li) => (
                    <text
                      key={li}
                      textAnchor="middle"
                      dy={lines.length > 1 ? (li === 0 ? -6 : 7) : 4}
                      fill={cfg.labelColor}
                      fontSize={node.type === "subject" ? 10 : 8}
                      fontFamily="'Rajdhani', sans-serif"
                      fontWeight="600"
                      letterSpacing="0.04em"
                    >
                      {line}
                    </text>
                  ))}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Side info panel */}
        <div className="graph-info-panel panel">
          {selectedNode ? (
            <div className="graph-node-detail animate-in">
              <div className="panel-header">
                <span className="panel-title">{selectedNode.id}</span>
                <span
                  className="mono"
                  style={{ fontSize: 9, color: "var(--text-dim)", cursor: "pointer" }}
                  onClick={() => setSelected(null)}
                >
                  ✕ CLOSE
                </span>
              </div>
              <div style={{ padding: 14 }}>
                <div className="node-type-badge" data-type={selectedNode.type}>
                  {selectedNode.type.toUpperCase().replace("-", " ")}
                </div>
                <div className="display" style={{ fontSize: 16, fontWeight: 700, margin: "8px 0 4px" }}>
                  {selectedNode.label.replace("\n", " ")}
                </div>

                {selectedNode.type === "subject" && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    Primary investigation subject. Connected to all active claim clusters.
                  </div>
                )}
                {selectedNode.type === "high" && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    High-signal cluster. 47 mentions, final score 0.67. Primary lead.
                  </div>
                )}
                {selectedNode.type === "misinfo" && (
                  <div style={{ fontSize: 11, color: "var(--red-dim)" }}>
                    ⚠ Flagged misinformation. Image reuse detected. Bot amplification confirmed.
                  </div>
                )}
                {selectedNode.type === "evidence" && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    Verified evidence supporting the Morocco Mall claim cluster.
                  </div>
                )}
                {selectedNode.type === "contradiction" && (
                  <div style={{ fontSize: 11, color: "var(--red-dim)" }}>
                    Critical contradiction. Photo traced to 2022 unrelated case.
                  </div>
                )}

                <div style={{ marginTop: 12 }}>
                  <div className="section-mini-label">Connected Edges</div>
                  {edges
                    .filter(e => e.from === selectedNode.id || e.to === selectedNode.id)
                    .map((e, i) => (
                      <div key={i} className="edge-item">
                        <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>
                          {e.from === selectedNode.id ? `→ ${e.to}` : `← ${e.from}`}
                        </span>
                        <span style={{ fontSize: 10, color: "var(--text-secondary)" }}>{e.label}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: 16 }}>
              <div className="panel-title" style={{ marginBottom: 10 }}>GRAPH LEGEND</div>
              <div className="graph-legend-full">
                {Object.entries(nodeConfig).map(([type, cfg]) => (
                  <div key={type} className="legend-full-item">
                    <svg width="14" height="14">
                      <circle cx="7" cy="7" r="6" fill={cfg.fill} stroke={cfg.stroke} strokeWidth="1.5" />
                    </svg>
                    <span style={{ fontSize: 10, color: "var(--text-secondary)", textTransform: "capitalize" }}>
                      {type.replace("-", " ")}
                    </span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16 }}>
                <div className="panel-title" style={{ marginBottom: 8 }}>EDGE TYPES</div>
                {[
                  { label: "Possible sighting", color: "rgba(0,200,255,0.5)", dash: "none" },
                  { label: "Evidence chain", color: "rgba(156,107,255,0.5)", dash: "none" },
                  { label: "Contradiction", color: "rgba(255,59,92,0.5)", dash: "8,3" },
                  { label: "Misinformation", color: "rgba(255,59,92,0.4)", dash: "5,4" },
                ].map((e, i) => (
                  <div key={i} className="edge-legend-item">
                    <svg width="32" height="10">
                      <line x1="2" y1="5" x2="30" y2="5"
                        stroke={e.color} strokeWidth="1.5"
                        strokeDasharray={e.dash === "none" ? undefined : e.dash}
                      />
                    </svg>
                    <span style={{ fontSize: 10, color: "var(--text-secondary)" }}>{e.label}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, fontSize: 10, color: "var(--text-dim)" }}>
                Click any node to see details and connections
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
