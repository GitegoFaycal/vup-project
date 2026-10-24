"""
02_district_table.py  -  VUP coverage and leakage by district / province / nation,
with design-based (Taylor-linearised, stratified-cluster) confidence intervals,
and a pre-transfer welfare measure.

Input : data/raw/Cross_Section/*.dta  and  data/clean/hh_vup.csv  (from 01_data_check.py)
Output: data/clean/hh_vup_full.csv      one row per household, with amounts + pre-transfer poverty
        data/clean/table_district.csv   30 districts
        data/clean/table_province.csv   5 provinces + urban/rural
        data/clean/table_national.csv   1 row

Definitions
  poor            poverty in {1,2}  (consumption/AE below total poverty line, NISR)
  xpoor           poverty == 1      (below food poverty line)
  vup_any         any of DS, CPW, ePW, NSDS, FS
  vup_transfer    any of DS, CPW, ePW, NSDS  (cash components; FS is a loan)
  coverage        share of poor households receiving vup_any
  leakage_post    share of vup_transfer households that are non-poor (post-transfer, as published)
  leakage_pre     same, using pre-transfer consumption = consumption minus VUP cash received
  uncovered_poor  estimated number of poor households receiving nothing (weight sum)
"""
import numpy as np
import pandas as pd
import yaml as _yaml
_cfg = _yaml.safe_load(open("config/eicv7.yaml"))
RAW = _cfg["paths"]["raw"]
OUT = _cfg["paths"]["clean"]



Z = 1.96
MIN_N = 30

# Standard NISR district codes (province digit + district digit). Verify against the codebook.
DISTRICTS = {11:"Nyarugenge",12:"Gasabo",13:"Kicukiro",
             21:"Nyanza",22:"Gisagara",23:"Nyaruguru",24:"Huye",25:"Nyamagabe",26:"Ruhango",27:"Muhanga",28:"Kamonyi",
             31:"Karongi",32:"Rutsiro",33:"Rubavu",34:"Nyabihu",35:"Ngororero",36:"Rusizi",37:"Nyamasheke",
             41:"Rulindo",42:"Gakenke",43:"Musanze",44:"Burera",45:"Gicumbi",
             51:"Rwamagana",52:"Nyagatare",53:"Gatsibo",54:"Kayonza",55:"Kirehe",56:"Ngoma",57:"Bugesera"}
PROVINCES = {1:"Kigali City",2:"Southern",3:"Western",4:"Northern",5:"Eastern"}   # unweighted domain size below which an estimate is flagged "not reportable"

# ---------- 1. household file with amounts and design variables ----------
hh = pd.read_csv(OUT + "hh_vup.csv")
pov = pd.read_stata(RAW + "CS_EICV7_poverty_file.dta", convert_categoricals=False)
hh = hh.merge(pov[["hhid", "cons1", "cons1ae"]], on="hhid")

def hh_amount(file, flag, cols):
    df = pd.read_stata(RAW + file + ".dta", convert_categoricals=False)
    df = df[df[flag] == 1]
    amt = df[cols].sum(axis=1, min_count=1)
    return df.assign(_a=amt).groupby("hhid")["_a"].sum(min_count=1)

# strata_id is only populated for beneficiaries in the module files, but it is
# deterministic: district code * 10 + urban/rural (verified on the 437 non-missing rows).
hh["strata_id"] = (hh.district * 10 + hh.ur).astype(int)

amts = {
    "DS_amt":   hh_amount("CS_S9D1_Direct_Support",       "s9d1q2", ["s9d1q4"]),
    "CPW_amt":  hh_amount("CS_S9D2_Classic_Public_Work",  "s9d2q1", ["s9d2q11"]),
    "ePW_amt":  hh_amount("CS_S9D3_Expanded_Public_Work", "s9d3q1", ["s9d3q10"]),
    "NSDS_amt": hh_amount("CS_S9D4_NSDS",                 "s9d4q1", ["s9d4q8a", "s9d4q8b", "s9d4q8c", "s9d4q8d"]),
}
for k, s in amts.items():
    hh = hh.drop(columns=[k], errors="ignore").merge(s.rename(k), on="hhid", how="left")
    hh[k] = hh[k].fillna(0)
hh["vup_cash"] = hh[list(amts)].sum(axis=1)

# ---------- 2. pre-transfer welfare ----------
# sol_jan = cons1ae deflated to Jan-2024 prices; keep the same household deflator.
deflator = hh.sol_jan / hh.cons1ae
hh["sol_pre"] = ((hh.cons1 - hh.vup_cash) / hh.ae * deflator).clip(lower=0)
hh["poverty_pre"] = np.select(
    [hh.sol_pre < hh.Extreme_line, hh.sol_pre < hh.Poverty_line], [1, 2], default=3)

hh["poor"]      = (hh.poverty <= 2).astype(int)
hh["xpoor"]     = (hh.poverty == 1).astype(int)
hh["poor_pre"]  = (hh.poverty_pre <= 2).astype(int)
hh["nonpoor"]   = (hh.poverty == 3).astype(int)
hh["nonpoor_pre"] = (hh.poverty_pre == 3).astype(int)

moved = ((hh.poor_pre == 1) & (hh.poor == 0) & (hh.vup_transfer == 1))
print(f"households lifted above the line by VUP cash (pre-poor, post-non-poor): "
      f"{int(moved.sum())} in sample, est. {int((moved*hh.weight).sum()):,}")

