from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from .db import init_db, get_db
from . import models, ml
from fastapi.middleware.cors import CORSMiddleware
from .auth import get_current_user

app = FastAPI(title="Yamuna Monitor - Backend")

# Allow CORS for local dev and Streamlit Cloud (keep open for prototype)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup (simple for prototype)
init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


class IngestReading(BaseModel):
    sensor_id: int
    timestamp: Optional[datetime] = None
    pH: Optional[float] = None
    DO2: Optional[float] = None
    BOD: Optional[float] = None
    COD: Optional[float] = None
    turbidity: Optional[float] = None
    ammonia: Optional[float] = None
    temperature: Optional[float] = None
    conductivity: Optional[float] = None


class PredictRequest(BaseModel):
    sensor_id: int


class SimulateRequest(BaseModel):
    sensor_id: int
    reduction_pct: float


class IssueCreate(BaseModel):
    title: str
    description: Optional[str] = None
    created_by: Optional[str] = None


@app.post("/ingest-reading")
def ingest_reading(payload: IngestReading, db: Session = Depends(get_db)):
    # Ensure sensor exists
    sensor = db.query(models.Sensor).filter(models.Sensor.id == payload.sensor_id).first()
    if not sensor:
        # create a simple placeholder sensor (in real world, sensors should be registered separately)
        sensor = models.Sensor(id=payload.sensor_id, name=f"Sensor {payload.sensor_id}", lat=28.653, lon=77.23)
        db.add(sensor)
        db.commit()
        db.refresh(sensor)

    reading = models.Reading(
        sensor_id=payload.sensor_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        pH=payload.pH,
        DO2=payload.DO2,
        BOD=payload.BOD,
        COD=payload.COD,
        turbidity=payload.turbidity,
        ammonia=payload.ammonia,
        temperature=payload.temperature,
        conductivity=payload.conductivity,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Simple anomaly detection using last 100 readings for this sensor
    rows = db.query(models.Reading).filter(models.Reading.sensor_id == payload.sensor_id).order_by(models.Reading.timestamp.desc()).limit(100).all()
    import pandas as pd

    df = pd.DataFrame([{
        "sensor_id": r.sensor_id,
        "timestamp": r.timestamp,
        "pH": r.pH,
        "DO2": r.DO2,
        "BOD": r.BOD,
        "COD": r.COD,
        "turbidity": r.turbidity,
        "ammonia": r.ammonia,
        "temperature": r.temperature,
        "conductivity": r.conductivity,
    } for r in rows])

    df2, alerts = ml.anomaly_detection(df)

    created_alerts = []
    for a in alerts:
        alert = models.Alert(sensor_id=a["sensor_id"], message=a["message"], severity=a["severity"], timestamp=a.get("timestamp"))
        db.add(alert)
        db.commit()
        db.refresh(alert)
        created_alerts.append({"id": alert.id, "message": alert.message})

    return {"status": "ok", "reading_id": reading.id, "alerts_created": created_alerts}


@app.get("/readings/{sensor_id}")
def get_readings(sensor_id: int, limit: int = 200, db: Session = Depends(get_db)):
    rows = db.query(models.Reading).filter(models.Reading.sensor_id == sensor_id).order_by(models.Reading.timestamp.desc()).limit(limit).all()
    return [{
        "id": r.id,
        "sensor_id": r.sensor_id,
        "timestamp": r.timestamp.isoformat(),
        "pH": r.pH,
        "DO2": r.DO2,
        "BOD": r.BOD,
        "COD": r.COD,
        "turbidity": r.turbidity,
        "ammonia": r.ammonia,
        "temperature": r.temperature,
        "conductivity": r.conductivity,
    } for r in rows]


@app.get("/alerts")
def get_alerts(unresolved_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(models.Alert)
    if unresolved_only:
        q = q.filter(models.Alert.resolved == False)
    rows = q.order_by(models.Alert.timestamp.desc()).all()
    return [{"id": a.id, "sensor_id": a.sensor_id, "severity": a.severity, "message": a.message, "timestamp": a.timestamp.isoformat(), "resolved": a.resolved} for a in rows]


@app.get("/sensors")
def list_sensors(db: Session = Depends(get_db)):
    """Return list of registered sensors."""
    rows = db.query(models.Sensor).order_by(models.Sensor.id).all()
    return [{
        "id": s.id,
        "name": s.name,
        "lat": s.lat,
        "lon": s.lon,
        "type": s.type,
        "last_service": s.last_service.isoformat() if s.last_service else None,
    } for s in rows]


# Note: Unauthenticated resolve endpoint removed. Use the auth-protected resolver defined later to require authentication when resolving alerts.


class IssueUpdate(BaseModel):
    status: str


# Note: Unauthenticated issue update endpoint removed. Use the auth-protected `/issues/{issue_id}` PATCH endpoint defined later to require authenticated updates.


@app.post("/predict-risk")
def predict_risk(payload: PredictRequest, db: Session = Depends(get_db)):
    rows = db.query(models.Reading).filter(models.Reading.sensor_id == payload.sensor_id).order_by(models.Reading.timestamp.desc()).limit(500).all()
    import pandas as pd
    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "pH": r.pH,
        "DO2": r.DO2,
        "BOD": r.BOD,
        "COD": r.COD,
        "turbidity": r.turbidity,
        "ammonia": r.ammonia,
        "temperature": r.temperature,
        "conductivity": r.conductivity,
    } for r in rows])

    result = ml.predict_risk(df)
    return result


@app.post("/simulate-policy")
def simulate_policy(payload: SimulateRequest, db: Session = Depends(get_db)):
    rows = db.query(models.Reading).filter(models.Reading.sensor_id == payload.sensor_id).order_by(models.Reading.timestamp.desc()).limit(500).all()
    import pandas as pd
    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "pH": r.pH,
        "DO2": r.DO2,
        "BOD": r.BOD,
        "COD": r.COD,
        "turbidity": r.turbidity,
        "ammonia": r.ammonia,
        "temperature": r.temperature,
        "conductivity": r.conductivity,
    } for r in rows])

    res = ml.simulate_policy(df, payload.reduction_pct)
    return res


@app.post("/issues")
def create_issue(payload: IssueCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create an issue. If authenticated, use user's email as created_by."""
    creator = None
    if current_user and isinstance(current_user, dict):
        creator = current_user.get("email") or current_user.get("user_metadata", {}).get("email")
    issue = models.Issue(title=payload.title, description=payload.description, created_by=creator or payload.created_by or "anonymous")
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return {"id": issue.id, "status": issue.status}


@app.get("/issues")
def list_issues(db: Session = Depends(get_db)):
    rows = db.query(models.Issue).order_by(models.Issue.created_at.desc()).all()
    return [{"id": i.id, "title": i.title, "status": i.status, "created_by": i.created_by, "created_at": i.created_at.isoformat()} for i in rows]


@app.patch("/issues/{issue_id}")
def update_issue(issue_id: int, payload: IssueUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # require authentication to update issues
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to update issues")
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = payload.status
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return {"id": issue.id, "status": issue.status}


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Mark an alert as resolved — requires authentication."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to resolve alerts")
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "resolved": alert.resolved}
