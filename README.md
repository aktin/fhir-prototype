# fhir-prototype

Python prototype for importing FHIR bundles into the AKTIN i2b2 data warehouse.
The goal is a working end-to-end pipeline first. Once it is stable, the logic
will be ported to `aktin/dwh-import`.

## Pipeline

1. ✅ Load a FHIR bundle (JSON) and build pandas DataFrames (patients, encounters, observations)
2. ⏳ Process and validate the DataFrames (optional)
3. Map the DataFrames to i2b2 observation facts
4. Import the facts into i2b2

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

## Test data

All bundles in `tests/fixtures/` are **synthetic**. They contain no real
patient data. Each bundle holds one patient with one ICU encounter and
observations based on the MII ICU module and ISiK profiles.

| File | Content |
|---|---|
| `bundle_min.json` | 68 resources, minimal example |
| `bundle_max_1.json` | 248 resources, finished encounter |
| `bundle_max_2.json` | 248 resources, ongoing encounter, spans a DST change |

Do not add real patient data to this repository.

