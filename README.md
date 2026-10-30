# Where VUP misses the poor

**A targeting layer for Rwanda's Vision Umurenge Programme, built on NISR's EICV7 survey and MINALOC's
2024 Financial Services instructions.**



| | |
|---|---|
| Live app | `https://vupscreener.streamlit.app/` (public, no login) |
| Demo video | `demo/VUP Screener Video.webm` |
| Data | NISR EICV7 cross-section, catalog 119: https://microdata.statistics.gov.rw/index.php/catalog/119 (licensed, not redistributed; aggregates in `data/clean/` and `dashboard/data/`; see `data/README.md`) |
| Code | this repository; everything runs from the root with `pip install -r requirements.txt` |
| Team | **NIYONGANA Anathole**, **GITEGO Faycal** - [University of Lay Adventist of Kigali (UNILAK)] |

 VUP is Rwanda's main safety net, reaching about 1.6 million people. Using EICV7 we
find that only 16 in 100 poor households receive any VUP component, that about 647,000 poor households
receive nothing, and that two-thirds of cash recipients are not poor. The households VUP misses are the
working poor: working-age heads, same household size as covered households, more children per worker. The
2024 Ministerial Instructions say the Financial Services component is for exactly these people. We built a
tool that shows LODA and districts where the gap is, shows sector officers whether an applicant fits the
written rules and how likely the household is to be poor, and generates the administrative data VUP does
not collect today.

---

## 1. The problem

### What we asked
In which districts do the largest shares of poor households receive no VUP component, and what
characterises the households that are missed?

### Why it matters
VUP is the Government of Rwanda's flagship social-protection programme (Direct Support, Classic and
Expanded Public Works, Nutrition-Sensitive Direct Support, Financial Services), implemented by LODA and
districts under MINALOC. NST2 (2024–2029) commits to reducing poverty and to a social-protection system
that supports households to graduate from poverty; Vision 2050 aims at the elimination of extreme
poverty. Both depend on the programme reaching the poor. NISR's own EICV7 VUP Thematic Report (2025)
showed that about 59% of beneficiary households are not poor, but no published source measures the other
side of targeting, the poor households VUP never reaches, or shows either at district level. That is the
gap this project fills.

### What we found (EICV7, 2023/24, household-weighted, 95% intervals)

| Indicator | Value |
|---|---|
| Poor households receiving any VUP component (coverage) | **15.9%** (14.7 - 17.1) |
| Extremely poor households receiving any VUP component | **18.2%** (15.0 - 21.3) |
| Poor households receiving nothing (estimate) | **=647,000**, of which = 112,000 extremely poor |
| Cash recipients who are non-poor, consumption as published | **65.7%** |
| Cash recipients who are non-poor, before the VUP cash is counted | **59.9%** |
| Households lifted above the line by VUP cash (estimate) | **=19,000** |
| Districts significantly below national coverage | **8**: Nyagatare, Kamonyi, Ngoma, Rwamagana, Gasabo, Gatsibo, Kicukiro, Nyarugenge |
| Largest absolute gaps | Nyagatare =50,000 uncovered poor households (coverage **4.3%**); Kamonyi =38,000 |
| Best-covered districts | Nyaruguru **40%**, Ngororero **29%** |

**Who is missed.** Covered poor households match the programme's vulnerability template (female-headed
35% vs 25% among uncovered; head aged 65+ 25% vs 12%; widowed 23% vs 11%; a member with disability
15% vs 9%). Uncovered poor households are male-headed, of working age, the same size (4.8 members), with
more children per worker, and own phones *more* often (76% vs 64%). Distance to services does not differ.
These are the working poor, the group the public-works and Financial Services components are designed
for. The 2024 Ministerial Instructions define FS clients as "people able to work within poor households"
(Art. 4); the component built for the missing group is the one reaching the best-off recipients.

---

## 2. What the app communicates and how to use it

### Pages

