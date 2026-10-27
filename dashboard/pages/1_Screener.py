
import json, os, sys, uuid, datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import theme
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
theme.apply("screener")
st.markdown('<div class="vup-page-title">FS application pre-screen</div>', unsafe_allow_html=True)
st.caption(f"Rules: {R['source']['title']}, {R['source']['number']} of {R['source']['date']}. "
           f"Poverty score: logistic model trained on EICV7 (AUC {M['metrics']['auc']}). "
           "This screen advises the Sector Loan Committee; the committee decides.")

STEPS = ["Applicant", "Household", "Dwelling and assets", "Result"]
KINDS = ["Individual", "Group", "Cooperative"]
EXCL_LABELS = [e["label"] for e in R["not_eligible"]]
DEFAULTS = dict(kind="Individual", n_members=10, women_youth=0.5, months_together=6, share_eligible=0.8, multi_group=False,
                share_poor=0.75, rca=True, repeat_good=False, has_account=True, viable=True, excl=[],
                district_code=int(DIST.district_code.iloc[0]), area="Rural", head_age=40, applicant_age=40, head_sex="Male",
                head_widowed=False, head_no_school=False, hhsize=5, n_child=2, n_elderly=0, n_working=2, adult_male=True,
                any_disabled=False, any_phone=True, floor_improved=False, wall_cement=False, roof_metal=True, electricity=False,
                toilet_improved=True, rooms=3, livestock=False, cattle=False, owns_dwelling=True, umudugudu=True, registry_poor="Unknown")
# the form keeps its own copy of every answer so values survive moving between steps
F = st.session_state.setdefault("fs_form", dict(DEFAULTS))
step = st.session_state.setdefault("fs_step", 1)


def stepper(cur):
    items = "".join(
        f'<div class="vup-step {"done" if i < cur else "active" if i == cur else ""}">'
        f'<span class="n">{"&#10003;" if i < cur else i}</span><span class="l">{name}</span></div>'
        for i, name in enumerate(STEPS, 1))
    st.markdown(f'<div class="vup-steps">{items}</div>', unsafe_allow_html=True)


@st.dialog("Eligibility criteria, Art. 4 to 6", width="large")
def criteria_dialog():
    src, tg, gq, gr, cr = R["source"], R["target_group"], R["general_requirements"], R["group_rules"], R["cooperative_rules"]
    st.caption(f"{src['title']}, {src['number']} of {src['date']}, {src['issuer']}.")
    st.markdown(
        f"**Art. 4, target group.** {tg['description'][0].upper() + tg['description'][1:]}. "
        f"Applicants must show {tg['must_show']}.\n\n"
        "**Art. 5(1), every applicant**\n"
        f"1. Aged {tg['min_age']} to {tg['max_age']} (Art. 5(1)(e)).\n"
        "2. Holds an account at an Umurenge SACCO or another financial institution (Art. 5(1)(b)).\n"
        "3. Presents a viable income-generating project (Art. 4(2), Art. 5(1)(f)).\n"
        f"4. Groups have worked together for at least {gq['group_min_months_together']} months (Art. 5(1)(c)); "
        "cooperatives hold RCA legal status (Art. 5(1)(d)).\n\n"
        "**Art. 5(2)(a), groups**\n"
        f"1. {gr['min_members']} to {gr['max_members']} members.\n"
        f"2. At least {gr['min_share_eligible_members']:.0%} of members individually meet the conditions above.\n"
        "3. No member belongs to another FS loan group, and the loan funds one joint project.\n\n"
        "**Art. 5(2)(b), cooperatives**\n"
        f"1. At least {cr['min_share_poor_members']:.0%} of members come from poor households "
        f"(at most {cr['max_share_other_members']:.0%} others).\n\n"
        "**Art. 6, not eligible**\n"
        + "\n".join(f"{i}. {e['label']} ({e['article']})." for i, e in enumerate(R["not_eligible"], 1)))
    st.caption("The full text is held by the sector office and in the project repository under config/fs_rules.yaml.")


stepper(step)

