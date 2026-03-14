"""
Bank Statement Analyzer — Streamlit UI
=======================================
Runs fully locally with LM Studio (port 1234) or Ollama (port 11434).
Your financial data never leaves your machine.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

# ── Path Setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Analyzer",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Ultra-Minimal Pitch-Black Theme ── */

/* Safely Hide Streamlit Bloat without breaking Layout */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
}

.stApp { 
    background: #000000; 
    color: #EDEDED; 
}

/* Sidebar & Generic Text Enforcements */
[data-testid="stSidebar"], [data-testid="stSidebar"] * {
    background-color: transparent;
    color: #EDEDED !important;
}
[data-testid="stSidebar"] {
    background: #000000 !important;
    border-right: 1px solid #1A1A1A;
}
[data-testid="stSidebar"] hr {
    border-bottom: 1px solid #1A1A1A;
}

/* Header */
.main-header { text-align: center; padding: 2.5rem 0 2rem; }
.main-header h1 {
    font-size: 2.6rem; font-weight: 500; letter-spacing: -0.8px;
    color: #FAFAFA !important; margin-bottom: 0.5rem;
}
.main-header p { color: #888888 !important; font-size: 0.95rem; }

/* Status Badges */
.status-online {
    display: inline-flex; align-items: center; gap: 8px;
    color: #A1A1AA !important; font-size: 0.8rem; font-weight: 500;
    padding: 6px 0;
}
.status-offline {
    display: inline-flex; align-items: center; gap: 8px;
    color: #F87171 !important; font-size: 0.8rem; font-weight: 500;
    padding: 6px 0;
}
.dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.dot-green { background: #34D399; box-shadow: 0 0 6px rgba(52, 211, 153, 0.4); }
.dot-red   { background: #F87171; box-shadow: 0 0 6px rgba(248, 113, 113, 0.4); }

/* Chat Bubbles */
.chat-user {
    background: #111111;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 12px 16px; margin: 8px 0 8px auto;
    max-width: 80%; color: #FAFAFA !important; font-size: 0.9rem;
}
.chat-bot {
    background: #0A0A0A;
    border: 1px solid #222222;
    border-radius: 6px;
    padding: 12px 16px; margin: 8px auto 8px 0;
    max-width: 85%; color: #EDEDED !important; font-size: 0.9rem;
}

/* Primary Button */
[data-testid="baseButton-primary"] {
    background: #111111 !important;
    color: #FFFFFF !important; 
    border: 1px solid #333333 !important;
    border-radius: 6px !important; 
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    margin-top: 4px;
    transition: all 0.2s ease !important;
}
[data-testid="baseButton-primary"]:hover:not(:disabled) {
    background: #222222 !important;
    border-color: #555555 !important;
    color: #FAFAFA !important;
}
[data-testid="baseButton-primary"]:disabled {
    background: #111111 !important;
    color: #888888 !important;
    border: 1px solid #333333 !important;
    opacity: 1 !important;
    cursor: not-allowed !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent; padding: 0;
    border-bottom: 1px solid #1A1A1A; gap: 24px;
}
.stTabs [data-baseweb="tab"] { 
    background: transparent; color: #888888 !important; 
    border-radius: 0; padding-bottom: 8px; font-weight: 500; 
}
.stTabs [aria-selected="true"] {
    background: transparent !important; 
    color: #FAFAFA !important;
    border-bottom: 2px solid #FAFAFA !important;
}

/* Uploader & Inputs */
[data-testid="stFileUploader"] > div > div {
    background: #000000 !important;
    border: 1px dashed #555555 !important; 
    border-radius: 6px !important;
    padding: 1rem !important;
}
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] div, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] div::before {
    color: #EDEDED !important;
}
[data-testid="stFileUploader"] section {
    background: transparent !important;
}

[data-testid="stFileDropzoneInstructions"] {
    background: transparent !important;
    color: #EDEDED !important;
}
[data-testid="stFileDropzoneInstructions"] > div > span, [data-testid="stFileDropzoneInstructions"] > div > small {
    color: #EDEDED !important;
}

[data-testid="stBaseButton-secondary"] {
    background: #3B82F6 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    opacity: 1 !important;
}

[data-testid="stTextInput"] > div > div {
    background: #0A0A0A !important;
    border: 1px solid #333333 !important; 
    border-radius: 6px !important;
    color: #EDEDED !important;
}
[data-testid="stTextInput"] > div > div:focus-within {
    border-color: #666666 !important;
    box-shadow: none !important;
}

/* Alerts */
[data-testid="stAlert"] {
    background: #0A0A0A !important;
    border: 1px solid #333333 !important;
    color: #EDEDED !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: LLM Connection Check ─────────────────────────────────────────────
@st.cache_data(ttl=10)
def check_llm_connection():
    """Check whether a local LLM server (LM Studio or Ollama) is reachable."""
    try:
        from agent.config import load_config
        cfg = load_config(ROOT / "config.yaml")
        base = cfg.llm.base_url.rstrip("/")
        is_ollama = "11434" in base
        url = f"{base}/api/tags" if is_ollama else f"{base}/models"
        r = requests.get(url, timeout=3)
        if r.status_code in (200, 404):
            provider = "Ollama" if is_ollama else "LM Studio"
            return True, provider, cfg.llm.model_id
        return False, "Unknown", ""
    except Exception:
        return False, "Unknown", ""


# ── Helper: Run Agent Pipeline ───────────────────────────────────────────────
def run_analysis(file_path: str, pdf_password: str | None = None) -> dict:
    """
    Run the full agent pipeline on a bank statement file.

    Args:
        file_path:    Absolute path to the uploaded file.
        pdf_password: Optional password for encrypted PDF statements.

    Returns:
        A result dict from the agent with at least a ``success`` key.
    """
    from main import run_agent
    goal = (
        f"Analyze the bank statement at '{file_path}'. "
        "Call read_statement with the file path, then categorize_transactions, "
        "then generate_dashboard, then save_memory."
    )
    return run_agent(goal, file_path=Path(file_path), pdf_password=pdf_password)


# ── Helper: LLM Chat ─────────────────────────────────────────────────────────
def ask_llm(question: str, context_summary: str) -> str:
    """
    Ask the local LLM a finance question using the loaded statement + vector search as context.
    """
    try:
        from agent.config import load_config
        from agent.llm_client import LLMClient
        from vector_store.semantic_search import semantic_search
        
        cfg = load_config(ROOT / "config.yaml")
        llm = LLMClient(cfg.llm)
        
        # 1. Semantic Search
        st.write("🔍 Searching transaction history...")
        search_results = semantic_search.search_transactions(question, k=10)
        
        relevant_context = context_summary + "\n\nRelevant Transactions Found:\n"
        if not search_results:
             relevant_context += "None specifically matching the query."
        else:
             for tx in search_results:
                 dt = tx.get('date', '')[:10]
                 amt = tx.get('amount', 0)
                 desc = tx.get('merchant', tx.get('raw_description', ''))
                 cat = tx.get('category', 'Unknown')
                 relevant_context += f"- {dt}: ₹{amt:,.2f} at {desc} [{cat}]\n"

        system = (
            "You are a personal finance advisor. "
            "Answer the user's question based strictly on their bank statement summary and relevant transactions below. "
            "Be concise, insightful, and use numbers from the data. Do NOT mention FAISS or vectors."
        )
        prompt = f"Context:\n{relevant_context}\n\nUser Question: {question}"
        
        return llm.complete(prompt, system=system, max_tokens=1024)
    except Exception as e:
        return f"⚠️ LLM Error: {e}"


# ── Helper: Read Latest HTML Dashboard ───────────────────────────────────────
def get_latest_dashboard() -> str | None:
    """Return HTML content of the most recently generated dashboard, or None."""
    reports_dir = ROOT / "reports"
    if reports_dir.exists():
        html_files = sorted(reports_dir.glob("*.html"), key=os.path.getmtime, reverse=True)
        if html_files:
            return html_files[0].read_text(encoding="utf-8")
    if (ROOT / "dashboard.html").exists():
        return (ROOT / "dashboard.html").read_text(encoding="utf-8")
    return None


# ────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💰 Finance Analyzer")
    st.markdown("---")

    # ── LLM Status ───────────────────────────────────────────────────────────
    online, provider, model = check_llm_connection()
    if online:
        st.markdown(
            f'<div class="status-online"><span class="dot dot-green"></span>'
            f'{provider} · {model}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-offline"><span class="dot dot-red"></span>'
            'LLM Offline</div>',
            unsafe_allow_html=True,
        )
        st.warning(
            "Start LM Studio and enable the server on port 1234, "
            "or run `ollama serve`.",
            icon="⚠️",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── File Upload ──────────────────────────────────────────────────────────
    st.markdown("**📂 Upload Statement**")
    uploaded_file = st.file_uploader(
        "Drag & drop or click to browse",
        type=["csv", "xlsx", "xls", "pdf"],
        label_visibility="collapsed",
    )

    # ── PDF Password (shown only when a PDF is uploaded) ─────────────────────
    pdf_password: str | None = None
    if uploaded_file and uploaded_file.name.lower().endswith(".pdf"):
        st.markdown("**🔐 PDF Password** *(if encrypted)*")
        pdf_password = st.text_input(
            "PDF Password",
            type="password",
            placeholder="Leave blank if not encrypted",
            label_visibility="collapsed",
            help=(
                "Many Indian banks (HDFC, SBI, ICICI) protect PDF statements "
                "with a password — usually your date of birth or mobile number. "
                "This is decrypted locally and never stored."
            ),
        ) or None  # Treat empty string as None

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button(
        "🔍 Analyze Statement",
        use_container_width=True,
        disabled=not uploaded_file,
    )

    st.markdown("---")
    st.markdown("**Supported formats**")
    st.markdown("- CSV (comma-separated)\n- Excel (.xlsx, .xls)\n- PDF bank statements")
    st.markdown("*PDF passwords are decrypted locally — never stored or transmitted.*")
    st.markdown("---")

    # ── Quick-load sample ────────────────────────────────────────────────────
    if st.button("📋 Load Sample Statement", use_container_width=True):
        sample = ROOT / "data" / "dummy_statement.csv"
        if sample.exists():
            st.session_state["sample_path"] = str(sample)
            st.session_state["sample_name"] = "dummy_statement.csv"
            st.success("Sample loaded! Click Analyze.")
        else:
            st.error("Sample not found. Run `python sample_output/generate_samples.py` first.")


# ────────────────────────────────────────────────────────────────────────────
#  MAIN AREA
# ────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>💰 Bank Statement Analyzer</h1>
    <p>Upload your bank statement · Get AI-powered insights · 100% local &amp; private</p>
</div>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key in ["analysis_done", "dashboard_html", "context_summary", "messages", "temp_path"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "messages" else []


# ── Analysis Trigger ──────────────────────────────────────────────────────────
if analyze_btn:
    if not online:
        st.error("❌ LLM is offline. Please start LM Studio or Ollama first.")
    elif uploaded_file:
        # Save uploaded file to a temp path
        suffix = Path(uploaded_file.name).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(uploaded_file.getbuffer())
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()
        st.session_state["temp_path"] = tmp_path

        steps = [
            ("📄", "Reading statement…"),
            ("🏷️", "Categorizing transactions…"),
            ("📊", "Generating dashboard…"),
            ("💾", "Saving to memory…"),
        ]

        with st.status("🤖 Agent is analyzing your statement…", expanded=True) as status_bar:
            cols = st.columns(len(steps))
            placeholders = [c.empty() for c in cols]

            def render_steps(active_idx: int) -> None:
                for i, (icon, label) in enumerate(steps):
                    if i < active_idx:
                        placeholders[i].markdown(f"✅ ~~{label}~~")
                    elif i == active_idx:
                        placeholders[i].markdown(f"⏳ **{label}**")
                    else:
                        placeholders[i].markdown(f"⬜ {label}")

            render_steps(0)
            time.sleep(0.3)

            try:
                result = run_analysis(tmp_path, pdf_password=pdf_password)

                if result.get("success"):
                    for i in range(len(steps)):
                        render_steps(i)
                        time.sleep(0.25)

                    # Grab the generated dashboard HTML
                    html = get_latest_dashboard()
                    if not html:
                        from tools.finance_tools import GLOBAL_STATE, generate_dashboard
                        if GLOBAL_STATE.get("df") is not None:
                            html_result = generate_dashboard()
                            if html_result and os.path.exists(str(html_result)):
                                html = Path(html_result).read_text(encoding="utf-8")
                            else:
                                html = html_result if isinstance(html_result, str) and "<" in str(html_result) else None

                    st.session_state["dashboard_html"] = html
                    st.session_state["analysis_done"] = True
                    st.session_state["messages"] = []

                    # Build context summary for the chat tab
                    from tools.finance_tools import GLOBAL_STATE
                    df = GLOBAL_STATE.get("df")
                    if df is not None:
                        inc = df[df["Amount"] > 0]["Amount"].sum() if "Amount" in df.columns else 0
                        exp = abs(df[df["Amount"] < 0]["Amount"].sum()) if "Amount" in df.columns else 0
                        cats = df["Category"].value_counts().to_dict() if "Category" in df.columns else {}
                        st.session_state["context_summary"] = (
                            f"Total transactions: {len(df)}\n"
                            f"Total income: ₹{inc:,.2f}\n"
                            f"Total expenses: ₹{exp:,.2f}\n"
                            f"Net balance: ₹{inc - exp:,.2f}\n"
                            f"Categories: {cats}"
                        )
                    status_bar.update(label="✅ Analysis complete!", state="complete")
                else:
                    status_bar.update(label=f"❌ {result.get('error', 'Analysis failed')}", state="error")
                    st.error(result.get("error") or result.get("output") or "Unknown error")

            except Exception as ex:
                status_bar.update(label=f"❌ Error: {ex}", state="error")
                st.exception(ex)

    elif st.session_state.get("sample_path"):
        sample_path = st.session_state["sample_path"]
        with st.status("🤖 Analyzing sample statement…", expanded=True) as status_bar:
            try:
                result = run_analysis(sample_path)
                if result.get("success"):
                    html = get_latest_dashboard()
                    st.session_state["dashboard_html"] = html
                    st.session_state["analysis_done"] = True
                    st.session_state["messages"] = []
                    status_bar.update(label="✅ Done!", state="complete")
                else:
                    status_bar.update(label=f"❌ {result.get('error')}", state="error")
            except Exception as ex:
                status_bar.update(label=f"❌ {ex}", state="error")
                st.exception(ex)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_dash, tab_insights, tab_recur, tab_fore, tab_chat = st.tabs([
    "📊 Dashboard", "💡 Insights", "🔁 Recurring", "📈 Forecast", "💬 Chat with AI"
])

# ─── Dashboard Tab ────────────────────────────────────────────────────────────
with tab_dash:
    if st.session_state.get("analysis_done") and st.session_state.get("dashboard_html"):
        components.html(st.session_state["dashboard_html"], height=900, scrolling=True)
    elif st.session_state.get("analysis_done"):
        # Fallback: render inline stats when no HTML dashboard is available
        try:
            from tools.finance_tools import GLOBAL_STATE
            df = GLOBAL_STATE.get("df")
            if df is not None:
                st.success("✅ Statement analyzed successfully!")
                col1, col2, col3, col4 = st.columns(4)
                inc = df[df["Amount"] > 0]["Amount"].sum() if "Amount" in df.columns else 0
                exp = abs(df[df["Amount"] < 0]["Amount"].sum()) if "Amount" in df.columns else 0
                col1.metric("Transactions", len(df))
                col2.metric("Total Income", f"₹{inc:,.0f}")
                col3.metric("Total Expenses", f"₹{exp:,.0f}")
                col4.metric("Net", f"₹{inc - exp:,.0f}")
                if "Category" in df.columns:
                    st.subheader("Spending by Category")
                    cat_data = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
                    st.bar_chart(cat_data)
                st.subheader("Transaction Table")
                st.dataframe(df, use_container_width=True, height=400)
        except Exception as e:
            st.warning(f"Dashboard unavailable: {e}")
    else:
        st.markdown("""
        <div style="text-align:center; padding: 4rem 2rem; color: #6b7280;">
            <div style="font-size: 5rem; margin-bottom: 1.5rem;">📊</div>
            <h2 style="color: #9ca3af; font-size:1.4rem; margin-bottom:1rem;">
                No statement analyzed yet
            </h2>
            <p style="max-width:500px; margin:0 auto;">
                Upload a <strong style="color:#a78bfa">bank statement</strong>
                (CSV, Excel, or PDF) using the sidebar, then click
                <strong style="color:#a78bfa">Analyze Statement</strong>
                to generate your financial dashboard.
            </p>
            <br>
            <p style="font-size:0.85rem;">
                Or open <strong>sample_output/dashboard.html</strong> in your browser
                for an instant preview.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ─── Insights Tab ─────────────────────────────────────────────────────────────
