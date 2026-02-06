import os
import streamlit as st
from supabase import create_client
import pandas as pd
from typing import List, Dict
from dotenv import load_dotenv

# Load local .env as a fallback so you can put SUPABASE_URL and SUPABASE_KEY in a .env file (make sure it's gitignored)
load_dotenv()


def _get_creds():
    # Prefer Streamlit secrets, fallback to env vars
    url = None
    key = None
    if hasattr(st, "secrets") and st.secrets.get("SUPABASE_URL"):
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    else:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in Streamlit secrets or env vars")
    return url, key


@st.cache_resource
def get_supabase_client():
    url, key = _get_creds()
    # create_client returns an object that should be cached as a resource, not data
    return create_client(url, key)


@st.cache_data(ttl=60)
def get_sensors() -> List[Dict]:
    """Return list of sensors from `sensors` table."""
    supabase = get_supabase_client()
    # order() uses 'desc' flag (supabase-py); use desc=False for ascending
    res = supabase.table("sensors").select("*").order("id", desc=False).execute()
    data = res.data if hasattr(res, "data") else res
    return data or []


@st.cache_data(ttl=60)
def get_latest_readings_for_all() -> Dict[int, Dict]:
    """Return a mapping sensor_id -> latest reading (or None).
    This does one query and groups locally.
    """
    supabase = get_supabase_client()
    # Fetch recent readings (limit to latest 2000) and pick latest per sensor
    res = supabase.table("readings").select("*").order("timestamp", desc=True).limit(2000).execute()
    rows = res.data or []
    by_sensor = {}
    for r in rows:
        sid = int(r.get("sensor_id"))
        if sid not in by_sensor:
            by_sensor[sid] = r
    return by_sensor


@st.cache_data(ttl=60)
def get_unresolved_alerts_counts() -> Dict[int, int]:
    """Return mapping sensor_id -> unresolved alerts count."""
    supabase = get_supabase_client()
    res = supabase.table("alerts").select("sensor_id, resolved").eq("resolved", False).execute()
    rows = res.data or []
    counts = {}
    for r in rows:
        sid = int(r.get("sensor_id"))
        counts[sid] = counts.get(sid, 0) + 1
    return counts


@st.cache_data(ttl=60)
def get_alerts(unresolved_only: bool = True) -> List[Dict]:
    """Return alerts from `alerts` table, optionally filtering to unresolved only."""
    supabase = get_supabase_client()
    q = supabase.table("alerts").select("*")
    if unresolved_only:
        q = q.eq("resolved", False)
    res = q.order("timestamp", desc=True).execute()
    data = res.data if hasattr(res, "data") else res
    return data or []


def resolve_alert(alert_id: int, access_token: str = None) -> Dict:
    """Resolve an alert by setting resolved=true. Requires access_token if RLS is enabled."""
    supabase = get_supabase_client()
    if access_token:
        try:
            supabase.auth.set_session(access_token, "")
        except Exception:
            pass
    res = supabase.table("alerts").update({"resolved": True}).eq("id", alert_id).execute()
    data = res.data if hasattr(res, "data") else res
    return data[0] if data else {}


@st.cache_data(ttl=60)
def get_issues() -> List[Dict]:
    """Return issues list from `issues` table."""
    supabase = get_supabase_client()
    res = supabase.table("issues").select("*").order("created_at", desc=True).execute()
    data = res.data if hasattr(res, "data") else res
    return data or []


def create_issue(title: str, description: str, created_by: str, access_token: str = None) -> Dict:
    """Create an issue row. Requires access_token if RLS is enabled."""
    supabase = get_supabase_client()
    if access_token:
        try:
            supabase.auth.set_session(access_token, "")
        except Exception:
            pass
    payload = {"title": title, "description": description, "created_by": created_by}
    res = supabase.table("issues").insert(payload).execute()
    data = res.data if hasattr(res, "data") else res
    return data[0] if data else {}


def update_issue_status(issue_id: int, status: str, access_token: str = None) -> Dict:
    """Update issue status. Requires access_token if RLS is enabled."""
    supabase = get_supabase_client()
    if access_token:
        try:
            supabase.auth.set_session(access_token, "")
        except Exception:
            pass
    res = supabase.table("issues").update({"status": status}).eq("id", issue_id).execute()
    data = res.data if hasattr(res, "data") else res
    return data[0] if data else {}


def get_sensor_details() -> List[Dict]:
    """Return combined sensor info for display: sensor fields + latest reading + alert count."""
    sensors = get_sensors()
    latest = get_latest_readings_for_all()
    alerts = get_unresolved_alerts_counts()

    out = []
    for s in sensors:
        sid = int(s.get("id"))
        lr = latest.get(sid)
        a_count = alerts.get(sid, 0)
        d = {
            "id": sid,
            "name": s.get("name"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "type": s.get("type"),
            "last_service": s.get("last_service"),
            "latest_reading": lr,
            "alert_count": a_count,
        }
        out.append(d)
    return out


def get_readings_for_sensor(sensor_id: int, limit: int = 500):
    supabase = get_supabase_client()
    res = supabase.table("readings").select("*").eq("sensor_id", sensor_id).order("timestamp", desc=True).limit(limit).execute()
    rows = res.data or []
    # Convert to DataFrame for easy plotting
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    return df