# ---------------- step 1: applicant ----------------
if step == 1:
    with st.container(border=True):
        theme.section("Applicant")
        F["kind"] = st.radio("Applicant type", KINDS, index=KINDS.index(F["kind"]), horizontal=True, key="fs_kind")
        if F["kind"] == "Group":
            c1, c2 = st.columns(2)
            F["n_members"] = int(c1.number_input("Number of members", 1, 60, min(F["n_members"], 60), key="fs_nm_g"))
            F["months_together"] = int(c2.number_input("Months the group has worked together", 0, 120, F["months_together"], key="fs_months"))
            F["women_youth"] = c1.slider("Share of members who are women or youth", 0.0, 1.0, F["women_youth"], 0.05, key="fs_wy_g")
            F["share_eligible"] = c2.slider("Share of members who individually meet Art. 4-6", 0.0, 1.0, F["share_eligible"], 0.05, key="fs_sh_el")
            F["multi_group"] = st.toggle("A member belongs to another FS loan group", F["multi_group"], key="fs_multi")
        elif F["kind"] == "Cooperative":
            c1, c2 = st.columns(2)
            F["n_members"] = int(c1.number_input("Number of members", 1, 500, F["n_members"], key="fs_nm_c"))
            F["women_youth"] = c2.slider("Share of members who are women or youth", 0.0, 1.0, F["women_youth"], 0.05, key="fs_wy_c")
            F["share_poor"] = c1.slider("Share of members from poor households", 0.0, 1.0, F["share_poor"], 0.05, key="fs_sh_poor")
            F["rca"] = c2.toggle("Holds RCA legal status (certificate presented)", F["rca"], key="fs_rca")
        st.markdown("**Conditions**")
        c1, c2 = st.columns(2)
        F["has_account"] = c1.toggle("Holds an account at Umurenge SACCO or another financial institution", F["has_account"], key="fs_acc")
        F["viable"] = c2.toggle("Presents a viable income-generating project", F["viable"], key="fs_viable")
        F["repeat_good"] = c1.toggle("Repaid a previous FS loan in full and on time", F["repeat_good"], key="fs_repeat")
        F["excl"] = st.multiselect("Exclusions (Art. 6): select any that apply", EXCL_LABELS, default=F["excl"], key="fs_excl",
                                   placeholder="None apply")

# ---------------- step 2: household ----------------
elif step == 2:
    with st.container(border=True):
        theme.section("Household of the applicant (or representative member)")
        c1, c2 = st.columns(2)
        codes = [int(c) for c in DIST.district_code]
        F["district_code"] = int(c1.selectbox("District", codes, index=codes.index(F["district_code"]), format_func=lambda c: DNAME[c], key="fs_dist"))
        F["area"] = c2.radio("Area", ["Rural", "Urban"], index=["Rural", "Urban"].index(F["area"]), horizontal=True, key="fs_area")
        F["applicant_age"] = int(c1.number_input("Age of applicant", 15, 100, F["applicant_age"], key="fs_app_age"))
        F["head_age"] = int(c2.number_input("Age of household head", 15, 100, F["head_age"], key="fs_head_age"))
        F["head_sex"] = c1.radio("Sex of head", ["Male", "Female"], index=["Male", "Female"].index(F["head_sex"]), horizontal=True, key="fs_head_sex")
        F["hhsize"] = int(c2.number_input("Household size", 1, 20, F["hhsize"], key="fs_hhsize"))
        F["n_child"] = int(c1.number_input("Members under 16", 0, 15, F["n_child"], key="fs_child"))
        F["n_elderly"] = int(c2.number_input("Members 65 or older", 0, 10, F["n_elderly"], key="fs_eld"))
        F["n_working"] = int(c1.number_input("Members aged 16-64 able to work", 0, 15, F["n_working"], key="fs_work"))
        st.markdown("**Characteristics**")
        c3, c4 = st.columns(2)
        F["adult_male"] = c3.toggle("At least one adult man (18+) in the household", F["adult_male"], key="fs_male")
        F["head_widowed"] = c4.toggle("Head is widowed", F["head_widowed"], key="fs_wid")
        F["head_no_school"] = c3.toggle("Head never attended school", F["head_no_school"], key="fs_school")
        F["any_disabled"] = c4.toggle("A member has a disability (a lot of difficulty or cannot do)", F["any_disabled"], key="fs_dis")
        F["any_phone"] = c3.toggle("Household owns a mobile phone", F["any_phone"], key="fs_phone")

