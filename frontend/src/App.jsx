import { useState } from "react";
import "./App.css";
import RequestPage from "./RequestPage";
import "./App.css";

function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
const handleLogin = async (e) => {
  e.preventDefault();

  setError("");

  if (!username || !password) {
    setError("Please enter username and password.");
    return;
  }

  try {
    const response = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username,
        password: password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      setError(data.detail || "Invalid username or password.");
      return;
    }

    // Save JWT token
localStorage.setItem("access_token", data.access_token);

// Open Request Page
setIsLoggedIn(true);

  } catch (error) {
    setError("Unable to connect to server.");
    console.error(error);
  }
};

if (isLoggedIn) {
  return <RequestPage />;
}

return (
    <div className="login-page">

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

          <form onSubmit={handleLogin}>

            {/* USERNAME */}
            <label>Username</label>

            <div className="input-box">
              <span>👤</span>

              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>


            {/* PASSWORD */}
            <label>Password</label>

            <div className="input-box">
              <span>🔒</span>

              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <span
                className="eye"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "🙈" : "👁️"}
              </span>
            </div>


            {/* ERROR */}
            {error && (
              <p className="error-message">
                ⚠️ {error}
              </p>
            )}


            {/* LOGIN BUTTON */}
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