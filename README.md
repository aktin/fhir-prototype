# fhir-prototype

Python prototype for importing FHIR bundles into the AKTIN i2b2 data warehouse.
The goal is a working end-to-end pipeline first. Once it is stable, the logic
will be ported to `aktin/dwh-import`.

## Pipeline

1. ✅ Load a FHIR bundle (JSON), index its entries and build pandas DataFrames for patients and encounters
2. ⏳ Validate the bundle and parse dates. Date and time conversion is done, checks before import are still open
3. ⏳ Translate Observations and Procedures into i2b2 observation facts by the rules in `icu_mapping.json`. The mechanics are done, the mapping holds only RASS so far
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
uv run python -c "from fhir_prototype.importer import CsvImporter; from fhir_prototype.pipeline import run; run('tests/fixtures/bundle_max_1.json', CsvImporter('output'))"
```

The first argument is the bundle file, the second is the importer that receives
the result. `CsvImporter` writes four files into its folder and creates the
folder if it does not exist:

| File | Content |
|---|---|
| `patients.csv` | one row per patient |
| `encounters.csv` | one row per encounter, times in UTC |
| `facts.csv` | fact rows that can be imported: one main row per resource and one row per modifier |
| `unmapped.csv` | resources that are not imported, one row each with a `reason` |

## Mapping

`src/fhir_prototype/icu_mapping.json` is the single source of truth for step 3.
Only resources whose profile is described there become facts. The code knows
no profiles, so supporting a new profile means adding an entry to this file,
not changing Python.

The file is an object keyed by profile URL. Each entry describes the rows of
`observation_fact` that one resource of this profile turns into:

```json
{
  "https://www.medizininformatik-initiative.de/fhir/ext/modul-icu/StructureDefinition/mii-pr-icu-score-rass": {
    "concept": {
      "concept_cd": "SNOMED:1345050000",
      "valtype_cd": "N",
      "nval_num": "@valueCodeableConcept.text",
      "start_date": "@effectivePeriod.start | effectiveDateTime",
      "end_date": "@effectivePeriod.end"
    },
    "modifiers": {
      "fhirVersion": {
        "valtype_cd": "T",
        "tval_char": "4.0.1"
      },
      "answerCode": {
        "valtype_cd": "T",
        "tval_char": "@'LOINC:' + valueCodeableConcept.coding.where(system = 'http://loinc.org').code"
      }
    }
  }
}
```

- `concept` describes the main row (`modifier_cd` `@`).
- Each entry in `modifiers` adds one row. Its key becomes the `modifier_cd`.
  Modifier rows share resource, patient, encounter, concept and times with the
  main row.
- Keys inside `concept` and the modifiers are column names of
  `observation_fact`: `concept_cd`, `valtype_cd`, `tval_char`, `nval_num`,
  `units_cd`, `start_date`, `end_date`. `expected_unit` in `concept` is a check,
  not a column (see below).
- A value starting with `@` is a FHIRPath expression evaluated on the resource.
  The first result is used. Any other value is taken as a constant.
- A modifier whose expression finds nothing produces no row.

### Rejected resources

A resource lands in `unmapped.csv` with one of these reasons, and none of its
rows is imported:

| Reason | When |
|---|---|
| `no concept in mapping` | its profile has no entry in the mapping |
| `no numeric value` | `valtype_cd` is `N`, but `nval_num` is empty or not a number |
| `unit differs from expected_unit` | `units_cd` does not match `expected_unit` |

Resources with status `entered-in-error`, `cancelled` or `not-done` are skipped.

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