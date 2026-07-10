import os

import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="RTO Compliance Query",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.5rem; max-width: 1180px; }
      [data-testid="stSidebar"] { background: #f6f8fb; border-right: 1px solid #d9e0e8; }
      .metric-row [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d9e0e8;
        border-radius: 8px;
        padding: 12px;
      }
      .query-chip button {
        border-radius: 8px;
        border: 1px solid #cfd8e3;
        background: #ffffff;
      }
      .status-box {
        border: 1px solid #d9e0e8;
        border-radius: 8px;
        padding: 12px;
        background: #ffffff;
        color: #1d2733;
      }
      .muted { color: #667487; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state():
    defaults = {
        "email": "",
        "authenticated": False,
        "history": [],
        "pending_question": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def ask_backend(question: str) -> dict:
    response = requests.post(
        f"{API_BASE}/chatbot/query",
        json={"question": question, "user_email": st.session_state.email},
        timeout=30,
    )
    if response.status_code == 403:
        raise PermissionError("This email is not authorized for compliance queries.")
    response.raise_for_status()
    return response.json()


def authenticate(email: str):
    if not email.strip():
        st.error("Enter your authorized email.")
        return
    try:
        ask_backend("How many employees are active?")
        st.session_state.email = email.strip()
        st.session_state.authenticated = True
        st.rerun()
    except PermissionError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Cannot connect to backend: {exc}")


def submit_question(question: str):
    clean = question.strip()
    if not clean:
        return
    st.session_state.history.append({"role": "user", "content": clean})
    with st.spinner("Querying compliance data..."):
        try:
            data = ask_backend(clean)
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "content": data.get("answer") or "No answer returned.",
                    "sql": data.get("sql_used", ""),
                    "row_count": data.get("row_count"),
                    "success": data.get("success", False),
                }
            )
        except PermissionError as exc:
            st.session_state.history.append({"role": "assistant", "content": str(exc), "success": False})
        except Exception as exc:
            st.session_state.history.append(
                {"role": "assistant", "content": f"Connection or query error: {exc}", "success": False}
            )


init_state()

with st.sidebar:
    st.title("RTO Query")
    st.caption("Leadership and HR compliance analytics")
    st.divider()
    st.markdown("**Backend**")
    st.code(API_BASE, language=None)

    if st.session_state.authenticated:
        st.markdown("**Signed in**")
        st.markdown(f"<div class='status-box'>{st.session_state.email}</div>", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.email = ""
            st.session_state.history = []
            st.rerun()
    else:
        with st.form("login_form"):
            email = st.text_input("Authorized email", placeholder="hr@example.com")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                st.session_state.email = email.strip()
                authenticate(email)

    st.divider()
    st.markdown("**Useful prompts**")
    suggestions = [
        "Which violations are currently open?",
        "Show the last 5 violations",
        "How many employees are on WEEKLY policy?",
        "List employees with EMAIL_ESCALATED violations",
        "Show reset violations from the latest cycle",
        "How many violations exist by policy type?",
    ]
    for idx, suggestion in enumerate(suggestions):
        if st.button(suggestion, key=f"suggestion_{idx}", use_container_width=True):
            st.session_state.pending_question = suggestion

st.title("RTO Compliance Query")
st.caption("Ask plain-English questions about employees, attendance, violations, and audit history.")

if not st.session_state.authenticated:
    st.info("Sign in from the sidebar with an authorized email to start querying compliance data.")
else:
    metric_container = st.container()
    with metric_container:
        st.markdown("<div class='metric-row'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Session queries", len([m for m in st.session_state.history if m["role"] == "user"]))
        c2.metric("Last row count", next((m.get("row_count") for m in reversed(st.session_state.history) if m["role"] == "assistant" and m.get("row_count") is not None), 0))
        c3.metric("Mode", "Read only")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    for msg in st.session_state.history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                if msg.get("success") is False:
                    st.error(msg["content"])
                else:
                    st.write(msg["content"])
                details = []
                if msg.get("row_count") is not None:
                    details.append(f"Rows: {msg['row_count']}")
                if msg.get("success") is not None:
                    details.append(f"Success: {msg['success']}")
                if details:
                    st.caption(" | ".join(details))
                if msg.get("sql"):
                    with st.expander("SQL used"):
                        st.code(msg["sql"], language="sql")

    pending = st.session_state.pending_question
    if pending:
        st.session_state.pending_question = None
        submit_question(pending)
        st.rerun()

    question = st.chat_input("Ask a compliance question...")
    if question:
        submit_question(question)
        st.rerun()
