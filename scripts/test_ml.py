"""Quick ML smoke tests."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import numpy as np
from backend import ml
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
rows = []
for i in range(48):
    rows.append({
        "timestamp": now - timedelta(hours=(48 - i)),
        "pH": 7 + np.random.randn() * 0.1,
        "DO2": 6 + np.random.randn() * 0.5,
        "BOD": max(0, 5 + np.random.randn() * 1.5),
        "COD": max(0, 50 + np.random.randn() * 10),
        "turbidity": max(0, 20 + np.random.randn() * 5),
        "ammonia": abs(np.random.randn() * 0.5),
        "temperature": 25 + np.random.randn() * 1.5,
        "conductivity": 300 + np.random.randn() * 20,
    })

df = pd.DataFrame(rows)

print("Anomaly detection ->", ml.anomaly_detection(df)[0].shape)
print("Predict risk ->", len(ml.predict_risk(df)["next_24h"]))
print("Simulate policy ->", len(ml.simulate_policy(df, 20)["next_24h"]))
