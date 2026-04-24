# Project Memory: ETH & UZH Foreign Professor Data Collection

## What We Are Doing
Collecting data on **how many foreign professors** are at ETH Zurich (ETHZ) and University of Zurich (UZH), broken down across two dimensions:
1. **Professor rank** — Full / Associate / Assistant (caveat below)
2. **Faculty/Department** — by academic field

The goal is to build a **panel dataset** spanning multiple years for analysis.

---

## Data Source
**Swiss Federal Statistical Office (FSO) — STAT-TAB PxWeb API**
- Base URL: `https://www.pxweb.bfs.admin.ch/api/v1/de`
- API docs: standard PxWeb REST API (POST queries in JSON, GET for metadata)
- Language: use `/de` endpoint (the `/en` endpoint returns "Bad Request" for metadata GETs)

---

## The Two Key Cubes

### Cube 1: `px-x-1504040100_103`
- **Title:** Personal der universitären Hochschulen — in Personen nach Jahr, Fachbereich, Staatsangehörigkeit (Kategorie) und Hochschule
- **Dimensions:** Year × Field × Nationality × University
- **Use for:** Foreign vs Swiss staff counts by field and university

### Cube 2: `px-x-1504040100_102`
- **Title:** Personal der universitären Hochschulen — in Personen nach Jahr, Fachbereich, Personalkategorie und Hochschule
- **Dimensions:** Year × Field × Rank × University
- **Use for:** Professor vs other staff counts by field and university

Both cubes cover **1980–2024** annually. Fetch **all available years** (1980–2024) to maximize data coverage. Note: FSO revised methodology in 2012, so pre-2012 data may not be directly comparable — but we still want it for the fullest possible picture.

---

## Dimension Codes

### University (`Hochschule`)
| Code | Label |
|------|-------|
| `70` | UZH (Universität Zürich) |
| `90` | ETHZ (ETH Zürich) |

### Nationality (`Staatsangehörigkeit (Kategorie)`)
| Code | Label |
|------|-------|
| `1` | Schweiz (Swiss) |
| `2` | Ausland (Foreign) |
| `99` | Unbekannt |

### Rank (`Personalkategorie`)
| Code | Label (German) | Label (English) |
|------|----------------|-----------------|
| `1` | Professor/-innen | Professors |
| `2` | Übrige Dozierende | Other Lecturers |
| `3` | Assistierende und wissenschaftliche Mitarbeitende | Assistants & Research Staff |
| `4` | Direktion, administrativ-technisches Personal | Admin & Technical Staff |

### Fields (`Fachbereich`) — selected
| Code | Label |
|------|-------|
| `101` | 1.1 Theologie |
| `102` | 1.2 Sprach- und Literaturwissenschaften |
| `103` | 1.3 Historische und Kulturwissenschaften |
| `104` | 1.4 Sozialwissenschaften |
| `200` | 2 Wirtschaftswissenschaften |
| `300` | 3 Recht |
| `401` | 4.1 Exakte Wissenschaften |
| `402` | 4.2 Naturwissenschaften |
| `501` | 5.1 Humanmedizin |
| `601` | 6.1 Bauwesen und Geodäsie |
| `602` | 6.2 Maschinen- und Elektroingenieurwissenschaften |
| `700` | 7 Interdisziplinäre und Andere |

---

## How to Query the API

### GET metadata for a cube
```
GET https://www.pxweb.bfs.admin.ch/api/v1/de/{cube_id}/{cube_id}.px
```
Returns all dimension names, codes, and value labels.

### POST to get data
```python
import requests

url = "https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-1504040100_103/px-x-1504040100_103.px"

query = {
    "query": [
        {"code": "Jahr",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Fachbereich",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Staatsangehörigkeit (Kategorie)",
         "selection": {"filter": "item", "values": ["1", "2"]}},
        {"code": "Hochschule",
         "selection": {"filter": "item", "values": ["70", "90"]}}
    ],
    "response": {"format": "csv"}
}

r = requests.post(url, json=query, headers={"Content-Type": "application/json"})
# Response is CSV encoded in latin-1
csv_text = r.content.decode("latin-1")
```

### Filter types
| Filter | Values example | Meaning |
|--------|----------------|---------|
| `"all"` | `["*"]` | Return all values |
| `"item"` | `["70", "90"]` | Return only these specific codes |
| `"top"` | `["5"]` | Return most recent N entries |

---

## Output Files Produced

All saved by `fetch_eth_uzh_professors.py` (relative to working directory when run):

| File | Contents |
|------|----------|
| `eth_uzh_staff_by_nationality_en.csv` | English: Year × Field × Nationality × University × Count |
| `eth_uzh_staff_by_rank_en.csv` | English: Year × Field × Rank × University × Count |
| `eth_uzh_foreign_staff_by_field_all_years_en.csv` | English: Foreign_Count, Total, Foreign_Share_% per field/year |
| `eth_uzh_staff_by_nationality_de.csv` | Deutsch: Original German labels, nationality × field |
| `eth_uzh_staff_by_rank_de.csv` | Deutsch: Original German labels, rank × field |
| `eth_uzh_foreign_staff_by_field_all_years_de.csv` | Deutsch: Ausländeranteil per Fachbereich/Jahr |

---

## ⚠️ Key Limitation: Professor Rank Granularity

**The public FSO API does NOT distinguish Full / Associate / Assistant professor.**
All professors are aggregated into a single category (code `1` = "Professor/-innen").

To get Full/Associate/Assistant breakdown, options are:
1. **ETH annual report PDFs** (2015–2024) — available at `ethz.ch/en/the-eth-zurich/working-teaching-and-research/personalkennzahlen.html` — do include rank breakdowns per department
2. **UZH interactive diagrams** — available at `jahresbericht.uzh.ch`
3. **FSO microdata request** — contact FSO directly for the disaggregated personnel file

---

## Next Steps / Open Tasks
- [ ] Scrape ETH/UZH annual report PDFs for Full/Associate/Assistant breakdown
- [ ] Fix output path issue: change `to_csv()` calls to use `os.path.dirname(os.path.abspath(__file__))` so CSVs save next to the script
- [ ] Add visualization: time series of foreign share by faculty for ETH vs UZH
- [ ] Consider whether to use headcount (persons) or FTE — cubes `_101`/`_103` differ on this

---

## Environment Notes
- API blocks server-side requests from some environments (returns HTTP 403)
- Works fine from browser (fetch) or local Python with `requests`
- Recommended packages: `requests`, `pandas`
- Install: `pip install requests pandas`
