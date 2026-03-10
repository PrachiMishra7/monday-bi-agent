import streamlit as st
from monday_api import get_boards
from agent import ask_agent, generate_leadership_update, extract_all_metrics

st.set_page_config(
    page_title="BI Agent — Skylark Drones",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "monday_data" not in st.session_state:
    st.session_state.monday_data = None
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

with st.sidebar:
    st.title("🚁 Skylark Drones")
    st.caption("Business Intelligence Agent")
    st.divider()

    if st.button("🔄 Refresh Data from Monday", use_container_width=True):
        st.session_state.data_loaded = False
        st.session_state.monday_data = None

    if not st.session_state.data_loaded:
        with st.spinner("Fetching latest data from monday.com..."):
            result = get_boards()
        if result["error"]:
            st.error(f"**Connection Error**\n\n{result['error']}")
            st.stop()
        else:
            st.session_state.monday_data = result
            st.session_state.data_loaded = True
            st.success("✅ Connected!")

    data = st.session_state.monday_data

    if data and data.get("boards_fetched"):
        st.markdown("**Boards loaded:**")
        for b in data["boards_fetched"]:
            st.markdown(f"- 📋 {b}")
    st.divider()

    if data and data.get("data"):
        try:
            metrics = extract_all_metrics(data["data"])
            issues = metrics.get("quality_issues", [])
            d = metrics["deals"]
            w = metrics["work_orders"]

            st.markdown("**Quick Stats**")
            col1, col2 = st.columns(2)
            col1.metric("Deals", d["total_count"])
            col2.metric("Work Orders", w["total_count"])
            col1.metric("Pipeline", f"${d['total_pipeline_value']:,.0f}")
            col2.metric("Revenue", f"${w['total_revenue']:,.0f}")

            if issues:
                with st.expander(f"⚠️ {len(issues)} data quality issues"):
                    for issue in issues:
                        st.caption(f"• {issue}")
        except Exception:
            pass

    st.divider()
    st.markdown("**Leadership Update**")
    if st.button("📝 Generate Weekly Update", use_container_width=True):
        if data and data.get("data"):
            with st.spinner("Drafting leadership update..."):
                update = generate_leadership_update(data)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"**📝 Weekly Leadership Update**\n\n{update}"
            })
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

st.title("📊 Monday.com Business Intelligence Agent")
st.caption("Ask anything about your pipeline, work orders, revenue, or team performance.")

if not st.session_state.chat_history:
    st.markdown("**Try asking:**")
    suggestions = [
        "How's our overall pipeline looking?",
        "Which sectors are performing best?",
        "Who are the top performers on the deals team?",
        "What's our win rate and average deal size?",
        "How are work orders trending — any bottlenecks?",
        "Give me a cross-board view of the energy sector.",
    ]
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 3].button(suggestion, key=f"sug_{i}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": suggestion})
            with st.spinner("Analyzing..."):
                answer = ask_agent(
                    suggestion,
                    st.session_state.monday_data,
                    st.session_state.chat_history[:-1]
                )
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analyzing your data..."):
            answer = ask_agent(
                prompt,
                st.session_state.monday_data,
                st.session_state.chat_history[:-1]
            )
        st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})