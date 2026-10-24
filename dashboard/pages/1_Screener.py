"""
Screener  -  pre-screens a VUP Financial Services application against the 2024 Ministerial
Instructions (rules from config/fs_rules.yaml) and scores household poverty with the EICV7
screener model. Advises the Sector Loan Committee; never decides.
No personal data is collected or stored: the session log keeps outcomes under a random case id.
"""
import json, os, uuid, datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HERE, "..", "data")

st.set_page_config(page_title="FS Screener", page_icon="🗂️", layout="wide")

@st.cache_data
def load():
    rules = yaml.safe_load(open(os.path.join(ROOT, "config", "fs_rules.yaml")))
    model = json.load(open(os.path.join(DATA, "screener_model.json")))
    dist = pd.read_csv(os.path.join(DATA, "districts.csv"))[["district_code", "district", "province", "coverage_poor", "alert_low_coverage"]]
    return rules, model, dist

R, M, DIST = load()
DNAME = dict(zip(DIST.district_code, DIST.district))

def score(inputs, district_code):
    x = [float(inputs[f]) for f in M["features"]]
    x += [1.0 if district_code == d else 0.0 for d in M["districts"][1:]]
    z = (np.array(x) - np.array(M["mean"])) / np.array(M["scale"])
    logit = float(np.dot(z, np.array(M["coef"])) + M["intercept"])
    return 1 / (1 + np.exp(-logit))

def ceiling(kind, n, women_youth_share, repeat_good_payer):
    table = R["ceilings_rwf"]
    if kind == "Individual":
        key = "individual_repeat_good_payer" if repeat_good_payer else "individual"
        return table[key][0]["amount"], f"Table 1, {key.replace('_', ' ')}"
    if kind == "Group":
        key = "group_women_youth_70pct" if women_youth_share >= 0.70 else "group"
        for row in table[key]:
            if row["members"][0] <= n <= row["members"][1]:
                return row["amount"], f"Table 1, {key.replace('_', ' ')}, {n} members"
        return None, "group size outside Table 1 (7 to 15 members)"
    for row in table["cooperative"]:
        if row["members"][0] <= n <= row["members"][1]:
            amt = row["amount"]
            note = f"Table 1, cooperative, {n} members"
            if women_youth_share >= 0.80:
                amt = int(amt * (1 + table["cooperative_women_youth_80pct_uplift"]))
                note += " (+20%, 80% women/youth, Art. 11(2)(a))"
            return amt, note
    return None, "cooperative size outside Table 1 (10 or more members)"

# ---------------- page ----------------
st.title("FS application pre-screen")
st.caption(f"Rules: {R['source']['title']}, {R['source']['number']} of {R['source']['date']}. "
           f"Poverty score: logistic model trained on EICV7 (AUC {M['metrics']['auc']}). "
           "This screen advises the Sector Loan Committee; the committee decides.")

left, right = st.columns([1, 1])
with left:
    st.subheader("1. Applicant")
    kind = st.radio("Applicant type", ["Individual", "Group", "Cooperative"], horizontal=True)
    n_members = 1
    women_youth = 0.0
    if kind == "Group":
        n_members = st.number_input("Number of members", 1, 60, 10)
        women_youth = st.slider("Share of members who are women or youth", 0.0, 1.0, 0.5, 0.05)
        months_together = st.number_input("Months the group has worked together", 0, 120, 6)
        share_eligible = st.slider("Share of members who individually meet Art. 4-6", 0.0, 1.0, 0.8, 0.05)
        multi_group = st.checkbox("Any member belongs to another FS loan group")
    elif kind == "Cooperative":
        n_members = st.number_input("Number of members", 1, 500, 20)
        women_youth = st.slider("Share of members who are women or youth", 0.0, 1.0, 0.5, 0.05)
        share_poor = st.slider("Share of members from poor households", 0.0, 1.0, 0.75, 0.05)
        rca = st.checkbox("Holds RCA legal status (certificate presented)", value=True)
    repeat_good = st.checkbox("Repaid a previous FS loan in full and on time")
    has_account = st.checkbox("Holds an account at Umurenge SACCO or another financial institution", value=True)
    viable = st.checkbox("Presents a viable income-generating project", value=True)
    st.markdown("**Exclusions (Art. 6)**")
    excl = {e["key"]: st.checkbox(e["label"]) for e in R["not_eligible"]}

    st.subheader("2. Household of the applicant (or representative member)")
    c1, c2 = st.columns(2)
    district_code = c1.selectbox("District", DIST.district_code, format_func=lambda c: DNAME[c])
    rural = 1 if c2.radio("Area", ["Rural", "Urban"], horizontal=True) == "Rural" else 0
    head_age = c1.number_input("Age of household head", 15, 100, 40)
    applicant_age = c2.number_input("Age of applicant", 15, 100, 40)
    head_female = 1 if c1.radio("Sex of head", ["Male", "Female"], horizontal=True) == "Female" else 0
    head_widowed = int(c2.checkbox("Head is widowed"))
    head_no_school = int(c1.checkbox("Head never attended school"))
    hhsize = c2.number_input("Household size", 1, 20, 5)
    n_child = c1.number_input("Members under 16", 0, 15, 2)
    n_elderly = c2.number_input("Members 65 or older", 0, 10, 0)
    n_working = c1.number_input("Members aged 16-64 able to work", 0, 15, 2)
    no_adult_male = int(not c2.checkbox("At least one adult man (18+) in the household", value=True))
    any_disabled = int(c1.checkbox("A member has a disability (a lot of difficulty or cannot do)"))
    any_phone = int(c2.checkbox("Household owns a mobile phone", value=True))

    st.markdown("**Dwelling and assets (home visit)**")
    c3, c4 = st.columns(2)
    floor_improved = int(c3.checkbox("Improved floor (cement, tiles, wood)"))
    wall_cement = int(c4.checkbox("Walls with cement or burnt bricks"))
    roof_metal = int(c3.checkbox("Metal sheet roof", value=True))
    electricity = int(c4.checkbox("Electricity (grid or solar)"))
    toilet_improved = int(c3.checkbox("Improved toilet", value=True))
    rooms = c4.number_input("Rooms in the dwelling", 1, 15, 3)
    livestock = int(c3.checkbox("Owns livestock or poultry"))
    cattle = int(c4.checkbox("Owns cattle"))
    owns_dwelling = int(c3.checkbox("Owns the dwelling", value=True))
    umudugudu = int(c4.checkbox("Lives in an umudugudu settlement", value=True))
    registry_poor = st.radio("Registered as a poor household in the social registry?", ["Unknown", "Yes", "No"], horizontal=True)

