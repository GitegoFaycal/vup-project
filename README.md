# Where VUP misses the poor

District-level evidence on the coverage gaps of the Vision Umurenge Programme (VUP), built from
NISR's EICV7 household survey for the **NISR 2026 Big Data Hackathon, Track 2: Financial Inclusion
and Poverty Reduction**.

**Question.** In which districts do the largest shares of poor households receive no VUP component,
and what characterises those households?

**Headline (EICV7, 2023/24, household-weighted).** Only 15.9 % (95 % CI 14.7–17.1) of poor households
receive any VUP component; an estimated 647,000 poor households receive nothing. Eight districts are
significantly below the national rate: Kicukiro, Nyagatare, Rwamagana, Gasabo, Nyarugenge, Gatsibo,
Ngoma and Kamonyi. By number of uncovered poor households the gap is largest in Nyagatare (≈50,000)
and Kamonyi (≈38,000). Uncovered poor households are the *working poor*: male-headed, working-age,
same household size as covered households, more children per worker. VUP reaches the visibly
vulnerable (elderly, widowed, disabled, no adult man) and misses them.

**Users.** LODA, MINALOC and district social-affairs officers deciding where to re-verify the social
registry before the next enrolment cycle; sector and cell officers pre-screening Financial Services
(FS) applications.

Live dashboard: `<deployed link>` (fill in after deployment)

## Quick start (dashboard only, no microdata needed)

The app reads the small aggregated tables already committed in `dashboard/data/`, so anyone can run
it without access to the NISR microdata.

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Run both commands from the repository root. Streamlit opens the app at http://localhost:8501; the
Screener and Tracker pages are listed in the sidebar. Python 3.10 or newer is assumed (developed on
3.14; packages are pinned to minimum versions in `requirements.txt`).

## What the app does

| Page | For whom | What it answers |
|---|---|---|
| **Map** | District planners, LODA | Where coverage of poor households is lowest; eight districts flagged; counts of uncovered households; six switchable indicators; CSV download of the district table |
| **District profile** | District social-affairs officers | One district against its province and the nation, in plain language |
| **Who is missed** | LODA programme design | Uncovered poor are the working poor; VUP reaches the visibly vulnerable |
| **Screener** | Sector/cell officers, Sector Loan Committee | Pre-screens an FS application against the 2024 Ministerial Instructions (rules in `config/fs_rules.yaml`) and scores household poverty with an EICV7 model; suggests a component and the Table 1 ceiling; produces a note for the committee file |
| **Tracker** | Sector executive secretaries | Working-day status of each application against the Art. 9 limits (5, 3, 7 days). Demo data |
| **Methods and limits** | Judges, analysts | Data, definitions, estimation, model card, limitations |

The Screener **advises**; the Sector Loan Committee decides. It stores no names or IDs. Each logged
screening adds a row (district, applicant type, rule outcome, failing article, poverty score,
component): administrative data on demand, rejection reasons and timeliness that VUP does not
collect today, and that keeps flowing between survey rounds.

Both the Screener log and the Tracker's application list live in the Streamlit session only. They
are cleared when the browser tab is refreshed; use the **Download** buttons to keep a copy. A
production version would write to the FS management information system instead.

## Repository layout

```
config/eicv7.yaml                survey-round mapping: files, variables, poverty lines, benchmarks, reporting rules
config/fs_rules.yaml             FS Ministerial Instructions (01/10 of 23/02/2024) encoded as rules, with article references
scripts/01_data_check.py         load, validate, reproduce NISR headline figures, build VUP flags
scripts/02_district_table.py     coverage / leakage by district with design-based CIs; pre-transfer welfare
scripts/03_profile.py            registry-observable features; uncovered vs covered poor profile
scripts/04_classifier.py         targeting classifier, cluster-grouped CV, model card
scripts/04b_screener_model.py    compact model on application-form inputs, exported as JSON for the Screener
scripts/05_build_dashboard_data.py  pack outputs + GeoJSON for the app
dashboard/app.py                 Streamlit dashboard (Map, District profile, Who is missed, Methods)
dashboard/pages/1_Screener.py    FS application pre-screen (rules + model)
dashboard/pages/2_Tracker.py     Art. 9 deadline tracker (demo data)
dashboard/data/                  small aggregated tables the app reads (committed)
data/raw/                        NISR microdata (NOT committed; see access below)
data/clean/                      intermediate outputs (table_*.csv and model_card.json committed; hh_*.csv not)
data/geo/rwanda_districts.geojson  district boundaries (committed)
data/README.md                   data sources and access notes
demo/README.md                   where to put the screen recording and a suggested script
requirements.txt                 Python dependencies
```

