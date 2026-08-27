import os
import json
import uuid
from datetime import datetime
import joblib
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'audit_trail.jsonl')
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'return_risk_model.pkl')
COLUMNS_PATH = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'return_risk_model_columns.pkl')

SYSTEM_PROMPT = """You are an expert payment disputes specialist assisting an e-commerce merchant on the Razorpay platform. Your objective is to evaluate chargeback disputes and draft objective, evidence-backed contest representations for acquiring banks.

### INPUT DATA
You will be provided with context containing:
- Dispute Reason Code (e.g., goods_services_not_received, goods_services_not_as_described_or_defective, credit_not_processed, unauthorized_transaction)
- Order Details (Dispute ID, Amount, Order Date, Respond-By Deadline)
- Delivery & Fulfillment Evidence (Delivered status, Delivery Date, Tracking ID, Receiver Confirmation)
- Customer Communication History (whether the customer contacted support before disputing)
- Return Policy Context (whether the order falls within the merchant's stated return window)

### YOUR TASK
1. Analyze Evidence Strength: classify as STRONG, WEAK, or AMBIGUOUS.
   - STRONG: Direct, verifiable proof addressing the dispute reason.
   - WEAK: Missing core proof (e.g., delivered=False, no tracking ID, or clear merchant fault).
   - AMBIGUOUS: Partial evidence present, but missing key verification.
2. Draft Representation Letter:
   - Write a clear, concise, professional response for the issuing bank's dispute operations team.
   - Reference only the explicit facts provided. Never invent tracking numbers, delivery dates, or customer interactions.
   - Treat None, empty, or omitted fields as non-existent. Do not infer or extrapolate missing data.
   - If WEAK, clearly advise in the reasoning why contesting carries a low probability of success, but still draft a basic response using only available facts if requested.

### CONSTRAINTS
- Zero Hallucination: Do not fabricate tracking IDs, timestamps, delivery confirmations, or customer statements not present in the input.
- Tone: Formal, objective, factual, and persuasive for banking representatives.
- Word Count: Keep DRAFT_RESPONSE between 100 and 150 words.

### OUTPUT FORMAT
ASSESSMENT: [STRONG | WEAK | AMBIGUOUS]
REASONING: [2-3 concise sentences]
DRAFT_RESPONSE: [Professional response text]
"""

def load_return_risk_model():
    model = joblib.load(MODEL_PATH)
    columns = joblib.load(COLUMNS_PATH)
    return model, columns

def score_order(order_dict, model, model_columns):
    df = pd.DataFrame([order_dict])
    df_encoded = pd.get_dummies(df, columns=['product_category', 'payment_method'])
    df_encoded = df_encoded.reindex(columns=model_columns, fill_value=0)
    probability = model.predict_proba(df_encoded)[:, 1][0]
    return probability

def format_dispute_for_prompt(dispute_row):
    return f"""
Dispute ID: {dispute_row['dispute_id']}
Reason Code: {dispute_row['reason_code']}
Amount: {dispute_row['amount']}
Order Date: {dispute_row['order_date']}
Delivered: {dispute_row['delivered']}
Delivery Date: {dispute_row['delivery_date']}
Tracking ID: {dispute_row['tracking_id']}
Receiver Confirmation: {dispute_row['receiver_confirmation']}
Customer Contacted Support Before Dispute: {dispute_row['customer_contacted_support']}
Within Return Window: {dispute_row['within_return_window']}
Respond By: {dispute_row['respond_by']}
"""

def get_dispute_response(dispute_row, model_name="gemini-3.6-flash"):
    formatted_input = format_dispute_for_prompt(dispute_row)
    model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(formatted_input)
    return response.text

def revise_dispute_response(dispute_row, original_draft, rejection_reason, rejection_note, model_name="gemini-3.6-flash"):
    formatted_input = format_dispute_for_prompt(dispute_row)
    revision_instruction = f"""
Your previous draft for this dispute was:
---
{original_draft}
---
A human reviewer REJECTED this draft for the following reason: {rejection_reason}
Reviewer's note: {rejection_note}

Please produce a revised ASSESSMENT, REASONING, and DRAFT_RESPONSE that addresses this specific feedback, following the same output format and constraints as before.

Original dispute details:
{formatted_input}
"""
    model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(revision_instruction)
    return response.text