| Page | For whom | What it answers | How you interact |
|---|---|---|---|
| **Map** | LODA, district planners | Where coverage of poor households is lowest and how many households that means | Choose one of six indicators; toggle the alert layer; hover a district for value, interval and sample size; read the flagged-district table; download the district CSV |
| **District profile** | District social-affairs officers | One district against its province and the nation | Pick a district; read the plain-language summary |
| **Who is missed** | LODA, MINALOC programme design | What uncovered poor households look like compared with covered ones | Read the grouped bars with intervals; the interpretation is written under the chart |
| **Screener** | Sector and cell officers, Sector Loan Committee | Does this FS application meet the 2024 instructions, how likely is the household to be poor, which component fits, what is the loan ceiling | Fill the form (applicant type, Art. 5–6 conditions, household facts from the application and home visit); read pass/fail per article, the poverty likelihood, the suggested component and Table 1 ceiling; download the pre-screening note; log the case |
| **Tracker** | Sector executive secretaries | Which applications breach the Art. 9 working-day limits (5, 3, 7 days) | Add applications with dates; late steps are highlighted. Ships with three fictional cases |
| **Methods and limits** | analysts | Data, definitions, estimation, model card, limitations, reuse | Read; expand the coefficient and calibration panels |

### Sixty-second walkthrough
Open the app. The four numbers at the top are the national picture. On the Map, leave the indicator on
coverage and look at the amber-outlined districts; the table below is sorted by uncovered households, so
the first row is where a re-verification campaign would reach the most people. Open District profile and
pick Nyagatare. Open Who is missed to see why those households are missed. Open Screener, choose Group,
set 12 members, tick the Art. 5 boxes, enter a household, and read the result: each article passes or
fails with its reference, the poverty score is given as "poor in about N of 10 cases", and the ceiling
comes from Table 1. Download the note.

### Design choices for usability
- One question per page; the map is the landing view because "where" is the first question a planner asks.
- Every number carries its interval and unweighted sample size on hover; districts with too few poor
  households in the sample are greyed, not hidden.
- Every chart has a sentence underneath saying what it means.
- The Screener uses the language of the instructions (articles, Table 1) because that is what the
  Sector Loan Committee reads.
- Tested on a laptop, an Android phone and an iPhone; the map simplifies to ranked bars if boundaries
  are missing, so the app never shows an empty panel.

### Running it
```
pip install -r requirements.txt
streamlit run dashboard/app.py        # or: python -m streamlit run dashboard/app.py
```
Run from the repository root. The app reads the aggregated tables committed in `dashboard/data/`, so it
works without the NISR microdata. Python 3.10 or newer.

---

## 3. Data

### NISR data (core)
**EICV7 cross-sectional sample, 2023–2024, v01** (NISR, catalog 119). 15,054 households, representative at
district level, fieldwork October 2023 to October 2024. It is the only dataset that records both a
household's consumption-based poverty status and its receipt of VUP by component. Files used:



## 4. Methodology and preprocessing

### Preprocessing log (what we found in the files and what we did)
| Issue | Finding | Action |
|---|---|---|
| "Any VUP component" flag | `s9d1q1` is labelled "any component" but equals the Direct Support flag exactly (437 = 437 households). Used naively it undercounts VUP four-fold | Any-VUP = union of the five component flags (1,891 households); documented in `01_data_check.py` |
| Extra rows in component files | 15,054 to 15,057 rows: households with two beneficiaries | Collapsed to one row per household; amounts summed |
| `strata_id` | Populated only for beneficiaries in module files | It equals district × 10 + urban/rural (verified on all non-missing rows); rebuilt for every household |
| Component amounts | DS and CPW/ePW annual; NSDS by quarter (`s9d4q8a–d`) | Summed per household; FS excluded from transfer totals because it is a loan |
| Poverty rates | Household rate 23.4% vs published population rate 27.4% | Both correct (poor households are larger); the app states which it uses |
| District sample support | Median 100 poor households per district (minimum 35); median 15 extremely poor (minimum 3) | District results on all poor; extreme poverty at province level only; cells under 30 flagged not reportable |
| District names | Codes only in the survey; names in the boundary file | Standard NISR codes mapped; fuzzy matching with a printed report of matches |

### Estimation
- All estimates use the household survey weight (`weight`); population figures use `pop_wt`.
- Standard errors by Taylor linearisation under a stratified, with-replacement cluster design
  (strata = district × urban/rural; PSU = enumeration cluster), implemented in `02_district_table.py`
  and `03_profile.py` for ratio estimators with domain estimation on the full sample.
- **Coverage**: share of poor households receiving any component. **Leakage**: share of cash recipients
  who are non-poor. **Pre-transfer leakage**: poverty re-classified after subtracting the VUP cash
  received in the last 12 months from consumption (assumes the cash was consumed), so households that
  VUP itself lifts above the line are not counted as leakage.
- **Alert rule**: a district is flagged when the upper bound of its 95% interval for coverage is below
  the national point estimate.


## 5. What is new

1. **The exclusion side of targeting, at district level.** Prior NISR reports (EICV4, EICV5, EICV7
   Thematic) measured leakage nationally and participation by district; none measured the share of poor
   households not reached, by district, with intervals.