with tab_insights:
    if st.session_state.get("analysis_done"):
        st.markdown("### 💡 AI Spending Insights")
        try:
             from database.queries import queries
             insights = queries.get_recent_insights()
             if insights:
                  for i, ins in enumerate(insights):
                       st.info(ins["text"])
             else:
                  st.write("No insights generated yet.")
        except Exception as e:
             st.error(f"Error loading insights: {e}")
    else:
        st.info("Analyze a statement to see AI insights.")

# ─── Recurring Tab ────────────────────────────────────────────────────────────
with tab_recur:
    if st.session_state.get("analysis_done"):
        st.markdown("### 🔁 Detected Subscriptions & Recurring Payments")
        try:
             from database.queries import queries
             recurring = queries.get_recurring_payments()
             if recurring:
                  import pandas as pd
                  df_rec = pd.DataFrame(recurring)
                  # Format nicely
                  df_rec['average_amount'] = df_rec['average_amount'].apply(lambda x: f"₹{x:,.2f}")
                  df_rec['interval_days'] = df_rec['interval_days'].apply(lambda x: f"~{x:.0f} days")
                  df_rec['last_seen'] = df_rec['last_seen'].apply(lambda x: str(x)[:10])
                  df_rec = df_rec[['merchant', 'average_amount', 'interval_days', 'last_seen']]
                  df_rec.columns = ['Merchant', 'Avg Amount', 'Interval', 'Last Seen']
                  st.table(df_rec)
             else:
                  st.write("No recurring payments detected.")
        except Exception as e:
             st.error(f"Error loading recurring payments: {e}")
    else:
        st.info("Analyze a statement to detect recurring payments.")

