import React, { useEffect, useState } from "react";
import {
  LayoutDashboard, Files, Bell, ShieldCheck, UploadCloud,
  Search, CalendarClock, AlertTriangle, CheckCircle2,
  FileText, Trash2, X, ChevronRight, LogOut, Sparkles,
  Loader2, Eye, EyeOff, ArrowUpRight, MessageCircle, Send
} from "lucide-react"; 
import "./styles.css";

// Keep this hostname the same as the browser address.
const API = "http://localhost:8000/api";

const api = (url, options = {}) =>
  fetch(url, {
    credentials: "include",
    ...options
  });

const categories = [
  "All", "Aadhaar", "PAN Card", "Passport", "Voter ID",
  "Driving Licence", "Vehicle Registration", "Insurance",
  "PUC Certificate", "GST Document", "Invoice",
  "Purchase Order", "Contract", "Licence", "Certificate",
  "Education", "Bank Statement", "Other"
];

const chartColors = [
  "#4778e8", "#20a78a", "#e5a23b", "#8b69d6",
  "#e16b78", "#49a6bd", "#7b8798", "#a2b36b",
  "#d17b45", "#5575a5"
];

const formatDate = value => {
  if (!value) return "Not detected";
  return new Date(value + "T00:00:00").toLocaleDateString(
    "en-IN",
    { day: "2-digit", month: "short", year: "numeric" }
  );
};

