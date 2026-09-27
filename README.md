# AIOps Predictive System: Real-Time Azure Telemetry & Time-to-Threshold Forecaster

A production-quality machine learning and telemetry forecasting platform designed to predict infrastructure capacity breaches and calculate estimated **time-to-threshold** before performance degradation occurs for Azure-hosted applications.

---

## 1. Real-Time Architecture & Decoupled Design

```text
               ┌────────────────────────────────────────────────────────┐
               │              React + Tailwind Dashboard                │
               │   (App Switcher, Live Telemetry, 30m Forecast, Alerts) │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                  HTTP REST Requests
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │                   FastAPI Backend                      │
               │           (/api/applications, /api/v1)                 │
               └───────────────┬────────────────────────┬───────────────┘
                               │                        │
                               ▼                        ▼
               ┌────────────────────────┐      ┌────────────────────────┐
               │    Telemetry Layer     │      │   Application Layer    │
               │  (TelemetryProvider)   │      │(Thresholds, Masked Sec)│
               └───┬────────────────┬───┘      └───────────┬────────────┘
                   │                │                      │
                   ▼                ▼                      ▼
           ┌──────────────┐ ┌──────────────┐     ┌──────────────────────┐
           │   CSV Mode   │ │  Azure Mode  │     │Threshold Normalizer  │
           │ (Synthetic)  │ │(Azure Monitor│     │ (Percentage -> Units)│
           └───────┬──────┘ └───────┬──────┘     └──────────┬───────────┘
                   │                │                       │
                   └────────┬───────┘                       │
                            ▼                               │
               ┌────────────────────────┐                   │
               │  Normalized Telemetry  │                   │
               │ (8 Standard Parameters)│                   │
               └────────────┬───────────┘                   │
                            ▼                               │
               ┌────────────────────────┐                   │
               │  Feature Engineering   │                   │
               │ (Lags, Deltas, Rolling)│                   │
               └────────────┬───────────┘                   │
                            ▼                               │
               ┌────────────────────────┐                   │
               │   8 LightGBM Models    │                   │
               │ (Recursive Multi-Step) │                   │
               └────────────┬───────────┘                   │
                            ▼                               │
               ┌────────────────────────┐                   │
               │ 30m Future Trajectory  │                   │
               └────────────┬───────────┘                   │
                            │                               │
                            ▼                               ▼
               ┌────────────────────────────────────────────────────────┐
               │            Threshold & Alert Engine                    │
               │ (CURRENT_BREACH, PREDICTED_BREACH, Earliest Crossing)  │
               └────────────────────────────┬───────────────────────────┘
                                            │
                                            ▼
               ┌────────────────────────────────────────────────────────┐
               │   Prediction Response & Active Operational Alerts      │
               └────────────────────────────────────────────────────────┘
```

---

## 2. Key Refactoring & Architectural Changes

1. **Automated Telemetry Retrieval**: The user no longer types 8 arbitrary numbers. When clicking **Predict**, the backend automatically fetches the latest telemetry window (last 60–75 minutes) directly from the configured provider (CSV or Azure).
2. **Threshold Normalization Layer**: Users configure all thresholds in **percentages (%)**. A mathematical normalization layer dynamically converts each percentage into effective native metric units based on configurable operational reference limits.
3. **Dedicated Alert Engine**: Distinguishes `CURRENT_BREACH` ($t=0$, CRITICAL), `PREDICTED_BREACH` ($1 \dots 30$ min with Critical $\le 15$m, Warning $16-30$m), and `NO_BREACH` (Safe).
4. **Earliest Predicted Breach**: Automatically identifies which metric will breach first, enabling SREs to prioritize incident triage.
5. **Decoupled Telemetry Layer**: The ML forecasting pipeline receives a standard, normalized schema (`cpu_percent`, `memory_percent`, `disk_io_mb_s`, `latency_ms`, `http_errors`, `http_success`, `network_mb_s`, `request_volume`) without knowing whether data originated from CSV or Azure Monitor.
6. **Strict Security**: Azure Client Secrets are never stored in React state, logs, or API responses (`••••••••` masked).

---

## 3. Threshold Percentage Conversion Formula

The system maps user-entered percentage thresholds to effective native units using the formula:

$$\text{Effective Threshold} = \text{Operational Limit} \times \left(\frac{\text{Threshold Percentage}}{100}\right)$$

### Examples:
* **CPU Utilization** (%): Operational Limit = $100\%$, Threshold = $80\% \to$ Effective Threshold = **80.0%**
* **Latency** (ms): Operational Limit = $500\text{ ms}$, Threshold = $80\% \to$ Effective Threshold = $500 \times 0.80 =$ **400.0 ms**
* **Disk I/O** (MB/s): Operational Limit = $80\text{ MB/s}$, Threshold = $80\% \to$ Effective Threshold = $80 \times 0.80 =$ **64.0 MB/s**
* **HTTP Errors** (count/min): Operational Limit = $50/\text{min}$, Threshold = $80\% \to$ Effective Threshold = $50 \times 0.80 =$ **40.0/min**
* **HTTP Success** (req/min): Operational Limit = $3500/\text{min}$, Threshold = $30\%$, Operator $\le \to$ Effective Threshold = $3500 \times 0.30 =$ **1050.0 req/min**