# ─── Forecast Tab ─────────────────────────────────────────────────────────────
with tab_fore:
    if st.session_state.get("analysis_done"):
        st.markdown("### 📈 Spending Forecast")
        try:
             from analysis.forecasting import forecasting_engine
             forecast = forecasting_engine.forecast_next_month()
             
             total = forecast.get("forecast_total", 0)
             cats = forecast.get("categories", {})
             
             col1, col2 = st.columns([1, 2])
             with col1:
                  st.metric("Predicted Next Month Spending", f"₹{total:,.2f}")
                  
             with col2:
                  if cats:
                       st.markdown("#### Projected Category Breakdown")
                       import pandas as pd
                       df_cats = pd.DataFrame(list(cats.items()), columns=['Category', 'Amount'])
                       # Render local chart
                       st.bar_chart(df_cats.set_index('Category'))
                  else:
                       st.write("Not enough category data for breakdown.")
        except Exception as e:
             st.error(f"Error generating forecast: {e}")
    else:
        st.info("Analyze a statement to see forecasts.")

# ─── Chat Tab ─────────────────────────────────────────────────────────────────
with tab_chat:
    if not st.session_state.get("analysis_done"):
        st.markdown("""
        <div style="text-align:center; padding:4rem 2rem; color:#6b7280;">
            <div style="font-size:4rem; margin-bottom:1rem;">💬</div>
            <h2 style="color:#9ca3af; font-size:1.3rem;">Analyze a statement first</h2>
            <p>Once your statement is analyzed, you can ask questions here.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(102,126,234,0.1); border:1px solid rgba(102,126,234,0.3);
             border-radius:12px; padding:12px 16px; margin-bottom:16px;
             font-size:0.9rem; color:#a78bfa;">
            💡 <strong>Ask anything about your finances</strong> — e.g.
            "What's my biggest spending category?", "How much did I spend on food?",
            "Give me 3 money-saving tips based on my spending."
        </div>
        """, unsafe_allow_html=True)

        # Display chat history
        for msg in st.session_state["messages"]:
            css_cls = "chat-user" if msg["role"] == "user" else "chat-bot"
            st.markdown(f'<div class="{css_cls}">{msg["content"]}</div>', unsafe_allow_html=True)

        # Chat input
        question = st.chat_input("Ask about your finances…")
        if question:
            st.session_state["messages"].append({"role": "user", "content": question})
            st.markdown(f'<div class="chat-user">{question}</div>', unsafe_allow_html=True)

            with st.spinner("Thinking…"):
                context = st.session_state.get("context_summary") or "Statement data loaded."
                answer = ask_llm(question, context)

            st.session_state["messages"].append({"role": "assistant", "content": answer})
            st.markdown(f'<div class="chat-bot">{answer}</div>', unsafe_allow_html=True)

        if st.session_state["messages"]:
            if st.button("🗑️ Clear chat", key="clear_chat"):
                st.session_state["messages"] = []
                st.rerun()
