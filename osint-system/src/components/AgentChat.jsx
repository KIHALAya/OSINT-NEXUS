import { useState, useRef, useEffect } from "react";
import { mockChatHistory, mockClaimClusters } from "../data/mockData";
import "./AgentChat.css";

const quickPrompts = [
  "What is the most credible crowd hypothesis?",
  "Show me all high-signal clusters",
  "Why is the Rabat sighting misinformation?",
  "What action should I take now?",
  "Summarize all evidence chains",
  "Compare crowd score vs AI verification",
];

export default function AgentChat() {
  const [messages, setMessages] = useState(mockChatHistory);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = (text) => {
    const userMsg = text || input.trim();
    if (!userMsg) return;

    setInput("");
    setMessages(prev => [...prev, {
      role: "user",
      content: userMsg,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    }]);

    setIsTyping(true);

    // Simulated AI response
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: generateResponse(userMsg),
        timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      }]);
    }, 1200 + Math.random() * 800);
  };

  return (
    <div className="chat-container">
      <div className="chat-layout">
        {/* Chat main */}
        <div className="chat-main panel">
          <div className="panel-header">
            <div className="chat-status">
              <div className="status-dot active"></div>
              <span className="panel-title">OSINT INTELLIGENCE AGENT</span>
            </div>
            <div className="chat-meta mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>
              Case CASE-2024-0847 · Context loaded · 163 posts analyzed
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}

            {isTyping && (
              <div className="chat-message assistant">
                <div className="msg-avatar agent">AI</div>
                <div className="msg-bubble typing">
                  <div className="typing-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="chat-input-area">
            <div className="quick-prompts-row">
              {quickPrompts.slice(0, 3).map((p, i) => (
                <button key={i} className="quick-prompt" onClick={() => sendMessage(p)}>
                  {p}
                </button>
              ))}
            </div>
            <div className="chat-input-row">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendMessage()}
                placeholder="Ask about claims, evidence, misinformation..."
                className="chat-input"
              />
              <button
                className="btn btn-primary"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isTyping}
              >
                SEND
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar: Context */}
        <div className="chat-sidebar">
          <div className="panel" style={{ marginBottom: 14 }}>
            <div className="panel-header">
              <span className="panel-title">ACTIVE CONTEXT</span>
            </div>
            <div style={{ padding: 12 }}>
              <div className="context-case">
                <div className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>CASE</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                  Amira Benali
                </div>
                <div className="tag tag-red" style={{ display: "inline-flex" }}>CRITICAL</div>
              </div>
              <div className="divider" style={{ margin: "10px 0" }} />
              <div className="context-stats">
                <div className="context-stat">
                  <span className="cs-val" style={{ color: "var(--cyan)" }}>4</span>
                  <span className="cs-label">clusters</span>
                </div>
                <div className="context-stat">
                  <span className="cs-val" style={{ color: "var(--green)" }}>2</span>
                  <span className="cs-label">leads</span>
                </div>
                <div className="context-stat">
                  <span className="cs-val" style={{ color: "var(--red)" }}>1</span>
                  <span className="cs-label">misinfo</span>
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">QUICK QUERIES</span>
            </div>
            <div style={{ padding: 10 }}>
              {quickPrompts.map((p, i) => (
                <button
                  key={i}
                  className="quick-prompt-full"
                  onClick={() => sendMessage(p)}
                >
                  <span className="qp-arrow">›</span>
                  <span>{p}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="chat-message system">
        <div className="system-msg">
          <span className="mono" style={{ fontSize: 9, color: "var(--cyan-dim)" }}>⬡ SYSTEM</span>
          <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{message.content}</span>
          <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>{message.timestamp}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-message ${isUser ? "user" : "assistant"}`}>
      {!isUser && <div className="msg-avatar agent">AI</div>}
      <div className="msg-bubble-wrap">
        <div className={`msg-bubble ${isUser ? "user" : "assistant"}`}>
          <FormattedMessage content={message.content} />
        </div>
        {message.relatedClaim && (
          <div className="msg-claim-tag">
            <span className="mono" style={{ fontSize: 9, color: "var(--text-dim)" }}>RELATED:</span>
            <span className="tag tag-cyan" style={{ fontSize: 9 }}>{message.relatedClaim}</span>
          </div>
        )}
        <div className="msg-time mono">{message.timestamp}</div>
      </div>
      {isUser && <div className="msg-avatar user">INV</div>}
    </div>
  );
}

function FormattedMessage({ content }) {
  // Simple markdown-like formatting
  const lines = content.split("\n");
  return (
    <div className="msg-content">
      {lines.map((line, i) => {
        if (line.startsWith("**") && line.endsWith("**")) {
          return <strong key={i} style={{ color: "var(--cyan)", fontWeight: 700 }}>{line.slice(2, -2)}</strong>;
        }
        // Process inline bold
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <span key={i}>
            {parts.map((part, j) => {
              if (part.startsWith("**") && part.endsWith("**")) {
                return <strong key={j} style={{ color: "var(--text-primary)", fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
              }
              return part;
            })}
            {i < lines.length - 1 && <br />}
          </span>
        );
      })}
    </div>
  );
}

function generateResponse(input) {
  const lower = input.toLowerCase();

  if (lower.includes("most credible") || lower.includes("best hypothesis")) {
    return "The **Morocco Mall Sighting** (CC-001) is the highest-confidence hypothesis with a final score of **0.67**.\n\n47 independent mentions from 31 unique accounts across 4 platforms. No significant contradictions. Temporal consistency confirmed.\n\n**Crowd Score:** 0.72 | **AI Verification:** 0.61\n\n⚡ Recommended action: Request CCTV footage for Jan 15, 14:00–18:00 immediately.";
  }

  if (lower.includes("misinfo") || lower.includes("rabat") || lower.includes("false")) {
    return "The **Rabat Sighting** (CC-003) was flagged as misinformation for two reasons:\n\n🚨 **Image Reuse:** The circulating photo was traced to Case #CASE-2022-0341 — an unrelated 2022 case.\n\n🤖 **Bot Amplification:** 75% of 89 sharing accounts were created under 30 days ago — coordinated inauthentic behavior.\n\nDespite highest raw engagement, this cluster has the lowest final score (0.14). It has been excluded from active leads.";
  }

  if (lower.includes("action") || lower.includes("next") || lower.includes("do now")) {
    return "**Recommended immediate actions:**\n\n1. **URGENT** — Contact Morocco Mall security, request CCTV Jan 15, 14:00–18:00 (Lead LEAD-001, confidence 67%)\n\n2. **MEDIUM** — Cross-check Casa-Port timestamp with Mall sighting. The 2h gap is suspicious but possible (Lead LEAD-002)\n\n3. **LOW** — Monitor Ain Diab cluster (CC-004) for corroborating posts. Currently only 9 mentions.\n\n4. **COMPLETED** — Rabat cluster deprioritized and marked as misinformation.";
  }

  if (lower.includes("high-signal") || lower.includes("high signal") || lower.includes("clusters")) {
    const high = mockClaimClusters.filter(c => c.status === "high-signal" || c.status === "medium-signal");
    return `There are **${high.length} active signal clusters:**\n\n🟢 **CC-001 Morocco Mall** — Final score 0.67 (HIGH)\n🟡 **CC-002 Train Station** — Final score 0.44 (MEDIUM)\n🔵 **CC-004 Ain Diab Beach** — Final score 0.31 (LOW)\n🔴 **CC-003 Rabat** — EXCLUDED (misinformation)\n\nFocus investigative resources on CC-001 first, then CC-002.`;
  }

  if (lower.includes("evidence")) {
    return "**Active evidence chains:**\n\n**CC-001 (Morocco Mall):**\n• Mall CCTV request initiated ✓\n• User-submitted photo — partial match (unverified)\n• 47 corroborating posts from 31 unique sources\n\n**CC-002 (Train Station):**\n• Station records request pending\n• No visual evidence yet\n• Timestamp conflict with CC-001 needs resolution\n\nAll evidence is traceable from community posts through clustering to verification.";
  }

  if (lower.includes("crowd") || lower.includes("score") || lower.includes("verification")) {
    return "**Scoring methodology breakdown:**\n\n**Crowd Score** (0–1): Based on frequency, source diversity, recency, engagement, and anti-bot signals.\n\n**AI Verification Score** (0–1): OSINT search confirmation, image matching, consistency analysis, contradiction detection.\n\n**Final Score** = weighted composite of both.\n\nThis approach ensures we leverage collective human intelligence while using AI as a filter and verifier — not a replacement.";
  }

  return "I've analyzed your query against the active case context. Based on current cluster data, the **Morocco Mall sighting** remains the highest-priority lead. Would you like me to dig deeper into any specific cluster, evidence chain, or generate a report for law enforcement?";
}
