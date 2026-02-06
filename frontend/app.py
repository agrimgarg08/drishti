"""Streamlit frontend for the DRISHTI.
Run: streamlit run frontend/app.py
"""
import os
import sys
import pathlib
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import supabase
from supabase import ClientOptions
import numpy as np
from sklearn.linear_model import LinearRegression

# Ensure repo root is on sys.path so we can import modules from project root (like supabase_client)
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(page_title="Drishti", layout="wide")

st.markdown(
    """
    <style>
    /* Target the sidebar title */
    section[data-testid="stSidebar"] h1 {
        font-size: 64px !important;  /* Increase font size */
        font-weight: bold;           /* Optional: make it bold */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.title("DRISHTI", text_alignment="center")
page = st.sidebar.selectbox("Select Page", ["Dashboard", "Alerts", "Simulation", "Issues"], label_visibility="collapsed")

# Supabase auth (rebuilt)
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client

        class _SessionStorage:
            def __init__(self):
                if "_supabase_storage" not in st.session_state:
                    st.session_state["_supabase_storage"] = {}

            def get_item(self, key: str):
                return st.session_state["_supabase_storage"].get(key)

            def set_item(self, key: str, value: str) -> None:
                st.session_state["_supabase_storage"][key] = value

            def remove_item(self, key: str) -> None:
                st.session_state["_supabase_storage"].pop(key, None)

        options = ClientOptions(storage=_SessionStorage(), flow_type="implicit")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
    except Exception:
        supabase = None

if "user" not in st.session_state:
    st.session_state["user"] = None
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = None


def _get_attr(obj, key):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_user(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("user") or obj.get("data")
    return getattr(obj, "user", None) or getattr(obj, "data", None)


def _extract_session(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("session")
    return getattr(obj, "session", None)


def _get_user_email(user):
    if not user:
        return None
    email = _get_attr(user, "email")
    if email:
        return email
    meta = _get_attr(user, "user_metadata")
    if isinstance(meta, dict):
        return meta.get("email")
    return getattr(meta, "email", None)


def _set_session_from_tokens(access_token, refresh_token):
    if not access_token or not refresh_token or not supabase:
        return False
    try:
        supabase.auth.set_session(access_token, refresh_token)
        user_res = supabase.auth.get_user()
        user = _extract_user(user_res)
        if user:
            st.session_state["user"] = user
            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = refresh_token
            return True
    except Exception:
        return False
    return False


st.sidebar.markdown("### Authentication (using Supabase)")
if supabase:
    # Restore session if we already have tokens
    if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
        _set_session_from_tokens(st.session_state["access_token"], st.session_state["refresh_token"])

    if not st.session_state["user"]:
        # Email/password login
        email = st.sidebar.text_input("Email", key="email")
        pw = st.sidebar.text_input("Password", type="password", key="pw")
        cols = st.sidebar.columns(2)
        if cols[0].button("Sign in"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                session = _extract_session(res)
                user = _extract_user(res) or _extract_user(session)
                if session:
                    st.session_state["access_token"] = _get_attr(session, "access_token")
                    st.session_state["refresh_token"] = _get_attr(session, "refresh_token")
                if user:
                    st.session_state["user"] = user
                    st.sidebar.success("Signed in")
                    st.rerun()
                else:
                    st.sidebar.error("Sign in failed")
            except Exception:
                st.sidebar.error("Auth error")
        if cols[1].button("Sign up"):
            try:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.sidebar.info("Signup requested. Check email for confirmation.")
            except Exception:
                st.sidebar.error("Signup failed")

    else:
        st.sidebar.write(f"Signed in: {_get_user_email(st.session_state['user'])}")
        if st.sidebar.button("Sign out"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state["user"] = None
            st.session_state["access_token"] = None
            st.session_state["refresh_token"] = None
            st.rerun()
else:
    st.sidebar.info("Supabase not configured. Add SUPABASE_URL and SUPABASE_KEY.")


def fetch_sensors():
    try:
        resp = requests.get(f"{API_BASE}/sensors")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return []
    return []


def dashboard():
    st.title("Dashboard")

    # Controls
    st.sidebar.markdown("### Map / Sensor Details")
    show_only_with_alerts = st.sidebar.checkbox("Show data for active alerts only", value=False)
    if st.sidebar.button("Refresh sensor data"):
        # clear cached supabase queries
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun() # DO NOT CHANGE!!!

    st.subheader("Sensor Map")
    try:
        from supabase_client import get_sensor_details, get_readings_for_sensor

        sensors = get_sensor_details()
    except Exception as e:
        st.error(f"Error fetching sensors from Supabase: {e}")
        sensors = []

    if not sensors:
        st.info("No sensors detected. Ensure SUPABASE_URL and SUPABASE_KEY are set in Streamlit secrets and the `sensors` table exists.")
        return

    # Build DataFrame for map
    def _row_to_flat(r):
        lr = r.get("latest_reading") or {}
        alert_count = r.get("alert_count", 0)
        alert_color = 'green' if alert_count == 0 else 'red'
        return {
            "id": r.get("id"),
            "name": r.get("name"),
            "lat": r.get("lat"),
            "lon": r.get("lon"),
            "last_service": r.get("last_service"),
            "alert_count": r.get("alert_count", 0),
            "pH": lr.get("pH"),
            "DO2": lr.get("DO2"),
            "BOD": lr.get("BOD"),
            "COD": lr.get("COD"),
            "turbidity": lr.get("turbidity"),
            "ammonia": lr.get("ammonia"),
            "temperature": lr.get("temperature"),
            "conductivity": lr.get("conductivity"),
            "latest_ts": lr.get("timestamp") if lr else None,
            "alert_color": alert_color,
        }

    rows = [_row_to_flat(r) for r in sensors]
    dfmap = pd.DataFrame(rows)

    if show_only_with_alerts:
        dfmap = dfmap[dfmap["alert_count"] > 0]

    # Plot using Plotly map (MapLibre; no token needed)
    if not dfmap.empty:
        # 
        center_lat = 28.6625
        center_lon = 77.2564
        fig = px.scatter_map(
            dfmap,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"id": True, "lat": True, "lon": True, "alert_count": True},
            zoom=9.7,
            height=500,
        )
        # Color markers by alert status: green (no alerts), red (alerts)
        fig.update_traces(
            marker=dict(size=10, color=dfmap["alert_color"], opacity=0.9),
            selector=dict(mode="markers"),
            customdata=dfmap[
                [
                    "id",
                    "lat",
                    "lon",
                    "alert_count",
                ]
            ],
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "ID: %{customdata[0]}<br>"
                "Latitude: %{customdata[1]:.4f}<br>"
                "Longitude: %{customdata[2]:.4f}<br>"
                "Alerts: %{customdata[3]}<br>"
                "<extra></extra>"
            ),
        )
        fig.update_layout(
            map_style="basic",
            map_center={"lat": center_lat, "lon": center_lon},
            margin=dict(l=0, r=0, t=0, b=0),
        )
        # Render chart simply (no optional click-to-select to avoid instability)
        st.plotly_chart(fig, width="stretch", config={"scrollZoom": False})
    else:
        st.info("No points to display on map.")
    st.divider()
    # Sensor detail panel
    st.subheader("Sensor Details & Readings")
    sensor_ids = sorted([int(x) for x in dfmap["id"].tolist()])
    
    # If filtering by alerts and no sensors match, show info and return
    if show_only_with_alerts and not sensor_ids:
        st.info("No sensors with active alerts found.")
        return
    
    # Number input for selecting sensor ID
    sid = st.number_input(
        "Enter Sensor ID",
        min_value=min(sensor_ids),
        max_value=max(sensor_ids),
        value=sensor_ids[0] if sensor_ids else 1,
        step=1,
    )
    
    # Validate that the entered ID exists
    if sid not in sensor_ids:
        st.error(f"Invalid drain ID: {int(sid)}")
        return

    df = None
    try:
        df = get_readings_for_sensor(sid)
    except Exception as e:
        st.error(f"Error fetching readings for sensor {sid}: {e}")
        st.info("This may be a temporary issue. Try refreshing the sensor data or selecting a different sensor.")
        df = None
    
    if df is None or df.empty:
        st.info("No readings yet for selected sensor.")
    else:
        # Normalize common parameter column names to canonical forms (case-insensitive) and coerce to numeric
        canonical = {
            "ph": "pH",
            "do2": "DO2",
            "bod": "BOD",
            "cod": "COD",
            "turbidity": "turbidity",
            "ammonia": "ammonia",
            "temperature": "temperature",
            "conductivity": "conductivity",
        }
        rename = {}
        for c in df.columns:
            lc = str(c).lower()
            if lc in canonical and c != canonical[lc]:
                rename[c] = canonical[lc]
        if rename:
            df = df.rename(columns=rename)

        # Coerce expected numeric parameters to numbers to ensure plotting and metrics work
        for c in ["pH", "DO2", "BOD", "COD", "turbidity", "ammonia", "temperature", "conductivity"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        # Use the most recent non-null value for each parameter so metrics show available readings
        
        cols1 = st.columns(4)
        cols2 = st.columns(4)
        
        def _last_non_null(df, col):
            try:
                if col in df.columns:
                    s = df[col].dropna()
                    return s.iloc[-1] if not s.empty else None
            except Exception:
                return None
            return None

        ph_val = _last_non_null(df, "pH")
        do2_val = _last_non_null(df, "DO2")
        bod_val = _last_non_null(df, "BOD")
        cod_val = _last_non_null(df, "COD")
        temp_val = _last_non_null(df, "temperature")
        turb_val = _last_non_null(df, "turbidity")
        ammo_val = _last_non_null(df, "ammonia")
        cond_val = _last_non_null(df, "conductivity")

        cols1[0].metric("pH", round(ph_val, 2) if pd.notna(ph_val) else "—")
        cols1[1].metric("DO₂ (mg/L)", round(do2_val, 2) if pd.notna(do2_val) else "—")
        cols1[2].metric("BOD (mg/L)", round(bod_val, 2) if pd.notna(bod_val) else "—")
        cols1[3].metric("COD (mg/L)", round(cod_val, 2) if pd.notna(cod_val) else "—")

        cols2[0].metric("Temp (°C)", round(temp_val, 2) if pd.notna(temp_val) else "—")
        cols2[1].metric("Turbidity (FNU)", round(turb_val, 2) if pd.notna(turb_val) else "—")
        cols2[2].metric("Ammonia (mg/L)", round(ammo_val, 2) if pd.notna(ammo_val) else "—")
        cols2[3].metric("Conductivity (μS/cm)", round(cond_val, 2) if pd.notna(cond_val) else "—")

        # Time series chart (last 14 days only)
        tdf = df.copy()
        tdf = tdf.sort_values("timestamp")
        if "timestamp" in tdf.columns and not tdf["timestamp"].isna().all():
            latest_ts = pd.to_datetime(tdf["timestamp"]).max()
            if pd.notna(latest_ts):
                window_start = latest_ts - pd.Timedelta(days=14)
                tdf = tdf[tdf["timestamp"] >= window_start]
        # Safely plot parameters by reshaping to long format to avoid Plotly length errors
        params = ["pH", "DO2", "BOD", "COD", "turbidity", "ammonia", "temperature", "conductivity"]
        available = [p for p in params if p in tdf.columns]
        if not available:
            st.info("No parameter columns available for plotting.")
        else:
            dfm = tdf.melt(id_vars="timestamp", value_vars=available, var_name="parameter", value_name="value")
            # Replace internal parameter code with display-friendly labels for plotting (DO₂ displayed but internal column remains DO2)
            dfm["parameter"] = dfm["parameter"].replace({
                "DO2": "DO₂",
                "turbidity": "Turbidity",
                "ammonia": "Ammonia",
                "temperature": "Temperature",
                "conductivity": "Conductivity",
            })
            dfm = dfm.dropna(subset=["value"])  # drop missing values
            try:
                fig = px.line(
                    dfm,
                    x="timestamp",
                    y="value",
                    color="parameter",
                    labels={"parameter": "Parameters", "timestamp": "Timestamp", "value": "Value"},
                )
                st.plotly_chart(fig, width="stretch")
            except Exception as e:
                st.error(f"Failed to render chart: {e}")
                st.write(dfm.head())

        st.write("Latest 10 readings")
        if "timestamp" in tdf.columns:
            latest10 = tdf.sort_values("timestamp", ascending=False).head(10)
        else:
            latest10 = tdf.tail(10)
        st.dataframe(latest10)

        # Link to alerts for this sensor
        a_count = int(dfmap.loc[dfmap["id"] == sid, "alert_count"].iloc[0]) if not dfmap.loc[dfmap["id"] == sid].empty else 0
        if a_count:
            st.warning(f"There is/are {a_count} unresolved alert(s) for this sensor. See the alerts page.")
        else:
            st.success("No active alerts for this sensor.")


def alerts_page():
    st.title("Alerts")
    st.subheader("Existing Alerts")
    unresolved = st.checkbox("Show unresolved only", value=True)
    if st.sidebar.button("Refresh alerts"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()
    # Prefer Supabase directly (no backend needed)
    rows = None
    try:
        from supabase_client import get_alerts

        rows = get_alerts(unresolved_only=unresolved)
    except Exception as e:
        st.error(f"Supabase not reachable: {e}")
        st.info("Check Streamlit secrets for SUPABASE_URL and SUPABASE_KEY.")
        return

    if rows:
        df = pd.DataFrame(rows)
        # Keep a consistent column order if present
        preferred_cols = ["id", "sensor_id", "severity", "message", "timestamp", "resolved"]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        st.dataframe(df, width="stretch")

        # Optional resolve action for unresolved alerts
        unresolved_ids = [a["id"] for a in rows if not a.get("resolved")]
        if unresolved_ids:
            st.subheader("Resolve an Alert")
            alert_id = st.number_input(
                "Enter Alert ID",
                min_value=int(min(unresolved_ids)),
                max_value=int(max(unresolved_ids)),
                value=int(unresolved_ids[0]),
                step=1,
            )
            if alert_id not in unresolved_ids:
                st.error(f"Invalid alert ID: {int(alert_id)}")
                return
            if st.button("Resolve Alert"):
                token = st.session_state.get("access_token")
                if not token:
                    st.error("Sign in with Supabase to resolve alerts")
                else:
                    try:
                        from supabase_client import resolve_alert

                        resolve_alert(
                            int(alert_id),
                            access_token=token,
                            refresh_token=st.session_state.get("refresh_token"),
                        )
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success("Resolved")
                        st.rerun() # DO NOT CHANGE!!!
                    except Exception as e:
                        st.error(f"Failed to resolve: {e}")
    else:
        st.info("No alerts")


def simulation_page():
    st.title("Simulation")
    try:
        from supabase_client import get_sensors

        sensors = get_sensors()
        sensor_ids = sorted([int(s.get("id")) for s in sensors if s.get("id") is not None])
    except Exception:
        sensor_ids = []

    if sensor_ids:
        sid = st.number_input(
            "Enter Sensor ID",
            min_value=min(sensor_ids),
            max_value=max(sensor_ids),
            value=sensor_ids[0],
            step=1,
        )
    else:
        sid = st.number_input("Enter Sensor ID", min_value=1, max_value=1000, value=1)
    pct = st.slider("Reduce pollutant discharges by %", min_value=0, max_value=100, value=20)
    horizon = st.slider("Forecast horizon (hours)", min_value=24, max_value=168, value=72, step=24)
    if st.button("Simulate"):
        try:
            from supabase_client import get_readings_for_sensor
        except Exception as e:
            st.error(f"Supabase not reachable: {e}")
            return

        df_raw = get_readings_for_sensor(int(sid), limit=500)
        if df_raw is None or df_raw.empty:
            st.info("No readings available for this sensor.")
            return

        # Normalize columns to lowercase for modeling
        df_raw = df_raw.copy()
        df_raw.columns = [str(c).lower() for c in df_raw.columns]
        if "timestamp" in df_raw.columns:
            df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        else:
            st.error("Missing timestamp column for simulation.")
            return

        def _pollution_index(row):
            """Return a 0-100 normalized risk score (higher = worse)."""
            # Expected ranges for normalization
            ph = row.get("ph", 7)
            do2 = row.get("do2", 8)
            bod = row.get("bod", 0)
            cod = row.get("cod", 0)
            turb = row.get("turbidity", 0)
            ammo = row.get("ammonia", 0)
            cond = row.get("conductivity", 0)

            # Normalize 0-1 (clamp)
            ph_dev = min(abs(ph - 7) / 3.0, 1.0)  # pH outside 4-10 treated as max risk
            do_def = min(max(0.0, (8 - do2) / 6.0), 1.0)  # DO2 below 2 is worst
            bod_n = min(max(bod / 20.0, 0.0), 1.0)
            cod_n = min(max(cod / 200.0, 0.0), 1.0)
            turb_n = min(max(turb / 100.0, 0.0), 1.0)
            ammo_n = min(max(ammo / 10.0, 0.0), 1.0)
            cond_n = min(max(cond / 2000.0, 0.0), 1.0)

            # Weighted sum -> 0-1
            score_0_1 = (
                0.15 * ph_dev
                + 0.20 * do_def
                + 0.20 * bod_n
                + 0.15 * cod_n
                + 0.10 * turb_n
                + 0.10 * ammo_n
                + 0.10 * cond_n
            )
            # Scale to 0-100 and clamp
            return float(min(max(score_0_1 * 100.0, 0.0), 100.0))

        def _forecast(df_in: pd.DataFrame):
            df_in = df_in.sort_values("timestamp")
            df_in["score"] = df_in.apply(_pollution_index, axis=1)
            df_hour = df_in.set_index("timestamp").resample("1h").mean().interpolate().reset_index()
            if df_hour.shape[0] < 6:
                last_score = float(df_in["score"].iloc[-1])
                ts = pd.to_datetime(df_in["timestamp"].iloc[-1])
                out = [{"ts": (ts + pd.Timedelta(hours=i)).isoformat(), "risk": last_score} for i in range(1, horizon + 1)]
                return out, float(df_in["score"].mean()), df_hour.shape[0], True
            df_hour["t_idx"] = np.arange(len(df_hour))
            model = LinearRegression()
            model.fit(df_hour[["t_idx"]], df_hour[["score"]])
            last_idx = df_hour["t_idx"].iloc[-1]
            out = []
            for i in range(1, horizon + 1):
                pred = model.predict(pd.DataFrame({"t_idx": [last_idx + i]}))[0, 0]
                out.append(
                    {
                        "ts": (df_hour["timestamp"].iloc[-1] + pd.Timedelta(hours=i)).isoformat(),
                        "risk": float(max(pred, 0)),
                    }
                )
            return out, float(df_in["score"].mean()), df_hour.shape[0], False

        # Baseline forecast
        base_next, base_avg, base_points, base_flat = _forecast(df_raw.copy())

        # Reduced forecast
        df_reduced = df_raw.copy()
        factor = max(0.0, min(1.0, 1.0 - pct / 100.0))
        for col in ["bod", "cod", "turbidity", "ammonia", "conductivity"]:
            if col in df_reduced.columns:
                df_reduced[col] = df_reduced[col] * factor
        red_next, red_avg, red_points, red_flat = _forecast(df_reduced)

        if base_flat or red_flat:
            st.info(
                f"Only {min(base_points, red_points)} hourly points available. Showing a flat projection for the next {horizon} hours."
            )
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Baseline Risk", round(base_avg, 2))
        c2.metric("Reduced Risk", round(red_avg, 2))

        if base_next and red_next:
            df_base = pd.DataFrame(base_next)
            df_base["scenario"] = "Baseline"
            df_red = pd.DataFrame(red_next)
            df_red["scenario"] = "Reduced"
            dfp = pd.concat([df_base, df_red], ignore_index=True)
            dfp["ts"] = pd.to_datetime(dfp["ts"])
            fig = px.line(
                dfp,
                x="ts",
                y="risk",
                color="scenario",
                line_dash="scenario",
                title=f"Projected Risk (next {horizon}h)",
                labels={"ts": "Timestamp", "risk": "Baseline Risk"},
            )
            fig.update_yaxes(range=[0, 100])
            fig.update_traces(selector=dict(name="Baseline"), line=dict(dash="solid"))
            fig.update_traces(selector=dict(name=f"Reduced ({pct}%)"), line=dict(dash="dash"))
            st.plotly_chart(fig, width="stretch")


def issues_page():
    st.title("Issues")
    st.subheader("Create an Issue")
    with st.form("create_issue"):
        t = st.text_input("Title")
        d = st.text_area("Description")
        submitted = st.form_submit_button("Create")
        if submitted:
            token = st.session_state.get("access_token")
            user = st.session_state.get("user")
            if not token or not user:
                st.error("Sign in with Supabase to submit issues")
            else:
                email = _get_user_email(user) or "unknown"
                try:
                    from supabase_client import create_issue

                    create_issue(
                        t,
                        d,
                        created_by=email,
                        access_token=token,
                        refresh_token=st.session_state.get("refresh_token"),
                    )
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    st.success("Issue created")
                except Exception as e:
                    st.error(f"Failed to create issue: {e}")

    st.divider()

    st.subheader("Existing Issues")
    show_open_only = st.checkbox("Show open only", value=True)

    if st.sidebar.button("Refresh issues"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()

    try:
        from supabase_client import get_issues

        rows = get_issues()
    except Exception as e:
        st.error(f"Supabase not reachable: {e}")
        st.info("Check Streamlit secrets for SUPABASE_URL and SUPABASE_KEY.")
        return

    if rows:
        df = pd.DataFrame(rows)
        if show_open_only and "status" in df.columns:
            df = df[df["status"] == "open"]
        if df.empty:
            st.info("No issues")
            return
        preferred_cols = ["id", "title", "description", "status", "created_by", "created_at"]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        st.dataframe(df, width="stretch")
        # allow closing an issue
        open_ids = [i["id"] for i in rows if i.get("status") != "closed"]
        if open_ids:
            st.divider()
            st.subheader("Close Issue")
            issue_id = st.number_input(
                "Enter Issue ID",
                min_value=int(min(open_ids)),
                max_value=int(max(open_ids)),
                value=int(open_ids[0]),
                step=1,
            )
            if issue_id not in open_ids:
                st.error(f"Invalid Issue ID: {int(issue_id)}")
                return
            if st.button("Close Issue"):
                token = st.session_state.get("access_token")
                if not token:
                    st.error("Sign in with Supabase to close issues")
                else:
                    try:
                        from supabase_client import update_issue_status

                        update_issue_status(
                            int(issue_id),
                            "closed",
                            access_token=token,
                            refresh_token=st.session_state.get("refresh_token"),
                        )
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success("Issue closed")
                        st.rerun() # DO NOT CHANGE!!!
                    except Exception as e:
                        st.error(f"Failed to close: {e}")
    else:
        st.info("No issues yet")


if page == "Dashboard":
    dashboard()
elif page == "Alerts":
    alerts_page()
elif page == "Simulation":
    simulation_page()
elif page == "Issues":
    issues_page()
