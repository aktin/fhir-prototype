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

The first run downloads the package given with `-ig`, its dependencies and the FHIR base packages into
`validation/fhir-home/` (about 1.2 GB, ignored by git). The validator does not read `validation/packages.txt`. This file
only lists the resulting packages, so that you can compare your cache with it (see below).
Later runs work without network. To check this, turn off the network and run the command again. Offline, the validator prints `Error fetching ...` for `hl7.terminology` and `hl7.fhir.uv.extensions`. It then uses
the cached packages, so these messages can be ignored.

- `-Duser.home` keeps the package cache in the repository instead of `~/.fhir`.
- `-tx n/a` turns off the terminology server, so codes are not checked against value sets. We have no SNOMED CT licence.
- `2027.0.0-ballot.3` is the only published version of the MII ICU module that contains the score profiles of the
  fixtures.
- Loading takes about 40 seconds and about 1 GB of memory.

Expected result: RASS passes. NRS fails with slicing errors on `Observation.code.coding`, which come from the profile,
not from the data.

To compare your package cache with the list:

```bash
diff validation/packages.txt <(ls validation/fhir-home/.fhir/packages | grep -v '^packages.ini$' | sort)
```

### Minimal profile folder

Most of the package cache is never used, because we only validate the profiles in `icu_mapping.json`. This command
reads the profile URLs from the mapping and collects them from the filled package cache, together with their parent
profiles, extensions, value sets and code systems:

```bash
uv run python -m fhir_prototype.profile_set
```

It writes the resources as JSON files into `validation/profiles/` (about 5 MB, ignored by git) and lists the mapping
profiles that are not in the MII ICU release, and the referenced resources that are in none of the packages.

Validate with the folder instead of the ICU package:

```bash
java -Duser.home="$PWD/validation/fhir-home" -jar validation/validator_cli.jar \
  tests/fixtures/observation_rass.json tests/fixtures/observation_nrs.json \
  -version 4.0.1 \
  -ig validation/profiles \
  -tx n/a
```

The result is the same as with the ICU package. With `-version 4.0.1` the validator still loads the FHIR core,
terminology and extension packages on its own, so the package cache must keep them. They are listed in
`VALIDATOR_PACKAGES` in `src/fhir_prototype/profile_set.py` (about 300 MB). A machine that only validates needs these
packages and the folder, not the whole cache.

### Validate bundles in the pipeline

`HapiValidator` in `src/fhir_prototype/validation.py` runs the validator for each bundle. It needs Java, the jar, the
filled package cache and the minimal profile folder from the steps above:

```bash
uv run python -c "
from pathlib import Path
from fhir_prototype.importer import CsvImporter
from fhir_prototype.mapping import load_mapping
from fhir_prototype.pipeline import run
from fhir_prototype.validation import HapiValidator

validator = HapiValidator(
    profiles={entry['profile'] for entry in load_mapping()},
    java='java',
    jar=Path('validation/validator_cli.jar'),
    ig=Path('validation/profiles'),
    fhir_home=Path.cwd() / 'validation/fhir-home',
)
run('delivery.zip', CsvImporter('output'), validator)
"
```

- Only the Patient, the Encounter and the resources whose `meta.profile` is in the mapping are validated. Other
  resources are left out and logged as ignored. Patient and Encounter are validated against FHIR R4 core.
- A bundle is invalid if the validator reports at least one issue with severity `fatal` or `error`. Errors and
  warnings are logged, information messages are not. Codes that cannot be checked without a terminology server, for
  example SNOMED CT, only give warnings or information messages.
- The constructor raises `FileNotFoundError` if Java or the jar cannot be found.
- One bundle takes about 15 to 20 seconds, most of it for starting Java and loading the packages.

Expected result: all three bundles in `tests/fixtures/` are invalid against `2027.0.0-ballot.3`, so the command above
skips them and ends with `InvalidBundleError: ... no bundle could be processed`. The integration test
in `tests/test_validation.py` runs the validator on `bundle_min.json` and is skipped if Java, the jar, the package
cache or the profile folder is missing.

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

All files in `tests/fixtures/` are **synthetic**. They contain no real
patient data. Each bundle holds one patient with one ICU encounter and
observations based on the MII ICU module and ISiK profiles.

| File                | Content                                              |
|---------------------|------------------------------------------------------|
| `bundle_min.json`   | 68 resources, minimal example                        |
| `bundle_max_1.json` | 248 resources, finished encounter                    |
| `bundle_max_2.json` | 248 resources, ongoing encounter, spans a DST change |
| `observation_rass.json` | RASS observation from `bundle_min.json`, for validation |
| `observation_nrs.json`  | NRS observation from `bundle_min.json`, for validation  |

Do not add real patient data to this repository.