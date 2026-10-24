"""
03_profile.py  -  Household features (registry-observable) and the profile of
uncovered poor households versus covered poor households.

Input : data/raw/Cross_Section/*.dta, data/clean/hh_vup_full.csv (from 02_district_table.py)
Output: data/clean/hh_features.csv     one row per household: outcome + features (for 04_classifier.py)
        data/clean/table_profile.csv   indicator x group, weighted %, design-based 95% CI, gap

Groups compared (poor = below total poverty line):
  uncovered_poor : poor, no VUP component
  covered_poor   : poor, any VUP component
  nonpoor_vup    : non-poor, any cash component   (the leakage group, for context)
"""
import numpy as np
import pandas as pd
import yaml as _yaml
_cfg = _yaml.safe_load(open("config/eicv7.yaml"))
RAW = _cfg["paths"]["raw"]
OUT = _cfg["paths"]["clean"]


Z = 1.96

def read(f, cols=None):
    df = pd.read_stata(RAW + f + ".dta", convert_categoricals=False, columns=cols)
    return df

hh = pd.read_csv(OUT + "hh_vup_full.csv")

# ---------- 1. person module -> household aggregates ----------
per = read("CS_S0_S1_S2_S3_S4_S6A_S6B_S6C_Person",
           ["hhid","pid","s1q1","s1q2","s1q3y","s1q4","s3q2","s3q7","s3q8","s3q9","s3q10","s3q11","s3q12",
            "s4aq1","s4aq2","s4bq4","s4bq8","s6aq4","s6aq5"])
dis = per[["s3q7","s3q8","s3q9","s3q10","s3q11","s3q12"]]
per["disabled"] = dis.isin([3, 4]).any(axis=1).astype(int)        # a lot of difficulty / cannot do at all
per["adult"]    = (per.s1q3y >= 18).astype(int)
per["adult_male"] = ((per.s1q3y >= 18) & (per.s1q1 == 1)).astype(int)
per["child"]    = (per.s1q3y < 16).astype(int)
per["elderly"]  = (per.s1q3y >= 65).astype(int)
per["working_age"] = ((per.s1q3y >= 16) & (per.s1q3y < 65)).astype(int)
per["has_phone"] = (per.s4bq8 == 1).astype(int)
per["insured"]  = (per.s3q2 == 1).astype(int)
per["literate_adult"] = ((per.s1q3y >= 15) & (per.s4bq4 == 1)).astype(int)
per["adult_15"] = (per.s1q3y >= 15).astype(int)
per["nonfarm_wage"] = (per.s6aq5 == 1).astype(int)

agg = per.groupby("hhid").agg(
    hhsize=("pid","size"), n_child=("child","sum"), n_elderly=("elderly","sum"),
    n_working=("working_age","sum"), n_adult_male=("adult_male","sum"),
    any_disabled=("disabled","max"), any_phone=("has_phone","max"),
    share_insured=("insured","mean"), n_literate=("literate_adult","sum"), n_adult15=("adult_15","sum"),
    any_nonfarm_wage=("nonfarm_wage","max")).reset_index()
agg["dependency_ratio"] = (agg.n_child + agg.n_elderly) / agg.n_working.replace(0, np.nan)
agg["dependency_ratio"] = agg.dependency_ratio.fillna(agg.n_child + agg.n_elderly).clip(upper=10)
agg["no_adult_male"] = (agg.n_adult_male == 0).astype(int)
agg["any_adult_literate"] = (agg.n_literate > 0).astype(int)

head = per[per.s1q2 == 1].drop_duplicates("hhid").set_index("hhid")
agg = agg.merge(pd.DataFrame({
    "head_female":  (head.s1q1 == 2).astype(int),
    "head_age":     head.s1q3y,
    "head_65plus":  (head.s1q3y >= 65).astype(int),
    "head_widowed": (head.s1q4 == 7).astype(int),
    "head_no_school": ((head.s4aq1 == 2) | head.s4aq1.isna()).astype(int),
    "head_secondary_plus": head.s4aq2.isin([5, 6, 7]).astype(int),
}).reset_index(), on="hhid", how="left")

