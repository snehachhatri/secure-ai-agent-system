import { useCallback, useEffect, useState } from "react";
import "./AdminDashboard.css";

const API = "http://127.0.0.1:8000";

function displayTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function AdminDashboard() {
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = localStorage.getItem("access_token");
  const username = localStorage.getItem("username");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [logsRes, statsRes, alertsRes] = await Promise.all([
        fetch(`${API}/admin/logs?limit=200`, { headers }),
        fetch(`${API}/admin/stats`, { headers }),
        fetch(`${API}/admin/alerts?limit=100`, { headers }),
      ]);
      const [logsData, statsData, alertsData] = await Promise.all([
        logsRes.json(), statsRes.json(), alertsRes.json(),
      ]);
      const failed = [logsRes, statsRes, alertsRes].find((response) => !response.ok);
      if (failed) {
        const body = [logsData, statsData, alertsData][[logsRes, statsRes, alertsRes].indexOf(failed)];
        throw new Error(body.detail || "Unable to load admin data.");
      }
      setLogs(logsData.logs || []);
      setStats(statsData);
      setAlerts(alertsData.alerts || []);
    } catch (err) {
      setError(err.message || "Unable to fetch admin data.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleLogout = () => {
    localStorage.clear();
    window.location.reload();
  };

  return (
    <div className="admin-dashboard">
      <header className="admin-header">
        <div className="admin-brand">
          <span className="brand-shield">🛡️</span>
          <div><h2>Secure AI Agent</h2><p>ADMIN MONITORING DASHBOARD</p></div>
        </div>
        <div className="admin-profile">
          <div><strong>{username || "Admin"}</strong><span>Administrator</span></div>
          <button className="refresh-btn" onClick={fetchData} disabled={loading}>↻ Refresh</button>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="admin-main">
        {error && <div className="admin-error">⚠️ {error}</div>}

        {stats && (
          <section className="stats-grid">
            <div className="stat-card"><span className="stat-label">Logged Actions</span><strong className="stat-value">{stats.total_requests}</strong></div>
            <div className="stat-card allowed"><span className="stat-label">Allowed</span><strong className="stat-value">{stats.allowed_requests}</strong></div>
            <div className="stat-card blocked"><span className="stat-label">Blocked</span><strong className="stat-value">{stats.blocked_requests}</strong></div>
            <div className="stat-card"><span className="stat-label">Need Clarification</span><strong className="stat-value">{stats.clarification_requests}</strong></div>
            <div className="stat-card alert-stat"><span className="stat-label">Security Alerts</span><strong className="stat-value">{stats.total_alerts}</strong></div>
          </section>
        )}

        <section className="admin-section">
          <div className="section-heading"><div><h2>📋 Audit Trail</h2><p>Recent authenticated actions and policy decisions</p></div><span>{logs.length} shown</span></div>
          {loading ? <p>Loading logs…</p> : logs.length === 0 ? <p>No audit records yet.</p> : (
            <div className="table-wrapper">
              <table>
                <thead><tr><th>Time</th><th>User</th><th>Role</th><th>Request</th><th>Action</th><th>Decision</th><th>Reason</th><th>Rule</th><th>Severity</th><th>Old → New</th></tr></thead>
                <tbody>{logs.map((log) => (
                  <tr key={log.id}>
                    <td>{displayTime(log.created_at)}</td>
                    <td>{log.username || `user ${log.user_id}`}</td>
                    <td>{log.role || "—"}</td>
                    <td className="request-cell" title={log.request_text}>{log.request_text || "—"}</td>
                    <td>{log.action || "—"}</td>
                    <td><span className={`badge badge-${log.decision === "allowed" ? "allow" : "block"}`}>{String(log.decision || "unknown").toUpperCase()}</span></td>
                    <td className="request-cell" title={log.reason}>{log.reason || "—"}</td>
                    <td>{log.rule || "—"}</td>
                    <td><span className={`severity severity-${log.severity || "none"}`}>{log.severity || "none"}</span></td>
                    <td>{log.old_value == null && log.new_value == null ? "—" : `${log.old_value ?? "—"} → ${log.new_value ?? "—"}`}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>

        <section className="admin-section">
          <div className="section-heading"><div><h2>🚨 Security Alerts</h2><p>Prompt injection, policy blocks, and anomaly responses</p></div><span>{alerts.length} shown</span></div>
          {loading ? <p>Loading alerts…</p> : alerts.length === 0 ? <p>No alerts recorded.</p> : (
            <div className="table-wrapper">
              <table>
                <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Severity</th><th>Message</th></tr></thead>
                <tbody>{alerts.map((alert) => (
                  <tr key={alert.id}>
                    <td>{displayTime(alert.created_at)}</td>
                    <td>{alert.username || `user ${alert.user_id}`}</td>
                    <td>{alert.action}</td>
                    <td><span className={`severity severity-${alert.severity}`}>{alert.severity}</span></td>
                    <td>{alert.message}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default AdminDashboard;
