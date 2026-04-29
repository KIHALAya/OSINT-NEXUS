import { useState } from "react";
import TopNav from "../components/TopNav";
import "./NewCase.css";

export default function NewCase({ navigate }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    subject: "", age: "", location: "", lastSeen: "", description: "", priority: "high",
  });

  const update = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div className="newcase-page">
      <TopNav navigate={navigate} currentPage="new-case" />
      <div className="newcase-body">
        <div className="newcase-card panel">
          <div className="panel-header">
            <span className="panel-title">NEW INVESTIGATION CASE</span>
            <span className="mono" style={{ fontSize: 10, color: "var(--text-dim)" }}>STEP {step}/3</span>
          </div>

          <div className="newcase-steps">
            {[1,2,3].map(s => (
              <div key={s} className={`nc-step ${s === step ? "active" : s < step ? "done" : ""}`}>
                <div className="nc-step-dot">{s < step ? "✓" : s}</div>
                <span>{["Subject Info", "Upload Assets", "Configure"][s-1]}</span>
              </div>
            ))}
          </div>

          <div className="newcase-form">
            {step === 1 && (
              <div className="form-step animate-in">
                <div className="form-row">
                  <div className="form-field">
                    <label>Subject Name</label>
                    <input value={form.subject} onChange={e => update("subject", e.target.value)} placeholder="Full name" />
                  </div>
                  <div className="form-field">
                    <label>Age</label>
                    <input value={form.age} onChange={e => update("age", e.target.value)} placeholder="Age" type="number" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>Last Known Location</label>
                    <input value={form.location} onChange={e => update("location", e.target.value)} placeholder="City, Region" />
                  </div>
                  <div className="form-field">
                    <label>Last Seen Date</label>
                    <input value={form.lastSeen} onChange={e => update("lastSeen", e.target.value)} type="date" />
                  </div>
                </div>
                <div className="form-field">
                  <label>Description</label>
                  <textarea value={form.description} onChange={e => update("description", e.target.value)}
                    rows={3} placeholder="Physical description, clothing, circumstances..." style={{ resize: "vertical" }} />
                </div>
                <div className="form-field">
                  <label>Priority Level</label>
                  <select value={form.priority} onChange={e => update("priority", e.target.value)}>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                  </select>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="form-step animate-in">
                <div className="upload-zone">
                  <div className="upload-icon">📁</div>
                  <div className="upload-title display">Upload Subject Images</div>
                  <div className="upload-sub">Drag & drop or click to upload. Supports JPG, PNG, HEIC</div>
                  <button className="btn btn-secondary" style={{ marginTop: 12 }}>SELECT FILES</button>
                </div>
                <div className="upload-zone" style={{ marginTop: 14 }}>
                  <div className="upload-icon">📋</div>
                  <div className="upload-title display">Upload Timeline Document</div>
                  <div className="upload-sub">PDF, DOCX, or plain text timeline of events</div>
                  <button className="btn btn-secondary" style={{ marginTop: 12 }}>SELECT FILES</button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="form-step animate-in">
                <div className="config-section">
                  <div className="config-title mono">COMMUNITY MONITORING TARGETS</div>
                  {["Twitter/X", "Reddit", "TikTok", "Facebook", "Forums/Boards"].map((p, i) => (
                    <div key={i} className="config-toggle">
                      <span style={{ fontSize: 13 }}>{p}</span>
                      <div className="toggle active"></div>
                    </div>
                  ))}
                </div>
                <div className="config-section">
                  <div className="config-title mono">AI PROCESSING OPTIONS</div>
                  {["Enable Claim Extraction", "Enable Misinfo Detection", "Enable Bot Detection", "Enable Image Matching"].map((o, i) => (
                    <div key={i} className="config-toggle">
                      <span style={{ fontSize: 13 }}>{o}</span>
                      <div className="toggle active"></div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="newcase-footer">
            {step > 1 && <button className="btn btn-ghost" onClick={() => setStep(s => s - 1)}>← BACK</button>}
            <div style={{ flex: 1 }} />
            {step < 3
              ? <button className="btn btn-primary" onClick={() => setStep(s => s + 1)}>NEXT →</button>
              : <button className="btn btn-primary" onClick={() => navigate("case", { ...form, id: "CASE-2024-0848", status: "active" })}>
                  LAUNCH INVESTIGATION ⚡
                </button>
            }
          </div>
        </div>
      </div>
    </div>
  );
}
