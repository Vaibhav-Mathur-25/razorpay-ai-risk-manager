# AI Risk Manager — Razorpay Buildathon (Track 2)

**Goal:** Stop merchant losses from returns and chargebacks, with every AI-driven money action kept explainable, bounded, and human-gated.

**Builder:** Solo, CS & Data Science undergrad. Background in imbalanced classification (churn prediction) and SQL/Python/Power BI pipelines. First-time LLM API user.

---

## Why two components, in this order

The system has two parts, built in this order deliberately:

1. **Return-Risk Scorer** — classical ML classification, a proven strength, banked first as a complete working system.
2. **Chargeback Evidence Responder** — an LLM-powered, human-gated agent, the new-learning piece, given the most iteration time since it carries the most risk and the most novelty.

This ordering meant the "safe" component was locked in early, freeing the rest of the timeline for the harder, unfamiliar part.

---

## Part 1: Return-Risk Scorer

### The gap it fills
Before a return happens, most merchants have no systematic way to flag which orders are likely to come back — return risk is usually only visible in hindsight.

### Data
A custom-built synthetic dataset (not Kaggle) — 20,000 transactions, 19 features: customer history, pricing, payment behavior, delivery, geography, and two labels (`is_returned`, `is_chargeback`).

**Why synthetic, and why not just random:** labels were generated causally — a logistic (log-odds → sigmoid) formula combines feature-driven risk factors into a probability, which is then sampled to produce the actual label. This was chosen over:
- **Independent random labels** — would make any resulting "accuracy" meaningless, since there'd be no real relationship for a model to learn.
- **Additive probability formulas** — clip at 1.0 once several risk factors stack, collapsing high-risk and extreme-risk transactions into the same bucket and destroying resolution exactly where it matters most.

Base rates were calibrated by generating, checking the actual resulting label rate, and adjusting the intercept — standard practice for synthetic data, not a failure of the first attempt.

### Model & evaluation
- **Random Forest**, `class_weight='balanced'`, stratified 80/20 split (16,000 / 4,000).
- **ROC-AUC: 0.72** — deliberately not higher, since labels were generated with intentional randomness (a perfect classifier here would indicate overfitting to noise, not genuine signal).
- **At default threshold:** precision 0.37, recall 0.59 on the minority class.
- **Feature importances match the intended causal design** — `customer_past_returns` is the top feature, followed by price and `product_category_apparel`, with payment-method features weakest — direct evidence the model learned real structure, not noise.

### Honest cost tradeoff (no cherry-picking)
A false positive here (flagging a low-risk order, e.g. triggering a COD-denial policy) and a false negative (missing an actual future return) were quantified in ₹ terms, not just reported as abstract precision/recall:

- **False negatives** (350 in test set): ~₹150–300 each in shipping/restocking cost → ₹52,500–105,000 total.
- **False positives** (832 in test set): assuming ~20% of wrongly-flagged genuine customers abandon the purchase, at a ~₹300–500 acquisition cost each → ₹50,000–83,000 total.

**These are roughly comparable** — the initial assumption that false positives are "safer" than false negatives did not hold once actual volumes were multiplied through. This is reported honestly rather than optimized away.

**On threshold tuning:** F1-optimal thresholding was tested and rejected — it increased false positives (832 → 1,194) for a negligible F1 gain, because F1 doesn't account for the actual (comparable) costs of each error type. The default threshold was kept, and cost-weighted threshold optimization is flagged as future work rather than silently applying a metric that doesn't match the real business objective.

**On model selection:** alternative models/hyperparameter tuning were considered and deliberately not pursued — since labels were synthetically generated with a known noise ceiling (~0.72 AUC by design), a different model was unlikely to meaningfully improve results, and that time was better spent on the LLM component.

---

## Part 2: Chargeback Evidence Responder

### The actual gap (validated against Razorpay's real product, not assumed)
Research into Razorpay's own dashboard, API, and blog content confirmed: merchants already have infrastructure to *view* disputes, *upload* evidence, and *track* status via dashboard or API. What's missing is help with the actual bottleneck — Razorpay's own content states merchants spend **2–5 hours per chargeback** just researching and writing the evidence response. This system sits on top of Razorpay's existing rails, targeting that specific bottleneck — not replacing the dispute infrastructure itself.

The dispute schema (reason codes, `evidence.*` fields, `respond_by` deadlines) mirrors Razorpay's actual Dispute API object, so the design maps directly onto their real system rather than an invented one.

### Flow (human-gated, not autonomous)
1. **AI drafts** an evidence response, given the dispute's reason code and known facts (delivery, tracking, communication history, return-window status).
2. **Human reviews**: approve / reject (with structured reason + free-text note) / edit directly.
3. **Approved →** auto-submitted. **Rejected →** AI revises using the specific feedback, or the human writes their own final version.
4. **Every step logged** — draft, assessment, decision, revision, submission, and eventual outcome — as an append-only audit trail (JSONL), reconstructable as a full timeline per dispute.

