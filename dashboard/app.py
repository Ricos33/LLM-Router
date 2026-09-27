import os
import sys
from pathlib import Path
import datetime
import pandas as pd
import streamlit as st

# Add project root to sys.path so app modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.storage import MetricsTracker
from app.config import settings
from app.router import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage

st.set_page_config(
    page_title="LLM-Router — Real-Time Cost & Savings Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #2e3440;
    }
    .badge-cheap {
        background-color: #059669;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
    }
    .badge-frontier {
        background-color: #7c3aed;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Storage & Router
@st.cache_resource
def get_tracker():
    return MetricsTracker(db_path=str(settings.db_path))

@st.cache_resource
def get_router():
    return RouterEngine()

tracker = get_tracker()
router = get_router()

# Sidebar
with st.sidebar:
    st.title("⚡ LLM Router")
    st.caption("Intelligent Cost-Optimization Gateway")
    st.markdown("---")
    
    st.subheader("⚙️ Active Configuration")
    st.write(f"**Classifier:** `{settings.classifier_mode.upper()}`")
    st.write(f"**Cheap Backend:** `{settings.cheap_model}` ({settings.cheap_provider})")
    st.write(f"**Frontier Backend:** `{settings.frontier_model}`")
    st.markdown("---")
    st.subheader("💰 Pricing (per 1M tokens)")
    st.caption(f"Cheap: ${settings.cheap_prompt_price_per_m} in / ${settings.cheap_completion_price_per_m} out")
    st.caption(f"Frontier: ${settings.frontier_prompt_price_per_m} in / ${settings.frontier_completion_price_per_m} out")

    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

# Main Title & Subtitle
st.title("📊 Real-Time LLM Cost & Routing Telemetry")
st.markdown(
    "Dynamically routing routine queries to **lightweight/local LLMs** while reserving **frontier models** "
    "for complex reasoning and code."
)

summary = tracker.get_summary()

# KPI Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)

total_reqs = summary["total_requests"]
cheap_reqs = summary["cheap_requests"]
frontier_reqs = summary["frontier_requests"]
cheap_pct = summary["cheap_percentage"]
saved_cost = summary["total_cost_saved"]
savings_pct = summary["savings_percentage"]
actual_cost = summary["total_cost_actual"]
baseline_cost = summary["total_cost_if_frontier"]

with col1:
    st.metric(
        label="Total Requests",
        value=f"{total_reqs:,}",
        help="All API completions routed through the gateway"
    )

with col2:
    st.metric(
        label="Cheap / Local Ratio",
        value=f"{cheap_pct:.1f}%",
        delta=f"{cheap_reqs} requests",
        delta_color="normal",
        help="Percentage of queries handled without invoking frontier models"
    )

with col3:
    st.metric(
        label="Frontier Baseline",
        value=f"${baseline_cost:.4f}",
        help="Hypothetical cost if all queries had been sent to frontier model"
    )

with col4:
    st.metric(
        label="Actual Incurred Cost",
        value=f"${actual_cost:.4f}",
        help="Actual aggregate cost incurred across cheap and frontier tiers"
    )

with col5:
    st.metric(
        label="Net Savings",
        value=f"${saved_cost:.4f}",
        delta=f"-{savings_pct:.1f}% saved" if savings_pct > 0 else "0%",
        delta_color="normal",
        help="Total dollars saved thanks to intelligent classification"
    )

st.markdown("---")

# Layout: Visual Charts + Interactive Playground
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader("📈 Traffic Breakdown & Cost Comparison")

    if total_reqs == 0:
        st.info("No requests recorded yet. Try testing a prompt in the interactive tester on the right!")
    else:
        # Cost Comparison DataFrame
        cost_df = pd.DataFrame({
            "Scenario": ["Frontier (100% gpt-4o)", "LLM-Router Hybrid (Actual)"],
            "Cost ($)": [baseline_cost, actual_cost]
        })
        st.bar_chart(cost_df.set_index("Scenario"), height=260)

        # Tier breakdown
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.write(f"🟢 **Cheap Tier ({settings.cheap_model}):** {cheap_reqs} ({cheap_pct}%)")
        with col_c2:
            st.write(f"🟣 **Frontier Tier ({settings.frontier_model}):** {frontier_reqs} ({summary['frontier_percentage']}%)")

with right_col:
    st.subheader("🧪 Interactive Route Tester")
    test_prompt = st.text_area(
        "Enter a test prompt:",
        value="Write a Python class implementing a distributed Raft consensus algorithm with heartbeat timers.",
        height=110
    )
    force_override = st.selectbox(
        "Routing Override (optional):",
        options=["Auto (Classifier)", "Force Cheap (Ollama)", "Force Frontier (GPT-4o)"]
    )

    if st.button("🚀 Route Request", use_container_width=True):
        header_override = None
        if "Cheap" in force_override:
            header_override = "cheap"
        elif "Frontier" in force_override:
            header_override = "frontier"

        req = ChatCompletionRequest(
            model="router-auto",
            messages=[ChatMessage(role="user", content=test_prompt)]
        )

        with st.spinner("Classifying and routing..."):
            import asyncio
            response = asyncio.run(router.route_and_execute(req, tier_header_override=header_override))

        meta = response.router_metadata
        if meta:
            tier_badge = "badge-cheap" if meta.routed_tier == "cheap" else "badge-frontier"
            st.markdown(
                f"**Decision:** <span class='{tier_badge}'>{meta.routed_tier.upper()}</span> &nbsp; "
                f"Model: `{meta.actual_model}` &nbsp; Latency: `{meta.latency_ms:.1f}ms`",
                unsafe_allow_html=True
            )
            st.write(f"**Complexity Score:** `{meta.classifier_score:.2f}`")
            st.write(f"**Saved on query:** `${meta.cost_saved_usd:.6f}`")
            with st.expander("Classifier Explanation", expanded=True):
                for r in meta.classifier_reasons:
                    st.write(f"• {r}")
            with st.expander("Completion Output", expanded=False):
                st.write(response.choices[0].message.content)
            st.rerun()

st.markdown("---")

# Recent Requests Log Table
st.subheader("📋 Live Request Log (Last 50)")
recent = tracker.get_recent_requests(limit=50)

if recent:
    formatted_rows = []
    for r in recent:
        formatted_rows.append({
            "Time": datetime.datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M:%S"),
            "Tier": r["routed_tier"].upper(),
            "Model": r["model_used"],
            "Prompt Preview": r["prompt_preview"],
            "Tokens": r["total_tokens"],
            "Latency (ms)": f"{r['latency_ms']:.1f}",
            "Cost ($)": f"${r['cost_actual']:.5f}",
            "Saved ($)": f"${r['cost_saved']:.5f}",
            "Reasons": " | ".join(r["classifier_reasons"][:2])
        })
    df_recent = pd.DataFrame(formatted_rows)
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.caption("No requests in log yet.")