def parse_llm_response(response_text):
    result = {"assessment": None, "reasoning": None, "draft_response": None}
    try:
        if "ASSESSMENT:" in response_text:
            result["assessment"] = response_text.split("ASSESSMENT:")[1].split("REASONING:")[0].strip()
        if "REASONING:" in response_text:
            result["reasoning"] = response_text.split("REASONING:")[1].split("DRAFT_RESPONSE:")[0].strip()
        if "DRAFT_RESPONSE:" in response_text:
            result["draft_response"] = response_text.split("DRAFT_RESPONSE:")[1].strip()
    except Exception:
        pass
    return result

def log_audit_event(dispute_id, event_type, ai_assessment=None, ai_draft_text=None,
                     human_decision=None, human_notes=None, final_submitted_text=None, outcome=None):
    entry = {
        "audit_id": str(uuid.uuid4()),
        "dispute_id": dispute_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "ai_assessment": ai_assessment,
        "ai_draft_text": ai_draft_text,
        "human_decision": human_decision,
        "human_notes": human_notes,
        "final_submitted_text": final_submitted_text,
        "outcome": outcome
    }
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    with open(AUDIT_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    return entry

def read_audit_trail(dispute_id=None):
    events = []
    if not os.path.exists(AUDIT_LOG_PATH):
        return events
    with open(AUDIT_LOG_PATH, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if dispute_id is None or entry['dispute_id'] == dispute_id:
                events.append(entry)
    return events

# --- Simulated Razorpay webhook ---

def generate_fake_webhook_payload(dispute_id, reason_code, amount, delivered=True):
    import random
    from datetime import datetime, timedelta
    order_date = datetime.now() - timedelta(days=random.randint(5, 20))
    respond_by = datetime.now() + timedelta(days=random.randint(7, 21))
    return {
        "entity": "event",
        "event": "payment.dispute.created",
        "payload": {
            "dispute": {
                "entity": {
                    "id": dispute_id,
                    "entity": "dispute",
                    "payment_id": f"pay_{random.randint(100000,999999)}",
                    "amount": amount,
                    "currency": "INR",
                    "reason_code": reason_code,
                    "respond_by": int(respond_by.timestamp()),
                    "status": "open",
                    "phase": "chargeback",
                    "created_at": int(datetime.now().timestamp())
                }
            }
        },
        "_simulated_extra_context": {
            "order_date": order_date.strftime("%Y-%m-%d"),
            "delivered": delivered,
            "delivery_date": (order_date + timedelta(days=random.randint(2,7))).strftime("%Y-%m-%d") if delivered else None,
            "tracking_id": f"TRK{random.randint(100000000,999999999)}" if delivered else None,
            "receiver_confirmation": "OTP verified on delivery" if delivered else None,
            "customer_contacted_support": random.choice([True, False]),
            "within_return_window": random.choice([True, False, None])
        }
    }

def webhook_to_dispute_row(payload):
    dispute_entity = payload["payload"]["dispute"]["entity"]
    extra = payload["_simulated_extra_context"]
    from datetime import datetime
    respond_by_date = datetime.fromtimestamp(dispute_entity["respond_by"]).strftime("%Y-%m-%d")
    return {
        "dispute_id": dispute_entity["id"],
        "reason_code": dispute_entity["reason_code"],
        "amount": dispute_entity["amount"],
        "order_date": extra["order_date"],
        "delivered": extra["delivered"],
        "delivery_date": extra["delivery_date"],
        "tracking_id": extra["tracking_id"],
        "receiver_confirmation": extra["receiver_confirmation"],
        "customer_contacted_support": extra["customer_contacted_support"],
        "within_return_window": extra["within_return_window"],
        "respond_by": respond_by_date
    }