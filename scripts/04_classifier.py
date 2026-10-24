"""
04_classifier.py  -  Targeting classifier: predict consumption poverty from
registry-observable household characteristics, then count predicted-poor households
that receive no VUP component, by district.

Input : data/clean/hh_features.csv  (from 03_profile.py)
Output: data/clean/model_card.json           metrics, coefficients, thresholds
        data/clean/table_model_district.csv  per district: predicted-poor-uncovered estimates
        data/clean/hh_scored.csv             hhid, p_poor, predicted flag (not for publication)

Design
  outcome        poor (consumption/AE below total poverty line, NISR definition)
  features       only what a social registry can observe; nothing collected after enrolment
                 (no SACCO/account/loan variables, no VUP variables, no consumption)
  model          L2-regularised logistic regression on standardised features + district dummies,
                 sample-weighted; HistGradientBoosting fitted for comparison only
  validation     5-fold GroupKFold grouped by enumeration cluster (clust), so households from one
                 cluster are never split across train and test
  threshold      chosen on out-of-fold predictions so that predicted prevalence equals the
                 weighted poverty rate (a registry would want to flag about as many as are poor)
Stated non-use  the model ranks households for re-verification; it does not decide eligibility.
"""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, precision_score, recall_score, brier_score_loss
import yaml as _yaml
_cfg = _yaml.safe_load(open("config/eicv7.yaml"))
RAW = _cfg["paths"]["raw"]
OUT = _cfg["paths"]["clean"]



X = pd.read_csv(OUT + "hh_features.csv")

NUM = ["head_age","hhsize","dependency_ratio","rooms","n_child","n_elderly","n_working",
       "min_health_centre","min_sector_office","min_food_market"]
BIN = ["head_female","head_65plus","head_widowed","head_no_school","head_secondary_plus",
       "any_disabled","no_adult_male","any_adult_literate","any_phone","any_nonfarm_wage",
       "floor_improved","wall_cement","roof_metal","electricity","grid","toilet_improved",
       "umudugudu","dispersed","owns_dwelling","livestock","cattle","rural"]
EXCLUDED = ["any_account","sacco","momo","bank","tontine","tried_loan","has_debt",
            "share_insured"]   # post-enrolment or not registry-observable; kept out on purpose

df = X.dropna(subset=NUM + BIN).copy()
print(f"rows used: {len(df):,} of {len(X):,}")
y = df.poor.values
w = df.weight.values
groups = df.clust.values

dist = pd.get_dummies(df.district.astype(int), prefix="d", drop_first=True).astype(float)
F = pd.concat([df[NUM + BIN].astype(float), dist], axis=1)
feature_names = F.columns.tolist()

# ---------- cluster-aware cross-validation ----------
gkf = GroupKFold(n_splits=5)
oof_lr = np.zeros(len(df)); oof_gb = np.zeros(len(df))
for tr, te in gkf.split(F, y, groups):
    sc = StandardScaler().fit(F.iloc[tr])
    lr = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(F.iloc[tr]), y[tr], sample_weight=w[tr])
    oof_lr[te] = lr.predict_proba(sc.transform(F.iloc[te]))[:, 1]
    gb = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0)
    gb.fit(F.iloc[tr], y[tr], sample_weight=w[tr])
    oof_gb[te] = gb.predict_proba(F.iloc[te])[:, 1]

def wmetrics(p, thr):
    pred = (p >= thr).astype(int)
    return dict(auc=round(roc_auc_score(y, p, sample_weight=w), 3),
                brier=round(brier_score_loss(y, p, sample_weight=w), 4),
                precision=round(precision_score(y, pred, sample_weight=w), 3),
                recall=round(recall_score(y, pred, sample_weight=w), 3),
                flagged_share=round(np.average(pred, weights=w), 3))

pov_rate = np.average(y, weights=w)
def prevalence_threshold(p):
    # smallest threshold such that weighted share flagged <= weighted poverty rate
    order = np.argsort(-p); cum = np.cumsum(w[order]) / w.sum()
    k = np.searchsorted(cum, pov_rate); return p[order][min(k, len(p)-1)]