# ---------------- step 3: dwelling and assets ----------------
elif step == 3:
    with st.container(border=True):
        theme.section("Dwelling and assets (home visit)")
        c3, c4 = st.columns(2)
        F["floor_improved"] = c3.toggle("Improved floor (cement, tiles, wood)", F["floor_improved"], key="fs_floor")
        F["wall_cement"] = c4.toggle("Walls with cement or burnt bricks", F["wall_cement"], key="fs_wall")
        F["roof_metal"] = c3.toggle("Metal sheet roof", F["roof_metal"], key="fs_roof")
        F["electricity"] = c4.toggle("Electricity (grid or solar)", F["electricity"], key="fs_elec")
        F["toilet_improved"] = c3.toggle("Improved toilet", F["toilet_improved"], key="fs_toilet")
        F["owns_dwelling"] = c4.toggle("Owns the dwelling", F["owns_dwelling"], key="fs_owns")
        F["livestock"] = c3.toggle("Owns livestock or poultry", F["livestock"], key="fs_live")
        F["cattle"] = c4.toggle("Owns cattle", F["cattle"], key="fs_cattle")
        F["umudugudu"] = c3.toggle("Lives in an umudugudu settlement", F["umudugudu"], key="fs_umu")
        F["rooms"] = int(c4.number_input("Rooms in the dwelling", 1, 15, F["rooms"], key="fs_rooms"))
        F["registry_poor"] = st.radio("Registered as a poor household in the social registry?", ["Unknown", "Yes", "No"],
                                      index=["Unknown", "Yes", "No"].index(F["registry_poor"]), horizontal=True, key="fs_reg")