with right:
    st.subheader("Result")
    # ---- rules ----
    checks = []
    def add(ok, label, art): checks.append((ok, label, art))
    tg = R["target_group"]
    add(tg["min_age"] <= applicant_age <= tg["max_age"], f"Applicant aged {tg['min_age']}-{tg['max_age']} (is {applicant_age})", "Art. 5(1)(e)")
    add(n_working >= 1, "Household has a member able to work", "Art. 4(1)")
    add(has_account, "Account at SACCO or financial institution", "Art. 5(1)(b)")
    add(viable, "Viable income-generating project", "Art. 4(2), 5(1)(f)")
    for e in R["not_eligible"]:
        add(not excl[e["key"]], f"Not excluded: {e['label'].lower()}", e["article"])
    if kind == "Group":
        gr = R["group_rules"]
        add(gr["min_members"] <= n_members <= gr["max_members"], f"Group of {gr['min_members']}-{gr['max_members']} members (has {n_members})", "Art. 5(2)(a)(i)")
        add(share_eligible >= gr["min_share_eligible_members"], f"At least 70% of members eligible ({share_eligible:.0%})", "Art. 5(2)(a)(i)")
        add(months_together >= R["general_requirements"]["group_min_months_together"], f"Worked together 3+ months ({months_together})", "Art. 5(1)(c)")
        add(not multi_group, "No member in more than one group", "Art. 5(2)(a)(ii)")
    if kind == "Cooperative":
        cr = R["cooperative_rules"]
        add(share_poor >= cr["min_share_poor_members"], f"At least 70% of members from poor households ({share_poor:.0%})", "Art. 5(2)(b)(i)")
        add(rca, "RCA legal status", "Art. 5(1)(d)")
    passed = all(ok for ok, _, _ in checks)

    # ---- model ----
    inputs = dict(hhsize=hhsize, n_child=n_child, n_elderly=n_elderly, n_working=n_working, no_adult_male=no_adult_male,
                  head_age=head_age, head_female=head_female, head_widowed=head_widowed, head_no_school=head_no_school,
                  any_disabled=any_disabled, any_phone=any_phone, floor_improved=floor_improved, wall_cement=wall_cement,
                  roof_metal=roof_metal, electricity=electricity, toilet_improved=toilet_improved, rooms=rooms,
                  livestock=livestock, cattle=cattle, owns_dwelling=owns_dwelling, umudugudu=umudugudu, rural=rural)
    p = score(inputs, int(district_code))
    likely_poor = p >= M["threshold"]
    band = "high" if p >= 0.6 else "moderate" if p >= M["threshold"] else "low"

    # ---- component suggestion ----
    if n_working == 0:
        comp, why = "Direct Support", R["component_logic"]["direct_support"]
    elif not viable or not has_account:
        comp, why = "Public Works (CPW or ePW)", R["component_logic"]["public_works"]
    elif passed:
        comp, why = "Financial Services", R["component_logic"]["financial_services"]
    else:
        comp, why = "Not FS as submitted", "one or more Art. 5-6 conditions fail; see checks"

    a, b, c = st.columns(3)
    a.metric("Rules (Art. 4-6)", "Pass" if passed else "Fail", help="All listed checks must pass")
    b.metric("Poverty likelihood", f"{p*100:.0f} %", help=f"Model threshold {M['threshold']*100:.0f}%; households like this are poor in about {p*10:.0f} of 10 cases")
    c.metric("Suggested component", comp)

    for ok, label, art in checks:
        st.markdown(f"{'✅' if ok else '❌'} {label} <span style='color:gray'>({art})</span>", unsafe_allow_html=True)

    st.markdown(f"**Poverty score, {band}.** Based on household composition, dwelling and assets, households like this one are below the "
                f"poverty line in about **{p*10:.0f} of 10 cases** in EICV7. "
                + ("The social registry also lists the household as poor. " if registry_poor == "Yes" else
                   "The social registry lists the household as non-poor; this score suggests a review. " if (registry_poor == "No" and likely_poor) else ""))
    if passed and not likely_poor:
        st.warning("Passes the rules but scores as unlikely to be poor. Art. 4 targets poor households; the committee may wish to verify.")
    if (not passed) and likely_poor and n_working >= 1:
        st.info("Likely poor and able to work, but fails a condition. If the failure is the SACCO account, account opening is a cheaper fix than rejection.")

    if comp == "Financial Services":
        amt, note = ceiling(kind, n_members, women_youth, repeat_good)
        lt = R["loan_terms"]
        if amt:
            st.markdown(f"**Loan ceiling: RWF {amt:,}** ({note}). Flat interest {lt['interest_rate_flat']*100:.0f}%, repayment within {lt['max_repayment_months']} months, no physical collateral (Art. 3). "
                        + (f"Above RWF {lt['district_approval_threshold_rwf']:,}: District technical committee approval needed (Art. 9)." if amt > lt["district_approval_threshold_rwf"] else "Sector Loan Committee can approve."))
            total = amt * (1 + lt["interest_rate_flat"])
            st.caption(f"Illustration at the ceiling: total repayable RWF {total:,.0f}; over {lt['max_repayment_months']} months about RWF {total/lt['max_repayment_months']:,.0f} per month.")
        else:
            st.error(f"Ceiling not determined: {note}.")

    # ---- note + log ----
    case = st.session_state.setdefault("case_id", str(uuid.uuid4())[:8].upper())
    note_md = f"""VUP-FS PRE-SCREENING NOTE  (case {case}, {dt.date.today()})
Applicant type: {kind}, members: {n_members}
District: {DNAME[int(district_code)]} ({'rural' if rural else 'urban'})
Rules (Art. 4-6): {'PASS' if passed else 'FAIL'}
""" + "\n".join(f"  [{'x' if ok else ' '}] {label} ({art})" for ok, label, art in checks) + f"""
Poverty likelihood (EICV7 model): {p*100:.0f}%  ({band})
Suggested component: {comp}  -  {why}
This note pre-screens an application for the Sector Loan Committee. It is not a decision.
"""
    st.download_button("Download pre-screening note", note_md, f"prescreen_{case}.txt", "text/plain")
    if st.button("Log this screening (no personal data)"):
        st.session_state.setdefault("log", []).append(dict(
            case=case, date=str(dt.date.today()), district=DNAME[int(district_code)], type=kind, members=n_members,
            rules_pass=passed, failed=[art for ok, _, art in checks if not ok], p_poor=round(p, 3),
            registry_poor=registry_poor, component=comp))
        st.session_state["case_id"] = str(uuid.uuid4())[:8].upper()
        st.success("Logged. Start a new case by changing the inputs.")

st.divider()
st.subheader("Session log: the data this tool generates")
log = st.session_state.get("log", [])
if log:
    L = pd.DataFrame(log)
    st.dataframe(L, hide_index=True, use_container_width=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Screened", len(L))
    k2.metric("Pass rules", int(L.rules_pass.sum()))
    k3.metric("Pass and likely poor", int((L.rules_pass & (L.p_poor >= M["threshold"])).sum()))
    fails = pd.Series([a for f in L.failed for a in f]).value_counts()
    if len(fails):
        st.markdown("**Most common failing condition:** " + ", ".join(f"{a} ({n})" for a, n in fails.head(3).items()))
    st.download_button("Download log (CSV)", L.to_csv(index=False), "screening_log.csv", "text/csv")
else:
    st.caption("Nothing logged yet. Each logged screening adds a row: district, applicant type, rule outcome, failing article, "
               "poverty score, component. Over time this is the demand, rejection-reason and rule-binding data VUP does not currently collect. "
               "Rows hold no names or IDs.")
