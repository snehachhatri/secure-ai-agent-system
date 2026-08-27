import "./App.css";

function App() {
  return (
    <div className="login-page">

      {/* Background effects */}
      <div className="glow glow-one"></div>
      <div className="glow glow-two"></div>

      <div className="login-wrapper">

        {/* LEFT SIDE */}
        <div className="brand-section">

          <div className="shield-icon">
            🛡️
          </div>

          <h1>
            Secure <span>AI Agent</span>
          </h1>

          <h2>Access Control System</h2>

          <div className="line"></div>

          <p className="description">
            A zero-trust access control system for AI agents.
            <br />
            Secure. Monitor. Authorize.
            <br />
            Every request. Every time.
          </p>

          <div className="security-shield">
            🔐
          </div>

          <div className="features">

            <div className="feature">
              <div className="feature-icon">🛡️</div>
              <h3>Secure</h3>
              <p>Zero-trust security</p>
            </div>

            <div className="feature">
              <div className="feature-icon">🤖</div>
              <h3>Smart Agents</h3>
              <p>Defined permissions</p>
            </div>

            <div className="feature">
              <div className="feature-icon">📊</div>
              <h3>Monitor</h3>
              <p>Real-time audit logs</p>
            </div>

          </div>

        </div>


        {/* RIGHT SIDE */}
        <div className="login-card">

          <div className="card-icon">
            🛡️
          </div>

          <h2>Welcome Back</h2>

          <p className="login-subtitle">
            Sign in to continue to your dashboard
          </p>

          <div className="divider">
            <span></span>
            <div></div>
            <span></span>
          </div>

          <form>

            <label>Username</label>

            <div className="input-box">
              <span>👤</span>

              <input
                type="text"
                placeholder="Enter your username"
              />
            </div>


            <label>Password</label>

            <div className="input-box">
              <span>🔒</span>

              <input
                type="password"
                placeholder="Enter your password"
              />

              <span className="eye">👁️</span>
            </div>


            <button className="login-button" type="submit">
              Login
              <span>→</span>
            </button>

          </form>

          <div className="secure-message">
            🛡️ Secure authentication
          </div>

        </div>

      </div>

      <footer>
        © 2026 Secure AI Agent Access Control System
      </footer>

    </div>
  );
}

export default App;