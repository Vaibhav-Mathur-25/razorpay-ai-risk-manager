import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import utils

st.set_page_config(page_title="Return-Risk Scorer", page_icon="📦", layout="wide")
st.title("Return-Risk Scorer")
st.caption("Predicts the likelihood a given order will be returned, using a Random Forest trained on customer, pricing, delivery, and payment features.")

model, model_columns = utils.load_return_risk_model()

st.subheader("Score a new order")

col1, col2, col3 = st.columns(3)
with col1:
    customer_past_returns = st.number_input("Customer's past returns", min_value=0, max_value=20, value=1)
    customer_past_chargebacks = st.number_input("Customer's past chargebacks", min_value=0, max_value=10, value=0)
    product_category = st.selectbox("Product category", ["apparel", "electronics", "groceries", "books", "home_furniture"])

with col2:
    item_price = st.number_input("Item price (₹)", min_value=1.0, value=1500.0)
    quantity = st.number_input("Quantity", min_value=1, max_value=10, value=1)
    payment_method = st.selectbox("Payment method", ["credit_card", "debit_card", "upi", "netbanking", "cod"])

with col3:
    payment_attempts = st.number_input("Payment attempts", min_value=1, max_value=5, value=1)
    delivery_days = st.number_input("Delivery days", min_value=1, max_value=30, value=5)
    address_mismatch = st.selectbox("Billing/shipping country mismatch", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes")

order_value = item_price * quantity

if st.button("Score This Order", type="primary"):
    order = {
        "customer_past_returns": customer_past_returns,
        "customer_past_chargebacks": customer_past_chargebacks,
        "product_category": product_category,
        "item_price": item_price,
        "quantity": quantity,
        "order_value": order_value,
        "payment_method": payment_method,
        "payment_attempts": payment_attempts,
        "delivery_days": delivery_days,
        "address_mismatch": address_mismatch
    }
    probability = utils.score_order(order, model, model_columns)

    st.divider()
    risk_pct = probability * 100

    if risk_pct >= 50:
        st.error(f"### Risk Score: {risk_pct:.1f}% — High Risk")
    elif risk_pct >= 25:
        st.warning(f"### Risk Score: {risk_pct:.1f}% — Moderate Risk")
    else:
        st.success(f"### Risk Score: {risk_pct:.1f}% — Low Risk")

    st.progress(min(probability, 1.0))

st.divider()

st.subheader("Model Performance & Honest Cost Tradeoff")

m1, m2, m3 = st.columns(3)
m1.metric("ROC-AUC", "0.72")
m2.metric("Precision (return class)", "0.37")
m3.metric("Recall (return class)", "0.59")

st.markdown("""
**On the false-positive vs. false-negative tradeoff:** at the default threshold, this model produces
roughly 832 false positives vs. 350 false negatives on a 4,000-order test set. Rather than reporting
only accuracy or F1, the actual ₹ cost of each error type was estimated:

- **False negatives** (missed returns): ~₹150–300 each in shipping/restocking → ~₹52,500–105,000 total
- **False positives** (wrongly flagged genuine orders, e.g. triggering a COD-denial policy):
  assuming ~20% customer abandonment at a ~₹300–500 acquisition cost → ~₹50,000–83,000 total

**These are roughly comparable** — the common assumption that false positives are "safer" than false
negatives did not hold once real volumes were multiplied through. F1-optimal thresholding was tested
and rejected: it increased false positives (832 → 1,194) for negligible F1 gain, since F1 doesn't
reflect the actual, comparable costs of each error type. The default threshold was kept deliberately,
and cost-weighted threshold optimization is noted as future work.
""")
