# fhir-prototype

Python prototype for importing FHIR bundles into the AKTIN i2b2 data warehouse.
The goal is a working end-to-end pipeline first. Once it is stable, the logic
will be ported to `aktin/dwh-import`.

## Pipeline

1. ✅ Load a FHIR bundle (JSON) and build pandas DataFrames (patients, encounters, observations, procedures)
2. ⏳ Process and validate the DataFrames. Date and time conversion is done, checks before import are still open
3. ⏳ Map the DataFrames to i2b2 observation facts. The mechanics are done, some concepts in the mapping table are provisional or still open
4. Import the facts into i2b2

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

## Run

Run steps 1 to 3 for one bundle and write the result as CSV:

```bash
uv run python -c "from fhir_prototype.pipeline import run; run('tests/fixtures/bundle_max_1.json', 'output')"
```

The first argument is the bundle file, the second is the output folder. It is
created if it does not exist and then contains two files:

| File | Content |
|---|---|
| `facts.csv` | rows that have an i2b2 concept and can be imported |
| `unmapped.csv` | rows without a concept in the mapping table, they are not imported |

## Mapping

`src/fhir_prototype/icu_mapping.csv` assigns an i2b2 `concept_cd` to each FHIR
profile (plus the device category for ventilation parameters). The code only
applies this table, so a mapping decision is a change in the CSV and not in the
code. The `status` column shows how settled a row is:

| Status | Meaning |
|---|---|
| `vorgeschlagen` | proposed, no open question |
| `vorläufig` | provisional concept, to be confirmed |
| `offen` | open question, see `open_question` |

Rows with an empty `concept_cd` end up in `unmapped.csv`.

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