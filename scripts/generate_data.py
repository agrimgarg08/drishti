"""Simple simulator that posts fake readings to the backend /ingest-reading endpoint.
Usage: python scripts/generate_data.py --url http://localhost:8000 --sensors 5 --count 100
"""
import requests
import random
import time
import argparse
from datetime import datetime, timedelta

PARAM_RANGES = {
    "pH": (6.0, 8.5),
    "DO2": (2.0, 9.0),
    "BOD": (1.0, 20.0),
    "COD": (10.0, 200.0),
    "turbidity": (1.0, 100.0),
    "ammonia": (0.0, 10.0),
    "temperature": (10.0, 35.0),
    "conductivity": (100.0, 2000.0),
}


def make_reading(sensor_id):
    r = {k: round(random.uniform(*v), 2) for k, v in PARAM_RANGES.items()}
    r["sensor_id"] = sensor_id
    r["timestamp"] = datetime.utcnow().isoformat()
    return r


def main(server_url, sensors, count, delay):
    for sid in range(1, sensors + 1):
        # ensure sensor exists by posting one reading
        r = make_reading(sid)
        requests.post(f"{server_url}/ingest-reading", json=r)

    for i in range(count):
        sid = random.randint(1, sensors)
        data = make_reading(sid)

        # occasionally inject anomaly
        if random.random() < 0.03:
            data["BOD"] *= random.uniform(3, 8)
            data["COD"] *= random.uniform(2, 5)
            data["pH"] = random.choice([5.0, 10.0])

        resp = requests.post(f"{server_url}/ingest-reading", json=data)
        print(i + 1, sid, resp.status_code, resp.json())
        time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--sensors", type=int, default=5)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0.5)

    args = parser.parse_args()
    main(args.url, args.sensors, args.count, args.delay)