---

## 4. API Endpoints

### Application & Real-Time Prediction APIs
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/applications` | List registered applications (secrets masked) |
| `POST` | `/api/applications` | Register new application (CSV or Azure connection) |
| `GET` | `/api/applications/{app_id}` | Retrieve application details |
| `PUT` | `/api/applications/{app_id}` | Update application settings |
| `DELETE` | `/api/applications/{app_id}` | Remove application configuration |
| `GET` | `/api/applications/{app_id}/telemetry` | Fetch recent telemetry window |
| `GET` | `/api/applications/{app_id}/telemetry/latest` | Fetch single latest telemetry observation |
| `GET` | `/api/applications/{app_id}/thresholds` | Fetch percentage thresholds & operational limits |
| `PUT` | `/api/applications/{app_id}/thresholds` | Update percentage thresholds & operational limits |
| `POST` | `/api/applications/{app_id}/predict` | **Real-Time Prediction Endpoint**: Automatically pulls telemetry, generates 30m trajectory, calculates time-to-threshold & alerts |

### Sample Real-Time Prediction Request
```bash
POST /api/applications/chatgpt-azure-prod/predict
Content-Type: application/json

{
  "horizon_minutes": 30
}
```

### Sample Real-Time Prediction Response
```json
{
  "application": {
    "id": "chatgpt-azure-prod",
    "name": "ChatGPT Azure Prod"
  },
  "prediction_time": "2026-09-26T13:20:00Z",
  "telemetry_source": "csv",
  "horizon_minutes": 30,
  "overall_status": "AT_RISK",
  "status_summary": "1 metric(s) projected to breach thresholds within 15 minutes.",
  "metrics_breaching_count": 1,
  "earliest_breach": {
    "metric": "cpu_percent",
    "predicted_crossing_minutes": 12,
    "predicted_crossing_time": "2026-09-26T13:32:00Z",
    "effective_threshold": 80.0,
    "current_value": 72.4,
    "severity": "CRITICAL"
  },
  "metrics": [
    {
      "metric": "cpu_percent",
      "unit": "%",
      "current_value": 72.4,
      "threshold_percentage": 80.0,
      "operational_limit": 100.0,
      "effective_threshold": 80.0,
      "operator": ">=",
      "predicted_value_30m": 86.2,
      "status": "PREDICTED_BREACH",
      "predicted_crossing_minutes": 12,
      "predicted_crossing_time": "2026-09-26T13:32:00Z",
      "severity": "CRITICAL",
      "message": "Predicted threshold crossing in ~12 min (Imminent / Critical).",
      "forecast": [
        {"minutes_ahead": 1, "predicted_timestamp": "...", "value": 72.8, "estimated_lower": 71.0, "estimated_upper": 74.6},
        {"minutes_ahead": 30, "predicted_timestamp": "...", "value": 86.2, "estimated_lower": 82.1, "estimated_upper": 90.3}
      ]
    }
  ],
  "failure_probability_30m": 0.04,
  "failure_risk_level": "LOW_FAILURE_RISK",
  "model_version": "1.0.0"
}
```

---

## 5. Development vs. Production Azure Mode

### Development Mode (`telemetry_source: "csv"`)
* Reads from `data/raw/chatgpt_azure_synthetic_telemetry_50000.csv`.
* Fully functional offline without requiring cloud credentials or internet connectivity.
* Provides repeatable time-series sequences for verification.

### Production Azure Mode (`telemetry_source: "azure"`)
* Configured with Azure Service Principal credentials (`tenant_id`, `client_id`, `client_secret`, `subscription_id`, `resource_group`, `resource_name`).
* Acquires OAuth2 bearer token from `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token`.
* Queries Azure Monitor REST API (`https://management.azure.com/.../providers/microsoft.insights/metrics`).
* Normalizes Azure metric names (`Percentage CPU`, `HttpResponseTime`, `Http5xx`, `Requests`) into the standard internal schema.
* Includes automated mock fallback stream when testing without active Azure subscription access.

---

## 6. How to Run the Application

### Option A: Local Execution
```bash
# 1. Activate virtual environment
.\venv\Scripts\activate

# 2. Run backend FastAPI server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. In a separate terminal, start frontend
cd frontend
npm run dev
# Dashboard available at http://localhost:3000 (or http://localhost:5173)
```

### Option B: Run Automated Tests
```bash
.\venv\Scripts\pytest backend/tests/ -v
```
*(All 21 unit, integration, data leakage, and security tests run and pass).*

### Option C: Docker Deployment
```bash
docker compose up --build
```
* **Frontend**: `http://localhost:3000`
* **API Swagger Docs**: `http://localhost:8000/docs`

---

## 7. Limitations & Operational Guidance

1. **Threshold Breach vs. Downtime**: A resource threshold breach reflects capacity saturation; it does not automatically imply a crash.
2. **Prediction Horizon**: The models are calibrated for 30-minute operational forecasting. Projections beyond 60 minutes exhibit wider uncertainty.
3. **Azure Metric Latency**: Azure Monitor metrics typically have a 1–3 minute emission lag in production. The preprocessor accounts for this through timestamp alignment.
