"""
VUP coverage gaps dashboard  -  Streamlit app.
Run:  streamlit run dashboard/app.py   (from the repo root)
Data: dashboard/data/  (built by scripts/05_build_dashboard_data.py)
"""
import json, os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import theme

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")

st.set_page_config(page_title="Where VUP misses the poor", page_icon="🗺️", layout="wide")

@st.cache_data
def load(stamp):
    # stamp (file mtimes) changes when 05_build_dashboard_data.py rewrites the data, which busts the cache
    dist = pd.read_csv(f"{D}/districts.csv")
    prov = pd.read_csv(f"{D}/provinces.csv")
    nat = pd.read_csv(f"{D}/national.csv").iloc[0]
    prof = pd.read_csv(f"{D}/profile.csv")
    card = json.load(open(f"{D}/model_card.json"))
    meta = json.load(open(f"{D}/meta.json"))
    geo = json.load(open(f"{D}/districts.geojson")) if os.path.exists(f"{D}/districts.geojson") else None
    return dist, prov, nat, prof, card, meta, geo

dist, prov, nat, prof, card, meta, geo = load(tuple(os.path.getmtime(os.path.join(D, f)) for f in sorted(os.listdir(D))))
ROUND = meta["round"]["label"]
SRC = f"Source: NISR, {ROUND}. Household-weighted, design-based 95% intervals."

INDICATORS = {
    "Coverage of poor households (%)": ("coverage_poor", "share of poor households receiving any VUP component", "Blues"),
    "Uncovered poor households (count)": ("uncovered_poor_hh_est", "estimated poor households receiving nothing", "Oranges"),
    "Leakage, post-transfer (%)": ("leakage_post", "share of cash recipients who are non-poor, consumption as published", "Purples"),
    "Leakage, pre-transfer (%)": ("leakage_pre", "share of cash recipients non-poor before the VUP cash is counted", "Purples"),
    "Poverty rate, households (%)": ("poverty_rate", "share of households below the total poverty line", "Reds"),
    "Model: predicted poor and uncovered (count)": ("pred_poor_uncovered_hh_est", "households the targeting model flags as poor that receive nothing", "Oranges"),
}

# ---------------- header: navbar + lead ----------------
theme.apply("overview")
st.markdown(f'<div class="vup-lead">Where poor households receive no VUP support, and how many of them there are, district by district. '
            "Tools for sector officers are in the top bar: <b>Screener</b> pre-screens an FS application against the 2024 instructions, "
            "<b>Tracker</b> follows Art. 9 deadlines.</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Poor households covered by any VUP component", f"{nat.coverage_poor:.1f} %",
          help=f"95% interval {nat.coverage_poor_lo:.1f} to {nat.coverage_poor_hi:.1f}")
c2.metric("Poor households receiving nothing", f"{int(nat.uncovered_poor_hh_est):,}",
          help=f"of which extremely poor: {int(nat.uncovered_xpoor_hh_est):,}")
c3.metric("Cash recipients who are non-poor", f"{nat.leakage_post:.1f} %",
          help=f"Pre-transfer: {nat.leakage_pre:.1f} %. The difference is households VUP lifts above the line.")
c4.metric("Districts flagged for low coverage", int(dist.alert_low_coverage.sum()),
          help=meta["reporting"]["alert_rule"])

tab_map, tab_district, tab_who, tab_methods = st.tabs(["Map", "District profile", "Who is missed", "Methods and limits"])

