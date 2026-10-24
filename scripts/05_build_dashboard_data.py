"""
05_build_dashboard_data.py  -  Pack the analysis outputs into the small tables the
dashboard loads. Joins the district GeoJSON if present (data/geo/rwanda_districts.geojson).

Run after 01-04b. Output: dashboard/data/*.csv|json
GeoJSON: any district-level file (OCHA COD-AB ADM2, geoBoundaries ADM2, World Bank districts).
         Names are matched case-insensitively, ignoring a "District" suffix, with a fuzzy
         fallback for spelling differences. The script prints what it matched.
"""
import difflib, json, os, re, sys
import pandas as pd, yaml

cfg = yaml.safe_load(open("config/eicv7.yaml"))
CLEAN, OUT = cfg["paths"]["clean"], "dashboard/data/"
os.makedirs(OUT, exist_ok=True)

dist = pd.read_csv(CLEAN + "table_district.csv")
model = pd.read_csv(CLEAN + "table_model_district.csv")
d = dist.merge(model.drop(columns=["n_hh"]), on="district_code", how="left")
d = d.rename(columns={"unit": "district"})
d["uncovered_poor_hh_est"] = d.uncovered_poor_hh_est.astype(int)
d.to_csv(OUT + "districts.csv", index=False)

prov = pd.read_csv(CLEAN + "table_province.csv").rename(columns={"unit": "area"})
prov.to_csv(OUT + "provinces.csv", index=False)
pd.read_csv(CLEAN + "table_national.csv").to_csv(OUT + "national.csv", index=False)
pd.read_csv(CLEAN + "table_profile.csv").to_csv(OUT + "profile.csv", index=False)
json.dump(json.load(open(CLEAN + "model_card.json")), open(OUT + "model_card.json", "w"), indent=2)
json.dump({"round": cfg["round"], "reporting": cfg["reporting"]}, open(OUT + "meta.json", "w"), indent=2)

# ---------- district boundaries ----------
geo_path = cfg["paths"]["geo"]
norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower()).replace("district", "")

if os.path.exists(geo_path):
    gj = json.load(open(geo_path, encoding="utf-8"))
    props = gj["features"][0]["properties"]
    name_key = next((k for k in props if k.upper() in
                     ("ADM2_EN", "NAME_2", "DISTRICT", "NAME", "ADM2", "DIST_NAME", "SHAPENAME")), None)
    if name_key is None:
        sys.exit(f"could not find a district-name property in {list(props)}; set name_key by hand")

    lookup = {norm(n): n for n in d.district}
    unmatched, used = [], {}
    for f in gj["features"]:
        raw = str(f["properties"][name_key])
        key = norm(raw)
        match = lookup.get(key)
        if match is None:
            close = difflib.get_close_matches(key, list(lookup), n=1, cutoff=0.75)
            match = lookup[close[0]] if close else None
            if match:
                print(f"  fuzzy: '{raw}' -> {match}")
        f["properties"]["district"] = match
        f["id"] = match
        if match is None:
            unmatched.append(raw)
        else:
            used[match] = used.get(match, 0) + 1

    # Plotly's geo renderer (d3-geo) wants exterior rings clockwise; RFC 7946 files (geoBoundaries, OCHA)
    # are counter-clockwise, which d3 reads as "the whole globe minus the district" and draws nothing useful.
    def ring_area(r):
        return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:])) / 2
    def rewind(poly):  # exterior clockwise (area < 0), holes counter-clockwise
        return [r if (ring_area(r) < 0) == (i == 0) else r[::-1] for i, r in enumerate(poly)]
    for f in gj["features"]:
        g = f["geometry"]
        if g["type"] == "Polygon":
            g["coordinates"] = rewind(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            g["coordinates"] = [rewind(p) for p in g["coordinates"]]

    json.dump(gj, open(OUT + "districts.geojson", "w"))
    n_ok = len(gj["features"]) - len(unmatched)
    print(f"geojson matched {n_ok} of {len(gj['features'])} features | unmatched: {unmatched}")
    dup = [k for k, v in used.items() if v > 1]
    missing = sorted(set(d.district) - set(used))
    if dup:     print("  WARNING two features mapped to the same district:", dup)
    if missing: print("  WARNING districts in the data with no boundary:", missing)
else:
    print(f"no GeoJSON at {geo_path}; dashboard will fall back to bar charts until it is added")
print("dashboard data written to", OUT)
