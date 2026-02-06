"""Simple ML utilities using pandas and scikit-learn.
Functions:
- anomaly_detection(df): returns DataFrame with 'anomaly' column and a list of alerts
- predict_risk(df): predicts risk score for next 24 hours (hourly)
- simulate_policy(df, reduction_pct): returns adjusted dataframe and projected improvement
"""
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import timedelta

NUMERIC_COLS = ["ph", "do2", "bod", "cod", "turbidity", "ammonia", "temperature", "conductivity"]


def anomaly_detection(df: pd.DataFrame, contamination: float = 0.05):
    """Mark anomalies using IsolationForest on numeric sensors.
    Returns (df_with_flag, alerts_list)
    """
    df = df.copy()
    if df.empty:
        return df, []

    X = df[NUMERIC_COLS].fillna(0).values
    iso = IsolationForest(contamination=contamination, random_state=42)
    preds = iso.fit_predict(X)
    df["anomaly"] = preds == -1

    alerts = []
    for _, row in df[df["anomaly"]].iterrows():
        alerts.append({
            "sensor_id": int(row.get("sensor_id", -1)),
            "message": "Anomalous reading detected",
            "severity": "high",
            "timestamp": row.get("timestamp"),
        })
    return df, alerts


def _pollution_index(row):
    # Simple normalized indicator: higher is worse
    # ph is neutral around 7; penalize if outside 6.5-8
    score = 0.0
    score += max(0, abs(row.get("ph", 7) - 7)) * 1.0
    score += max(0, (8 - row.get("DO2", 8))) * 1.5  # low DO2 is bad
    score += row.get("bod", 0) * 0.2
    score += row.get("cod", 0) * 0.1
    score += row.get("turbidity", 0) * 0.05
    score += row.get("ammonia", 0) * 0.2
    score += row.get("conductivity", 0) * 0.01
    return score


def predict_risk(df: pd.DataFrame):
    """Predict pollution risk (pollution index) for next 24 hours hourly using linear regression.
    Returns a dict: {"next_24h": [{"ts":..., "risk": ...}, ...], "baseline": current_score}
    """
    df = df.copy()
    if df.empty:
        return {"next_24h": [], "baseline": 0}

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)
    df["score"] = df.apply(_pollution_index, axis=1)

    # Aggregate hourly
    numeric_cols = [
    "ph", "do2", "bod", "cod",
    "turbidity", "ammonia",
    "temperature", "conductivity",
    "score"
    ]
    df_hour = (
    df.set_index("timestamp")[numeric_cols]
    .resample("1h")
    .mean()
    .interpolate()
    )
    df_hour = df_hour.reset_index()
    if df_hour.shape[0] < 2:
        # Not enough data, repeat last value
        last_score = df["score"].iloc[-1]
        next_24 = []
        ts = pd.to_datetime(df["timestamp"].iloc[-1])
        for i in range(1, 25):
            next_24.append({"ts": (ts + timedelta(hours=i)).isoformat(), "risk": float(last_score)})
        return {"next_24h": next_24, "baseline": float(last_score)}

    # Use past hourly averages to predict future
    df_hour["t_idx"] = np.arange(len(df_hour))
    model = LinearRegression()
    model.fit(df_hour[["t_idx"]], df_hour[["score"]])

    last_idx = df_hour["t_idx"].iloc[-1]
    next_24 = []
    for i in range(1, 25):
        t_df = pd.DataFrame({"t_idx": [last_idx + i]})
        pred = model.predict(t_df)[0, 0]
        next_24.append({"ts": (df_hour["timestamp"].iloc[-1] + timedelta(hours=i)).isoformat(), "risk": float(max(pred, 0))})

    baseline = float(df["score"].mean())
    return {"next_24h": next_24, "baseline": baseline}


def simulate_policy(df: pd.DataFrame, reduction_pct: float):
    """Apply a simple reduction to pollutant columns and return projected improvement in risk.
    reduction_pct: 0-100
    Returns {"projected_baseline": float, "projected_next_24h": [...]}
    """
    factor = max(0.0, min(1.0, 1.0 - reduction_pct / 100.0))
    df = df.copy()
    if df.empty:
        return {"projected_baseline": 0, "projected_next_24h": []}

    # Reduce pollutant columns (bod, cod, turbidity, ammonia, conductivity)
    for col in ["bod", "cod", "turbidity", "ammonia", "conductivity"]:
        if col in df.columns:
            df[col] = df[col] * factor

    # Reuse predict_risk on adjusted data
    return predict_risk(df)
