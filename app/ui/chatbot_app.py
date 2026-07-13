import os

import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

USEFUL_PROMPTS = [
    "Which violations are currently open?",
    "Show the last 5 violations",
    "How many employees are on WEEKLY policy?",
    "List employees with EMAIL_ESCALATED violations",
    "Show reset violations from the latest cycle",
    "How many violations exist by policy type?",
]

st.set_page_config(
    page_title="RTO Compliance",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --blue: #2563eb;
        --blue-dark: #1d4ed8;
        --purple: #7c3aed;
        --purple-soft: #ede9fe;
        --background: #f5f7ff;
        --panel: #ffffff;
        --border: #dbe4f3;
        --text: #172033;
        --muted: #64748b;
        --green: #059669;
      }
      .stApp { background: var(--background); color: var(--text); }
      .block-container { padding-top: 1.4rem; max-width: 1180px; }
      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e40af 0%, #4f46e5 52%, #6d28d9 100%);
        border-right: 0;
        box-shadow: 8px 0 30px rgba(55, 48, 163, .15);
      }
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] p,
      [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #ffffff; }
      h1, h2, h3, p, label { color: var(--text); }
      .hero {
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        border: 0;
        border-radius: 18px;
        background: linear-gradient(115deg, #2563eb 0%, #4f46e5 50%, #7c3aed 100%);
        box-shadow: 0 14px 35px rgba(79, 70, 229, .24);
      }
      .hero h1 { margin: 0; font-size: 2rem; color: #ffffff; }
      .hero p { margin: .45rem 0 0; color: #eef2ff; }
      [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 8px 24px rgba(37, 99, 235, .08);
      }
      [data-testid="stMetricLabel"] { color: var(--muted); }
      [data-testid="stMetricValue"] { color: var(--blue); }
      [data-testid="stChatMessage"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 15px;
        padding: .4rem .8rem;
        margin-bottom: .65rem;
        box-shadow: 0 5px 18px rgba(79, 70, 229, .06);
      }
      .stButton > button, [data-testid="stFormSubmitButton"] > button {
        border-radius: 10px;
        border: 1px solid #c7d2fe;
        background: #ffffff;
        color: var(--blue-dark);
        transition: all .15s ease;
      }
      .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        border-color: var(--purple);
        color: #ffffff;
        background: linear-gradient(100deg, var(--blue), var(--purple));
        transform: translateY(-1px);
      }
      [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, .96);
        color: #3730a3;
        border-color: rgba(255, 255, 255, .75);
      }
      [data-testid="stSidebar"] .stButton > button p {
        color: #3730a3 !important;
      }
      [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(100deg, #2563eb, #7c3aed);
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, .75);
        box-shadow: 0 7px 18px rgba(30, 27, 75, .25);
      }
      [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button p {
        color: #ffffff !important;
        font-weight: 700;
      }
      .status-box {
        border: 1px solid rgba(255, 255, 255, .5);
        border-radius: 10px;
        padding: 12px;
        background: rgba(255, 255, 255, .96);
        color: #3730a3;
      }
      [data-testid="stChatInput"] textarea {
        background: #ffffff;
        color: var(--text);
        border-color: #a5b4fc;
      }
      [data-testid="stExpander"], [data-testid="stAlert"] {
        background: #ffffff;
        border-color: var(--border);
      }
      hr { border-color: var(--border); }
      code { color: #4338ca !important; }
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
                    "needs_disambiguation": data.get("needs_disambiguation", False),
                    "employee_matches": data.get("employee_matches", []),
                    "original_question": clean,
                    "total_matches": data.get("total_matches", 0),
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
    st.title("RTO Compliance")
    st.caption("Governance and compliance intelligence")
    st.divider()
    st.markdown("**Backend**")
    st.code(API_BASE, language=None)

    if st.session_state.authenticated:
        st.markdown("**Signed in**")
        st.markdown(f"<div class='status-box'>{st.session_state.email}</div>", unsafe_allow_html=True)
        st.write("")
        if st.button("Sign out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.email = ""
            st.session_state.history = []
            st.rerun()
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.history = []
            st.session_state.pending_question = None
            st.rerun()
    else:
        with st.form("login_form"):
            email = st.text_input("Authorized email", placeholder="hr@example.com")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                st.session_state.email = email.strip()
                authenticate(email)

st.markdown(
    """
    <div class="hero">
      <h1>RTO Compliance</h1>
      <p>Monitor attendance, investigate violations, and explore compliance insights in one place.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.authenticated:
    st.info("Sign in from the sidebar with an authorized email to start querying compliance data.")
else:
    user_queries = len([m for m in st.session_state.history if m["role"] == "user"])
    successful_answers = len([
        m for m in st.session_state.history
        if m["role"] == "assistant" and m.get("success") is True
    ])
    last_row_count = next((
        m.get("row_count") for m in reversed(st.session_state.history)
        if m["role"] == "assistant" and m.get("row_count") is not None
    ), 0)

    st.subheader("Dashboard")
    metric_container = st.container()
    with metric_container:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Session queries", user_queries)
        c2.metric("Successful answers", successful_answers)
        c3.metric("Last row count", last_row_count)
        c4.metric("Data access", "Read only")

    st.divider()

    with st.chat_message("assistant"):
        st.write("How may I help you today?")
        st.caption("Useful prompts")
        prompt_columns = st.columns(2)
        for idx, suggestion in enumerate(USEFUL_PROMPTS):
            with prompt_columns[idx % 2]:
                if st.button(
                    suggestion,
                    key=f"suggestion_{idx}",
                    use_container_width=True,
                ):
                    st.session_state.pending_question = suggestion

    for message_index, msg in enumerate(st.session_state.history):
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
                if msg.get("needs_disambiguation"):
                    st.caption("Select the intended employee")
                    for match_index, employee in enumerate(msg.get("employee_matches", [])):
                        label = f"{employee['emp_name']} · {employee['emp_sapid']}"
                        if st.button(
                            label,
                            key=f"employee_match_{message_index}_{match_index}",
                            use_container_width=True,
                        ):
                            original = msg.get("original_question", "")
                            st.session_state.pending_question = (
                                f"{original} for employee {employee['emp_name']} "
                                f"with employee code {employee['emp_sapid']}"
                            )
                    total_matches = msg.get("total_matches", 0)
                    shown_matches = len(msg.get("employee_matches", []))
                    if total_matches > shown_matches:
                        st.caption(
                            f"Showing {shown_matches} of {total_matches} matches. "
                            "Enter a complete name or employee code to narrow the result."
                        )

    pending = st.session_state.pending_question
    if pending:
        st.session_state.pending_question = None
        submit_question(pending)
        st.rerun()

    question = st.chat_input("Ask a compliance question...")
    if question:
        submit_question(question)
        st.rerun()