2. **Pre-transfer welfare**, so the programme's success is not mistaken for leakage.
3. **An alert layer** that turns a colour map into a short list a planner can act on.
4. **A rules engine from a legal text.** The Ministerial Instructions are data in `config/fs_rules.yaml`;
   the Screener cites the article for every pass or fail; MINALOC can amend rules without a developer.
5. **A calibrated proxy-means model** in the spirit of IPA's Poverty Probability Index, fitted on EICV7
   with cluster-aware validation, built from inputs a loan application already collects.
6. **Survey-round portability.** Every survey-specific name, code and line lives in `config/eicv7.yaml`;
   EICV8 is a new configuration file and a rerun, and the dashboard reads the round label from its data.
7. **A tool that generates data.** Every logged screening produces a record (district, applicant type,
   rule outcome, failing article, poverty score, component) with no names or IDs: demand, rejection
   reasons and binding constraints that the programme does not record today and that keep flowing
   between surveys. The survey supplies the denominator; the tool supplies the numerator.

---

## 6. Impact: who uses it and what changes

| User | Decision supported | Evidence the tool gives |
|---|---|---|
| LODA (allocation and MIS) | Where to direct social-registry re-verification and public-works slots before the next enrolment cycle | Eight flagged districts with counts of uncovered poor households; the working-poor profile |
| MINALOC (programme design) | Whether FS and public works reach the labour-endowed poor they are written for | FS recipients' poverty distribution; the rule-model disagreement cases |
| District social-affairs officers and BDEU | Which sectors to prioritise; what to tell the District Council | District profile with intervals and a plain-language summary |
| Sector Loan Committees and cell officials | Whether to recommend an FS application, under which ceiling, with which component | Article-by-article check, poverty likelihood, ceiling, printable note |
| Sector executive secretaries | Which applications are late at which step | Tracker against Art. 9 limits |

**Alignment with LODA.** LODA already owns the beneficiary register, the budget and the MIS. Those systems
record what was done; they do not show who is being missed or help a committee apply the rules. This
project is a targeting layer on top of them, not a replacement: standalone it exports CSV and notes; in
production the Screener and Tracker are modules inside LODA's FS management information system, which
Art. 8(5) of the instructions requires LODA to operationalise, and records live under LODA's access
controls and the data protection law.

**Pilot proposal.** Nyagatare and Kamonyi, the two districts with the most uncovered poor households, for
one enrolment cycle: sector officers use the Screener on every FS application; the Tracker records the
Art. 9 steps; LODA compares the poverty profile of new enrolments with the previous cycle. Cost: laptops
the sectors already have and a half-day of training per sector.

---

## 7. Reproducing the analysis from the microdata

1. Request the EICV7 cross-sectional microdata at https://microdata.statistics.gov.rw/index.php/catalog/119
   and unzip the `.dta` files into `data/raw/Cross_Section/`.
2. Boundaries are already in `data/geo/rwanda_districts.geojson`; any district-level GeoJSON can replace
   them (the build script prints what it matched).
3. From the repository root:

```
pip install -r requirements.txt
python scripts/01_data_check.py           # validates files, reproduces NISR headline figures, builds VUP flags
python scripts/02_district_table.py       # coverage/leakage by district with design-based CIs; pre-transfer welfare
python scripts/03_profile.py              # registry-observable features; uncovered vs covered poor
python scripts/04_classifier.py           # targeting model, cluster-grouped validation, model card
python scripts/04b_screener_model.py      # compact screener model -> JSON
python scripts/05_build_dashboard_data.py # packs tables + boundaries for the app
streamlit run dashboard/app.py
```

| Script | Reads | Writes |
|---|---|---|
| `01_data_check.py` | poverty file, five VUP modules | `data/clean/hh_vup.csv` |
| `02_district_table.py` | raw files, `hh_vup.csv` | `hh_vup_full.csv`, `table_national.csv`, `table_province.csv`, `table_district.csv` |
| `03_profile.py` | person, household, access, savings, credit modules, `hh_vup_full.csv` | `hh_features.csv`, `table_profile.csv` |
| `04_classifier.py` | `hh_features.csv` | `model_card.json`, `table_model_district.csv`, `hh_scored.csv` |
| `04b_screener_model.py` | `hh_features.csv` | `dashboard/data/screener_model.json` |
| `05_build_dashboard_data.py` | `table_*.csv`, `model_card.json`, GeoJSON, `config/eicv7.yaml` | everything in `dashboard/data/` |

