import { useState } from "react";
import "./RequestPage.css";

function RequestPage() {
  const [request, setRequest] = useState("");
  const [result, setResult] = useState(null);

  const quickRequests = [
    "Show me customer CUST001's details",
    "Show me customer CUST002's details",
    "Delete customer CUST001",
  ];

  const handleRequest = (e) => {
    e.preventDefault();

    if (!request.trim()) {
      setResult({
        type: "error",
        title: "Request Required",
        message: "Please enter a request before sending.",
      });
      return;
    }

    // Temporary demo decision
    if (
      request.toLowerCase().includes("delete") ||
      request.toLowerCase().includes("export")
    ) {
      setResult({
        type: "blocked",
        title: "Access Blocked",
        message: "Policy Engine denied this request.",
        reason: "Agent does not have permission for this action.",
      });
    } else {
      setResult({
        type: "allowed",
        title: "Access Allowed",
        message: "Policy Engine approved this request.",
        reason: "Required permission is available.",
      });
    }
  };

  const useQuickRequest = (text) => {
    setRequest(text);
    setResult(null);
  };

  return (
    <div className="request-page">

      {/* Background effects */}
      <div className="request-orb orb-one"></div>
      <div className="request-orb orb-two"></div>
      <div className="request-grid"></div>

      {/* HEADER */}
      <header className="request-header">

        <div className="brand">
          <div className="brand-shield">🛡️</div>

          <div>
            <h2>Secure AI Agent</h2>
            <p>ACCESS CONTROL SYSTEM</p>
          </div>
        </div>

        <div className="header-status">
          <span className="status-dot"></span>
          SYSTEM SECURE
        </div>

        <div className="profile">
          <div className="profile-avatar">👤</div>

          <div>
            <strong>Customer</strong>
            <span>Authenticated</span>
          </div>
        </div>

      </header>


      {/* MAIN */}
      <main className="request-main">

        {/* PAGE TITLE */}
        <section className="page-heading">

          <div className="heading-icon">
            🤖
          </div>

          <div>
            <div className="eyebrow">
              <span></span>
              SECURE REQUEST GATEWAY
            </div>

            <h1>
              What can your <span>AI Agent</span> do for you?
            </h1>

            <p>
              Submit a request and our Policy Engine will verify
              whether the requested action is authorized.
            </p>
          </div>

        </section>


        {/* REQUEST CARD */}
        <section className="request-card">

          <div className="card-top">

            <div>
              <div className="card-label">
                <span className="pulse-dot"></span>
                NEW REQUEST
              </div>

              <h2>Describe your request</h2>
            </div>

            <div className="request-id">
              REQUEST
              <strong>#DEMO-001</strong>
            </div>

          </div>


          <form onSubmit={handleRequest}>

            <div className="textarea-wrapper">

              <div className="textarea-icon">
                ✦
              </div>

              <textarea
                value={request}
                onChange={(e) => {
                  setRequest(e.target.value);
                  setResult(null);
                }}
                placeholder="Example: Show me customer CUST001's details"
              />

              <div className="character-count">
                {request.length} characters
              </div>

            </div>


            {/* QUICK REQUESTS */}
            <div className="quick-section">

              <span className="quick-title">
                TRY A SAMPLE REQUEST
              </span>

              <div className="quick-buttons">

                {quickRequests.map((item, index) => (
                  <button
                    type="button"
                    key={index}
                    onClick={() => useQuickRequest(item)}
                  >
                    {item}
                  </button>
                ))}

              </div>

            </div>


            {/* SECURITY INFO */}
            <div className="security-info">

              <div className="security-icon">
                🔐
              </div>

              <div>
                <strong>Zero-Trust Verification</strong>

                <p>
                  Every request is authenticated, authorized,
                  and evaluated by the Policy Engine before
                  accessing protected resources.
                </p>
              </div>

              <div className="secure-badge">
                SECURE
              </div>

            </div>


            {/* BUTTON */}
            <button className="send-button" type="submit">
              <span>🚀</span>
              Send Secure Request
              <span className="button-arrow">→</span>
            </button>

          </form>

        </section>


        {/* RESULT */}
        {result && result.type !== "error" && (
          <section
            className={`decision-card ${
              result.type === "allowed"
                ? "decision-allowed"
                : "decision-blocked"
            }`}
          >

            <div className="decision-icon">
              {result.type === "allowed" ? "✓" : "×"}
            </div>

            <div className="decision-content">
              <span className="decision-label">
                POLICY DECISION
              </span>

              <h2>{result.title}</h2>

              <p>{result.message}</p>

              <div className="decision-reason">
                <span>Reason:</span> {result.reason}
              </div>
            </div>

            <div className="decision-status">
              {result.type === "allowed" ? "ALLOW" : "BLOCK"}
            </div>

          </section>
        )}

        {result?.type === "error" && (
          <div className="request-error">
            ⚠️ {result.message}
          </div>
        )}


        {/* FLOW */}
        <section className="flow-section">

          <div className="flow-heading">
            <span className="line"></span>
            <h2>SECURE REQUEST FLOW</h2>
            <span className="line"></span>
          </div>


          <div className="flow-container">

            <div className="flow-node active">
              <div className="node-icon">👤</div>
              <strong>USER</strong>
              <span>Request</span>
            </div>

            <div className="flow-connector">
              <span></span>
              <b>→</b>
            </div>

            <div className="flow-node">
              <div className="node-icon">🤖</div>
              <strong>AI AGENT</strong>
              <span>Process</span>
            </div>

            <div className="flow-connector">
              <span></span>
              <b>→</b>
            </div>

            <div className="flow-node">
              <div className="node-icon">🌐</div>
              <strong>GATEWAY</strong>
              <span>Verify</span>
            </div>

            <div className="flow-connector">
              <span></span>
              <b>→</b>
            </div>

            <div className="flow-node">
              <div className="node-icon">🛡️</div>
              <strong>POLICY ENGINE</strong>
              <span>Authorize</span>
            </div>

            <div className="flow-connector">
              <span></span>
              <b>→</b>
            </div>

            <div className="flow-node">
              <div className="node-icon">⚡</div>
              <strong>DECISION</strong>
              <span>Allow / Block</span>
            </div>

          </div>

        </section>

      </main>


      {/* FOOTER */}
      <footer className="request-footer">
        <span>🛡️</span>
        Zero-Trust Architecture
        <span className="footer-separator">•</span>
        Every request is verified
        <span className="footer-separator">•</span>
        Secure AI Agent Access Control System
      </footer>

    </div>
  );
}

export default RequestPage;