# ---------------- step 4: result ----------------
else:
    kind, n_members, women_youth = F["kind"], F["n_members"], F["women_youth"]
    excl = {e["key"]: e["label"] in F["excl"] for e in R["not_eligible"]}
    rural = 1 if F["area"] == "Rural" else 0
    district_code = F["district_code"]

    # ---- rules ----
    checks = []
    def add(ok, label, art): checks.append((ok, label, art))
    tg = R["target_group"]
    add(tg["min_age"] <= F["applicant_age"] <= tg["max_age"], f"Applicant aged {tg['min_age']}-{tg['max_age']} (is {F['applicant_age']})", "Art. 5(1)(e)")
    add(F["n_working"] >= 1, "Household has a member able to work", "Art. 4(1)")
    add(F["has_account"], "Account at SACCO or financial institution", "Art. 5(1)(b)")
    add(F["viable"], "Viable income-generating project", "Art. 4(2), 5(1)(f)")
    for e in R["not_eligible"]:
        add(not excl[e["key"]], f"Not excluded: {e['label'].lower()}", e["article"])
    if kind == "Group":
        gr = R["group_rules"]
        add(gr["min_members"] <= n_members <= gr["max_members"], f"Group of {gr['min_members']}-{gr['max_members']} members (has {n_members})", "Art. 5(2)(a)(i)")
        add(F["share_eligible"] >= gr["min_share_eligible_members"], f"At least 70% of members eligible ({F['share_eligible']:.0%})", "Art. 5(2)(a)(i)")
        add(F["months_together"] >= R["general_requirements"]["group_min_months_together"], f"Worked together 3+ months ({F['months_together']})", "Art. 5(1)(c)")
        add(not F["multi_group"], "No member in more than one group", "Art. 5(2)(a)(ii)")
    if kind == "Cooperative":
        cr = R["cooperative_rules"]
        add(F["share_poor"] >= cr["min_share_poor_members"], f"At least 70% of members from poor households ({F['share_poor']:.0%})", "Art. 5(2)(b)(i)")
        add(F["rca"], "RCA legal status", "Art. 5(1)(d)")
    passed = all(ok for ok, _, _ in checks)

    # ---- model ----
    inputs = dict(hhsize=F["hhsize"], n_child=F["n_child"], n_elderly=F["n_elderly"], n_working=F["n_working"],
                  no_adult_male=int(not F["adult_male"]), head_age=F["head_age"], head_female=int(F["head_sex"] == "Female"),
                  head_widowed=int(F["head_widowed"]), head_no_school=int(F["head_no_school"]), any_disabled=int(F["any_disabled"]),
                  any_phone=int(F["any_phone"]), floor_improved=int(F["floor_improved"]), wall_cement=int(F["wall_cement"]),
                  roof_metal=int(F["roof_metal"]), electricity=int(F["electricity"]), toilet_improved=int(F["toilet_improved"]),
                  rooms=F["rooms"], livestock=int(F["livestock"]), cattle=int(F["cattle"]), owns_dwelling=int(F["owns_dwelling"]),
                  umudugudu=int(F["umudugudu"]), rural=rural)
    p = score(inputs, district_code)
    likely_poor = p >= M["threshold"]
    band = "high" if p >= 0.6 else "moderate" if p >= M["threshold"] else "low"

    # ---- component suggestion ----
    if F["n_working"] == 0:
        comp, why = "Direct Support", R["component_logic"]["direct_support"]
    elif not F["viable"] or not F["has_account"]:
        comp, why = "Public Works (CPW or ePW)", R["component_logic"]["public_works"]
    elif passed:
        comp, why = "Financial Services", R["component_logic"]["financial_services"]
    else:
        comp, why = "Not FS as submitted", "one or more Art. 5-6 conditions fail; see checks"

    a, b, c = st.columns(3)
    a.metric("Rules (Art. 4-6)", "Pass" if passed else "Fail", help="All listed checks must pass")
    b.metric("Poverty likelihood", f"{p*100:.0f} %", help=f"Model threshold {M['threshold']*100:.0f}%; households like this are poor in about {p*10:.0f} of 10 cases")
    c.metric("Suggested component", comp)

    left, right = st.columns([1, 1])
    with left:
        with st.container(border=True):
            theme.section("Eligibility checks")
            if st.button("View the eligibility criteria (Art. 4 to 6)", type="tertiary", icon=":material/open_in_new:", key="fs_criteria"):
                criteria_dialog()
            n_fail = sum(not ok for ok, _, _ in checks)
            st.markdown("All conditions are met." if n_fail == 0 else
                        f"{n_fail} condition{'s' if n_fail > 1 else ''} not met.")
            items = "".join(
                f'<li>{label}: <span class="{"vup-pass" if ok else "vup-fail"}">{"Pass" if ok else "Fail"}</span></li>'
                for ok, label, art in checks)
            st.markdown(f'<div class="vup-check"><ol>{items}</ol></div>', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            theme.section("Poverty score and component")
            st.markdown(f"**Poverty score, {band}.** Based on household composition, dwelling and assets, households like this one are below the "
                        f"poverty line in about **{p*10:.0f} of 10 cases** in EICV7. "
                        + ("The social registry also lists the household as poor. " if F["registry_poor"] == "Yes" else
                           "The social registry lists the household as non-poor; this score suggests a review. " if (F["registry_poor"] == "No" and likely_poor) else ""))
            st.markdown(f"**Suggested component: {comp}.** {why[0].upper() + why[1:]}.")
            if passed and not likely_poor:
                st.warning("Passes the rules but scores as unlikely to be poor. Art. 4 targets poor households; the committee may wish to verify.")
            if (not passed) and likely_poor and F["n_working"] >= 1:
                st.info("Likely poor and able to work, but fails a condition. If the failure is the SACCO account, account opening is a cheaper fix than rejection.")
            if comp == "Financial Services":
                amt, note = ceiling(kind, n_members, women_youth, F["repeat_good"])
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
District: {DNAME[district_code]} ({'rural' if rural else 'urban'})
Rules (Art. 4-6): {'PASS' if passed else 'FAIL'}
""" + "\n".join(f"  {i}. {label} ({art}): {'pass' if ok else 'FAIL'}" for i, (ok, label, art) in enumerate(checks, 1)) + f"""
Poverty likelihood (EICV7 model): {p*100:.0f}%  ({band})
Suggested component: {comp}  -  {why}
This note pre-screens an application for the Sector Loan Committee. It is not a decision.
"""
    d1, d2, d3 = st.columns([1, 1, 1])
    d1.download_button("Download pre-screening note", note_md, f"prescreen_{case}.txt", "text/plain", icon=":material/download:")
    if d2.button("Log this screening (no personal data)", icon=":material/save:"):
        st.session_state.setdefault("log", []).append(dict(
            case=case, date=str(dt.date.today()), district=DNAME[district_code], type=kind, members=n_members,
            rules_pass=passed, failed=[art for ok, _, art in checks if not ok], p_poor=round(p, 3),
            registry_poor=F["registry_poor"], component=comp))
        st.session_state["case_id"] = str(uuid.uuid4())[:8].upper()
        st.success("Logged. Start a new application to screen the next case.")
    if d3.button("Start a new application", icon=":material/restart_alt:"):
        st.session_state["fs_form"] = dict(DEFAULTS)
        st.session_state["fs_step"] = 1
        st.session_state["case_id"] = str(uuid.uuid4())[:8].upper()
        st.rerun()

# ---------------- navigation ----------------
nav_back, _, nav_next = st.columns([1, 3, 1])
if step > 1 and nav_back.button("Back", icon=":material/arrow_back:", key="fs_back", width="stretch"):
    st.session_state["fs_step"] = step - 1
    st.rerun()
if step < 4 and nav_next.button("See result" if step == 3 else "Next", type="primary", icon=":material/arrow_forward:", key="fs_next", width="stretch"):
    st.session_state["fs_step"] = step + 1
    st.rerun()

st.divider()
st.subheader("Session log: the data this tool generates")
log = st.session_state.get("log", [])
if log:
    L = pd.DataFrame(log)
    st.dataframe(L, hide_index=True, width="stretch")
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
