# RA-013 — Public Source Acquisition Adapters Implementation

## Purpose

Implement the initial controlled public source acquisition adapters for NHTSA vPIC and EPA FuelEconomy.gov REST web services, translating external source payloads into valid Tier 1 `SourceAssertionSet` artifacts while preserving source provenance and raw factual assertions without candidate normalization or canonical import.

## Governing Architecture

Governed by the approved [RA-010 Source Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md) and [RA-011 Ingestion Serialization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md).

## Official Source Documentation Reviewed

1. **NHTSA vPIC REST API**:
   * *Endpoint*: `https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMakeYear/make/{make}/modelyear/{year}?format=json`
   * *Contract*: Returns JSON envelope with `Count`, `Message`, `SearchCriteria`, and `Results` array containing `Make_ID`, `Make_Name`, `Model_ID`, `Model_Name`.
   * *Access*: Public REST web service payload requiring no API key or authentication for the selected endpoint during RA-013. Broader legal/source-use status was not independently adjudicated by RA-013.
2. **EPA / FuelEconomy.gov REST Web Services**:
   * *Endpoint*: `https://www.fueleconomy.gov/ws/rest/vehicle/{vehicle_id}`
   * *Contract*: Returns JSON vehicle payload containing `id`, `year`, `make`, `model`, `drive`, `displ`, `cyl`, `trany`, `vClass`, `city08`, `highway08`. Maps `city08` → `city_mpg_epa_rating` and `highway08` → `highway_mpg_epa_rating`.
   * *Access*: Public REST web service payload requiring no API key or authentication for the selected endpoint during RA-013. Broader legal/source-use status was not independently adjudicated by RA-013.


## Implementation Design & Module Placement

The Python acquisition package is organized under `reference/ingestion/acquisition/`:

```text
reference/ingestion/acquisition/
├── __init__.py         # Package public API exports
├── base.py             # BaseSourceAdapter, TransportCallable, default_http_transport, exception hierarchy
├── nhtsa.py            # NHTSAAdapter (vPIC REST API client)
├── epa.py              # EPAAdapter (FuelEconomy.gov REST API client)
└── smoke_test.py       # Live manual smoke testing utilities (isolated from offline unit tests)
```

* **Transport Isolation & Security**: `default_http_transport` uses standard library `urllib.request` with finite timeouts, custom User-Agent headers, and strict TLS certificate verification (`ssl.create_default_context()`). Hostname and certificate-chain validation remain 100% enabled for all requests. Unit tests use injectable transport callables loading test fixtures, ensuring `python manage.py test` is 100% offline.
* **Dependencies**: Uses strictly Python standard library (`urllib.request`, `ssl`, `json`, `datetime`, `pathlib`). Zero third-party HTTP dependencies added.

## Scope

### Included
* Implement `BaseSourceAdapter` abstract base class and exception hierarchy (`AcquisitionError`, `TransportError`, `SourceParseError`).
* Implement `NHTSAAdapter` converting NHTSA `GetModelsForMakeYear` response items into Tier 1 `SourceAssertionSet` artifacts.
* Implement `EPAAdapter` converting EPA `vehicle/{id}` response payloads into Tier 1 `SourceAssertionSet` artifacts.
* Implement 2 test-owned response fixtures under `reference/tests/fixtures/acquisition/`:
  1. `nhtsa/get_models_toyota_2020.json`
  2. `epa/vehicle_42101.json`
* Implement 8 automated test methods in `reference/tests/test_acquisition_adapters.py` verifying request construction, response parsing, assertion extraction, provenance, transport error handling, malformed JSON handling, and contract validation via RA-012 `validate_artifact`.
* Implement bounded live smoke test helper functions in `reference/ingestion/acquisition/smoke_test.py`.
* Update `docs/implementation/CURRENT_STATE.md` and `CHANGELOG.md`.

### Not Included
* Candidate normalization or `CandidateConfigurationDocument` generation.
* Cross-source reconciliation or conflict resolution.
* Canonical Reference matching, deduplication, or `VehicleDefinition` writes.
* Django ORM staging models or migrations.
* Production ingestion storage directories on disk.
* Commercial-source adapters (J.D. Power, Toyota scraping).

## Completion Record

Status: Completed

Completion date: 2026-08-15

Files created:
- `reference/ingestion/acquisition/__init__.py`
- `reference/ingestion/acquisition/base.py`
- `reference/ingestion/acquisition/nhtsa.py`
- `reference/ingestion/acquisition/epa.py`
- `reference/ingestion/acquisition/smoke_test.py`
- `reference/tests/fixtures/acquisition/nhtsa/get_models_toyota_2020.json`
- `reference/tests/fixtures/acquisition/epa/vehicle_42101.json`
- `reference/tests/test_acquisition_adapters.py`
- `docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md`

Files modified:
- `reference/ingestion/__init__.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (acquisition tooling uses pure Python data structures without Django ORM models).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 58 tests in 3.371s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean status on pre-existing tracked files.
- `Live Smoke Test`: Passed (NHTSA returned 4 assertions for 2020 Toyota 4Runner; EPA returned 9 assertions for vehicle ID 42101).