# ---------------- map ----------------
with tab_map:
    left, right = st.columns([3, 1])
    with right:
        ind = st.selectbox("Indicator", list(INDICATORS))
        col, desc, scale = INDICATORS[ind]
        show_alerts = st.checkbox("Show alert layer", value=True,
                                  help="Districts whose coverage interval lies entirely below the national rate")
        st.markdown(f"**What this shows:** {desc}.")
        st.markdown(f"National value: **{nat[col]:,.1f}**" if "count" not in ind else
                    f"National total: **{int(nat.get(col, dist[col].sum())):,}**")
    d = dist.copy()
    d["label"] = d.district
    d.loc[~d.reportable_poor, col] = None
    # plain-language hover text (one HTML string per district) instead of raw column names
    STANDARD = {"coverage_poor", "uncovered_poor_hh_est", "leakage_post", "n_poor"}
    def hover_text(r):
        if not r.reportable_poor:
            return (f"<b>{r.district}</b>, {r.province}<br><br>Not reported: fewer than 30 poor households in the sample.")
        lines = [f"<b>{r.district}</b>, {r.province}<br>"]
        if col not in STANDARD:
            v = f"{int(r[col]):,}" if "count" in ind else f"{r[col]:.1f} %"
            lines.append(f"<b>{ind.split(' (')[0]}: {v}</b>")
        lines += [f"Coverage of poor households: <b>{r.coverage_poor:.1f} %</b> (95% interval {r.coverage_poor_lo:.1f} to {r.coverage_poor_hi:.1f})",
                  f"Poor households receiving nothing: <b>{int(r.uncovered_poor_hh_est):,}</b>",
                  f"Cash recipients who are non-poor: <b>{r.leakage_post:.0f} %</b>",
                  f"Poor households in sample: {int(r.n_poor)}",
                  "Flagged for low coverage: <b>Yes</b>" if r.alert_low_coverage else "Flagged for low coverage: No"]
        return "<br>".join(lines)
    d["hover"] = d.apply(hover_text, axis=1)
    HOVER = dict(customdata=d[["hover"]].to_numpy(), hovertemplate="%{customdata[0]}<extra></extra>")
    hover = {"district": False}
    with left:
        if geo is not None:
            fig = px.choropleth(d, geojson=geo, locations="district", featureidkey="properties.district",
                                color=col, color_continuous_scale=scale, range_color=(0, d[col].max()), hover_name="district", hover_data=hover)
            fig.update_traces(**HOVER)
            if show_alerts:
                al = d[d.alert_low_coverage]
                # outline flagged districts by re-drawing them with a thick border
                fig.add_trace(go.Choropleth(geojson=geo, locations=al.district, featureidkey="properties.district",
                                            z=[1]*len(al), showscale=False, colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                                            marker_line_color="#b5791a", marker_line_width=3, hoverinfo="skip", name="alert"))
            fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560, coloraxis_colorbar_title="")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("District boundaries not loaded yet (add data/geo/rwanda_districts.geojson and rerun 05). Showing ranked bars.")
            dd = d.sort_values(col)
            fig = px.bar(dd, x=col, y="district", orientation="h", color="alert_low_coverage" if show_alerts else None,
                         color_discrete_map={True: "#b5791a", False: "#124e44"}, hover_data=hover)
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            for tr in fig.data:  # px splits the bars by colour; give each trace the hover text of its own rows
                tr.customdata = dd.loc[dd.district.isin(tr.y), ["hover"]].set_index(dd.loc[dd.district.isin(tr.y), "district"]).loc[list(tr.y)].to_numpy()
            if "coverage" in col:
                fig.update_traces(error_x=dict(type="data", symmetric=False,
                                               array=dd.coverage_poor_hi - dd[col], arrayminus=dd[col] - dd.coverage_poor_lo))
            fig.update_layout(height=760, margin=dict(l=0, r=0, t=0, b=0), yaxis_title="", showlegend=False)
            st.plotly_chart(fig, width="stretch")
    st.caption(SRC + " Grey districts have fewer than 30 poor households in the sample and are not reportable.")

    theme.section("Flagged districts")
    fl = dist[dist.alert_low_coverage].sort_values("uncovered_poor_hh_est", ascending=False)
    st.markdown("These districts cover significantly fewer of their poor households than the country as a whole. "
                "Sorted by the number of poor households receiving nothing, which is what a re-verification exercise would budget against.")
    st.dataframe(fl[["district", "province", "coverage_poor", "coverage_poor_lo", "coverage_poor_hi",
                     "uncovered_poor_hh_est", "pred_poor_uncovered_hh_est", "leakage_post", "n_poor"]]
                 .rename(columns={"coverage_poor": "coverage %", "coverage_poor_lo": "low", "coverage_poor_hi": "high",
                                  "uncovered_poor_hh_est": "uncovered poor hh", "pred_poor_uncovered_hh_est": "model: predicted poor, uncovered",
                                  "leakage_post": "leakage %", "n_poor": "poor hh in sample"}),
                 hide_index=True, width="stretch")
    st.download_button("Download district table (CSV)", dist.to_csv(index=False), "vup_gaps_districts.csv", "text/csv")

