import streamlit as st

st.set_page_config(page_title="Refund Rehab", page_icon="chart_with_upwards_trend", layout="wide")

st.title("Refund Rehab")
st.subheader("Treating the merchant's returns and chargeback problem")

st.markdown("A two-part system for e-commerce risk: predict returns before they happen, and handle chargeback disputes with a human always in control of the final call.")

st.divider()

st.markdown("### How it works")

steps = [
    ("1", "Order placed", "A new order enters the queue and is scored the same second."),
    ("2", "Risk scored", "Return probability, expected loss in rupees, and why."),
    ("3", "Dispute drafted", "If it's later disputed, the AI drafts the bank response."),
    ("4", "Human reviews", "Approve, reject with feedback, or edit directly. Nothing ships alone."),
    ("5", "Fully logged", "Every draft, decision, and outcome, permanently recorded."),
]

cols = st.columns(5)
for col, (num, title, desc) in zip(cols, steps):
    with col:
        with st.container(border=True):
            st.markdown(f"<span style='background-color:#1E88F0;color:white;border-radius:50%;padding:2px 9px;font-weight:bold;'>{num}</span>", unsafe_allow_html=True)
            st.markdown(f"**{title}**")
            st.caption(desc)

st.divider()

st.markdown("### At a glance")
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Return-Risk ROC-AUC", "0.738")
    st.caption("Benchmarked against Random Forest and a single-feature heuristic")
with m2:
    st.metric("Chargeback Cases Validated", "5")
    st.caption("Strong, weak, and ambiguous evidence, tested individually")
with m3:
    st.metric("Est. FN Cost (test set)", "Rs.38K-76K")
    st.caption("Missed returns: shipping and restocking")
with m4:
    st.metric("Est. FP Cost (test set)", "Rs.67K-112K")
    st.caption("Wrongly flagged orders: the larger cost")

st.divider()

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("#### Order Risk Queue")
        st.write("A live queue of incoming orders, each automatically scored for return risk with a plain-language explanation and a recommended action, plus the honest false-positive vs. false-negative cost tradeoff behind the model.")
        st.page_link("pages/1_Order_Risk_Queue.py", label="Go to Order Risk Queue")

with col2:
    with st.container(border=True):
        st.markdown("#### Chargeback Review")
        st.write("AI drafts an evidence-backed response to a disputed transaction. A human always approves, rejects, or edits before anything is submitted, and every step is logged.")
        st.page_link("pages/2_Chargeback_Review.py", label="Go to Chargeback Review")