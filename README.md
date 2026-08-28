# Refund Rehab

*Treating the merchant's returns and chargeback problem.*

Built for Razorpay's AI Risk Manager buildathon (Track 2).

**Goal:** Stop merchant losses from returns and chargebacks, with every AI-driven money action kept explainable, bounded, and human-gated.

**Live demo:** https://refund-rehab.streamlit.app

**Builder:** Solo, CS & Data Science undergrad. Background in imbalanced classification (churn prediction) and SQL/Python/Power BI pipelines, with prior LLM API work on small undeployed projects (a chatbot and a virtual assistant). This is the first system taken through to deployment.

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
- Per-category loss rates are reasoned defaults, not measured figures — no return-handling cost data was available to fit them. They are exposed as editable inputs precisely so they are read as assumptions rather than findings; a merchant would set them from their own restocking and shipping costs.
- Simulated disputes and orders added during a session live in Streamlit session state only, so they do not survive a page refresh or persist across users. Only the seed dispute set is durable.
- Model artifacts were pickled under scikit-learn 1.6.1 and load under 1.9.0, producing a version warning. Dependency versions should be pinned before anyone else runs this.

---

## Interactive Dashboard

A Streamlit application (`app/`) ties both components into one working product, rather than leaving them as notebook cells:

- **Home** — project overview, at-a-glance metrics, and navigation.
- **Order Risk Queue** — a live queue of incoming orders, each scored automatically on arrival, showing the risk tier, a plain-language explanation of the top risk drivers, the expected rupee loss on that order, and the customer's risk history. High-risk orders surface a human decision (approve anyway / require prepayment) rather than acting automatically; once an order is dispositioned it leaves the pending queue and the headline totals drop accordingly, so the numbers respond to reviewer action. A manual scoring form is retained for ad-hoc checks, and the honest cost-tradeoff analysis is surfaced directly in the UI rather than buried in docs.

**Expected loss, modelled properly:** the queue does not simply report `probability × order value`, which would assume a return costs the merchant the full order value. A returned item usually comes back and can be resold, so the merchant loses only the handling cost — return shipping, restocking, non-refunded gateway fees, and resale markdown. Expected loss is therefore `probability × order value × loss rate`, structurally mirroring the `PD × LGD × EAD` form used in credit risk. Loss rates are **per category** (groceries approach total loss since perishables can't be resold; books are near-fully recoverable; electronics sit in between due to open-box discounting) and are exposed as an editable sidebar control rather than hidden constants, because they are merchant assumptions, not model outputs. The UI shows both figures — order value at risk, and expected cost after applying the loss rate — so the distinction is never blurred.

**A feature deliberately not built:** the obvious next move was to have "require prepayment" reduce an order's risk score. Before building it, the model was queried directly on the same order under each payment method. Prepaid methods scored *equal to or slightly higher* than COD, because `payment_method` drives chargeback risk in this dataset, not return risk — COD was excluded from chargeback risk entirely, since there is no card to dispute. Shipping the feature anyway would have made risk visibly rise when a reviewer mitigated it. Instead, dispositioning an order clears it from the pending queue: the totals move because work was cleared, not because risk was conjured away.
- **Chargeback Review** — the human-gated queue: generate an AI draft, see its evidence-strength assessment, and approve / reject-for-revision / edit-directly, exactly as specified in the original design.
- **Audit Trail** — a full, timestamped, cycle-grouped history of every draft, decision, revision, and outcome for any dispute, proving (not just claiming) explainability. A summary panel reports how the AI actually performed: how many drafts were approved unchanged, sent back for revision, or rewritten by a human, plus how many the AI itself flagged WEAK and advised against contesting.

**Visible AI-to-human feedback loop:** when a reviewer rejects a draft, the UI shows the original draft, the reviewer's stated objection, and the AI's revision in sequence — so the causality is visible rather than implied. It also reports whether the AI's evidence-strength assessment changed, which surfaced a useful robustness property in testing: asked to argue more forcefully, the model strengthened its argument without inflating its own confidence rating.

**Bounded authority:** the Chargeback Review page includes a role selector (Reviewer / Manager). Reviewers cannot approve disputes above a set value threshold — the approve action is disabled with an explanation, and the acting role is written into the audit record. This makes the "bounded" requirement a working mechanism rather than a claim.

**Cross-linked customers:** orders and disputes draw from one shared customer registry, so both pages can show the same customer's history (total orders, past returns, prior chargebacks). A dispute from a customer who has disputed before is visibly different from a first-time dispute.

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
