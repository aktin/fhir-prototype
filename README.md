# fhir-prototype

Python prototype for importing FHIR bundles into the AKTIN i2b2 data warehouse.
The goal is a working end-to-end pipeline first. Once it is stable, the logic
will be ported to `aktin/dwh-import`.

## Pipeline

1. ✅ Load a FHIR bundle (JSON) and build pandas DataFrames (patients, encounters)
2. ⏳ Process and validate the DataFrames. Date and time conversion is done, checks before import are still open
3. ⏳ Map the DataFrames to i2b2 observation facts. The mechanics are done, some concepts in the mapping table are
   provisional or still open
4. Import the facts into i2b2

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

## Run

Run steps 1 to 3 for all bundles of one ZIP file and write the result as CSV.
The test fixtures can be packed into a ZIP like this:

```bash
uv run python -m zipfile -c delivery.zip tests/fixtures/*.json
```

Then run the pipeline:

```bash
uv run python -c "from fhir_prototype.importer import CsvImporter; from fhir_prototype.pipeline import run; run('delivery.zip', CsvImporter('output'))"
```

The first argument is the ZIP file, the second is the output folder. It is
created if it does not exist and then contains one subfolder per JSON file in
the ZIP (for example `output/bundle_min/`) with four files:

| File             | Content                                                            |
|------------------|--------------------------------------------------------------------|
| `patients.csv`   | one row per patient in the bundle                                  |
| `encounters.csv` | one row per encounter in the bundle                                |
| `facts.csv`      | rows that have an i2b2 concept and can be imported                 |
| `unmapped.csv`   | rows without a concept in the mapping table, they are not imported |

Bundles that cannot be processed are skipped with a warning.

## Offline validation

The HL7 FHIR validator checks resources against their profiles on the local machine.
It needs network access only once, to fill its package cache.

Download the validator (tested with version 7.0.6 and Java 25):

```bash
mkdir -p validation
curl -L -o validation/validator_cli.jar https://github.com/hapifhir/org.hl7.fhir.core/releases/download/7.0.6/validator_cli.jar
```

Validate one RASS and one NRS observation:

```bash
java -Duser.home="$PWD/validation/fhir-home" -jar validation/validator_cli.jar \
  tests/fixtures/observation_rass.json tests/fixtures/observation_nrs.json \
  -version 4.0.1 \
  -ig de.medizininformatikinitiative.kerndatensatz.icu#2027.0.0-ballot.3 \
  -tx n/a
```

The first run downloads the packages listed in `validation/packages.txt` into `validation/fhir-home/` (about 1.2 GB,
ignored by git).
Later runs work without network. To check this on Linux, put `unshare -rn` in front of the command.

- `-Duser.home` keeps the package cache in the repository instead of `~/.fhir`.
- `-tx n/a` turns off the terminology server, so codes are not checked against value sets. We have no SNOMED CT licence.
- `2027.0.0-ballot.3` is the only published version of the MII ICU module that contains the score profiles of the
  fixtures.
- Loading takes about 40 seconds and up to 7 GB of memory.

Expected result: RASS passes. NRS fails with slicing errors on `Observation.code.coding`, which come from the profile,
not from the data.

To compare your package cache with the list:

```bash
diff validation/packages.txt <(ls validation/fhir-home/.fhir/packages | grep -v '^packages.ini$' | sort)
```

## Mapping

`src/fhir_prototype/icu_mapping.json` assigns an i2b2 `concept_cd` to each FHIR
profile (plus the device category for ventilation parameters). The file is a
JSON list of objects. The code only applies this file, so a mapping decision is
a change in the JSON file and not in the code. The `status` field shows how
settled an entry is:

| Status          | Meaning                              |
|-----------------|--------------------------------------|
| `vorgeschlagen` | proposed, no open question           |
| `vorläufig`     | provisional concept, to be confirmed |
| `offen`         | open question, see `open_question`   |

Entries with an empty `concept_cd` end up in `unmapped.csv`.

## Test data

All bundles in `tests/fixtures/` are **synthetic**. They contain no real
patient data. Each bundle holds one patient with one ICU encounter and
observations based on the MII ICU module and ISiK profiles.

| File                | Content                                              |
|---------------------|------------------------------------------------------|
| `bundle_min.json`   | 68 resources, minimal example                        |
| `bundle_max_1.json` | 248 resources, finished encounter                    |
| `bundle_max_2.json` | 248 resources, ongoing encounter, spans a DST change |

Do not add real patient data to this repository.