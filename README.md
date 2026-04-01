<p align="center">
  <a href="https://drishti-teamrocket.streamlit.app/">
    <img 
      src="frontend/drishti_banner.png" 
      alt="Banner"
      style="max-height: 300px; max-width: 100%; height: auto; width: auto;"
    >
  </a>
</p>

<div align="center">

# DRISHTI

### Real-time river pollution monitoring, anomaly detection, and response support for the Yamuna

<p>
  <a href="https://drishti-teamrocket.streamlit.app/"><strong>Live App</strong></a>
</p>

</div>

---

## Overview

Delhi accounts for a small stretch of the Yamuna, but a disproportionate share of its pollution load. In practice, response often begins only after visible degradation, public complaints, or manual inspection.

**DRISHTI** is a lightweight monitoring and decision-support platform built to make that workflow more proactive. It brings live sensor readings, anomaly detection, risk simulation, alert tracking, and issue management into one operational view.

Instead of reacting late, the platform supports a clearer loop:

<p align="center">
  <strong>Monitor</strong> -> <strong>Detect</strong> -> <strong>Predict</strong> -> <strong>Respond</strong>
</p>

---

## What DRISHTI Does

<table>
  <tr>
    <td valign="top" width="50%">
      <h3>Live Monitoring</h3>
      <p>Tracks water-quality parameters such as pH, DO, BOD, COD, turbidity, ammonia, temperature, and conductivity through a unified dashboard.</p>
      <br>
    </td>
    <td valign="top" width="50%">
      <h3>Anomaly Detection</h3>
      <p>Uses an <strong>Isolation Forest</strong> model to flag abnormal sensor patterns and generate alerts for potential pollution events.</p>
      <br>
    </td>
  </tr>
  <tr>
    <td valign="top" width="50%">
      <h3>Risk Simulation</h3>
      <p>Projects short-term pollution risk and compares baseline conditions against discharge-reduction scenarios.</p>
      <br>
    </td>
    <td valign="top" width="50%">
      <h3>Operational Workflow</h3>
      <p>Lets teams review alerts, create issues, and track follow-up actions from the same interface.</p>
      <br>
    </td>
  </tr>
</table>

---

## Why This Matters

River pollution is not just a data problem. It is a coordination problem.

DRISHTI is designed around a few practical gaps:

- Monitoring is often periodic rather than continuous.
- Illegal or intermittent discharge can be missed between inspections.
- Agencies need one place to view readings, alerts, and follow-up actions.
- Pollution control decisions are stronger when teams can compare baseline risk with simulated interventions.

---

## Core Features

### Dashboard
- Sensor map with location-based visibility
- Latest readings and time-series visualization
- Quick inspection of drain-level pollution indicators

### Alerts
- Automatic anomaly detection from sensor readings
- Severity-based alert generation
- Resolution workflow for active alerts

### Simulation
- Forecast-style pollution risk projection
- Side-by-side scenario comparison
- Policy experimentation by reducing pollutant discharge inputs

### Issue Tracking
- Create issues tied to field observations or system events
- Track open and closed issues
- Support authenticated operational workflows

---

## System Flow

```text
Sensors / Sample Data
        |
        v
Database + Auth Layer
        |
        v
ML Detection + Risk Logic
        |
        v
FastAPI Backend
        |
        v
Streamlit Dashboard
        |
        v
Alerts, Issues, and Action
```

---

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Streamlit, Plotly, Pandas |
| PostgreSQL & Auth | Supabase (PostgreSQL + Auth) |
| Backend (REST APIs) | FastAPI, SQLAlchemy, Uvicorn |
| ML Model | Scikit-learn `IsolationForest`, Linear Regression |
| Programming Language | Python |
| Version Control & Hosting | Git, GitHub, Streamlit Community Cloud |

### Stack Breakdown

**Frontend**
- Streamlit powers the dashboard UI
- Plotly handles interactive charts and map-based visualization
- Pandas is used for shaping and displaying sensor data

**PostgreSQL & Auth**
- Supabase provides the hosted PostgreSQL layer
- Supabase Auth enables sign-in, sign-up, and protected workflows

**Backend (REST APIs)**
- FastAPI exposes endpoints for readings, sensors, alerts, issues, prediction, and simulation
- SQLAlchemy manages models and database access

**ML Model (Isolation Forest)**
- `IsolationForest` is used for anomaly detection on water-quality readings
- A lightweight regression-based risk projection supports forecasting and policy simulation

**Programming Language**
- Python is used across the frontend, backend, data processing, and ML layers

**Version Control & Hosting**
- Git and GitHub support collaboration and version tracking
- The app is designed for simple cloud deployment, with the current frontend hosted on Streamlit

---

## Project Structure

```text
drishti/
|-- backend/        # FastAPI app, DB models, auth, ML utilities
|-- frontend/       # Streamlit dashboard and assets
|-- migrations/     # SQL migration files
|-- scripts/        # Testing, setup, and sample-data utilities
|-- supabase_client.py
|-- streamlit_app.py
`-- README.md
```

---

## Use Cases

- Continuous monitoring of river or drain segments
- Early detection of abnormal pollution spikes
- Comparing likely outcomes before applying mitigation measures
- Giving field and operations teams a single place to track system events

---

## Vision

DRISHTI is not just a dashboard. It is a prototype for how environmental monitoring systems can become more actionable: less static reporting, more real-time visibility, and faster intervention when water quality starts to deteriorate.

---



