// imports: we bring in React and some chart libraries
import "./App.css";
import React, { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2"; // Bar chart component
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from "chart.js";

// Register chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function App() {
  // React "state" to store the summary data we get from Django
  const [summary, setSummary] = useState(null);
  const [file, setFile] = useState(null);       // state for file upload
  const [loading, setLoading] = useState(false); // state for loading spinner
  const [error, setError] = useState(null);      // state for errors

  // useEffect runs once when the page loads
  // useEffect(() => {
  //   setLoading(true);
  //   fetch("http://127.0.0.1:8000/api/summary/")
  //     .then((res) => {
  //       if (!res.ok) throw new Error("Failed to fetch summary");
  //       return res.json();
  //     })
  //     .then((data) => {
  //       setSummary(data);
  //       setError(null);
  //     })
  //     .catch((err) => {
  //       console.error("Fetch error:", err);
  //       setError("Could not load summary. Please upload a CSV.");
  //     })
  //     .finally(() => setLoading(false));
  // }, []);

  // Upload handler
  function handleUpload() {
    if (!file) return alert("Please select a CSV file first.");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    fetch("http://127.0.0.1:8000/api/upload/", {
      method: "POST",
      body: formData
    })
      .then((res) => {
        if (!res.ok) throw new Error("Upload failed");
        return res.json();
      })
      .then((data) => {
        setSummary(data); // update charts and table with new summary
        setError(null);
      })
      .catch((err) => {
        console.error("Upload error:", err);
        setError("Upload failed. Please try again.");
      })
      .finally(() => setLoading(false));
  }

  // Show loading spinner
  if (loading) return <p style={{ fontSize: "18px" }}>⏳ Loading...</p>;

  // Show error message
  if (error) return (
    <div style={{ padding: "20px", color: "red" }}>
      <h2>Error</h2>
      <p>{error}</p>
      {/* Upload section still available */}
      <h3>Upload CSV File</h3>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleUpload}>Upload</button>
    </div>
  );

  // If no summary yet
  if (!summary && !loading) {
  return (
    <div className="container">
      <h1>Chemical Equipment Summary</h1>

      <div className="card">
        <h2>Upload CSV File</h2>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload} style={{ marginLeft: "10px" }}>
          Upload
        </button>
        <p style={{ marginTop: "10px", color: "#555" }}>
          Please upload a CSV file to view equipment analysis.
        </p>
      </div>
    </div>
  );
}


  // Extract labels and values for type distribution chart
  const typeLabels = Object.keys(summary.type_distribution);
  const typeValues = Object.values(summary.type_distribution);

  // Chart data for equipment type distribution
  const typeChartData = {
    labels: typeLabels,
    datasets: [
      {
        label: "Equipment Count",
        data: typeValues,
        backgroundColor: "rgba(75,192,192,0.6)" // teal color
      }
    ]
  };

  // Chart data for average values (flowrate, pressure, temperature)
  const avgChartData = {
    labels: ["Flowrate", "Pressure", "Temperature"],
    datasets: [
      {
        label: "Averages",
        data: [
          summary.avg_flowrate,
          summary.avg_pressure,
          summary.avg_temperature
        ],
        backgroundColor: "rgba(153,102,255,0.6)" // purple color
      }
    ]
  };

  // What React will show on the page
  return (
  <div className="container">
    <h1>Chemical Equipment Summary</h1>

    {/* Upload section */}
    <div className="card">
      <h2>Upload CSV File</h2>
      <div className="upload-row">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload}>Upload</button>
      </div>
    </div>

    {/* Overview table */}
    <div className="card">
      <h2>Overview</h2>
      <table>
        <tbody>
          <tr>
            <td>Total Equipment</td>
            <td>{summary.total_equipment}</td>
          </tr>
          <tr>
            <td>Avg Flowrate</td>
            <td>{summary.avg_flowrate.toFixed(2)}</td>
          </tr>
          <tr>
            <td>Avg Pressure</td>
            <td>{summary.avg_pressure.toFixed(2)}</td>
          </tr>
          <tr>
            <td>Avg Temperature</td>
            <td>{summary.avg_temperature.toFixed(2)}</td>
          </tr>
        </tbody>
      </table>
    </div>

    {/* Charts */}
    <div className="card">
      <h2>Type Distribution</h2>
      <Bar data={typeChartData} />
    </div>

    <div className="card">
      <h2>Average Parameters</h2>
      <Bar data={avgChartData} />
    </div>
  </div>
);

}

// Export App so React can use it
export default App;