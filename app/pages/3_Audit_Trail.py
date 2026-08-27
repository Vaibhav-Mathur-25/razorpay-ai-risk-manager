import streamlit as st
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import utils

st.set_page_config(page_title="Audit Trail", page_icon="🧾", layout="wide")
st.title("Audit Trail")
st.caption("Full, timestamped history of every AI draft, human decision, and outcome — nothing overwritten, nothing hidden.")

all_events = utils.read_audit_trail()
dispute_ids = sorted(set(e['dispute_id'] for e in all_events))

if not dispute_ids:
    st.info("No audit events logged yet. Go review a dispute first.")
else:
    selected = st.selectbox("Select a dispute to view its history", dispute_ids)
    events = [e for e in all_events if e['dispute_id'] == selected]
    events.sort(key=lambda e: e['timestamp'])  # oldest-first internally, to detect cycles correctly

    ICONS = {
        "DRAFT_CREATED": "📝",
        "HUMAN_DECISION": "🧑‍⚖️",
        "DRAFT_REVISED": "🔄",
        "SUBMITTED": "📤",
        "OUTCOME": "🏁"
    }

    num_cycles = sum(1 for e in events if e['event_type'] == 'DRAFT_CREATED')
    st.markdown(f"**{len(events)} events across {max(num_cycles, 1)} review cycle(s)**")
    st.divider()

    # group events into cycles, each starting at a DRAFT_CREATED
    cycles = []
    current_cycle = []
    for e in events:
        if e['event_type'] == 'DRAFT_CREATED' and current_cycle:
            cycles.append(current_cycle)
            current_cycle = []
        current_cycle.append(e)
    if current_cycle:
        cycles.append(current_cycle)

    # show newest cycle first, but events within a cycle stay in their natural order
    for cycle_num, cycle in enumerate(reversed(cycles), 1):
        real_cycle_num = len(cycles) - cycle_num + 1
        st.markdown(f"#### Cycle {real_cycle_num}")

        for e in cycle:
            icon = ICONS.get(e['event_type'], "•")
            time_short = e['timestamp'].split('T')[1].split('.')[0]  # just HH:MM:SS
            date_short = e['timestamp'].split('T')[0]

            if e['event_type'] in ("DRAFT_CREATED", "DRAFT_REVISED"):
                st.markdown(f"{icon} **{e['event_type'].replace('_', ' ').title()}** · {date_short} {time_short} · Assessment: **{e['ai_assessment']}**")
                with st.expander("View draft text", expanded=False):
                    st.write(e['ai_draft_text'])

            elif e['event_type'] == "HUMAN_DECISION":
                decision_label = {"approved": "✅ Approved", "rejected_for_revision": "❌ Rejected for revision", "human_edited": "✏️ Edited directly"}.get(e['human_decision'], e['human_decision'])
                st.markdown(f"{icon} **Human Decision** · {date_short} {time_short} · {decision_label}")
                if e['human_notes']:
                    st.caption(f"Note: {e['human_notes']}")

            elif e['event_type'] == "SUBMITTED":
                st.markdown(f"{icon} **Submitted** · {date_short} {time_short}")
                with st.expander("View final submitted text", expanded=False):
                    st.write(e['final_submitted_text'])

            elif e['event_type'] == "OUTCOME":
                outcome_label = {"won": "🏆 Won", "lost": "💔 Lost"}.get(e['outcome'], e['outcome'])
                st.markdown(f"{icon} **Outcome** · {date_short} {time_short} · {outcome_label}")

        st.divider()
