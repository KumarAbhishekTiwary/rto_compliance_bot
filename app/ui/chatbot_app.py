import streamlit as st
import requests
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

st.set_page_config(page_title="RTO Compliance Chatbot", page_icon="🏢", layout="centered")
st.title("🏢 RTO Compliance Chatbot")
st.caption("For HR & Leadership — query compliance data in plain English")

# Session state
if "email" not in st.session_state:
    st.session_state.email = ""
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "history" not in st.session_state:
    st.session_state.history = []

# Login
if not st.session_state.authenticated:
    with st.form("login_form"):
        email = st.text_input("Enter your authorized email", placeholder="hr@example.com")
        submitted = st.form_submit_button("Sign In")
        if submitted:
            # Quick auth check via a test query
            try:
                r = requests.post(f"{API_BASE}/chatbot/query", json={"question": "SELECT 1", "user_email": email}, timeout=10)
                if r.status_code == 403:
                    st.error("❌ Unauthorized email. Contact your admin.")
                else:
                    st.session_state.email = email
                    st.session_state.authenticated = True
                    st.rerun()
            except Exception as e:
                st.error(f"Cannot connect to backend: {e}")
else:
    st.success(f"✅ Signed in as **{st.session_state.email}**")
    if st.button("Sign Out"):
        st.session_state.authenticated = False
        st.session_state.history = []
        st.rerun()

    st.divider()

    # Suggested queries
    st.markdown("**Try asking:**")
    suggestions = [
        "How many employees are on WEEKLY policy?",
        "Show me the last 5 violations",
        "Show all violations of Alice",
        "Which violations are currently OPEN?",
        "How many employees attended office this week?",
    ]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"sug_{i}"):
            st.session_state._pending_question = s

    # Chat input
    question = st.chat_input("Ask a compliance question...")
    if hasattr(st.session_state, "_pending_question"):
        question = st.session_state._pending_question
        del st.session_state._pending_question

    if question:
        st.session_state.history.append({"role": "user", "content": question})
        with st.spinner("Thinking..."):
            try:
                r = requests.post(
                    f"{API_BASE}/chatbot/query",
                    json={"question": question, "user_email": st.session_state.email},
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    sql = data.get("sql", "")
                    result = data.get("result", {})
                    rows = result.get("rows", [])
                    answer = f"Found **{len(rows)}** result(s)."
                    st.session_state.history.append({
                        "role": "assistant",
                        "content": answer,
                        "sql": sql,
                        "rows": rows,
                    })
                else:
                    st.session_state.history.append({
                        "role": "assistant",
                        "content": f"Error: {r.text}",
                    })
            except Exception as e:
                st.session_state.history.append({
                    "role": "assistant",
                    "content": f"Connection error: {e}",
                })

    # Display history
    for msg in st.session_state.history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
                if msg.get("sql"):
                    with st.expander("SQL Query"):
                        st.code(msg["sql"], language="sql")
                if msg.get("rows"):
                    st.dataframe(msg["rows"], use_container_width=True)
