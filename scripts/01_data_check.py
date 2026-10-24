"""
01_data_check.py  -  EICV7 cross-section: load, validate, build household-level VUP flags.

Run from the repo root with the NISR files in data/raw/Cross_Section/.
Outputs data/clean/hh_vup.csv (one row per household) and prints the checks.

Findings this script reproduces (EICV7, NISR 2025):
  - national poverty 27.4 %, extreme poverty 5.4 %  (pop-weighted)
  - ~380k households / ~1.57M people in a VUP household (benchmark 391k / 1.59M)
"""
import numpy as np
import pandas as pd
import yaml as _yaml
_cfg = _yaml.safe_load(open("config/eicv7.yaml"))
RAW = _cfg["paths"]["raw"]
OUT = _cfg["paths"]["clean"]



COMPONENTS = {
    # name: (file, receipt flag, amount variable or None)
    "DS":   ("CS_S9D1_Direct_Support",      "s9d1q2", "s9d1q4"),
    "CPW":  ("CS_S9D2_Classic_Public_Work", "s9d2q1", None),
    "ePW":  ("CS_S9D3_Expanded_Public_Work","s9d3q1", None),
    "NSDS": ("CS_S9D4_NSDS",                "s9d4q1", None),
    "FS":   ("CS_S9D5_Financial_Services",  "s9d5q1", "s9d5q4"),  # a loan, not a transfer
}

pov = pd.read_stata(RAW + "CS_EICV7_poverty_file.dta", convert_categoricals=False)
assert pov.hhid.is_unique, "poverty file must be one row per household"
print(f"households: {len(pov):,}")

# 1. Reproduce the published headline figures (pov_jan / epov_jan are stored as 0/100)
w = pov.pop_wt
print(f"poverty  {np.average(pov.pov_jan,  weights=w):.2f} %   (NISR: 27.4)")
print(f"extreme  {np.average(pov.epov_jan, weights=w):.2f} %   (NISR: 5.4)")

# 2. Component receipt, collapsed to household level.
#    NOTE: s9d1q1 is labelled "any component" but equals the Direct Support flag
#    (437 == 437 in the raw file). The true any-VUP flag is the union below.
keep = ["hhid","clust","province","district","ur","weight","pop_wt","member","ae","sol_jan",
        "poverty","pov_jan","epov_jan","Poverty_line","Extreme_line","quintile"]
hh = pov[keep].copy()

for name, (f, flag, amt) in COMPONENTS.items():
    df = pd.read_stata(RAW + f + ".dta", convert_categoricals=False)
    dups = df.hhid.duplicated().sum()
    rec = df[df[flag] == 1]
    g = rec.groupby("hhid")
    out = g.size().rename(name).to_frame()
    if amt:
        out[name + "_amt"] = g[amt].sum(min_count=1)   # sum over multiple beneficiaries
    hh = hh.merge(out, on="hhid", how="left")
    hh[name] = hh[name].fillna(0).gt(0).astype(int)
    print(f"{name:5s} rows {len(df):,}  dup hhid {dups}  beneficiary hh {int(hh[name].sum())}  "
          f"est. {int((hh[name]*hh.weight).sum()):,}")

hh["vup_any"]    = hh[list(COMPONENTS)].max(axis=1)
hh["vup_transfer"] = hh[["DS","CPW","ePW","NSDS"]].max(axis=1)   # cash components only
print(f"any VUP: est. {int((hh.vup_any*hh.weight).sum()):,} households, "
      f"{int((hh.vup_any*hh.pop_wt).sum()):,} people  (benchmark 390,878 / 1,591,579)")

# 3. Headline targeting numbers
lab = {1: "extremely poor", 2: "moderately poor", 3: "non-poor"}
cov = hh.groupby("poverty").apply(lambda g: 100*np.average(g.vup_any, weights=g.weight)).round(1)
print("\ncoverage (% of households receiving any VUP):\n", cov.rename(lab))
leak = hh[hh.vup_any == 1].groupby("poverty").weight.sum()
print("\ncomposition of VUP households (%):\n", (leak/leak.sum()*100).round(1).rename(lab))

# 4. Sample support per district
g = hh.groupby("district")
print("\nunweighted n per district  (min / median)")
print("  poor          ", g.apply(lambda x: (x.poverty <= 2).sum()).min(), "/", g.apply(lambda x: (x.poverty <= 2).sum()).median())
print("  extremely poor", g.apply(lambda x: (x.poverty == 1).sum()).min(), "/", g.apply(lambda x: (x.poverty == 1).sum()).median())

import os; os.makedirs(OUT, exist_ok=True)

hh.to_csv(OUT + "hh_vup.csv", index=False)
print(f"\nwrote {OUT}hh_vup.csv  ({len(hh):,} rows)")