**Checks to expect.** Script 01 prints poverty 27.37% and extreme poverty 5.44% and ≈380k VUP households;
if these differ, stop and check the files. Script 05 prints `geojson matched 30 of 30`.

---

## 8. Limitations and responsible use

- Cross-sectional survey: associations, not causes. Recipients' consumption is measured after receiving
  support (the pre-transfer adjustment is an approximation that assumes the cash was consumed).
- About 500 households per district: counts carry sampling error and are always shown with intervals;
  extreme-poverty coverage is reported at province level only.
- Self-reported receipt and amounts; Asset Transfer and Skills Development components are not covered by
  the survey modules.
- Fieldwork spanned a year; seasonal effects are averaged.
- The model informs where to re-verify; it must not decide eligibility. The Screener advises; the Sector
  Loan Committee decides.
- No ranking of districts as blame: the framing is where additional support would reach the most people.

## 9. Privacy and data handling

- Microdata never leaves the licensed environment; only aggregates and coefficients are published.
- The Screener collects no names or identifiers; each case has a random eight-character id. The session
  log and the Tracker list live in the browser session and clear on refresh; use the Download buttons.
- The Tracker ships with three fictional applications.
- A production deployment stores records in LODA's MIS under its access controls and Rwanda's data
  protection law (Law No. 058/2021).

## 10. Configuration and reuse

- `config/eicv7.yaml`: file names, variable names, the stratum formula, poverty lines, published
  benchmarks, reporting rules (minimum unweighted n of 30, alert rule, confidence level). No script
  hard-codes a variable name a new round might change. EICV8 = copy to `eicv8.yaml`, update from the new
  codebook, rerun.
- `config/fs_rules.yaml`: the Ministerial Instructions with article references. Revised instructions =
  edit this file.

## 11. Repository layout

```
README.md                          this file
requirements.txt                   pandas, numpy, scikit-learn, plotly, streamlit, pyyaml, jinja2
config/eicv7.yaml                  survey-round configuration
config/fs_rules.yaml               FS instructions as rules
scripts/01_… 05_…                  the pipeline (see §7)
dashboard/app.py                   Map, District profile, Who is missed, Methods and limits
dashboard/pages/1_Screener.py      FS application pre-screen
dashboard/pages/2_Tracker.py       Art. 9 deadline tracker
dashboard/data/                    aggregated tables, model JSONs, boundaries (committed)
data/README.md                     data sources and access
data/clean/                        aggregate tables and model card (committed); household files (not)
data/geo/rwanda_districts.geojson  district boundaries
data/raw/                          NISR microdata (not committed)
demo/demo.webm                     screen recording
```

## 12. Troubleshooting

- `FileNotFoundError: config/eicv7.yaml`: run scripts and the app from the repository root.
- `streamlit` not recognised: use `python -m streamlit run dashboard/app.py`.
- Build script exits with "could not find a district-name property": add the property name to the list
  in `scripts/05_build_dashboard_data.py`.
- Map shows bars instead of boundaries: `dashboard/data/districts.geojson` is missing; rerun script 05.
- Map shows only some districts after rebuilding: clear Streamlit's cache (press `C`, then `R`) or restart.

## 13. Sources

- NISR (2025). *Seventh Integrated Household Living Conditions Survey (EICV7), 2023–2024, Cross-Sectional Sample*, v01. https://microdata.statistics.gov.rw/index.php/catalog/119
- NISR (2025). *EICV7 VUP Thematic Report*. https://microdata.statistics.gov.rw/index.php/catalog/121
- NISR (2025). *EICV7 Main Indicators Report* and *Methodological Note*.
- MINALOC (2024). *Ministerial Instructions No. 01/10 of 23/02/2024 determining the management and implementation of the VUP Financial Services credit scheme*.
- OCHA (2023). Rwanda subnational administrative boundaries (COD-AB) / geoBoundaries RWA ADM2.
- World Bank ASPIRE indicator definitions (coverage, targeting accuracy, pre-transfer welfare); IPA Poverty Probability Index (proxy-means logic).

## 14. Team and declarations

Team: **NIYONGANA Anathole and GITEGO Faycal** -  University of Lay Adventist Of Kigali **(UNILAK)**. This submission is our own original work, not previously
submitted elsewhere; all sources are acknowledged above.

**Licence:**  NISR microdata is used under NISR's terms and is not redistributed.
Intellectual property in the submitted work is assigned to NISR under the competition rules.