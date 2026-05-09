import { useState, useRef } from "react";
import TopNav from "../components/TopNav";
import "./NewCase.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function NewCase({ navigate }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    subject: "", age: "", location: "", lastSeen: "", description: "", priority: "high",
    images: [], documents: [],
    monitoring: {
      "Twitter/X": true, "Reddit": true, "TikTok": true, "Facebook": true, "Forums/Boards": true
    },
    aiOptions: {
      "Enable Claim Extraction": true, "Enable Misinfo Detection": true, "Enable Bot Detection": true, "Enable Image Matching": true
    }
  });

  const imageInputRef = useRef(null);
  const docInputRef = useRef(null);

  const update = (k, v) => setForm(p => ({ ...p, [k]: v }));
  const toggleConfig = (section, key) => {
    setForm(p => ({
      ...p,
      [section]: { ...p[section], [key]: !p[section][key] }
    }));
  };

  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e, type) => {
    const files = Array.from(e.target.files);
    setForm(p => ({ ...p, [type]: [...p[type], ...files] }));
  };

  const removeFile = (type, index) => {
    setForm(p => ({
      ...p,
      [type]: p[type].filter((_, i) => i !== index)
    }));
  };

  const handleLaunch = async () => {
    setIsLaunching(true);
    setError(null);

    try {
      // 1. Create the case
      const createResp = await fetch(`${API_BASE}/api/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_name: form.subject,
          subject_description: form.description,
          age: parseInt(form.age) || null,
          location: form.location,
          last_seen_date: form.lastSeen,
          priority: form.priority,
        }),
      });

      if (!createResp.ok) throw new Error("Failed to create case");
      const { case_id } = await createResp.json();

      // 2. Upload files if any
      const allFiles = [...form.images, ...form.documents];
      if (allFiles.length > 0) {
        const formData = new FormData();
        allFiles.forEach(file => {
          formData.append("files", file);
        });

        const uploadResp = await fetch(`${API_BASE}/api/cases/${case_id}/upload`, {
          method: "POST",
          body: formData,
        });

        if (!uploadResp.ok) throw new Error("Failed to upload files");
      }

      // 3. Trigger the investigation run
      const runResp = await fetch(`${API_BASE}/api/cases/${case_id}/run`, {
        method: "POST",
      });

      if (!runResp.ok) throw new Error("Failed to start investigation");

      // 3. Navigate to Case View
      navigate("case", { 
        id: case_id, 
        subject: form.subject, 
        age: form.age, 
        location: form.location, 
        lastSeen: form.lastSeen,
        priority: form.priority,
        status: "active" 
      });
    } catch (err) {
      console.error("Launch error:", err);
      setError(err.message);
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <div className="newcase-page">
      <TopNav navigate={navigate} currentPage="new-case" />
      <div className="newcase-body">
        <div className="newcase-card panel">
          <div className="panel-header">
            <span className="panel-title">NEW INVESTIGATION CASE</span>
            <span className="mono" style={{ fontSize: 10, color: "var(--text-dim)" }}>STEP {step}/3</span>
          </div>

          {error && <div className="error-banner" style={{ padding: 10, background: "rgba(255,0,0,0.1)", color: "red", fontSize: 12, marginBottom: 15, border: "1px solid red" }}>Error: {error}</div>}

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
                <input 
                  type="file" 
                  ref={imageInputRef} 
                  style={{ display: "none" }} 
                  multiple 
                  accept="image/*"
                  onChange={(e) => handleFileChange(e, "images")}
                />
                <div className="upload-zone" onClick={() => imageInputRef.current.click()} style={{ cursor: "pointer" }}>
                  <div className="upload-icon">📁</div>
                  <div className="upload-title display">Upload Subject Images</div>
                  <div className="upload-sub">Drag & drop or click to upload. Supports JPG, PNG, HEIC</div>
                  <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={(e) => { e.stopPropagation(); imageInputRef.current.click(); }}>SELECT FILES</button>
                  
                  {form.images.length > 0 && (
                    <div className="file-list" style={{ marginTop: 15, textAlign: "left", width: "100%" }}>
                      {form.images.map((f, i) => (
                        <div key={i} className="file-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.05)", padding: "4px 8px", marginBottom: 4, borderRadius: 4, fontSize: 12 }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                          <button onClick={(e) => { e.stopPropagation(); removeFile("images", i); }} style={{ background: "none", border: "none", color: "#ff4444", cursor: "pointer", fontSize: 14 }}>×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <input 
                  type="file" 
                  ref={docInputRef} 
                  style={{ display: "none" }} 
                  multiple 
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => handleFileChange(e, "documents")}
                />
                <div className="upload-zone" onClick={() => docInputRef.current.click()} style={{ marginTop: 14, cursor: "pointer" }}>
                  <div className="upload-icon">📋</div>
                  <div className="upload-title display">Upload Timeline Document</div>
                  <div className="upload-sub">PDF, DOCX, or plain text timeline of events</div>
                  <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={(e) => { e.stopPropagation(); docInputRef.current.click(); }}>SELECT FILES</button>

                  {form.documents.length > 0 && (
                    <div className="file-list" style={{ marginTop: 15, textAlign: "left", width: "100%" }}>
                      {form.documents.map((f, i) => (
                        <div key={i} className="file-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.05)", padding: "4px 8px", marginBottom: 4, borderRadius: 4, fontSize: 12 }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                          <button onClick={(e) => { e.stopPropagation(); removeFile("documents", i); }} style={{ background: "none", border: "none", color: "#ff4444", cursor: "pointer", fontSize: 14 }}>×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="form-step animate-in">
                <div className="config-section">
                  <div className="config-title mono">COMMUNITY MONITORING TARGETS</div>
                  {Object.keys(form.monitoring).map((p, i) => (
                    <div key={i} className="config-toggle" onClick={() => toggleConfig("monitoring", p)} style={{ cursor: "pointer" }}>
                      <span style={{ fontSize: 13, color: form.monitoring[p] ? "var(--text)" : "var(--text-dim)" }}>{p}</span>
                      <div className={`toggle ${form.monitoring[p] ? "active" : ""}`}></div>
                    </div>
                  ))}
                </div>
                <div className="config-section">
                  <div className="config-title mono">AI PROCESSING OPTIONS</div>
                  {Object.keys(form.aiOptions).map((o, i) => (
                    <div key={i} className="config-toggle" onClick={() => toggleConfig("aiOptions", o)} style={{ cursor: "pointer" }}>
                      <span style={{ fontSize: 13, color: form.aiOptions[o] ? "var(--text)" : "var(--text-dim)" }}>{o}</span>
                      <div className={`toggle ${form.aiOptions[o] ? "active" : ""}`}></div>
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
              : <button className="btn btn-primary" disabled={isLaunching} onClick={handleLaunch}>
                  {isLaunching ? "LAUNCHING..." : "LAUNCH INVESTIGATION ⚡"}
                </button>
            }
          </div>
        </div>
      </div>
    </div>
  );
}
