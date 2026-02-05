from supabase import create_client, Client
import streamlit as st

def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in Streamlit secrets.")
    return create_client(url, key)
