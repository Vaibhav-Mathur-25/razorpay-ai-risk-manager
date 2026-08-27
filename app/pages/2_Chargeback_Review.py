import streamlit as st
import pandas as pd
import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import utils

st.set_page_config(page_title="Chargeback Review", page_icon="⚖️", layout="wide")
st.title("Chargeback Review Queue")

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'test_disputes.csv')

if 'disputes_df' not in st.session_state:
    st.session_state.disputes_df = pd.read_csv(DATA_PATH)

st.markdown("New disputes normally arrive via Razorpay's `payment.dispute.created` webhook. This button simulates that event for demo purposes.")
if st.button("Simulate Incoming Dispute (webhook)"):
    new_id = f"disp_{random.randint(100,999)}"
    reason = random.choice(["goods_services_not_received", "goods_services_not_as_described_or_defective", "unauthorized_transaction", "credit_not_processed"])
    amount = random.randint(500, 15000)
    delivered = random.choice([True, False])
    fake_payload = utils.generate_fake_webhook_payload(new_id, reason, amount, delivered=delivered)
    new_row = utils.webhook_to_dispute_row(fake_payload)
    st.session_state.disputes_df = pd.concat([st.session_state.disputes_df, pd.DataFrame([new_row])], ignore_index=True)
    st.success(f"New dispute {new_id} received via webhook and added to queue.")
    st.rerun()

disputes_df = st.session_state.disputes_df

BADGE_COLORS = {"STRONG": "STRONG", "WEAK": "WEAK", "AMBIGUOUS": "AMBIGUOUS"}

if "drafts" not in st.session_state:
    st.session_state.drafts = {}

st.divider()
st.subheader("Queue")
for idx, row in disputes_df.iterrows():
    dispute_id = row['dispute_id']
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        col1.markdown(f"**{dispute_id}**")
        col2.markdown(f"{row['reason_code']}")
        col3.markdown(f"Rs.{row['amount']}")
        col4.markdown(f"Due: {row['respond_by']}")

        if dispute_id not in st.session_state.drafts:
            if col4.button("Generate Draft", key=f"gen_{dispute_id}"):
                with st.spinner("AI drafting response..."):
                    raw = utils.get_dispute_response(row)
                    parsed = utils.parse_llm_response(raw)
                    st.session_state.drafts[dispute_id] = {"raw": raw, "parsed": parsed, "row": row}
                    utils.log_audit_event(
                        dispute_id=dispute_id, event_type="DRAFT_CREATED",
                        ai_assessment=parsed["assessment"], ai_draft_text=raw
                    )
                st.rerun()
        else:
            draft = st.session_state.drafts[dispute_id]
            assessment = draft["parsed"]["assessment"] or "UNKNOWN"
            st.markdown(f"**Assessment: {assessment}**")

            with st.expander("View reasoning and draft"):
                st.markdown(f"**Reasoning:** {draft['parsed']['reasoning']}")
                st.markdown(f"**Draft Response:**")
                st.text_area("draft_text", value=draft["parsed"]["draft_response"], height=150, key=f"draft_{dispute_id}", label_visibility="collapsed")

            b1, b2, b3 = st.columns(3)
            if b1.button("Approve", key=f"approve_{dispute_id}"):
                utils.log_audit_event(dispute_id=dispute_id, event_type="HUMAN_DECISION",
                                       human_decision="approved", final_submitted_text=draft["parsed"]["draft_response"])
                utils.log_audit_event(dispute_id=dispute_id, event_type="SUBMITTED",
                                       final_submitted_text=draft["parsed"]["draft_response"])
                st.success("Approved and submitted.")

            if b2.button("Reject", key=f"reject_{dispute_id}"):
                st.session_state[f"show_reject_{dispute_id}"] = True

            if b3.button("Edit", key=f"edit_{dispute_id}"):
                st.session_state[f"show_edit_{dispute_id}"] = True

            if st.session_state.get(f"show_reject_{dispute_id}"):
                reason = st.selectbox("Reason", ["missing_evidence", "wrong_tone", "factually_incorrect", "incomplete_argument", "other"], key=f"reason_{dispute_id}")
                note = st.text_input("What should change?", key=f"note_{dispute_id}")
                if st.button("Submit rejection & revise", key=f"submit_reject_{dispute_id}"):
                    utils.log_audit_event(dispute_id=dispute_id, event_type="HUMAN_DECISION",
                                           human_decision="rejected_for_revision", human_notes=f"{reason}: {note}")
                    with st.spinner("AI revising..."):
                        revised_raw = utils.revise_dispute_response(draft["row"], draft["raw"], reason, note)
                        revised_parsed = utils.parse_llm_response(revised_raw)
                        st.session_state.drafts[dispute_id] = {"raw": revised_raw, "parsed": revised_parsed, "row": draft["row"]}
                        utils.log_audit_event(dispute_id=dispute_id, event_type="DRAFT_REVISED",
                                               ai_assessment=revised_parsed["assessment"], ai_draft_text=revised_raw)
                    st.session_state[f"show_reject_{dispute_id}"] = False
                    st.rerun()

            if st.session_state.get(f"show_edit_{dispute_id}"):
                edited = st.text_area("Your final version", key=f"edited_text_{dispute_id}")
                if st.button("Submit edited version", key=f"submit_edit_{dispute_id}"):
                    utils.log_audit_event(dispute_id=dispute_id, event_type="HUMAN_DECISION",
                                           human_decision="human_edited", final_submitted_text=edited)
                    utils.log_audit_event(dispute_id=dispute_id, event_type="SUBMITTED", final_submitted_text=edited)
                    st.session_state[f"show_edit_{dispute_id}"] = False
                    st.success("Human-edited version submitted.")