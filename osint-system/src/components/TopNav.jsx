import "./TopNav.css";

export default function TopNav({ navigate, currentPage, caseData }) {
  return (
    <nav className="topnav">
      <div className="topnav-left">
        <div className="topnav-logo" onClick={() => navigate("dashboard")}>
          <div className="logo-mark">
            <span className="logo-hex">⬡</span>
          </div>
          <div className="logo-text">
            <span className="logo-name">SENTINEL</span>
            <span className="logo-sub">OSINT · AI INTELLIGENCE PLATFORM</span>
          </div>
        </div>

        {caseData && (
          <div className="topnav-breadcrumb">
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-item" onClick={() => navigate("dashboard")}>Cases</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-item active">{caseData.id}</span>
          </div>
        )}
      </div>

      <div className="topnav-center">
        <div className="system-status">
          <div className="status-dot active"></div>
          <span className="mono" style={{ fontSize: 11, color: "var(--text-dim)" }}>
            SYSTEM OPERATIONAL
          </span>
        </div>
      </div>

      <div className="topnav-right">
        <div className="nav-time mono">
          {new Date().toISOString().slice(0, 19).replace("T", " ")} UTC
        </div>
        <div className="nav-user">
          <div className="user-avatar">INV</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600 }}>Investigator</div>
            <div style={{ fontSize: 10, color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>L3 CLEARANCE</div>
          </div>
        </div>
      </div>
    </nav>
  );
}
