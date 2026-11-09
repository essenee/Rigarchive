# Configurator default trim selection

Created: 2026-11-08
Status: Complete
Completed: 2026-11-08

The public generation configurator uses `AUTO_SELECT_TRIM_THRESHOLD = 10` in
`reference/services.py`. After resolving explicit URL filters, a selected model
year with more than 10 active configurations defaults to its first displayed trim.
The existing selected-trim context drives both styling and third-column choices.
Valid explicit trims (including unnamed trims) and exact configuration links take
precedence. Invalid/stale parameters, all-years views and small lists retain their
existing behavior. No template or JavaScript changes are needed.

Verification with `.venv/bin/python` and `RIGARCHIVE_TEST_DB_PATH=:memory:`:

- `manage.py test reference.tests.test_experimental_hub --noinput`: 44 passed.
- `manage.py check`: passed.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- Coverage includes 10/11, 20 and 49 configurations, display ordering, explicit
  trim selection, native-link switching, exact deep links, unnamed trims, stale
  parameters and active selected-year scope.

The unchanged JavaScript suite was not rerun because Node is unavailable. Tests
use isolated resources; no development database operations, migrations, ingestion,
canonical updates, commits or pushes were performed. The owner's clarified 10/11
boundary supersedes the original conflicting 20/21 test request. No architectural
or schema changes were required.
