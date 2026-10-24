# Data

## Source microdata (not committed, licensed)
Rwanda - Integrated Household Living Conditions Survey (EICV7), 2023-2024, Cross-Sectional Sample, v01.
National Institute of Statistics of Rwanda. Request access and download from:
https://microdata.statistics.gov.rw/index.php/catalog/119
Unzip the .dta files into `data/raw/Cross_Section/`. Files used: CS_EICV7_poverty_file, CS_S9D1 to CS_S9D5 (VUP
components), CS_S0_..._Person, CS_S01_S5_S7_Household, CS_S5F_access_to_services, CS_S10C_Savings, CS_S10A1_A2_credits.

## Boundaries
District boundaries (admin level 2) as GeoJSON in `data/geo/rwanda_districts.geojson`, from
https://data.humdata.org/dataset/cod-ab-rwa (OCHA COD-AB) or https://www.geoboundaries.org (RWA ADM2).

## Derived, committed
`data/clean/table_*.csv` and `model_card.json`: aggregated, non-identifying results written by the scripts.
`../dashboard/data/`: the same tables packed for the app, plus `screener_model.json`.

## Rules
`../config/fs_rules.yaml`: MINALOC Ministerial Instructions No. 01/10 of 23/02/2024 (VUP Financial Services), encoded.
