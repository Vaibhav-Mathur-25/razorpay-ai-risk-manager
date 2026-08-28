import streamlit as st

st.set_page_config(page_title="AI Risk Manager", page_icon="📊", layout="wide")

st.title("AI Risk Manager")
st.subheader("Reducing merchant losses from returns and chargebacks")

st.markdown("A two-part system for e-commerce risk: predict returns before they happen, and handle chargeback disputes with a human always in control of the final call.")

st.divider()

st.markdown("### How it works")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown("**📦 Order placed**")
c2.markdown("**📊 Risk scored**")
c3.markdown("**⚖️ Dispute drafted**")
c4.markdown("**🧑‍⚖️ Human reviews**")
c5.markdown("**🧾 Fully logged**")

st.divider()

st.markdown("### At a glance")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Return-Risk ROC-AUC", "0.72")
m2.metric("Chargeback Cases Validated", "5")
m3.metric("Est. FN Cost (test set)", "₹52.5K-105K")
m4.metric("Est. FP Cost (test set)", "₹50K-83K")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### Order Risk Queue")
    st.write("A live queue of incoming orders, each automatically scored for return risk with a plain-language explanation and a recommended action — plus the honest false-positive vs. false-negative cost tradeoff behind the model.")
    st.page_link("pages/1_Order_Risk_Queue.py", label="Go to Order Risk Queue →")

with col2:
    st.markdown("#### Chargeback Review")
    st.write("AI drafts an evidence-backed response to a disputed transaction. A human always approves, rejects, or edits before anything is submitted — every step logged.")
    st.page_link("pages/2_Chargeback_Review.py", label="Go to Chargeback Review →")