# ---------- 2. dwelling and assets ----------
dw = read("CS_S01_S5_S7_Household",
          ["hhid","s5aq1","s5aq3","s5aq7","s5cq14","s5cq16","s5cq25","s5dq1","s5dq2","s5dq3","s7aq4","s7aq4a"])
feat = pd.DataFrame({
    "hhid": dw.hhid,
    "floor_improved": dw.s5dq3.isin([3,4,5,6,7]).astype(int),
    "wall_cement":    dw.s5dq1.isin([2,4,5,8,10]).astype(int),
    "roof_metal":     (dw.s5dq2 == 1).astype(int),
    "electricity":    dw.s5cq14.isin([1,2,3]).astype(int),
    "grid":           dw.s5cq14.isin([1,3]).astype(int),
    "toilet_improved": dw.s5cq25.isin([1,2,3,4,5,6]).astype(int),
    "umudugudu":      (dw.s5aq1 == 1).astype(int),
    "dispersed":      (dw.s5aq1 == 3).astype(int),
    "owns_dwelling":  dw.s5aq7.isin([1,2,3]).astype(int),
    "rooms":          dw.s5aq3,
    "livestock":      (dw.s7aq4 == 1).astype(int),
    "cattle":         (dw.s7aq4a.fillna(0) > 0).astype(int),
})

# ---------- 3. access to services (minutes) ----------
acc = read("CS_S5F_access_to_services", ["hhid","s5fq0","s5fq3a","s5fq3b"])
acc["minutes"] = acc.s5fq3a.fillna(0)*60 + acc.s5fq3b.fillna(0)
acc = acc.pivot_table(index="hhid", columns="s5fq0", values="minutes", aggfunc="first")
acc = acc.rename(columns={2:"min_food_market", 10:"min_health_centre", 12:"min_sector_office", 5:"min_road"})
acc = acc[["min_food_market","min_health_centre","min_sector_office","min_road"]].reset_index()

# ---------- 4. financial inclusion ----------
sv = read("CS_S10C_Savings", ["hhid","s10cq1","s10cq4","s10cq5","s10cq8"])
fin = sv.groupby("hhid").agg(
    any_account=("s10cq4", lambda s: int((s == 1).any())),
    sacco=("s10cq5", lambda s: int((s == 4).any())),
    momo=("s10cq5", lambda s: int((s == 5).any())),
    bank=("s10cq5", lambda s: int(s.isin([1,2,3]).any())),
    tontine=("s10cq8", lambda s: int((s == 1).any()))).reset_index()
cr = read("CS_S10A1_A2_credits", ["hhid","s10aq1","s10aq3"])
cr = cr.groupby("hhid").agg(tried_loan=("s10aq1", lambda s: int((s == 1).any())),
                            has_debt=("s10aq3", lambda s: int((s == 1).any()))).reset_index()

# ---------- 5. assemble ----------
X = hh.merge(agg, on="hhid", how="left").merge(feat, on="hhid", how="left") \
      .merge(acc, on="hhid", how="left").merge(fin, on="hhid", how="left").merge(cr, on="hhid", how="left")
X["rural"] = (X.ur == 2).astype(int)
X["group"] = np.select([(X.poor == 1) & (X.vup_any == 0), (X.poor == 1) & (X.vup_any == 1),
                        (X.poor == 0) & (X.vup_transfer == 1)],
                       ["uncovered_poor", "covered_poor", "nonpoor_vup"], default="other")
X.to_csv(OUT + "hh_features.csv", index=False)
print("features written:", X.shape, "| missing per column (top):")
print(X.isna().sum().sort_values(ascending=False).head(6).to_string())

# ---------- 6. profile with design-based CIs ----------
from importlib import import_module

