import streamlit as st
import pandas as pd
import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import utils

st.set_page_config(page_title="Order Risk Queue", page_icon="ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â°ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦", layout="wide")
st.title("Order Risk Queue")
st.caption("Live order queue. Every order is scored automatically the moment it's placed.")

model, model_columns = utils.load_return_risk_model()

if 'orders' not in st.session_state:
    seed_orders = [utils.generate_random_order() for _ in range(4)]
    st.session_state.orders = seed_orders

st.markdown("New orders normally arrive via your order management system. This button simulates a new order being placed.")
if st.button("Simulate New Order Placed"):
    new_order = utils.generate_random_order()
    st.session_state.orders.insert(0, new_order)
    st.rerun()

st.divider()
total_at_risk = 0.0
total_value = 0.0
for _o in st.session_state.orders:
    _df = pd.DataFrame([{k: v for k, v in _o.items() if k != "order_id"}])
    _enc = pd.get_dummies(_df, columns=["product_category", "payment_method"])
    _enc = _enc.reindex(columns=model_columns, fill_value=0)
    _p = model.predict_proba(_enc)[:, 1][0]
    total_at_risk += _p * _o["order_value"]
    total_value += _o["order_value"]

k1, k2, k3 = st.columns(3)
k1.metric("Orders in queue", len(st.session_state.orders))
k2.metric("Total order value", "Rs." + format(total_value, ",.0f"))
k3.metric("Expected return loss", "Rs." + format(total_at_risk, ",.0f"))

st.subheader("Order Queue")

RISK_LABELS = {"HIGH": ":red[HIGH RISK]", "MEDIUM": ":orange[MEDIUM RISK]", "LOW": ":green[LOW RISK]"}

for order in st.session_state.orders:
    order_df = pd.DataFrame([{k: v for k, v in order.items() if k not in ['order_id']}])
    encoded = pd.get_dummies(order_df, columns=['product_category', 'payment_method'])
    encoded = encoded.reindex(columns=model_columns, fill_value=0)
    probability = model.predict_proba(encoded)[:, 1][0]
    risk_tier, action = utils.recommend_action(probability)
    reasons = utils.explain_order_risk(order)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
        c1.markdown(f"**{order['order_id']}**  \nCustomer {order['customer_id']}")
        c2.markdown(f"{order['product_category']}  \nRs.{order['order_value']:.0f}")
        c3.markdown(f"**{probability*100:.1f}%** | {RISK_LABELS[risk_tier]}")
        c4.markdown(f"*{action}*")
        st.caption("Expected loss on this order: Rs." + format(probability * order["order_value"], ",.0f"))
        st.caption("Why: " + "; ".join(reasons))
        st.caption("Risk history: " + utils.customer_risk_note(order["customer_id"]))

        if risk_tier == "HIGH":
            decision_key = f"decision_{order['order_id']}"
            if decision_key not in st.session_state:
                b1, b2, b3 = st.columns([1, 1.4, 3])
                if b1.button("Approve anyway", key=f"approve_{order['order_id']}"):
                    st.session_state[decision_key] = "approved"
                    st.rerun()
                if b2.button("Confirm: require prepayment", key=f"confirm_{order['order_id']}"):
                    st.session_state[decision_key] = "prepayment"
                    st.rerun()
            elif st.session_state[decision_key] == "approved":
                st.success(f"{order['order_id']} approved by reviewer, overriding HIGH risk flag.")
            elif st.session_state[decision_key] == "prepayment":
                st.info(f"{order['order_id']} flagged for prepayment requirement.")

st.divider()
with st.expander("Score a custom order manually"):
    col1, col2, col3 = st.columns(3)
    with col1:
        customer_past_returns = st.number_input("Customer's past returns", min_value=0, max_value=20, value=1)
        customer_past_chargebacks = st.number_input("Customer's past chargebacks", min_value=0, max_value=10, value=0)
        product_category = st.selectbox("Product category", ["apparel", "electronics", "groceries", "books", "home_furniture"])
    with col2:
        item_price = st.number_input("Item price (Rs.)", min_value=1.0, value=1500.0)
        quantity = st.number_input("Quantity", min_value=1, max_value=10, value=1)
        payment_method = st.selectbox("Payment method", ["credit_card", "debit_card", "upi", "netbanking", "cod"])
    with col3:
        payment_attempts = st.number_input("Payment attempts", min_value=1, max_value=5, value=1)
        delivery_days = st.number_input("Delivery days", min_value=1, max_value=30, value=5)
        address_mismatch = st.selectbox("Billing/shipping mismatch", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes")

    if st.button("Score This Order", type="primary"):
        manual_order = {
            "customer_past_returns": customer_past_returns, "customer_past_chargebacks": customer_past_chargebacks,
            "product_category": product_category, "item_price": item_price, "quantity": quantity,
            "order_value": item_price * quantity, "payment_method": payment_method,
            "payment_attempts": payment_attempts, "delivery_days": delivery_days, "address_mismatch": address_mismatch
        }
        probability = utils.score_order(manual_order, model, model_columns)
        risk_tier, action = utils.recommend_action(probability)
        reasons = utils.explain_order_risk(manual_order)
        st.markdown(f"### {probability*100:.1f}% | {RISK_LABELS[risk_tier]}")
        st.markdown(f"*{action}*")
        st.caption("Why: " + "; ".join(reasons))
        st.caption("Risk history: " + utils.customer_risk_note(order["customer_id"]))

st.divider()
st.subheader("Model Performance & Honest Cost Tradeoff")
m1, m2, m3 = st.columns(3)
m1.metric("ROC-AUC", "0.72")
m2.metric("Precision (return class)", "0.37")
m3.metric("Recall (return class)", "0.59")
st.markdown("""
At the default threshold, this model produces roughly 832 false positives vs. 350 false negatives on a
4,000-order test set. Estimated cost: false negatives ~Rs.52.5K-105K total, false positives ~Rs.50K-83K total
(assuming ~20% customer abandonment on wrongly-flagged orders). These are roughly comparable  -ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â F1-optimal
thresholding was tested and rejected since it increased false positives without lowering real cost.""")
