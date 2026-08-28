import streamlit as st

st.set_page_config(page_title="Refund Rehab", page_icon="ðŸ“Š", layout="wide")

st.title("Refund Rehab")
st.subheader("Treating the merchant's returns and chargeback problem")

st.markdown("A two-part system for e-commerce risk: predict returns before they happen, and handle chargeback disputes with a human always in control of the final call.")

st.divider()

st.markdown("### How it works")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown("**ðŸ“¦ Order placed**")
c2.markdown("**ðŸ“Š Risk scored**")
c3.markdown("**âš–ï¸ Dispute drafted**")
c4.markdown("**ðŸ§‘â€âš–ï¸ Human reviews**")
c5.markdown("**ðŸ§¾ Fully logged**")

st.divider()

st.markdown("### At a glance")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Return-Risk ROC-AUC", "0.738")
m2.metric("Chargeback Cases Validated", "5")
m3.metric("Est. FN Cost (test set)", "Rs.38K-76K")
m4.metric("Est. FP Cost (test set)", "Rs.67K-112K")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### Order Risk Queue")
    st.write("A live queue of incoming orders, each automatically scored for return risk with a plain-language explanation and a recommended action â€” plus the honest false-positive vs. false-negative cost tradeoff behind the model.")
    st.page_link("pages/1_Order_Risk_Queue.py", label="Go to Order Risk Queue â†’")

with col2:
    st.markdown("#### Chargeback Review")
    st.write("AI drafts an evidence-backed response to a disputed transaction. A human always approves, rejects, or edits before anything is submitted â€” every step logged.")
    st.page_link("pages/2_Chargeback_Review.py", label="Go to Chargeback Review â†’")