# ---------------- district profile ----------------
with tab_district:
    sel = st.selectbox("District", sorted(dist.district), index=sorted(dist.district).index(
        dist.sort_values("uncovered_poor_hh_est", ascending=False).district.iloc[0]))
    r = dist[dist.district == sel].iloc[0]
    p = prov[prov.area == r.province].iloc[0] if (prov.area == r.province).any() else None
    theme.section(f"{sel}, {r.province} Province")
    if r.alert_low_coverage:
        st.warning("Flagged: coverage of poor households is significantly below the national rate.")
    a, b, c = st.columns(3)
    a.metric("Coverage of poor households", f"{r.coverage_poor:.1f} %", delta=f"{r.coverage_poor - nat.coverage_poor:+.1f} vs national",
             delta_color="normal", help=f"95% interval {r.coverage_poor_lo:.1f} to {r.coverage_poor_hi:.1f}; {int(r.n_poor)} poor households in sample")
    b.metric("Poor households receiving nothing", f"{int(r.uncovered_poor_hh_est):,}",
             help=f"Model-based estimate: {int(r.pred_poor_uncovered_hh_est):,}")
    c.metric("Leakage (post / pre transfer)", f"{r.leakage_post:.0f} % / {r.leakage_pre:.0f} %")

    rows = pd.DataFrame({
        "level": [sel, r.province, "Rwanda"],
        "coverage": [r.coverage_poor, p.coverage_poor if p is not None else None, nat.coverage_poor],
        "lo": [r.coverage_poor_lo, p.coverage_poor_lo if p is not None else None, nat.coverage_poor_lo],
        "hi": [r.coverage_poor_hi, p.coverage_poor_hi if p is not None else None, nat.coverage_poor_hi]})
    fig = go.Figure(go.Bar(x=rows.level, y=rows.coverage, marker_color=["#b5791a", "#7fa89a", "#124e44"],
                           error_y=dict(type="data", symmetric=False, array=rows.hi - rows.coverage, arrayminus=rows.coverage - rows.lo)))
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="coverage of poor households, %")
    st.plotly_chart(fig, width="stretch")
    st.markdown(f"**In plain terms:** of every 100 poor households in {sel}, about **{r.coverage_poor:.0f}** receive a VUP component. "
                f"That leaves an estimated **{int(r.uncovered_poor_hh_est):,}** poor households with no support. "
                f"Among households that do receive VUP cash, about **{r.leakage_post:.0f} in 100** are above the poverty line.")
    st.caption("Extreme-poverty coverage is reported at province level only; district samples of extremely poor households are too small.")

# ---------------- who is missed ----------------
with tab_who:
    theme.section("Uncovered poor households compared with covered poor households")
    st.markdown("Households below the poverty line that receive **no** VUP component, next to those that receive one. "
                "Where the bars' intervals do not overlap, the difference is unlikely to be sampling noise.")
    sub = prof[~prof.indicator.str.contains("mean")].copy()
    sub = sub.sort_values("gap_uncovered_minus_covered")
    fig = go.Figure()
    for grp, name, colr in [("uncovered_poor", "Uncovered poor", "#b5791a"), ("covered_poor", "Covered poor", "#124e44")]:
        fig.add_trace(go.Bar(y=sub.indicator, x=sub[grp], name=name, orientation="h", marker_color=colr,
                             error_x=dict(type="data", symmetric=False, array=sub[grp + "_hi"] - sub[grp], arrayminus=sub[grp] - sub[grp + "_lo"])))
    fig.update_layout(barmode="group", height=820, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="% of households", yaxis_title="",
                      legend=dict(orientation="h", y=1.02, x=0))
    st.plotly_chart(fig, width="stretch")
    st.markdown(
        "**Reading the chart.** Covered poor households match the programme's vulnerability template: more often female-headed, "
        "elderly, widowed, with a member with disability or no adult man. Uncovered poor households are more often male-headed and "
        "of working age, with the same household size and more children per worker. They are the working poor, the group the public-works "
        "components are designed for. Phone ownership and distance to services do not explain the gap.")
    st.markdown("**On accounts.** 90% of covered poor households have a SACCO account against 33% of uncovered ones, because VUP pays "
                "through Umurenge SACCOs. The uncovered poor mostly have mobile money (71%), so a MoMo payment channel matters for them.")
    means = prof[prof.indicator.str.contains("mean")][["indicator", "uncovered_poor", "covered_poor", "nonpoor_vup"]]
    st.dataframe(means.rename(columns={"uncovered_poor": "uncovered poor", "covered_poor": "covered poor", "nonpoor_vup": "non-poor recipients"}),
                 hide_index=True, width="stretch")
    st.caption(SRC)