def ratio_ci(d, num, den, w="weight", strata="strata_id", psu="clust"):
    W, Y, Xd = d[w].values, d[num].values.astype(float), d[den].values.astype(float)
    sx = (W*Xd).sum(); r = (W*Y).sum()/sx
    z = W*(Y - r*Xd)/sx
    t = pd.DataFrame({"z": z, "s": d[strata].values, "c": d[psu].values})
    zc = t.groupby(["s","c"])["z"].sum().reset_index()
    var = sum(len(g)/(len(g)-1)*((g.z-g.z.mean())**2).sum() for _, g in zc.groupby("s") if len(g) > 1)
    se = np.sqrt(var); return r, r - Z*se, r + Z*se

INDICATORS = [  # (column, label, is_mean)
    ("head_female","Female-headed household",0), ("head_65plus","Head aged 65 or more",0),
    ("head_widowed","Head widowed",0), ("head_no_school","Head never attended school",0),
    ("any_disabled","Any member with a disability",0), ("no_adult_male","No adult male in household",0),
    ("hhsize","Household size (mean)",1), ("dependency_ratio","Dependency ratio (mean)",1),
    ("any_phone","Any member owns a mobile phone",0), ("any_adult_literate","Any literate adult",0),
    ("share_insured","Share of members with health insurance (mean)",1),
    ("floor_improved","Improved floor",0), ("wall_cement","Walls with cement",0), ("roof_metal","Metal roof",0),
    ("electricity","Electricity (grid or solar)",0), ("toilet_improved","Improved toilet",0),
    ("umudugudu","Lives in umudugudu settlement",0), ("dispersed","Dispersed / isolated housing",0),
    ("livestock","Owns livestock or poultry",0), ("cattle","Owns cattle",0),
    ("any_account","Any account (bank, SACCO, MFI, MoMo)",0), ("sacco","SACCO account",0), ("momo","Mobile money account",0),
    ("tontine","Member of a tontine / savings group",0), ("has_debt","Currently owes a loan",0),
    ("min_health_centre","Minutes to health centre (mean)",1), ("min_sector_office","Minutes to sector office (mean)",1),
    ("min_food_market","Minutes to food market (mean)",1), ("rural","Rural",0),
]
rows = []
for col, label, is_mean in INDICATORS:
    d = X.copy(); d["_v"] = d[col].astype(float)
    ok = d._v.notna()
    row = {"indicator": label, "variable": col}
    for grp in ["uncovered_poor","covered_poor","nonpoor_vup"]:
        dom = ((d.group == grp) & ok).astype(int)
        d["_num"] = d._v.fillna(0)*dom; d["_den"] = dom
        r, lo, hi = ratio_ci(d, "_num", "_den")
        scale = 1 if is_mean else 100
        row[grp] = round(r*scale, 1); row[grp+"_lo"] = round(max(lo*scale, 0), 1); row[grp+"_hi"] = round(hi*scale, 1)
    row["gap_uncovered_minus_covered"] = round(row["uncovered_poor"] - row["covered_poor"], 1)
    row["n_uncovered"] = int(((X.group=="uncovered_poor") & X[col].notna()).sum())
    row["n_covered"]   = int(((X.group=="covered_poor") & X[col].notna()).sum())
    rows.append(row)
prof = pd.DataFrame(rows)
prof.to_csv(OUT + "table_profile.csv", index=False)
pd.set_option("display.width", 220)
print("\nuncovered poor vs covered poor (weighted %, or mean where stated)\n")
print(prof[["indicator","uncovered_poor","uncovered_poor_lo","uncovered_poor_hi","covered_poor","covered_poor_lo","covered_poor_hi",
            "nonpoor_vup","gap_uncovered_minus_covered"]].to_string(index=False))
print("\nn uncovered poor =", int((X.group=="uncovered_poor").sum()), " n covered poor =", int((X.group=="covered_poor").sum()),
      " n non-poor VUP cash =", int((X.group=="nonpoor_vup").sum()))
