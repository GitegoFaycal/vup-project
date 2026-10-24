"""
Tracker  -  monitors each application against the working-day limits in Art. 9 of the
FS Ministerial Instructions. Demo runs on sample entries; a production version would read
the same fields from the FS management information system (Art. 8(5), Art. 12(4)).
"""
import os, datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
st.set_page_config(page_title="FS Tracker", page_icon="⏱️", layout="wide")
R = yaml.safe_load(open(os.path.join(ROOT, "config", "fs_rules.yaml")))
T = R["timelines_working_days"]

st.title("Application timeline tracker")
st.caption("Art. 9 limits: cell to sector within "
           f"{T['cell_to_sector_submission']} working days; feedback on rejection within {T['rejection_feedback']}; "
           f"disbursement within {T['disbursement_after_contract']} working days of contract signing. "
           "Demo data only; no real applications.")

def wd(a, b):
    if pd.isna(a) or pd.isna(b): return None
    # busday_count needs day precision; pandas >= 3 timestamps are datetime64[us]
    return int(np.busday_count(pd.Timestamp(a).date(), pd.Timestamp(b).date()))

SAMPLE = pd.DataFrame([
    dict(case="A1F3", sector="Karama", received_cell="2026-10-05", sent_sector="2026-10-09", decision="2026-10-15", outcome="Approved", contract="2026-10-16", disbursed="2026-10-22"),
    dict(case="B7C2", sector="Rwimiyaga", received_cell="2026-10-06", sent_sector="2026-10-16", decision="2026-10-20", outcome="Rejected", contract=None, disbursed=None),
    dict(case="C9D8", sector="Musheri", received_cell="2026-10-07", sent_sector="2026-10-10", decision="2026-10-14", outcome="Approved", contract="2026-10-15", disbursed=None),
])
if "apps" not in st.session_state:
    st.session_state["apps"] = SAMPLE.copy()

with st.expander("Add an application"):
    c = st.columns(4)
    case = c[0].text_input("Case id", "NEW1")
    sector = c[1].text_input("Sector", "")
    received = c[2].date_input("Received at cell", dt.date.today())
    sent = c[3].date_input("Sent to sector", dt.date.today())
    c = st.columns(4)
    decision = c[0].date_input("Committee decision", dt.date.today())
    outcome = c[1].selectbox("Outcome", ["Pending", "Approved", "Rejected"])
    contract = c[2].date_input("Contract signed", dt.date.today()) if outcome == "Approved" else None
    disbursed = c[3].date_input("Disbursed", dt.date.today()) if outcome == "Approved" else None
    if st.button("Add"):
        st.session_state["apps"] = pd.concat([st.session_state["apps"], pd.DataFrame([dict(
            case=case, sector=sector, received_cell=str(received), sent_sector=str(sent), decision=str(decision),
            outcome=outcome, contract=str(contract) if contract else None, disbursed=str(disbursed) if disbursed else None)])], ignore_index=True)

A = st.session_state["apps"].copy()
for col in ["received_cell", "sent_sector", "decision", "contract", "disbursed"]:
    A[col] = pd.to_datetime(A[col], errors="coerce")
today = np.datetime64(dt.date.today())
A["cell_to_sector_wd"] = [wd(a, b) for a, b in zip(A.received_cell, A.sent_sector)]
A["contract_to_disb_wd"] = [wd(a, b if not pd.isna(b) else today) for a, b in zip(A.contract, A.disbursed)]
A["feedback_wd"] = [wd(a, today) if o == "Rejected" else None for a, o in zip(A.decision, A.outcome)]

def flag(row):
    f = []
    if row.cell_to_sector_wd is not None and row.cell_to_sector_wd > T["cell_to_sector_submission"]:
        f.append(f"cell to sector {row.cell_to_sector_wd} wd (limit {T['cell_to_sector_submission']})")
    if row.outcome == "Approved" and row.contract_to_disb_wd is not None and row.contract_to_disb_wd > T["disbursement_after_contract"]:
        f.append(f"disbursement {row.contract_to_disb_wd} wd after contract (limit {T['disbursement_after_contract']})"
                 + (" and still pending" if pd.isna(row.disbursed) else ""))
    return "; ".join(f) if f else "on time"
A["status"] = A.apply(flag, axis=1)

late = (A.status != "on time").sum()
k1, k2, k3 = st.columns(3)
k1.metric("Applications", len(A))
k2.metric("Breaching an Art. 9 limit", int(late))
k3.metric("Awaiting disbursement", int(((A.outcome == "Approved") & A.disbursed.isna()).sum()))

show = A[["case", "sector", "received_cell", "sent_sector", "decision", "outcome", "contract", "disbursed",
          "cell_to_sector_wd", "contract_to_disb_wd", "status"]].copy()
for col in ["received_cell", "sent_sector", "decision", "contract", "disbursed"]:
    show[col] = show[col].dt.strftime("%d %b").fillna("")
st.dataframe(show.style.apply(lambda s: ["background-color:#fbf1dc" if v != "on time" else "" for v in s] if s.name == "status" else [""]*len(s)),
             hide_index=True, use_container_width=True)
st.caption("Working days exclude Saturdays and Sundays; public holidays are not yet excluded. "
           "The thematic report found only 10% of CPW payments on time nationally; this view would show, per sector, which step is late.")