## Reproducing the analysis from the microdata

### Prerequisites

1. Request the EICV7 cross-sectional microdata from NISR:
   https://microdata.statistics.gov.rw/index.php/catalog/119 and unzip the `.dta` files into
   `data/raw/Cross_Section/`. The files used are listed in `data/README.md` and in
   `config/eicv7.yaml` under `files`.
2. District boundaries are already in `data/geo/rwanda_districts.geojson`. To replace them, any
   district-level GeoJSON works (OCHA COD-AB ADM2, geoBoundaries ADM2); names are matched
   case-insensitively with a fuzzy fallback and the build script prints what it matched.
3. `pip install -r requirements.txt`

### Pipeline

All scripts use paths relative to the repository root, so run them from there, in this order:

```
python scripts/01_data_check.py
python scripts/02_district_table.py
python scripts/03_profile.py
python scripts/04_classifier.py
python scripts/04b_screener_model.py
python scripts/05_build_dashboard_data.py
streamlit run dashboard/app.py
```

| Script | Reads | Writes |
|---|---|---|
| `01_data_check.py` | raw poverty file and the five VUP component modules | `data/clean/hh_vup.csv` |
| `02_district_table.py` | raw files, `hh_vup.csv` | `hh_vup_full.csv`, `table_national.csv`, `table_province.csv`, `table_district.csv` |
| `03_profile.py` | raw person, household, access, savings and credit modules, `hh_vup_full.csv` | `hh_features.csv`, `table_profile.csv` |
| `04_classifier.py` | `hh_features.csv` | `model_card.json`, `table_model_district.csv`, `hh_scored.csv` |
| `04b_screener_model.py` | `hh_features.csv` | `dashboard/data/screener_model.json` |
| `05_build_dashboard_data.py` | all `table_*.csv`, `model_card.json`, the GeoJSON, `config/eicv7.yaml` | everything in `dashboard/data/` |

The household-level files (`hh_*.csv`) contain one row per surveyed household and are excluded by
`.gitignore`. Only aggregated tables are committed.

### Checks to expect

