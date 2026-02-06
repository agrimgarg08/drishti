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

# Optional Supabase auth (if configured). Falls back to demo login.
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

if "user" not in st.session_state:
    st.session_state["user"] = None
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = None

st.sidebar.markdown("### Authentication")
if supabase:
    st.sidebar.write("Supabase auth available")
    # Restore session if we have tokens from a prior login in this browser session
    if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
        try:
            supabase.auth.set_session(
                st.session_state["access_token"],
                st.session_state["refresh_token"],
            )
            user_res = supabase.auth.get_user()
            user = user_res.get("user") if isinstance(user_res, dict) else getattr(user_res, "user", None)
            if user:
                st.session_state["user"] = user
        except Exception:
            pass
    # Handle OAuth redirect (Supabase sends ?code=... on return)
    try:
        params = st.query_params
        oauth_code = params.get("code")
        if isinstance(oauth_code, list):
            oauth_code = oauth_code[0] if oauth_code else None
        if oauth_code and not st.session_state["user"]:
            res = supabase.auth.exchange_code_for_session(oauth_code)
            if isinstance(res, dict):
                session = res.get("session")
                user = res.get("user")
            else:
                session = getattr(res, "session", None)
                user = getattr(res, "user", None)
            if session and user:
                st.session_state["user"] = user
                st.session_state["access_token"] = session.get("access_token")
                st.session_state["refresh_token"] = session.get("refresh_token")
                # Clear query params to avoid re-processing
                st.query_params.clear()
                st.sidebar.success("Signed in")
    except Exception:
        pass

    if not st.session_state["user"]:
        # Email/password login
        email = st.sidebar.text_input("Email", key="email")
        pw = st.sidebar.text_input("Password", type="password", key="pw")
        cols = st.sidebar.columns(2)
        if cols[0].button("Sign in"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                session = res.get("session") if isinstance(res, dict) else None
                user = res.get("user") if isinstance(res, dict) else None
                if session and user:
                    st.session_state["user"] = user
                    st.session_state["access_token"] = session.get("access_token")
                    st.sidebar.success("Signed in")
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

        st.sidebar.markdown("— or —")
        if st.sidebar.button("Sign in with GitHub"):
            try:
                redirect_to = os.getenv("SUPABASE_REDIRECT_URL") or "http://localhost:8501"
                res = supabase.auth.sign_in_with_oauth(
                    {"provider": "github", "options": {"redirect_to": redirect_to}}
                )
                if isinstance(res, dict):
                    url = res.get("url")
                else:
                    url = getattr(res, "url", None)
                if url:
                    st.sidebar.link_button("Continue to GitHub", url)
                else:
                    st.sidebar.error("Failed to start GitHub login")
            except Exception:
                st.sidebar.error("Auth error")
    else:
        st.sidebar.write(f"Signed in: {st.session_state['user'].get('email')}")
        if st.sidebar.button("Sign out"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state["user"] = None
else:
    st.sidebar.info("Supabase not configured — demo login available")
    if not st.session_state["user"]:
        demo_user = st.sidebar.text_input("Demo username", key="demo_user")
        if st.sidebar.button("Demo login"):
            st.session_state["user"] = {"email": demo_user or "demo"}
            st.sidebar.success("Signed in (demo)")
    else:
        st.sidebar.write(f"Signed in: {st.session_state['user'].get('email')}")
        if st.sidebar.button("Sign out demo"):
            st.session_state["user"] = None


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
    st.sidebar.markdown("### Map / Sensors")
    show_only_with_alerts = st.sidebar.checkbox("Show sensors with active alerts only", value=False)
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

    # Plot using Plotly mapbox (open-street-map so no token needed)
    if not dfmap.empty:
        center_lat = 28.6139
        center_lon = 77.2090
        fig = px.scatter_mapbox(
            dfmap,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"id": True, "lat": True, "lon": True, "alert_count": True},
            zoom=10,
            height=500,
        )
        # Color markers by alert status: green (no alerts), red (alerts)
        fig.update_traces(
            marker=dict(size=10, color=dfmap["alert_color"], opacity=0.9),
            selector=dict(mode="markers"),
        )
        fig.update_layout(mapbox_style="open-street-map", mapbox_center={"lat": center_lat, "lon": center_lon})
        # Render chart simply (no optional click-to-select to avoid instability)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No points to display on map.")

    # Sensor detail panel
    st.subheader("Sensor Details & Readings")
    sensor_ids = sorted([int(x) for x in dfmap["id"].tolist()])
    
    # If filtering by alerts and no sensors match, show info and return
    if show_only_with_alerts and not sensor_ids:
        st.info("No sensors with active alerts found.")
        return
    
    # Number input for selecting sensor ID
    sid = st.number_input("Enter drain number (ID)", min_value=1, max_value=10000, value=sensor_ids[0] if sensor_ids else 1, step=1)
    
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

        # Time series chart
        tdf = df.copy()
        tdf = tdf.sort_values("timestamp")
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
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to render chart: {e}")
                st.write(dfm.head())

        st.write("Latest 10 readings")
        st.dataframe(tdf.tail(10))

        # Link to alerts for this sensor
        a_count = int(dfmap.loc[dfmap["id"] == sid, "alert_count"].iloc[0]) if not dfmap.loc[dfmap["id"] == sid].empty else 0
        if a_count:
            st.warning(f"There are {a_count} unresolved alert(s) for this sensor. See the Alerts page.")
        else:
            st.success("No active alerts for this sensor")


def alerts_page():
    st.title("Alerts")
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
        st.dataframe(df, use_container_width=True)

        # Optional resolve action for unresolved alerts
        unresolved_ids = [a["id"] for a in rows if not a.get("resolved")]
        if unresolved_ids:
            st.markdown("### Resolve Alert")
            alert_id = st.number_input(
                "Enter alert ID",
                min_value=int(min(unresolved_ids)),
                max_value=int(max(unresolved_ids)),
                value=int(unresolved_ids[0]),
                step=1,
            )
            if alert_id not in unresolved_ids:
                st.error(f"Invalid alert ID: {int(alert_id)}")
                return
            if st.button("Resolve alert"):
                token = st.session_state.get("access_token")
                if not token:
                    st.error("Sign in with Supabase to resolve alerts")
                else:
                    try:
                        from supabase_client import resolve_alert

                        resolve_alert(int(alert_id), access_token=token)
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
    st.title("Policy Simulation")
    sid = st.number_input("Sensor ID", min_value=1, max_value=1000, value=1)
    pct = st.slider("Reduce pollutant discharges by %", min_value=0, max_value=100, value=20)
    if st.button("Simulate"):
        resp = requests.post(f"{API_BASE}/simulate-policy", json={"sensor_id": sid, "reduction_pct": pct})
        if resp.status_code == 200:
            res = resp.json()
            # prefer projected_baseline if supplied by backend, else use baseline
            st.metric("Baseline risk", round(res.get("projected_baseline", res.get("baseline", 0)), 2))
            next_24 = res.get("next_24h", [])
            if next_24:
                df = pd.DataFrame(next_24)
                df["ts"] = pd.to_datetime(df["ts"])
                fig = px.line(df, x="ts", y="risk", title=f"Projected risk (next 24h) after {pct}% reduction")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Simulation failed")


def issues_page():
    st.title("Issues")
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
                email = user.get("email") or user.get("user_metadata", {}).get("email") or "unknown"
                try:
                    from supabase_client import create_issue

                    create_issue(t, d, created_by=email, access_token=token)
                    try:
                        st.cache_data.clear()
                    except Exception:
                        pass
                    st.success("Issue created")
                except Exception as e:
                    st.error(f"Failed to create issue: {e}")

    if st.button("Refresh issues"):
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
        preferred_cols = ["id", "title", "description", "status", "created_by", "created_at"]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        st.dataframe(df, use_container_width=True)
        # allow closing an issue
        open_ids = [i["id"] for i in rows if i.get("status") != "closed"]
        if open_ids:
            st.markdown("### Close Issue")
            issue_id = st.number_input(
                "Enter issue ID",
                min_value=int(min(open_ids)),
                max_value=int(max(open_ids)),
                value=int(open_ids[0]),
                step=1,
            )
            if issue_id not in open_ids:
                st.error(f"Invalid issue ID: {int(issue_id)}")
                return
            if st.button("Close issue"):
                token = st.session_state.get("access_token")
                if not token:
                    st.error("Sign in with Supabase to close issues")
                else:
                    try:
                        from supabase_client import update_issue_status

                        update_issue_status(int(issue_id), "closed", access_token=token)
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success("Issue closed")
                        st.experimental_rerun()
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
