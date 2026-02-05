"""Seed some sensors into the DB using the SQLAlchemy models (runs inside project).
Usage: python -m scripts.init_db
"""
from backend.db import SessionLocal, init_db
from backend.models import Sensor

init_db()

sensors = [
    {"id": 1, "name": "Yamuna Upstream - Wazirabad", "lat": 28.707, "lon": 77.235},
    {"id": 2, "name": "Najafgarh Drain Entry", "lat": 28.553, "lon": 77.095},
    {"id": 3, "name": "Okhla Barrage", "lat": 28.547, "lon": 77.270},
]

if __name__ == "__main__":
    db = SessionLocal()
    for s in sensors:
        if not db.query(Sensor).filter(Sensor.id == s["id"]).first():
            db.add(Sensor(id=s["id"], name=s["name"], lat=s["lat"], lon=s["lon"]))
    db.commit()
    print("Sensors seeded")
    db.close()