The first script prints the reproduced population-weighted poverty rate (27.4 %) and extreme poverty
rate (5.4 %), and the estimated number of VUP households (≈380k against NISR's 391k benchmark). If
either is off, stop and check the files before going further. The benchmark values are stored in
`config/eicv7.yaml` under `benchmarks`.

The classifier script prints out-of-fold metrics; the committed model card reports AUC 0.814 and
Brier score 0.137. The screener model prints its own, slightly lower, metrics because it uses fewer
inputs.

The dashboard caches its data keyed on file modification times, so re-running the build script
refreshes the running app without a restart.

## Configuration

**`config/eicv7.yaml`** holds everything specific to the survey round: file names, variable names,
the stratum formula, poverty lines, published benchmark figures, and the reporting rules (minimum
unweighted sample of 30 per district, alert rule, confidence level). The scripts read it at start-up;
none of them hard-codes a variable name that a new round might change.

**`config/fs_rules.yaml`** encodes the FS Ministerial Instructions: eligibility (Art. 4 to 6), loan
terms (Art. 3, 12), ceilings by applicant type and group size (Art. 11, Table 1), the Art. 9
working-day limits, and the City of Kigali former-street-vendor scheme (Art. 14). Every rule carries
its article so the Screener can cite it on screen. If the instructions are revised, change this file,
not the code.

## Method in brief

- Poverty status, consumption aggregates and lines as published by NISR.
- Any-VUP flag = union of the five component modules (Direct Support, Classic Public Works, Expanded
  Public Works, NSDS, Financial Services). The file's "any component" variable is the Direct Support
  flag only, so it is not used.
- Weighted estimates; Taylor-linearised SEs with strata (district × urban/rural) and clusters.
- Pre-transfer welfare: consumption minus reported VUP cash (FS loans excluded), re-classified against
  the same lines, so households lifted above the line by VUP are not counted as leakage.
- Alert rule: district coverage upper CI bound below the national point estimate.
- Districts with fewer than 30 poor households in sample are not reported; extreme-poverty coverage is
  province-level only.

### Targeting model

- Outcome: household consumption per adult equivalent below the NISR total poverty line.
- Features: 32 registry-observable characteristics (household composition, head, dwelling, assets,
  distance to services) plus district dummies. Financial-inclusion and post-enrolment variables
  (accounts, SACCO, loans, insurance) are excluded on purpose.
- Model: L2 logistic regression, sample-weighted, standardised inputs. Gradient boosting fitted for
  comparison only (AUC 0.818 vs 0.814; not worth the loss of transparency).
- Validation: 5-fold GroupKFold by enumeration cluster, so households from one cluster never appear
  in both train and test. Calibration by decile is in the model card.
- Threshold: chosen so that the share flagged equals the weighted poverty rate.
- Full card: `dashboard/data/model_card.json`. The Screener uses a separate, smaller model
  (`screener_model.json`) restricted to inputs an officer can take from an application form and a
  home visit; it is exported as plain JSON and scored with numpy, so no pickle and no scikit-learn
  version pinning at runtime.

## Limitations

Cross-sectional data (associations only); recipients' consumption is measured post-transfer;
~500 households per district, so counts carry sampling error; self-reported receipt; Asset Transfer
and Skills Development are not in the survey modules. The model ranks areas for re-verification and
must not decide any household's eligibility.

## Reuse across survey rounds

All survey-specific knowledge lives in `config/eicv7.yaml`. Onboarding EICV8 means copying it to
`config/eicv8.yaml`, updating variable names and lines from the new codebook, pointing the scripts at
the new file, and re-running the pipeline.

## Privacy and data handling

- NISR microdata is licensed and never committed. `.gitignore` excludes `data/raw/` and all
  household-level outputs.
- Committed tables are aggregates at district, province or national level, or model coefficients.
- The Screener collects no names or identifiers. Each case gets a random eight-character id, and the
  session log holds district, applicant type, rule outcomes, poverty score and suggested component only.
- The Tracker ships with three fictional sample applications.

## Troubleshooting

- **`FileNotFoundError: config/eicv7.yaml`**: run the scripts and the app from the repository root.
- **Build script exits with "could not find a district-name property"**: the GeoJSON uses a property
  name the script does not recognise. Add it to the list in `scripts/05_build_dashboard_data.py`.
- **Map shows no boundaries**: `dashboard/data/districts.geojson` is missing. Re-run the build script
  with the GeoJSON in place; the rest of the app works without it.
- **Reproduced poverty rate does not match 27.4 %**: check that the `.dta` files are the
  cross-sectional sample, v01, and that the paths in `config/eicv7.yaml` point to them.

## Sources

- NISR (2025). *Seventh Integrated Household Living Conditions Survey (EICV7), 2023–2024, Cross-Sectional Sample*, v01.
- NISR (2025). *EICV7 VUP Thematic Report*. Used as the national benchmark.
- NISR (2025). *EICV7 Main Indicators Report* and *Methodological Note*.
- OCHA (2023). Rwanda subnational administrative boundaries (COD-AB), or geoBoundaries ADM2.
- MINALOC (2024). Ministerial Instructions No. 01/10 of 23/02/2024 determining the management and implementation of the VUP Financial Services credit scheme.

## Team and declarations

Team: [Name 1], [Name 2] — [University]. Original work, not previously submitted elsewhere.

**AI assistance disclosure.** Claude (Anthropic) was used as an assistant for drafting code,
documentation and design options. All analysis choices, validation and interpretation were made and
checked by the team, who take full responsibility for the submission.

Licence: code MIT; results CC BY 4.0. NISR microdata is used under NISR's terms and is not redistributed.