thr_lr, thr_gb = prevalence_threshold(oof_lr), prevalence_threshold(oof_gb)
m_lr, m_gb = wmetrics(oof_lr, thr_lr), wmetrics(oof_gb, thr_gb)
print("\nout-of-fold, cluster-grouped 5-fold, weighted")
print("logistic         ", m_lr, "threshold", round(thr_lr, 3))
print("gradient boosting", m_gb, "threshold", round(thr_gb, 3))

# calibration of the logistic model by decile
dec = pd.qcut(oof_lr, 10, labels=False, duplicates="drop")
cal = pd.DataFrame({"dec": dec, "p": oof_lr, "y": y, "w": w}).groupby("dec").apply(
    lambda g: pd.Series({"pred": np.average(g.p, weights=g.w), "obs": np.average(g.y, weights=g.w), "n": len(g)})).round(3)
print("\ncalibration (logistic), by decile of predicted probability\n", cal.to_string())

# ---------- final logistic fit on all data (the deployed model) ----------
sc = StandardScaler().fit(F)
lr = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(F), y, sample_weight=w)
coef = pd.Series(lr.coef_[0], index=feature_names)
core = coef[[c for c in feature_names if not c.startswith("d_")]].sort_values()
print("\nstandardised coefficients (log-odds of being poor), registry features only\n", core.round(3).to_string())

df["p_poor"] = oof_lr                      # use out-of-fold scores for all downstream counts
df["pred_poor"] = (df.p_poor >= thr_lr).astype(int)

# ---------- district table: predicted poor and not covered ----------
def est(g, mask): return float((mask * g.weight).sum())
rows = []
for d, g in df.groupby("district"):
    rows.append({
        "district_code": int(d),
        "n_hh": len(g),
        "pred_poor_hh_est": est(g, g.pred_poor),
        "pred_poor_uncovered_hh_est": est(g, g.pred_poor * (1 - g.vup_any)),
        "actual_poor_uncovered_hh_est": est(g, g.poor * (1 - g.vup_any)),
        "high_score_uncovered_hh_est": est(g, (g.p_poor >= 0.5) * (1 - g.vup_any)),   # stricter cut
        "share_uncovered_among_pred_poor": round(np.average(1 - g.vup_any[g.pred_poor == 1],
                                                            weights=g.weight[g.pred_poor == 1]), 3) if g.pred_poor.sum() else np.nan,
        "recall_in_district": round(recall_score(g.poor, g.pred_poor, sample_weight=g.weight), 3) if g.poor.sum() else np.nan,
    })
md = pd.DataFrame(rows)
for c in [c for c in md.columns if c.endswith("_est")]: md[c] = md[c].round(0).astype(int)
md.to_csv(OUT + "table_model_district.csv", index=False)
df[["hhid","district","p_poor","pred_poor","poor","vup_any"]].to_csv(OUT + "hh_scored.csv", index=False)

card = {
    "outcome": "poor (consumption per adult equivalent below NISR total poverty line, EICV7)",
    "weighted_poverty_rate_households": round(pov_rate, 4),
    "n_households": int(len(df)), "n_clusters": int(df.clust.nunique()),
    "features_registry_observable": NUM + BIN, "features_district_dummies": int(dist.shape[1]),
    "features_excluded_on_purpose": EXCLUDED,
    "model": "L2 logistic regression, C=0.3, standardised inputs, sample-weighted",
    "validation": "5-fold GroupKFold by enumeration cluster, out-of-fold metrics, weighted",
    "metrics_logistic": m_lr, "threshold_logistic": round(float(thr_lr), 4),
    "metrics_gradient_boosting_comparison": m_gb,
    "calibration_deciles": cal.reset_index().to_dict(orient="records"),
    "coefficients_standardised": core.round(4).to_dict(),
    "intended_use": "rank households / areas for social-registry re-verification; descriptive support for planners",
    "non_use": "must not be used to decide any individual household's eligibility or benefit",
    "limitations": ["cross-sectional survey; associations only",
                    "district-level sample ~500 households; counts carry sampling error",
                    "outcome measured post-transfer for recipients"],
}
json.dump(card, open(OUT + "model_card.json", "w"), indent=2)
print("\nnational: predicted-poor & uncovered households est.", f"{md.pred_poor_uncovered_hh_est.sum():,}",
      "| actual poor & uncovered", f"{md.actual_poor_uncovered_hh_est.sum():,}")
print("wrote model_card.json, table_model_district.csv, hh_scored.csv")