function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    name: "",
    email: "",
    password: ""
  });

  const [showPassword, setShowPassword] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);

  const [page, setPage] = useState("Overview");
  const [docs, setDocs] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [stats, setStats] = useState({
    total_documents: 0,
    expired: 0,
    due_soon: 0,
    categories: []
  });

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState(null);

  // Restore an existing login session.
  useEffect(() => {
    async function checkSession() {
      try {
        const response = await api(`${API}/auth/me`);
        if (response.ok) {
          const data = await response.json();
          setUser(data.user);
        }
      } catch (error) {
        console.error("Session check:", error);
      } finally {
        setChecking(false);
      }
    }

    checkSession();
  }, []);

  // Load dashboard data from backend.
  async function refresh() {
    try {
      const [documentsResponse, alertsResponse, statsResponse] =
        await Promise.all([
          api(`${API}/documents`),
          api(`${API}/alerts`),
          api(`${API}/dashboard`)
        ]);

      if (
        documentsResponse.status === 401 ||
        alertsResponse.status === 401 ||
        statsResponse.status === 401
      ) {
        setUser(null);
        return;
      }

      if (
        !documentsResponse.ok ||
        !alertsResponse.ok ||
        !statsResponse.ok
      ) {
        throw new Error("Could not load dashboard data.");
      }

      const [documents, alertData, statsData] =
        await Promise.all([
          documentsResponse.json(),
          alertsResponse.json(),
          statsResponse.json()
        ]);

      setDocs(documents);
      setAlerts(alertData);
      setStats(statsData);
    } catch (error) {
      setMessage(error.message || "Cannot reach backend.");
    }
  }

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  // Search and category filtering.
  useEffect(() => {
    if (!user) return;

    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams();

        if (query) params.set("q", query);
        if (category !== "All") {
          params.set("category", category);
        }

        const response = await api(
          `${API}/documents?${params.toString()}`
        );

        if (response.ok) {
          setDocs(await response.json());
        }
      } catch (error) {
        console.error(error);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, category, user]);

  // Registration and login.
  async function submitAuth(event) {
    event.preventDefault();
    setAuthBusy(true);
    setMessage("");

    try {
      const isRegister = authMode === "register";
      const endpoint = isRegister ? "register" : "login";

      const payload = isRegister
        ? authForm
        : {
            email: authForm.email,
            password: authForm.password
          };

      const response = await api(`${API}/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      // After registration, return to login.
      if (isRegister) {
        setAuthMode("login");
        setAuthForm({
          name: "",
          email: authForm.email,
          password: ""
        });
        setMessage("Account created successfully! Please sign in.");
        return;
      }

      // Verify the login session.
      const sessionResponse = await api(`${API}/auth/me`);

      if (!sessionResponse.ok) {
        throw new Error(
          "Login succeeded, but your session could not be verified."
        );
      }

      const sessionData = await sessionResponse.json();

      setUser(sessionData.user);
      setPage("Overview");
      setAuthForm({
        name: "",
        email: "",
        password: ""
      });
      setMessage("Welcome to DocuSure!");

    } catch (error) {
      setMessage(error.message || "Something went wrong.");
    } finally {
      setAuthBusy(false);
    }
  }

  // Logout function.
  async function logout() {
    try {
      await api(`${API}/auth/logout`, {
        method: "POST"
      });
    } catch (error) {
      console.error("Logout error:", error);
    }

    setUser(null);
    setDocs([]);
    setAlerts([]);
    setSelected(null);
    setPage("Overview");
    setQuery("");
    setCategory("All");
    setMessage("You have been logged out.");
  }

  // Upload a document.
  async function upload(file) {
    if (!file) return;

    setBusy(true);
    setMessage("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await api(`${API}/documents`, {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setMessage(
        "Document uploaded successfully. Please verify the suggested details."
      );

      await refresh();
      setPage("Documents");

    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  // Save document details.
  async function saveDetails() {
    if (!selected) return;

    try {
      const response = await api(
        `${API}/documents/${selected.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            expiry_date: selected.expiry_date || null,
            category: selected.category,
            notes: selected.notes || ""
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Update failed.");
      }

      setSelected(data);
      await refresh();
      setMessage("Document details updated.");

    } catch (error) {
      setMessage(error.message);
    }
  }

  // Delete document.
  async function deleteDocument(id) {
    if (!window.confirm("Are you sure you want to delete this document?")) {
      return;
    }

    try {
      const response = await api(
        `${API}/documents/${id}`,
        { method: "DELETE" }
      );

      if (!response.ok) {
        throw new Error("Could not delete document.");
      }

      setSelected(null);
      await refresh();
      setMessage("Document deleted successfully.");

    } catch (error) {
      setMessage(error.message);
    }
  }

  // Open original document.
  async function openOriginalFile(id) {
    try {
      const response = await api(`${API}/documents/${id}/file`);

      if (!response.ok) {
        throw new Error("Could not open original file.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      window.open(url, "_blank");

      setTimeout(() => URL.revokeObjectURL(url), 60000);

    } catch (error) {
      setMessage(error.message);
    }
  }

  // Loading screen.
  if (checking) {
    return (
      <div className="loading-screen">
        <ShieldCheck size={36} />
        <h2>DocuSure</h2>
        <Loader2 className="spin" />
        <p>Preparing your secure workspace...</p>
      </div>
    );
  }

  // Login and registration screen.
  if (!user) {
    return (
      <div className="auth-shell">
        <section className="auth-visual">
          <div className="auth-brand">
            <div className="brand-mark">
              <ShieldCheck size={24} />
            </div>
            <div>
              <b>docu<span>sure</span></b>
              <small>DOCUMENT INTELLIGENCE</small>
            </div>
          </div>

          <div className="auth-visual-copy">
            <span className="eyebrow">
              SMARTER DOCUMENT MANAGEMENT
            </span>

            <h1>Your documents.<br />Your control.</h1>

            <p>
              Organise, monitor and manage your important
              business documents in one secure workspace.
            </p>

            <div className="auth-feature">
              <ShieldCheck size={19} />
              Secure document management
            </div>

            <div className="auth-feature">
              <CalendarClock size={19} />
              Intelligent expiry monitoring
            </div>

            <div className="auth-feature">
              <Sparkles size={19} />
              AI-assisted document classification
            </div>
          </div>

          <div className="auth-visual-foot">
            © 2026 DocuSure · Document Intelligence Platform
          </div>
        </section>

        <section className="auth-main">
          <form className="auth-card" onSubmit={submitAuth}>
            <div className="auth-mobile-brand">
              <ShieldCheck size={25} /> DocuSure
            </div>

            <span className="eyebrow">
              {authMode === "login" ? "WELCOME BACK" : "GET STARTED"}
            </span>

            <h2>
              {authMode === "login"
                ? "Sign in to your account"
                : "Create your account"}
            </h2>

            <p className="auth-subtitle">
              {authMode === "login"
                ? "Enter your details to access your workspace."
                : "Join DocuSure and manage your documents smarter."}
            </p>

            {message && <div className="notice">{message}</div>}

            {authMode === "register" && (
              <label className="auth-label">
                Full name
                <input
                  type="text"
                  required
                  minLength="2"
                  placeholder="Enter your full name"
                  value={authForm.name}
                  onChange={e =>
                    setAuthForm({ ...authForm, name: e.target.value })
                  }
                />
              </label>
            )}

            <label className="auth-label">
              Email address
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={authForm.email}
                onChange={e =>
                  setAuthForm({ ...authForm, email: e.target.value })
                }
              />
            </label>

            <label className="auth-label">
              Password
              <div className="password-wrapper">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength="8"
                  placeholder="Enter your password"
                  value={authForm.password}
                  onChange={e =>
                    setAuthForm({ ...authForm, password: e.target.value })
                  }
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label="Show or hide password"
                >
                  {showPassword
                    ? <EyeOff size={17} />
                    : <Eye size={17} />}
                </button>
              </div>
            </label>

            <button
              className="primary-btn auth-submit"
              disabled={authBusy}
            >
              {authBusy
                ? "Please wait..."
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
              <ChevronRight size={17} />
            </button>

            <div className="auth-switch">
              {authMode === "login"
                ? "Don't have an account?"
                : "Already have an account?"}

              <button
                type="button"
                onClick={() => {
                  setAuthMode(
                    authMode === "login" ? "register" : "login"
                  );
                  setMessage("");
                }}
              >
                {authMode === "login"
                  ? "Create account"
                  : "Sign in"}
              </button>
            </div>

            <div className="auth-security">
              <ShieldCheck size={16} />
              Your account is protected with secure
              password hashing and session cookies.
            </div>
          </form>
        </section>
      </div>
    );
  }

  // Dashboard calculations.
  const firstName = user.name.split(" ")[0];

  const greeting =
    new Date().getHours() < 12
      ? "Good morning"
      : new Date().getHours() < 17
        ? "Good afternoon"
        : "Good evening";

  const recent = docs.slice(0, 5);

  const totalDocs = Number(stats.total_documents ?? docs.length ?? 0);

  const categoryData = (stats.categories || [])
    .filter(item => Number(item.count) > 0);

  const activeDocs = docs.filter(
    doc => (doc.status || "").toLowerCase() === "active"
  ).length;

  const expiredDocs = docs.filter(
    doc => (doc.status || "").toLowerCase() === "expired"
  ).length;

  const criticalDocs = docs.filter(
    doc => ["critical", "expiring soon"].includes(
      (doc.status || "").toLowerCase()
    )
  ).length;

  const reviewDocs = Math.max(
    0,
    docs.length - activeDocs - expiredDocs - criticalDocs
  );

  const complianceScore = docs.length
    ? Math.round((activeDocs / docs.length) * 100)
    : 0;

  const averageConfidence = docs.length
    ? Math.round(
        docs.reduce(
          (sum, doc) =>
            sum + Math.max(
              0,
              Math.min(1, Number(doc.confidence) || 0)
            ),
          0
        ) / docs.length * 100
      )
    : 0;

  // Pie chart segment calculation.
  let pieCursor = 0;

  const pieStops = categoryData.map((item, index) => {
    const start = pieCursor;
    pieCursor += totalDocs
      ? (Number(item.count) / totalDocs) * 100
      : 0;

    return `${chartColors[index % chartColors.length]} ${start}% ${pieCursor}%`;
  });

  const categoryPieStyle = {
    background: categoryData.length
      ? `conic-gradient(${pieStops.join(", ")})`
      : "#e9edf4"
  };

  return (
    <div className="app-shell">

      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <b>docu<span>sure</span></b>
            <small>DOCUMENT INTELLIGENCE</small>
          </div>
        </div>

        <div className="workspace">
          <div className="workspace-icon">
            {firstName.charAt(0).toUpperCase()}
          </div>
          <div>
            <b>{user.name}</b>
            <small>{user.role || "User"} account</small>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        {[
          { name: "Overview", icon: LayoutDashboard },
          { name: "Documents", icon: Files },
          { name: "Expiry alerts", icon: Bell }
        ].map(item => (
          <button
            key={item.name}
            className={`nav-item ${page === item.name ? "active" : ""}`}
            onClick={() => setPage(item.name)}
          >
            <item.icon size={18} />
            {item.name}

            {item.name === "Expiry alerts" && alerts.length > 0 && (
              <span className="nav-count">{alerts.length}</span>
            )}
          </button>
        ))}

        <div className="sidebar-bottom">
          <div className="help-card">
            <Sparkles size={18} />
            <b>Smart document review</b>
            <p>
              AI-assisted extraction helps you stay organised.
              Always verify suggested information.
            </p>
          </div>

          <div className="profile">
            <div className="avatar">
              {firstName.charAt(0).toUpperCase()}
            </div>
            <div>
              <b>{user.name}</b>
              <small>{user.email}</small>
            </div>
            <button
              className="logout-btn"
              onClick={logout}
              title="Logout"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <b>{page}</b>
          </div>

          <div className="top-actions">
            <span className="system-status">
              <i /> System ready
            </span>

            <button
              className="icon-btn"
              onClick={() => setPage("Expiry alerts")}
            >
              <Bell size={19} />
              {alerts.length > 0 && <em />}
            </button>

            <div className="avatar">
              {firstName.charAt(0).toUpperCase()}
            </div>

            <button className="top-logout" onClick={logout}>
              <LogOut size={15} /> Logout
            </button>
          </div>
        </header>

        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                SME COMPLIANCE WORKSPACE
              </div>

              <h1>
                {page === "Overview"
                  ? `${greeting}, ${firstName}! 👋`
                  : page}
              </h1>

              <p>
                {page === "Overview"
                  ? "Here is your document and compliance overview for today."
                  : page === "Documents"
                    ? "Manage, review and search your business documents."
                    : "Monitor upcoming and expired documents."}
              </p>
            </div>

            <label className="primary-btn upload-btn">
              <UploadCloud size={17} />
              Upload document

              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                hidden
                onChange={e => {
                  upload(e.target.files[0]);
                  e.target.value = "";
                }}
              />
            </label>
          </div>

          {message && (
            <div className="notice">
              <span>{message}</span>
              <button onClick={() => setMessage("")}>
                <X size={15} />
              </button>
            </div>
          )}

          {busy && (
            <div className="upload-progress">
              <Loader2 className="spin" size={17} />
              Uploading and analysing your document...
            </div>
          )}

          {/* OVERVIEW DASHBOARD */}
          {page === "Overview" && (
            <>
              <div className="stats-grid">
                <Stat
                  icon={Files}
                  label="Total documents"
                  value={totalDocs}
                  tint="blue"
                  note="Documents in your account"
                />

                <Stat
                  icon={CalendarClock}
                  label="Expiring in 30 days"
                  value={stats.due_soon}
                  tint="amber"
                  note="Upcoming renewals"
                />

                <Stat
                  icon={AlertTriangle}
                  label="Expired documents"
                  value={stats.expired}
                  tint="red"
                  note="Action required"
                />

                <Stat
                  icon={CheckCircle2}
                  label="Document categories"
                  value={categoryData.length}
                  tint="green"
                  note="Identified document types"
                />
              </div>

              {/* PIE CHART AND COMPLIANCE ANALYTICS */}
              <section
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: 18,
                  marginBottom: 22
                }}
              >
                <div className="panel" style={{ padding: 22 }}>
                  <div className="panel-head">
                    <div>
                      <h3>Document portfolio</h3>
                      <p>Live category distribution</p>
                    </div>
                    <span className="pill">{totalDocs} files</span>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 22,
                      flexWrap: "wrap",
                      paddingTop: 12
                    }}
                  >
                    <div
                      role="img"
                      aria-label="Pie chart showing document category distribution"
                      style={{
                        ...categoryPieStyle,
                        width: 168,
                        height: 168,
                        borderRadius: "50%",
                        flex: "0 0 168px",
                        position: "relative",
                        boxShadow: "inset 0 0 0 1px rgba(0,0,0,.04)"
                      }}
                    >
                      <div
                        style={{
                          position: "absolute",
                          inset: 27,
                          borderRadius: "50%",
                          background: "var(--panel, #fff)",
                          display: "grid",
                          placeContent: "center",
                          textAlign: "center"
                        }}
                      >
                        <strong style={{ fontSize: 27, lineHeight: 1.1 }}>
                          {totalDocs}
                        </strong>
                        <small style={{ color: "#7b8494" }}>
                          documents
                        </small>
                      </div>
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gap: 10,
                        minWidth: 150,
                        flex: 1
                      }}
                    >
                      {categoryData.length ? (
                        categoryData.map((item, index) => (
                          <div
                            key={item.name}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: 12,
                              fontSize: 13
                            }}
                          >
                            <span
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8
                              }}
                            >
                              <i
                                style={{
                                  width: 9,
                                  height: 9,
                                  borderRadius: 3,
                                  background: chartColors[
                                    index % chartColors.length
                                  ],
                                  display: "inline-block"
                                }}
                              />
                              {item.name}
                            </span>

                            <b>
                              {totalDocs
                                ? Math.round(
                                    Number(item.count) / totalDocs * 100
                                  )
                                : 0}%
                            </b>
                          </div>
                        ))
                      ) : (
                        <span style={{ color: "#7b8494", fontSize: 13 }}>
                          Upload documents to see category insights.
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* COMPLIANCE SCORE */}
                <div className="panel" style={{ padding: 22 }}>
                  <div className="panel-head">
                    <div>
                      <h3>Compliance snapshot</h3>
                      <p>Based on your current document statuses</p>
                    </div>
                    <ShieldCheck size={20} />
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 18,
                      margin: "18px 0"
                    }}
                  >
                    <div
                      style={{
                        width: 104,
                        height: 104,
                        borderRadius: "50%",
                        background: `conic-gradient(#20a78a ${complianceScore}%, #edf0f5 0)`,
                        display: "grid",
                        placeItems: "center",
                        flex: "0 0 104px"
                      }}
                    >
                      <div
                        style={{
                          width: 78,
                          height: 78,
                          borderRadius: "50%",
                          background: "var(--panel, #fff)",
                          display: "grid",
                          placeContent: "center",
                          textAlign: "center"
                        }}
                      >
                        <strong style={{ fontSize: 23 }}>
                          {complianceScore}%
                        </strong>
                        <small style={{ color: "#7b8494" }}>active</small>
                      </div>
                    </div>

                    <div
                      style={{
                        flex: 1,
                        display: "grid",
                        gap: 9,
                        fontSize: 13
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Active</span>
                        <b>{activeDocs}</b>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Expired</span>
                        <b>{expiredDocs}</b>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Critical / expiring soon</span>
                        <b>{criticalDocs}</b>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Needs review / other</span>
                        <b>{reviewDocs}</b>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      borderTop: "1px solid #edf0f5",
                      paddingTop: 14,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <span style={{ color: "#7b8494", fontSize: 13 }}>
                      Average extraction confidence
                    </span>
                    <strong style={{ fontSize: 20 }}>
                      {averageConfidence}%
                    </strong>
                  </div>

                  <small style={{ color: "#8a93a2", display: "block", marginTop: 8 }}>
                    Confidence is the average score returned by document
                    analysis. Verify extracted details manually.
                  </small>
                </div>
              </section>

              {/* RECENT DOCUMENTS AND ALERTS */}
              <div className="dashboard-grid">
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h3>Recent documents</h3>
                      <p>Your latest uploaded files</p>
                    </div>

                    <button
                      className="text-btn"
                      onClick={() => setPage("Documents")}
                    >
                      View all <ArrowUpRight size={15} />
                    </button>
                  </div>

                  <DocumentTable
                    docs={recent}
                    onSelect={setSelected}
                  />

                  {recent.length === 0 && <Empty />}
                </section>

                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h3>Attention required</h3>
                      <p>Upcoming and expired documents</p>
                    </div>

                    <span className="pill">
                      {alerts.length} alerts
                    </span>
                  </div>

                  {alerts.slice(0, 5).map(alert => (
                    <div className="alert-row" key={alert.id}>
                      <div
                        className={`alert-icon ${
                          alert.days_remaining < 0 ? "red" : "amber"
                        }`}
                      >
                        <AlertTriangle size={16} />
                      </div>

                      <div className="alert-info">
                        <b>{alert.filename}</b>
                        <small>
                          {alert.days_remaining < 0
                            ? `${Math.abs(alert.days_remaining)} days overdue`
                            : `Expires in ${alert.days_remaining} days`}
                          {" · "}{alert.category}
                        </small>
                      </div>

                      <button
                        className="arrow-btn"
                        onClick={() => setSelected(alert)}
                      >
                        <ChevronRight size={17} />
                      </button>
                    </div>
                  ))}

                  {alerts.length === 0 && (
                    <div className="empty-small">
                      <CheckCircle2 size={25} />
                      <b>All clear!</b>
                      <span>No expiry alerts.</span>
                    </div>
                  )}
                </section>
              </div>

              {/* CATEGORY BREAKDOWN */}
              <section className="panel category-panel">
                <div className="panel-head">
                  <div>
                    <h3>Document categories</h3>
                    <p>Your document library breakdown</p>
                  </div>
                </div>

                <div className="category-list">
                  {(stats.categories || []).map(item => (
                    <div className="category-item" key={item.name}>
                      <div className="category-symbol">
                        <FileText size={17} />
                      </div>

                      <div className="category-name">
                        <b>{item.name}</b>
                        <div className="bar">
                          <i
                            style={{
                              width: `${
                                totalDocs
                                  ? Number(item.count) / totalDocs * 100
                                  : 0
                              }%`
                            }}
                          />
                        </div>
                      </div>

                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}

          {/* DOCUMENT LIBRARY */}
          {page === "Documents" && (
            <section className="panel">
              <div className="toolbar">
                <div className="searchbox">
                  <Search size={17} />
                  <input
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    placeholder="Search documents..."
                  />
                </div>

                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                >
                  {categories.map(item => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>

              <DocumentTable docs={docs} onSelect={setSelected} />
              {docs.length === 0 && <Empty />}
            </section>
          )}

          {/* EXPIRY ALERTS */}
          {page === "Expiry alerts" && (
            <section className="panel">
              <div className="panel-head">
                <div>
                  <h3>Expiry monitoring</h3>
                  <p>
                    Documents expiring within 30 days or already expired
                  </p>
                </div>
                <span className="pill">{alerts.length} alerts</span>
              </div>

              {alerts.map(alert => (
                <div className="full-alert" key={alert.id}>
                  <div
                    className={`alert-icon ${
                      alert.days_remaining < 0 ? "red" : "amber"
                    }`}
                  >
                    <AlertTriangle size={17} />
                  </div>

                  <div className="alert-info">
                    <b>{alert.filename}</b>
                    <small>
                      {alert.category} · {formatDate(alert.expiry_date)}
                    </small>
                  </div>

                  <span
                    className={`status ${
                      alert.days_remaining < 0 ? "danger" : "warning"
                    }`}
                  >
                    {alert.days_remaining < 0
                      ? "Expired"
                      : `${alert.days_remaining} days left`}
                  </span>

                  <button
                    className="secondary-btn small"
                    onClick={() => setSelected(alert)}
                  >
                    Review
                  </button>
                </div>
              ))}

              {alerts.length === 0 && <Empty />}
            </section>
          )}

          <footer>
            © 2026 DocuSure
            <span>Built for smarter document operations</span>
          </footer>
        </div>
      </main>

      {/* DOCUMENT REVIEW MODAL */}
      {selected && (
        <div
          className="modal-backdrop"
          onClick={() => setSelected(null)}
        >
          <div
            className="detail-modal"
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <span className="eyebrow">DOCUMENT REVIEW</span>
                <h2>{selected.filename}</h2>
              </div>

              <button
                className="icon-btn"
                onClick={() => setSelected(null)}
              >
                <X size={19} />
              </button>
            </div>

            <div className="detail-grid">
              <div>
                <small>Detected category</small>
                <b>{selected.category}</b>
              </div>
              <div>
                <small>Extraction confidence</small>
                <b>{Math.round((selected.confidence || 0) * 100)}%</b>
              </div>
              <div>
                <small>Uploaded</small>
                <b>{selected.uploaded_at?.slice(0, 10) || "—"}</b>
              </div>
              <div>
                <small>Remaining days</small>
                <b>{selected.remaining_days ?? "Not available"}</b>
              </div>
            </div>

            <label className="field-label">
              Confirm document category
            </label>

            <select
              className="modal-select"
              value={selected.category || "Other"}
              onChange={e =>
                setSelected({
                  ...selected,
                  category: e.target.value
                })
              }
            >
              {categories.filter(c => c !== "All").map(c => (
                <option key={c}>{c}</option>
              ))}
            </select>

            <label className="field-label">
              Confirm expiry date
            </label>

            <input
              className="date-field"
              type="date"
              value={selected.expiry_date || ""}
              onChange={e =>
                setSelected({
                  ...selected,
                  expiry_date: e.target.value
                })
              }
            />

            <label className="field-label">Notes</label>

            <textarea
              className="notes-field"
              value={selected.notes || ""}
              onChange={e =>
                setSelected({
                  ...selected,
                  notes: e.target.value
                })
              }
              placeholder="Add document notes..."
            />

            <button
              className="primary-btn save-btn"
              onClick={saveDetails}
            >
              Save verified details
            </button>

            <div className="extracted">
              <b>Extracted text preview</b>
              <pre>
                {selected.extracted_text ||
                  "No text was extracted. Check that Tesseract OCR is installed."}
              </pre>
            </div>

            <div className="modal-actions">
              <button
                className="secondary-btn"
                onClick={() => openOriginalFile(selected.id)}
              >
                Open original file
              </button>

              <button
                className="delete-btn"
                onClick={() => deleteDocument(selected.id)}
              >
                <Trash2 size={15} /> Delete
              </button>
            </div>

            <p className="disclaimer">
              Always verify suggested categories and dates
              against the original document.
            </p>
          </div>
        </div>
      )}

      {/* DOCUSURE AI ASSISTANT */}
      <Assistant
        onNavigate={setPage}
        onOpenDocument={document => {
          setPage("Documents");
          setSelected(document);
        }}
      />
    </div>
  );
}


/* STATISTICS CARD */
function Stat({ icon: Icon, label, value, note, tint }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tint}`}>
        <Icon size={19} />
      </div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-note">{note}</div>
    </div>
  );
}


// DOCUMENT TABLE
function DocumentTable({ docs, onSelect }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>DOCUMENT NAME</th>
            <th>CATEGORY</th>
            <th>UPLOADED</th>
            <th>EXPIRY DATE</th>
            <th>STATUS</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          {docs.map(doc => {
            const status = doc.status || "Needs review";

            const statusClass =
              status === "Expired"
                ? "danger"
                : status === "Critical" || status === "Expiring Soon"
                  ? "warning"
                  : status === "Active"
                    ? "success"
                    : "neutral";

            return (
              <tr
                key={doc.id}
                onClick={() => onSelect(doc)}
              >
                <td>
                  <div className="file-cell">
                    <div className="file-icon">
                      <FileText size={17} />
                    </div>
                    <b>{doc.filename}</b>
                  </div>
                </td>

                <td>
                  <span className="category-tag">
                    {doc.category}
                  </span>
                </td>

                <td>{doc.uploaded_at?.slice(0, 10) || "—"}</td>
                <td>{formatDate(doc.expiry_date)}</td>

                <td>
                  <span className={`status ${statusClass}`}>
                    {status}
                  </span>
                </td>

                <td>
                  <ChevronRight size={16} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


// EMPTY STATE
function Empty() {
  return (
    <div className="empty-state">
      <div><Files size={25} /></div>
      <b>No documents found</b>
      <p>
        Upload your first document to start building your document library.
      </p>
    </div>
  );
}

export default App;

function Assistant({ onNavigate, onOpenDocument }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm your DocuSure AI assistant. Ask me to find documents, check expiry alerts or navigate your workspace."
    }
  ]);

  async function sendMessage(event) {
    event.preventDefault();

    const text = input.trim();
    if (!text || busy) return;

    setMessages(current => [
      ...current,
      { role: "user", content: text }
    ]);
    setInput("");
    setBusy(true);

    try {
      const response = await api(`${API}/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Assistant request failed.");
      }

      setMessages(current => [
        ...current,
        { role: "assistant", content: data.reply }
      ]);

      for (const action of data.actions || []) {
        if (action.type === "navigate") {
          onNavigate(action.page);
        }

        if (action.type === "open_document" && action.document) {
          onOpenDocument(action.document);
        }
      }
    } catch (error) {
      setMessages(current => [
        ...current,
        {
          role: "assistant",
          content: error.message || "I couldn't complete that request."
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-assistant">
      {open && (
        <section className="assistant-window">
          <header className="assistant-header">
            <div className="assistant-brand">
              <span className="assistant-icon">
                <Sparkles size={18} />
              </span>
              <div>
                <b>DocuSure AI</b>
                <small>Workspace assistant</small>
              </div>
            </div>

            <button
              className="assistant-close"
              onClick={() => setOpen(false)}
              aria-label="Close assistant"
            >
              <X size={18} />
            </button>
          </header>

          <div className="assistant-messages">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`assistant-message ${
                  message.role === "user" ? "user" : "bot"
                }`}
              >
                {message.content}
              </div>
            ))}

            {busy && (
              <div className="assistant-message bot">
                <Loader2 size={15} className="spin" />
                Thinking...
              </div>
            )}
          </div>

          <form className="assistant-input" onSubmit={sendMessage}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask DocuSure anything..."
              disabled={busy}
            />
            <button type="submit" disabled={busy || !input.trim()}>
              <Send size={17} />
            </button>
          </form>
        </section>
      )}

      <button
        className="assistant-launcher"
        onClick={() => setOpen(value => !value)}
        aria-label="Open DocuSure AI assistant"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
        {!open && <span>Ask AI</span>}
      </button>
    </div>
  );
}
