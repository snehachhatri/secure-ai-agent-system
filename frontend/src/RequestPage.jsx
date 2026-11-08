import { useState } from "react";
import "./RequestPage.css";

const API = "http://127.0.0.1:8000";

function DataView({ data }) {
  if (Array.isArray(data)) {
    if (!data.length) return <p className="empty-data">No matching records.</p>;
    const columns = [...new Set(data.flatMap((row) => Object.keys(row || {})))];
    return (
      <div className="result-table-wrap">
        <table className="result-table">
          <thead><tr>{columns.map((key) => <th key={key}>{key.replaceAll("_", " ")}</th>)}</tr></thead>
          <tbody>
            {data.map((row, index) => (
              <tr key={index}>{columns.map((key) => <td key={key}>{String(row?.[key] ?? "—")}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (data && typeof data === "object") {
    return <pre className="result-json">{JSON.stringify(data, null, 2)}</pre>;
  }
  return <p>{String(data ?? "")}</p>;
}

function RequestPage() {
  const [request, setRequest] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const role = localStorage.getItem("role") || "student";
  const username = localStorage.getItem("username") || "User";
  const roleContent = {
    student: {
      title: "Your student requests",
      description: "Check your own marks, fees, and attendance. The policy engine protects other students’ records.",
      samples: ["Show my marks", "Show my fees", "Show my attendance", "Show my marks and fees"],
    },
    faculty: {
      title: "Your faculty requests",
      description: "Review marks for subjects assigned to you. Updates are checked against subject ownership and result status.",
      samples: ["Show DBMS marks", "Show Python marks", "Show Data Structures marks"],
    },
    hod: {
      title: "Your department requests",
      description: "Review students and marks within your department. The policy engine enforces your department boundary.",
      samples: ["List failing students in my department", "Show marks in my department"],
    },
  };
  const page = roleContent[role] || roleContent.student;

  const handleRequest = async (e) => {
    e.preventDefault();
    if (!request.trim()) {
      setResult({ type: "error", message: "Please enter a request before sending." });
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API}/request`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ request_text: request }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed.");
      setResult({ ...data, type: data.decision || "error" });
    } catch (error) {
      setResult({ type: "error", message: error.message || "Unable to connect to server." });
    } finally {
      setLoading(false);
    }
  };

  const useQuickRequest = (text) => {
    setRequest(text);
    setResult(null);
  };

  const handleLogout = () => {
    localStorage.clear();
    window.location.reload();
  };

  const isBlocked = result?.type === "blocked";
  const decisionTone = result?.type === "allowed" ? "decision-allowed"
    : isBlocked ? "decision-blocked" : "decision-neutral";
  const decisionGlyph = result?.type === "allowed" ? "✓" : isBlocked ? "×" : "!";
  const showDecision = result && result.type !== "error";

  return (
    <div className="request-page">
      <div className="request-orb orb-one" />
      <div className="request-orb orb-two" />
      <div className="request-grid" />

      <header className="request-header">
        <div className="brand">
          <div className="brand-shield">🛡️</div>
          <div><h2>Secure AI Agent</h2><p>ACCESS CONTROL SYSTEM</p></div>
        </div>
        <div className="header-status"><span className="status-dot" />SYSTEM SECURE</div>
        <div className="profile">
          <div className="profile-avatar">👤</div>
          <div>
            <strong>{username}</strong>
            <span>{role}</span>
          </div>
          <button className="request-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="request-main">
        <section className="page-heading">
          <div className="heading-icon">🤖</div>
          <div>
            <div className="eyebrow"><span />SECURE REQUEST GATEWAY</div>
            <h1>{page.title}</h1>
            <p>{page.description}</p>
          </div>
        </section>

        <section className="request-card">
          <div className="card-top">
            <div><div className="card-label"><span className="pulse-dot" />NEW REQUEST</div><h2>Describe your request</h2></div>
            <div className="request-id">SECURE GATEWAY<strong>POLICY + DATA</strong></div>
          </div>
          <form onSubmit={handleRequest}>
            <div className="textarea-wrapper">
              <div className="textarea-icon">✦</div>
              <textarea
                value={request}
                onChange={(e) => { setRequest(e.target.value); setResult(null); }}
                placeholder="Example: Show my marks"
                maxLength={2000}
              />
              <div className="character-count">{request.length} / 2000 characters</div>
            </div>

            <div className="quick-section">
              <span className="quick-title">TRY A SAMPLE REQUEST</span>
              <div className="quick-buttons">
                {page.samples.map((item) => (
                  <button type="button" key={item} onClick={() => useQuickRequest(item)}>{item}</button>
                ))}
              </div>
            </div>

            <div className="security-info">
              <div className="security-icon">🔐</div>
              <div><strong>Zero-Trust Verification</strong><p>Every action is checked against your role and data permissions.</p></div>
              <div className="secure-badge">SECURE</div>
            </div>
            <button className="send-button" type="submit" disabled={loading}>
              <span>🚀</span>{loading ? "Checking request..." : "Send Secure Request"}<span className="button-arrow">→</span>
            </button>
          </form>
        </section>

        {showDecision && (
          <section className={`decision-card ${decisionTone}`}>
            <div className="decision-icon">{decisionGlyph}</div>
            <div className="decision-content">
              <span className="decision-label">REQUEST DECISION</span>
              <h2>{result.message || `Request ${result.decision}`}</h2>
              <p>Overall decision: <strong>{String(result.decision).toUpperCase()}</strong></p>
            </div>
            <div className="decision-status">{String(result.decision).toUpperCase()}</div>
          </section>
        )}

        {result?.results?.length > 0 && (
          <section className="action-results">
            <h2>Action results</h2>
            {result.results.map((item, index) => (
              <article className="action-result" key={`${item.action}-${index}`}>
                <div className="action-result-heading">
                  <strong>{item.action}</strong>
                  <span className={`badge badge-${item.decision}`}>{String(item.decision).toUpperCase()}</span>
                </div>
                {item.reason && <p className="decision-reason">{item.reason}</p>}
                {item.message && <p>{item.message}</p>}
                {item.old_value !== undefined && <p>Old value: {String(item.old_value)} · New value: {String(item.new_value)}</p>}
                {item.data !== undefined && <DataView data={item.data} />}
              </article>
            ))}
          </section>
        )}

        {result?.not_understood?.length > 0 && (
          <section className="request-note"><strong>Not understood</strong><ul>{result.not_understood.map((item, i) => <li key={i}>{item}</li>)}</ul></section>
        )}

        {result?.anomaly && (
          <section className="anomaly-card">
            <div><span className="decision-label">ANOMALY MONITOR</span><h2>{result.anomaly.level} · {result.anomaly.action}</h2></div>
            <div className="anomaly-score">Score <strong>{result.anomaly.score}</strong><small>Rules {result.anomaly.rule_score} · ML {result.anomaly.ml_score}</small></div>
            {result.anomaly.reasons?.length > 0 && <ul>{result.anomaly.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>}
          </section>
        )}

        {result?.type === "error" && <div className="request-error">⚠️ {result.message}</div>}

        <section className="flow-section">
          <div className="flow-heading"><span className="line" /><h2>SECURE REQUEST FLOW</h2><span className="line" /></div>
          <div className="flow-container">
            {["USER", "AI AGENT", "GATEWAY", "POLICY ENGINE", "DATABASE"].map((label, index) => (
              <div className="flow-node" key={label}><div className="node-icon">{["👤", "🤖", "🌐", "🛡️", "🗄️"][index]}</div><strong>{label}</strong><span>{["Request", "Plan", "Inspect", "Authorize", "Execute"][index]}</span></div>
            ))}
          </div>
        </section>
      </main>

      <footer className="request-footer"><span>🛡️</span>Zero-Trust Architecture<span className="footer-separator">•</span>Every request is verified<span className="footer-separator">•</span>Secure AI Agent Access Control System</footer>
    </div>
  );
}

export default RequestPage;