# ---------------- methods ----------------
with tab_methods:
    st.subheader("Data")
    st.markdown(f"- {meta['round']['source']}. Fieldwork {meta['round']['fieldwork']}. 15,054 households, representative at district level.\n"
                "- Poverty status, consumption aggregates and poverty lines as published by NISR (total line RWF 560,127; food line RWF 356,432 per adult equivalent, Jan 2024 prices).\n"
                "- VUP receipt from the five component modules (Direct Support, Classic and Expanded Public Works, Nutrition-Sensitive Direct Support, Financial Services). "
                "The variable labelled \"any component\" in the file equals the Direct Support flag; the any-VUP indicator here is the union of the five.\n"
                "- District boundaries: OCHA common operational dataset. No other external data enters the estimates.")
    st.subheader("Definitions")
    st.markdown("- **Poor**: consumption per adult equivalent below the total poverty line. **Extremely poor**: below the food poverty line.\n"
                "- **Coverage**: share of poor households receiving at least one VUP component.\n"
                "- **Leakage**: share of households receiving a cash component (FS loans excluded) that are non-poor. "
                "**Pre-transfer** leakage recomputes poverty after subtracting the VUP cash reported for the last 12 months from consumption, "
                "assuming the cash was fully consumed.\n"
                "- **Alert**: the upper bound of a district's 95% interval for coverage is below the national point estimate.")
    st.subheader("Estimation")
    st.markdown("All figures use the household survey weight. Standard errors use Taylor linearisation with strata (district by urban/rural) and "
                "enumeration clusters, with-replacement approximation. Districts with fewer than 30 poor households in the sample are not reported. "
                "Household-level poverty (23.4%) differs from the published population rate (27.4%) because poor households are larger; both are correct.")
    st.subheader("Targeting model")
    m = card["metrics_logistic"]
    st.markdown(f"- {card['model']}. Validation: {card['validation']}.\n"
                f"- Out-of-fold AUC {m['auc']}, precision {m['precision']}, recall {m['recall']} at a threshold that flags {m['flagged_share']*100:.0f}% of households.\n"
                f"- Gradient boosting comparison: AUC {card['metrics_gradient_boosting_comparison']['auc']} (kept as a check; the logistic model is deployed for interpretability).\n"
                f"- Features: {len(card['features_registry_observable'])} registry-observable characteristics plus district. Excluded on purpose: {', '.join(card['features_excluded_on_purpose'])}.\n"
                f"- **Intended use:** {card['intended_use']}.\n- **Not for:** {card['non_use']}.")
    with st.expander("Model coefficients (standardised log-odds of being poor)"):
        co = pd.Series(card["coefficients_standardised"]).sort_values()
        st.plotly_chart(px.bar(co, orientation="h", height=700).update_layout(showlegend=False, yaxis_title="", xaxis_title="coefficient",
                                                                              margin=dict(l=0, r=0, t=0, b=0)), width="stretch")
    with st.expander("Calibration by decile"):
        st.dataframe(pd.DataFrame(card["calibration_deciles"]), hide_index=True)
    st.subheader("Limitations")
    st.markdown("- Cross-sectional survey: associations, not causes. Recipients' consumption is measured after receiving support.\n"
                "- About 500 households per district; counts carry sampling error and are shown with intervals.\n"
                "- Self-reported VUP receipt and amounts. Asset Transfer and Skills Development components are not covered by the survey modules.\n"
                "- Survey fieldwork 2023/24; census population 2022 where counts are scaled.\n"
                "- Nothing here identifies a household. Results are aggregated; no record-level data is published.")
    st.subheader("Reuse")
    st.markdown("The pipeline is driven by `config/eicv7.yaml`, which maps concepts to the round's variable names and lines. "
                "A new round means a new config file and a rerun; this dashboard reads the round label from the data it is given.")
    st.caption(f"{meta['round']['citation']} | Code and documentation: see the project README.")
