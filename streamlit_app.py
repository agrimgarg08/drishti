import streamlit as st
from supabase_client import get_supabase_client
import json

st.title("Drishti — Streamlit frontend")

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"Supabase client error: {e}")
    st.stop()

st.sidebar.header("Actions")
table_name = st.sidebar.text_input("Table name", value="")
if not table_name:
    st.info("Type a table name (e.g., 'users') in the sidebar to begin.")
    st.stop()

if st.sidebar.button("Load rows"):
    try:
        res = supabase.table(table_name).select("*").limit(100).execute()
        data = getattr(res, "data", None)
        if not data:
            st.warning("No rows returned — table may not exist or schema changed.")
        else:
            st.write(f"Showing up to 100 rows from `{table_name}`")
            st.dataframe(data)
    except Exception as e:
        st.error(f"Query error: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("Insert a row (JSON)")

json_input = st.sidebar.text_area("Row JSON", height=150, value='{"column":"value"}')
if st.sidebar.button("Insert row"):
    try:
        obj = json.loads(json_input)
        insert_res = supabase.table(table_name).insert(obj).execute()
        st.success("Insert executed")
        st.write(getattr(insert_res, "data", insert_res))
    except Exception as e:
        st.error(f"Insert error: {e}")

st.markdown("If you see errors about missing columns or tables, you likely changed the DB schema on Supabase — update the table name or schema accordingly.")
