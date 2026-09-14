import { useState, useEffect } from "react";
import "./AdminDashboard.css";

function AdminDashboard() {
  const [logs, setLogs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = localStorage.getItem("access_token");
  const username = localStorage.getItem("username");

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const headers = { Authorization: `Bearer ${token}` };

      const [logsRes, customersRes, statsRes] = await Promise.all([
        fetch("http://127.0.0.1:8000/admin/logs", { headers }),
        fetch("http://127.0.0.1:8000/admin/customers", { headers }),
        fetch("http://127.0.0.1:8000/admin/stats", { headers }),
      ]);

      const logsData = await logsRes.json();
      const customersData = await customersRes.json();
      const statsData = await statsRes.json();

      setLogs(logsData.logs || []);
      setCustomers(customersData.customers || []);
      setStats(statsData);
    } catch (err) {
      setError("Unable to fetch admin data.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    window.location.reload();
  };

  return (
    <div className="admin-dashboard">
      <header className="admin-header">
        <div className="admin-brand">
          <span className="brand-shield">🛡️</span>
          <div>
            <h2>Secure AI Agent</h2>
            <p>ADMIN MONITORING DASHBOARD</p>
          </div>
        </div>

        <div className="admin-profile">
          <div>
            <strong>{username || "Admin"}</strong>
            <span>Administrator</span>
          </div>
          <button className="refresh-btn" onClick={fetchData}>
            🔄 Refresh
          </button>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="admin-main">
        {error && <div className="admin-error">⚠️ {error}</div>}

        {stats && (
          <section className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Total Requests</span>
              <strong className="stat-value">{stats.total_requests}</strong>
            </div>
            <div className="stat-card allowed">
              <span className="stat-label">Allowed</span>
              <strong className="stat-value">{stats.allowed_requests}</strong>
            </div>
            <div className="stat-card blocked">
              <span className="stat-label">Blocked</span>
              <strong className="stat-value">{stats.blocked_requests}</strong>
            </div>
          </section>
        )}

        <section className="admin-section">
          <h2>📋 Audit Trail — All Agent Requests</h2>
          {loading ? (
            <p>Loading logs...</p>
          ) : logs.length === 0 ? (
            <p>No requests yet.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Agent</th>
                    <th>Request</th>
                    <th>Action</th>
                    <th>Customer ID</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log._id}>
                      <td>{log.username}</td>
                      <td>{log.agent_name}</td>
                      <td>{log.request_text}</td>
                      <td>{log.action}</td>
                      <td>{log.customer_id || "-"}</td>
                      <td>
                        <span
                          className={`badge ${
                            log.decision === "allowed" ? "badge-allow" : "badge-block"
                          }`}
                        >
                          {log.decision.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="admin-section">
          <h2>🗄️ Live Customer Database</h2>
          {loading ? (
            <p>Loading customers...</p>
          ) : customers.length === 0 ? (
            <p>No customer records found.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Customer ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Order ID</th>
                    <th>Order Status</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((c) => (
                    <tr key={c._id}>
                      <td>{c.customer_id}</td>
                      <td>{c.name}</td>
                      <td>{c.email}</td>
                      <td>{c.order_id}</td>
                      <td>{c.order_status}</td>
                      <td>₹{c.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default AdminDashboard;