### Model note
Built and validated on **Google Gemini (gemini-3.6-flash)**, free tier — chosen after a payment-processing issue blocked direct Anthropic billing. The prompt and architecture are provider-agnostic; Claude was the original target and remains a planned swap given its typically stronger structured-output and hallucination-resistance behavior, but Gemini was empirically validated (not just assumed adequate) against 5 varied test cases before being adopted.

### What was actually tested, and what it proved
Five synthetic disputes were built spanning a deliberate range of evidence strength:

| Case | Scenario | AI Assessment | Correct? |
|---|---|---|---|
| disp_001 | Clean delivery, OTP confirmed | STRONG | ✅ |
| disp_002 | Delivered, but customer claims defect | AMBIGUOUS | ✅ |
| disp_003 | Delivered, return window closed | (human-edited path tested) | — |
| disp_004 | Delivered w/ OTP, but "unauthorized transaction" claim | AMBIGUOUS | ✅ — correctly distinguished physical delivery from payment authorization |
| disp_005 | Never delivered, no evidence | WEAK | ✅ — correctly recommended against confident contesting |

Key findings, evidenced not asserted:
- **No fabricated facts** across any test case — every figure, date, and ID in each draft traced back to the input data.
- **Tone genuinely shifted with evidence strength** — confident and assertive for STRONG cases, neutral/factual for WEAK cases, rather than uniformly persuasive regardless of merit.
- **Revisions genuinely incorporated specific human feedback** — e.g., asked to "emphasize the return-window point," the model restructured its argument to lead with that point and closed with a firmer request, without inflating its own confidence (`AMBIGUOUS` stayed `AMBIGUOUS`).
- **Human authority is real, not simulated** — a human approved a AI-flagged WEAK case in testing, and the audit trail transparently preserved both facts side by side (`AI Assessment: WEAK`, `Human Decision: approved`) rather than hiding the override.
- One reliability issue caught: the model once misspelled "AMBIGUOUS" in its output — noted as a reason to avoid strict-equality string parsing on assessment fields in any production version.

### Known limitations
- Tested against synthetic disputes, not live Razorpay dispute data — a real integration would need to handle messier, incomplete, or contradictory real-world evidence.
- Evaluated on 5 hand-designed cases, not a statistically large sample — sufficient to validate the design's behavior, not to claim a measured win-rate.
- No automated win/loss outcome tracking yet exists (the `outcome` field is logged but currently only ever set manually/simulated) — a real system would need to ingest Razorpay's dispute-status webhooks to populate this automatically.
- Anthropic Claude billing was blocked during this build; Gemini was substituted and validated, but a side-by-side comparison of both models on the same cases (an interesting robustness check) wasn't completed due to time constraints.

---

## Interactive Dashboard

A Streamlit application (`app/`) ties both components into one working product, rather than leaving them as notebook cells:

- **Home** — project overview, at-a-glance metrics, and navigation.
- **Return-Risk Scorer** — live scoring form for a new order, plus the honest cost-tradeoff analysis surfaced directly in the UI (not buried in docs).
- **Chargeback Review** — the human-gated queue: generate an AI draft, see its evidence-strength assessment, and approve / reject-for-revision / edit-directly, exactly as specified in the original design.
- **Audit Trail** — a full, timestamped, cycle-grouped history of every draft, decision, revision, and outcome for any dispute, proving (not just claiming) explainability.

**Simulated dispute ingestion:** since this build doesn't have a live Razorpay merchant account, new disputes are introduced via a simulated `payment.dispute.created` webhook — a button on the Chargeback Review page generates a payload matching Razorpay's actual webhook schema (`entity`, `payment_id`, `reason_code`, `respond_by`, etc.) and feeds it into the same review pipeline a real webhook would. A production version would replace this with a real endpoint subscribed to Razorpay's dispute webhooks.

**Theming:** a custom dark navy/blue theme (`.streamlit/config.toml`) was used in place of Streamlit's defaults, to read as a deliberate fintech risk-dashboard rather than a generic demo.

### Running the dashboard
```
pip install -r requirements.txt
streamlit run app/Home.py
```
Requires a `.env` file at the project root with `GOOGLE_API_KEY=<your key>` (see Model note above; the code is structured so swapping to `ANTHROPIC_API_KEY` / Claude only requires changing `app/utils.py`).

## Tech stack
Python, pandas, NumPy, scikit-learn, Jupyter (Return-Risk Scorer); Google Generative AI SDK, python-dotenv, JSON/JSONL audit logging, Streamlit (Chargeback Responder + Dashboard).
