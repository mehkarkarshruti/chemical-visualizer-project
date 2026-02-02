import React, { useEffect, useState } from "react";
import "./App.css";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from "chart.js";
import UploadSection from "./components/UploadSection";
import { History, Home, BarChart, FileText, X, ChevronLeft, ChevronRight, Sun, Moon } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function App() {
  // State
  const [summary, setSummary] = useState(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const [activeView, setActiveView] = useState("home");
  const [showHistory, setShowHistory] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Dark Mode Effect
  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode');
      document.body.classList.remove('light-mode');
    } else {
      document.body.classList.add('light-mode');
      document.body.classList.remove('dark-mode');
    }
  }, [darkMode]);

  // Fetch history
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/history/")
      .then((res) => res.json())
      .then((data) => setHistory(data))
      .catch((err) => console.error("History fetch error:", err));
  }, []);

  // Upload handler
  const handleUpload = (uploadedFile) => {
    if (!uploadedFile) return alert("Please select a CSV file first.");
    
    setLoading(true);
    const formData = new FormData();
    formData.append("file", uploadedFile);

    fetch("http://127.0.0.1:8000/api/upload/", {
      method: "POST",
      body: formData
    })
      .then((res) => {
        if (!res.ok) throw new Error("Upload failed");
        return res.json();
      })
      .then((data) => {
        setSummary(data);
        setError(null);
        setActiveView("dashboard");
        
        // Refresh history
        return fetch("http://127.0.0.1:8000/api/history/");
      })
      .then((res) => res.json())
      .then((data) => setHistory(data))
      .catch((err) => {
        console.error("Upload error:", err);
        setError("Upload failed. Please check your CSV format and try again.");
      })
      .finally(() => setLoading(false));
  };

  // PDF download
  const handleDownloadPDF = () => {
    window.open("http://127.0.0.1:8000/api/report/", "_blank");
  };

  // Chart data
  const typeLabels = summary ? Object.keys(summary.type_distribution || {}) : [];
  const typeValues = summary ? Object.values(summary.type_distribution || {}) : [];

  const typeChartData = {
    labels: typeLabels,
    datasets: [
      {
        label: "Equipment Count",
        data: typeValues,
        backgroundColor: "rgba(79, 70, 229, 0.6)",
        borderColor: "rgba(79, 70, 229, 1)",
        borderWidth: 1
      }
    ]
  };

  const avgChartData = {
    labels: ["Flowrate", "Pressure", "Temperature"],
    datasets: [
      {
        label: "Average Values",
        data: summary
          ? [summary.avg_flowrate, summary.avg_pressure, summary.avg_temperature]
          : [],
        backgroundColor: [
          "rgba(16, 185, 129, 0.6)",
          "rgba(245, 158, 11, 0.6)", 
          "rgba(239, 68, 68, 0.6)"
        ],
        borderColor: [
          "rgba(16, 185, 129, 1)",
          "rgba(245, 158, 11, 1)",
          "rgba(239, 68, 68, 1)"
        ],
        borderWidth: 1
      }
    ]
  };

  // Sidebar Component
  const SidebarComponent = () => (
    <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!sidebarCollapsed && <h3>Navigation</h3>}
        <button 
          className="collapse-btn"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        >
          {sidebarCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        <button 
          className={`nav-btn ${activeView === 'home' ? 'active' : ''}`}
          onClick={() => setActiveView('home')}
        >
          <Home size={20} />
          {!sidebarCollapsed && <span>Home</span>}
        </button>

        <button 
          className={`nav-btn ${activeView === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveView('dashboard')}
        >
          <BarChart size={20} />
          {!sidebarCollapsed && <span>Dashboard</span>}
        </button>

        <button 
          className={`nav-btn ${activeView === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveView('reports')}
        >
          <FileText size={20} />
          {!sidebarCollapsed && <span>Reports</span>}
        </button>

        <div className="nav-divider"></div>

        <button 
          className="nav-btn history-btn"
          onClick={() => setShowHistory(true)}
        >
          <History size={20} />
          {!sidebarCollapsed && (
            <>
              <span>History</span>
              <span className="badge">{history.length}</span>
            </>
          )}
        </button>
      </nav>
    </div>
  );

  // History Drawer
  const HistoryDrawer = () => (
    showHistory && (
      <div className="history-drawer">
        <div className="drawer-header">
          <h3>📋 Upload History</h3>
          <button onClick={() => setShowHistory(false)}>
            <X size={24} />
          </button>
        </div>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="empty-history">No upload history yet</p>
          ) : (
            history.map((item, index) => (
              <div key={index} className="history-item">
                <div className="history-time">
                  {new Date(item.uploaded_at).toLocaleString()}
                </div>
                <div className="history-stats">
                  <span>📊 {item.total_equipment} equipment</span>
                  <span>🌡️ {item.avg_temperature.toFixed(1)}°C</span>
                  <span>⚡ {item.avg_flowrate.toFixed(1)} flow</span>
                </div>
                <button 
                  className="view-btn"
                  onClick={() => {
                    alert(`Viewing report from ${new Date(item.uploaded_at).toLocaleString()}`);
                  }}
                >
                  View Details
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    )
  );

  // Render different views
  const renderView = () => {
    switch (activeView) {
      case "home":
        return (
          <div className="home-view">
            <UploadSection onUpload={handleUpload} loading={loading} />
            
            {error && (
              <div className="error-card">
                <h3>⚠️ Upload Error</h3>
                <p>{error}</p>
              </div>
            )}
            
            {history.length > 0 && (
              <div className="quick-stats">
                <h3>📊 Recent Activity</h3>
                <div className="stats-preview">
                  <div className="stat">
                    <span className="stat-label">Last Upload</span>
                    <span className="stat-value">
                      {new Date(history[0].uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Total Records</span>
                    <span className="stat-value">{history[0].total_equipment}</span>
                  </div>
                  <button 
                    className="btn-outline"
                    onClick={() => setActiveView("dashboard")}
                  >
                    View Full Dashboard →
                  </button>
                </div>
              </div>
            )}
          </div>
        );

      case "dashboard":
        if (!summary) {
          return (
            <div className="empty-dashboard">
              <h2>No Data Available</h2>
              <p>Please upload a CSV file to view the dashboard</p>
              <button 
                className="btn-primary"
                onClick={() => setActiveView("home")}
              >
                ← Go to Upload
              </button>
            </div>
          );
        }

        return (
          <div className="dashboard-view">
            <div className="dashboard-header">
              <h2>Equipment Analytics Dashboard</h2>
              <div className="header-actions">
                <button className="btn-outline" onClick={handleDownloadPDF}>
                  📄 Export PDF
                </button>
              </div>
            </div>

            <div className="stats-grid">
              <div className="stat-card">
                <h3>Total Equipment</h3>
                <div className="value">{summary.total_equipment}</div>
              </div>
              <div className="stat-card">
                <h3>Avg Flowrate</h3>
                <div className="value">{summary.avg_flowrate.toFixed(2)}</div>
              </div>
              <div className="stat-card">
                <h3>Avg Pressure</h3>
                <div className="value">{summary.avg_pressure.toFixed(2)}</div>
              </div>
              <div className="stat-card">
                <h3>Avg Temperature</h3>
                <div className="value">{summary.avg_temperature.toFixed(2)}</div>
              </div>
            </div>

            <div className="charts-container">
              <div className="chart-card">
                <h3>Equipment Type Distribution</h3>
                <div style={{ height: '300px' }}>
                  <Bar data={typeChartData} />
                </div>
              </div>
              <div className="chart-card">
                <h3>Average Parameters</h3>
                <div style={{ height: '300px' }}>
                  <Bar data={avgChartData} />
                </div>
              </div>
            </div>
          </div>
        );

      case "reports":
        return (
          <div className="reports-view">
            <h2>📄 Generated Reports</h2>
            <div className="reports-list">
              <div className="report-card">
                <div className="report-info">
                  <h3>Current Analysis Report</h3>
                  <p>Latest equipment data analysis</p>
                  {summary && (
                    <div className="report-stats">
                      <span>📊 {summary.total_equipment} equipment</span>
                      <span>📅 {new Date().toLocaleDateString()}</span>
                    </div>
                  )}
                </div>
                <button 
                  className="btn-primary"
                  onClick={handleDownloadPDF}
                  disabled={!summary}
                >
                  Download PDF
                </button>
              </div>
              
              {history.slice(0, 5).map((item, index) => (
                <div key={index} className="report-card">
                  <div className="report-info">
                    <h3>Historical Report #{index + 1}</h3>
                    <p>{new Date(item.uploaded_at).toLocaleString()}</p>
                    <div className="report-stats">
                      <span>📊 {item.total_equipment} equipment</span>
                      <span>⚡ {item.avg_flowrate.toFixed(2)} flowrate</span>
                    </div>
                  </div>
                  <button 
                    className="btn-outline"
                    onClick={() => {
                      alert(`Would generate PDF for ${new Date(item.uploaded_at).toLocaleString()}`);
                    }}
                  >
                    Regenerate
                  </button>
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return <div>Unknown view</div>;
    }
  };

  return (
    <div className="app-container">
      <SidebarComponent />
      <HistoryDrawer />
      
      <main className="main-content">
        <header className="app-header">
          <div className="header-left">
            <h1>🧪 Chemical Equipment Visualizer</h1>
            <p className="subtitle">Real-time analytics for chemical equipment parameters</p>
          </div>
          <div className="header-right">
            <button 
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
              {darkMode ? "Light Mode" : "Dark Mode"}
            </button>
          </div>
        </header>

        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Analyzing your CSV data...</p>
          </div>
        )}

        <div className="content-area">
          {renderView()}
        </div>
        {/* Footer always visible */}
        <footer style={{ marginTop: "20px", textAlign: "center", color: "#6b7280" }}>
          <p>Developed by: Shruti Mehkarkar | Email: mehkarkars1211@gmail.com | University: VIT Bhopal University</p>
        </footer>


      </main>
    </div>
  );
}

export default App;