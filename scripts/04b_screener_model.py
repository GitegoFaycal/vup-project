"""
04b_screener_model.py  -  Compact poverty model for the screener, using only inputs a sector
officer can take from a loan application and a home visit. Exported as plain JSON so the
dashboard scores it with numpy (no pickle, no sklearn version pinning).

Input : data/clean/hh_features.csv   Output: dashboard/data/screener_model.json
Validation: 5-fold GroupKFold by enumeration cluster, weighted, as in 04_classifier.py.
"""
import json
import numpy as np
import pandas as pd
import yaml as _yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score

_cfg = _yaml.safe_load(open("config/eicv7.yaml"))
OUT = _cfg["paths"]["clean"]
X = pd.read_csv(OUT + "hh_features.csv")

# Inputs the screener form asks for (order matters; the app builds the vector in this order)
FEATURES = ["hhsize", "n_child", "n_elderly", "n_working", "no_adult_male",
            "head_age", "head_female", "head_widowed", "head_no_school",
            "any_disabled", "any_phone",
            "floor_improved", "wall_cement", "roof_metal", "electricity", "toilet_improved", "rooms",
            "livestock", "cattle", "owns_dwelling", "umudugudu", "rural"]
DISTRICTS = sorted(X.district.dropna().astype(int).unique().tolist())

df = X.dropna(subset=FEATURES).copy()
y, w, g = df.poor.values, df.weight.values, df.clust.values
F = df[FEATURES].astype(float)
for d in DISTRICTS[1:]:
    F[f"d_{d}"] = (df.district.astype(int) == d).astype(float)

oof = np.zeros(len(df))
for tr, te in GroupKFold(5).split(F, y, g):
    sc = StandardScaler().fit(F.iloc[tr])
    m = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(F.iloc[tr]), y[tr], sample_weight=w[tr])
    oof[te] = m.predict_proba(sc.transform(F.iloc[te]))[:, 1]
pov = np.average(y, weights=w)
order = np.argsort(-oof); cum = np.cumsum(w[order]) / w.sum()
thr = float(oof[order][min(np.searchsorted(cum, pov), len(oof) - 1)])
pred = (oof >= thr).astype(int)
metrics = dict(auc=round(roc_auc_score(y, oof, sample_weight=w), 3),
               precision=round(precision_score(y, pred, sample_weight=w), 3),
               recall=round(recall_score(y, pred, sample_weight=w), 3), threshold=round(thr, 4))
print("screener model, out-of-fold:", metrics)

sc = StandardScaler().fit(F)
m = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(F), y, sample_weight=w)
model = {
    "features": FEATURES, "districts": DISTRICTS,
    "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(),
    "coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0]),
    "threshold": thr, "metrics": metrics,
    "outcome": "household consumption per adult equivalent below the NISR total poverty line (EICV7)",
    "trained_on": "EICV7 cross-section, 15,054 households, survey-weighted",
}
json.dump(model, open("dashboard/data/screener_model.json", "w"), indent=1)
print("wrote dashboard/data/screener_model.json")
