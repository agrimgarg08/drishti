"""Smoke test backend endpoints using TestClient (no external server needed).
Run: python scripts/test_api.py
"""
import sys
import os
# ensure repo root is on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from backend.main import app
import time

client = TestClient(app)

print("health ->", client.get("/health").json())

# list sensors
print("sensors ->", client.get("/sensors").json())

# ingest a reading for sensor 1
payload = {
    "sensor_id": 1,
    "pH": 7.2,
    "DO2": 6.5,
    "BOD": 4.2,
    "COD": 50.3,
    "turbidity": 20.0,
    "ammonia": 0.5,
    "temperature": 28.0,
    "conductivity": 300.0,
}
print("ingest ->", client.post("/ingest-reading", json=payload).json())

# get readings
print("readings ->", client.get("/readings/1").status_code)

# fetch alerts
print("alerts ->", client.get("/alerts").status_code)

# predict risk
print("predict ->", client.post("/predict-risk", json={"sensor_id": 1}).status_code)

# simulate policy
print("simulate ->", client.post("/simulate-policy", json={"sensor_id": 1, "reduction_pct": 20}).status_code)

# create & list issue
print("create issue ->", client.post("/issues", json={"title": "Test", "description": "desc"}).json())
print("issues ->", client.get("/issues").json())

# if an alert exists, resolve it
alerts = client.get("/alerts").json()
if alerts:
    a = alerts[0]
    r = client.post(f"/alerts/{a['id']}/resolve")
    # Endpoint may require authentication; print status and response for visibility
    try:
        body = r.json()
    except Exception:
        body = r.text
    print("resolve ->", r.status_code, body)

print("smoke tests done")