# ---------- 3. design-based ratio estimator ----------
def ratio_ci(d, num, den, w="weight", strata="strata_id", psu="clust"):
    """Weighted ratio sum(w*num)/sum(w*den) with Taylor-linearised variance under a
    stratified, with-replacement cluster design. Pass the FULL sample with num/den
    zeroed outside the domain so domain estimation is handled correctly."""
    W, Y, X = d[w].values, d[num].values.astype(float), d[den].values.astype(float)
    sx = (W * X).sum()
    if sx == 0:
        return np.nan, np.nan, np.nan
    r = (W * Y).sum() / sx
    z = W * (Y - r * X) / sx                      # linearised contributions
    t = pd.DataFrame({"z": z, "s": d[strata].values, "c": d[psu].values})
    zc = t.groupby(["s", "c"])["z"].sum().reset_index()
    var = 0.0
    for _, g in zc.groupby("s"):
        n = len(g)
        if n > 1:
            var += n / (n - 1) * ((g.z - g.z.mean()) ** 2).sum()
    se = np.sqrt(var)
    return r, se, (r - Z * se, r + Z * se)

def table(hh, by):
    rows = []
    groups = [("Rwanda", hh)] if by is None else [(k, g) for k, g in hh.groupby(by)]
    for key, g in groups:
        dom = hh.index.isin(g.index)
        d = hh.copy()
        row = {"unit": key, "n_hh": len(g), "n_poor": int(g.poor.sum()), "n_xpoor": int(g.xpoor.sum()),
               "n_vup": int(g.vup_any.sum()), "n_vup_transfer": int(g.vup_transfer.sum())}
        # poverty rate (hh-weighted) for context
        d["_num"] = hh.poor * dom; d["_den"] = dom.astype(int)
        r, se, ci = ratio_ci(d, "_num", "_den"); row.update(poverty_rate=r, poverty_rate_lo=ci[0], poverty_rate_hi=ci[1])
        # coverage of poor
        d["_num"] = hh.vup_any * hh.poor * dom; d["_den"] = hh.poor * dom
        r, se, ci = ratio_ci(d, "_num", "_den"); row.update(coverage_poor=r, coverage_poor_lo=ci[0], coverage_poor_hi=ci[1])
        # coverage of extremely poor
        d["_num"] = hh.vup_any * hh.xpoor * dom; d["_den"] = hh.xpoor * dom
        r, se, ci = ratio_ci(d, "_num", "_den"); row.update(coverage_xpoor=r, coverage_xpoor_lo=ci[0], coverage_xpoor_hi=ci[1])
        # leakage, post and pre transfer, among cash recipients
        d["_num"] = hh.nonpoor * hh.vup_transfer * dom; d["_den"] = hh.vup_transfer * dom
        r, se, ci = ratio_ci(d, "_num", "_den"); row.update(leakage_post=r, leakage_post_lo=ci[0], leakage_post_hi=ci[1])
        d["_num"] = hh.nonpoor_pre * hh.vup_transfer * dom
        r, se, ci = ratio_ci(d, "_num", "_den"); row.update(leakage_pre=r, leakage_pre_lo=ci[0], leakage_pre_hi=ci[1])
        # counts (weight sums)
        row["poor_hh_est"] = (g.poor * g.weight).sum()
        row["uncovered_poor_hh_est"] = (g.poor * (1 - g.vup_any) * g.weight).sum()
        row["uncovered_xpoor_hh_est"] = (g.xpoor * (1 - g.vup_any) * g.weight).sum()
        row["vup_hh_est"] = (g.vup_any * g.weight).sum()
        row["reportable_poor"]  = row["n_poor"]  >= MIN_N
        row["reportable_xpoor"] = row["n_xpoor"] >= MIN_N
        rows.append(row)
    t = pd.DataFrame(rows)
    pct = [c for c in t.columns if c.startswith(("poverty_rate", "coverage", "leakage"))]
    t[pct] = (t[pct] * 100).round(1)
    t[[c for c in pct if c.endswith("_lo")]] = t[[c for c in pct if c.endswith("_lo")]].clip(lower=0)
    cnt = [c for c in t.columns if c.endswith("_est")]
    t[cnt] = t[cnt].round(0).astype("Int64")
    return t

nat  = table(hh, None)
prov = table(hh, "province")
ur   = table(hh, "ur"); ur["unit"] = ur["unit"].map({1: "Urban", 2: "Rural"})
dist = table(hh, "district")
dist.insert(1, "district_code", dist.unit.astype(int)); dist["unit"] = dist.district_code.map(DISTRICTS)
dist.insert(1, "province", (dist.district_code // 10).map(PROVINCES))
prov["unit"] = prov.unit.map(PROVINCES)

# alert: district coverage significantly below national (upper bound of CI < national point estimate)
nat_cov = nat.coverage_poor.iloc[0]
dist["alert_low_coverage"] = dist.reportable_poor & (dist.coverage_poor_hi < nat_cov)

hh.to_csv(OUT + "hh_vup_full.csv", index=False)
nat.to_csv(OUT + "table_national.csv", index=False)
pd.concat([prov, ur]).to_csv(OUT + "table_province.csv", index=False)
dist.to_csv(OUT + "table_district.csv", index=False)

pd.set_option("display.width", 200)
print("\nNATIONAL\n", nat.T)
print("\nPROVINCE / AREA\n", pd.concat([prov, ur])[["unit","n_poor","n_xpoor","poverty_rate","coverage_poor","coverage_poor_lo","coverage_poor_hi",
      "coverage_xpoor","coverage_xpoor_lo","coverage_xpoor_hi","leakage_post","leakage_pre","uncovered_poor_hh_est"]].to_string(index=False))
print("\nDISTRICT (sorted by coverage of the poor)\n", dist.sort_values("coverage_poor")[["unit","n_poor","poverty_rate","coverage_poor","coverage_poor_lo","coverage_poor_hi",
      "leakage_post","leakage_pre","uncovered_poor_hh_est","alert_low_coverage"]].to_string(index=False))
