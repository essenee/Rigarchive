"""Desktop OAuth adapter and guarded draft publication for Google Sheets."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from django.core.management.base import CommandError


SCOPE = "https://www.googleapis.com/auth/drive.file"
FILE_ID = re.compile(r"[A-Za-z0-9_-]{1,200}")
FIELDS = (
    "spreadsheetId,properties(title),sheets(properties,protectedRanges,merges,basicFilter,"
    "filterViews,charts,data(startRow,startColumn,columnMetadata(pixelSize),"
    "rowMetadata(pixelSize),rowData(values(userEnteredValue,userEnteredFormat,note,dataValidation,textFormatRuns)))"
    ")"
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def write_private(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def registry_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def read_registry(path, key, *, allow_pending=False):
    try:
        state = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise CommandError("Publication registry is unreadable; restore the trusted registry.") from exc
    if not isinstance(state, dict) or state.get("schema") != 1 or state.get("generation") != key:
        raise CommandError("Wrong or invalid publication registry; restore it from a trusted backup.")
    if state.get("mode") != "draft":
        raise CommandError("Protected or unsupported publication registry.")
    spreadsheet_id, prior = state.get("spreadsheet"), state.get("sheets")
    if allow_pending and "spreadsheet" in state and spreadsheet_id is None and prior == {}:
        if "release_audit" in state:
            check_release_audit(path, state)
        return state
    if "release_audit" in state:
        raise CommandError("Released reservation requires a separate --publish --initialize command.")
    if (not isinstance(spreadsheet_id, str) or not FILE_ID.fullmatch(spreadsheet_id)
            or not isinstance(prior, dict) or any(
                not isinstance(name, str) or not isinstance(pin, dict)
                or type(pin.get("id")) is not int or pin["id"] < 0
                or not isinstance(pin.get("fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", pin["fingerprint"])
                or type(pin.get("rows")) is not int or pin["rows"] < 0
                or type(pin.get("columns")) is not int or pin["columns"] < 0
                for name, pin in prior.items()
            ) or len({pin["id"] for pin in prior.values()}) != len(prior)):
        raise CommandError("Incomplete or invalid registry. Restore it or reconcile the known spreadsheet ID.")
    return state


def connect(directory, *, authorize=False, persist=True):
    token = directory / "token.json"
    client = directory / "credentials.json"
    if not token.is_file() and not authorize:
        raise CommandError("Google token missing. Run the command with --authorize after desktop OAuth setup.")
    if authorize and not client.is_file():
        raise CommandError("Desktop OAuth credentials.json is missing from the Google state directory.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise CommandError("Install the optional Google client packages from requirements-configuration-logic.txt.") from None
    try:
        if authorize:
            flow = InstalledAppFlow.from_client_secrets_file(str(client), [SCOPE])
            credentials = flow.run_local_server(port=0, authorization_prompt_message="",
                                                access_type="offline", prompt="consent")
        else:
            saved = json.loads(token.read_text())
            saved_scopes = saved.get("scopes")
            if not isinstance(saved_scopes, list) or SCOPE not in saved_scopes:
                raise CommandError("Saved Google token lacks drive.file scope metadata. Run --authorize to grant per-file access.")
            credentials = Credentials.from_authorized_user_info(saved, [SCOPE])
            if not credentials.valid and credentials.refresh_token:
                credentials.refresh(Request())
        granted = credentials.granted_scopes
        if granted is not None and SCOPE not in granted:
            raise CommandError("Google did not grant drive.file access. Run --authorize and grant the requested scope.")
        if not credentials.valid or not credentials.refresh_token or not credentials.has_scopes([SCOPE]):
            raise ValueError("Invalid authorization")
        if persist and (authorize or credentials.to_json() != token.read_text()):
            write_private(token, credentials.to_json())
        return build("sheets", "v4", credentials=credentials, cache_discovery=False).spreadsheets()
    except CommandError:
        raise
    except Exception:
        # OAuth and HTTP errors can include credential material.
        raise CommandError("Google authorization failed. Check the OAuth client, test-user access and consent, then retry --authorize.") from None


SCOPE_ERRORS = {"ACCESS_TOKEN_SCOPE_INSUFFICIENT", "insufficientPermissions"}
SERVICE_ERRORS = {"SERVICE_DISABLED", "accessNotConfigured"}
POLICY_ERRORS = {"ORG_RESTRICTION_VIOLATION", "domainPolicy", "appNotAuthorizedToFile",
                 "PERMISSION_DENIED", "forbidden", "insufficientFilePermissions", "notFound"}
AUTH_ERRORS = {"UNAUTHENTICATED", "authError", "invalidCredentials"}
SAFE_REASONS = SCOPE_ERRORS | SERVICE_ERRORS | POLICY_ERRORS | AUTH_ERRORS | {
    "RATE_LIMIT_EXCEEDED", "rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded",
    "RESOURCE_EXHAUSTED", "CONSUMER_INVALID", "billingNotEnabled", "INVALID_ARGUMENT",
    "FAILED_PRECONDITION", "badRequest", "NOT_FOUND", "INTERNAL", "UNAVAILABLE",
}


def google_reason(exc):
    """Expose recognized machine reason codes only, never Google messages or metadata."""
    raw = getattr(exc, "content", None)
    if not isinstance(raw, (str, bytes)):
        return None
    try:
        error = json.loads(raw)["error"]
    except (ValueError, KeyError, TypeError):
        return None
    if isinstance(error, dict):
        for field in ("details", "errors"):
            entries = error.get(field)
            if isinstance(entries, list):
                for entry in entries:
                    reason = entry.get("reason") if isinstance(entry, dict) else None
                    if isinstance(reason, str) and reason in SAFE_REASONS:
                        return reason
        status = error.get("status")
        if isinstance(status, str) and status in SAFE_REASONS:
            return status
    return None


def api_call(operation, method, **kwargs):
    try:
        return method(**kwargs).execute(num_retries=0)
    except Exception as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        status = status if type(status) is int and 100 <= status <= 599 else None
        reason = google_reason(exc)
        if reason in SCOPE_ERRORS:
            action = "Run --authorize and grant drive.file access."
        elif reason in SERVICE_ERRORS:
            action = "Enable the Google Sheets API in the desktop OAuth client's Google Cloud project."
        elif status == 401 or reason in AUTH_ERRORS:
            action = "Run --authorize with the intended Google account."
        elif status in (403, 404) and operation == "spreadsheets.create":
            action = "Check the OAuth client's Cloud project and whether the account or organization permits spreadsheet creation."
        elif status in (403, 404):
            action = "Verify that the OAuth app and account have access to the registered spreadsheet."
        else:
            action = "Inspect the Google project or known spreadsheet before retrying."
        summary = f"HTTP {status}" if status else "no HTTP status"
        if reason:
            summary += f", {reason}"
        if operation == "spreadsheets.create":
            action += " Preserve the creation reservation and check Drive before retrying."
        raise CommandError(f"Google request failed during Sheets {operation} ({summary}). {action}") from None


def entered(value):
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, bool):
        return {"boolValue": value}
    return {"numberValue": value}


def desired_values(table):
    return {(r, c): entered(value) for r, row in enumerate(table.rows)
            for c, value in enumerate(row) if entered(value)}


def remote_values(sheet):
    values = {}
    for block in sheet.get("data", ()):
        for i, row in enumerate(block.get("rowData", ())):
            for j, cell in enumerate(row.get("values", ())):
                value = cell.get("userEnteredValue")
                if value:
                    values[(block.get("startRow", 0) + i, block.get("startColumn", 0) + j)] = value
    return values


def fingerprint(sheet):
    # The API field mask excludes calculated cell values.
    return digest(sheet)


def read_remote(api, spreadsheet_id, title):
    response = api_call("spreadsheets.get", api.get, spreadsheetId=spreadsheet_id, includeGridData=True, fields=FIELDS)
    if response.get("spreadsheetId") != spreadsheet_id or response.get("properties", {}).get("title") != title:
        raise CommandError("Registered spreadsheet identity or title differs. Publication stopped.")
    sheets = response.get("sheets", [])
    if not sheets or any(s["properties"].get("sheetType", "GRID") != "GRID" for s in sheets):
        raise CommandError("Spreadsheet has missing or unsupported worksheets.")
    return {s["properties"]["title"]: s for s in sheets}


def create(api, draft, path):
    # Persist intent before the remote request. An ambiguous response cannot lead to a second create.
    state = dict(schema=1, generation=draft.key, mode="draft", spreadsheet=None, sheets={})
    write_private(path, json.dumps(state))
    result = api_call("spreadsheets.create", api.create, body={"properties": {"title": draft.title}, "sheets": [
        {"properties": {"title": table.name, "sheetId": index + 1}}
        for index, table in enumerate(draft.sheets)
    ]}, fields="spreadsheetId")
    spreadsheet_id = result.get("spreadsheetId")
    if not isinstance(spreadsheet_id, str) or not FILE_ID.fullmatch(spreadsheet_id):
        raise CommandError("Google did not return a valid spreadsheet ID. Keep the registry and reconcile.")
    state["spreadsheet"] = spreadsheet_id
    write_private(path, json.dumps(state))
    return state


def check_managed(remote, prior, expected):
    if set(remote) - expected or set(prior) - set(remote):
        raise CommandError("Unexpected or removed worksheets. Restore the trusted tabs or reconcile manually.")
    for name, sheet in remote.items():
        if sheet.get("protectedRanges"):
            raise CommandError(f"Protected worksheet {name}; publication stopped.")
        pin = prior.get(name)
        if pin:
            if pin["id"] != sheet["properties"]["sheetId"] or pin["fingerprint"] != fingerprint(sheet):
                raise CommandError(f"Unexpected external change in {name}; publication stopped.")
        elif (remote_values(sheet) or sheet.get("merges") or sheet.get("basicFilter")
              or sheet.get("filterViews") or sheet.get("charts") or any(
                  cell for block in sheet.get("data", ()) for row in block.get("rowData", ())
                  for cell in row.get("values", ())
              )):
            raise CommandError(f"{name} is populated or formatted without a trusted fingerprint.")


def sheet_requests(table, sheet_id, sheet, previous, index):
    rows = len(table.rows)
    columns = len(table.widths)
    old_rows = previous["rows"] if previous else 0
    old_columns = previous["columns"] if previous else 0
    grid = sheet["properties"].get("gridProperties", {}) if sheet else {}
    properties = {"sheetId": sheet_id, "gridProperties": {
        "rowCount": max(rows, grid.get("rowCount", 0), 100),
        "columnCount": max(columns, grid.get("columnCount", 0), 26),
        "frozenRowCount": 4,
        "hideGridlines": True,
    }}
    managed = {"sheetId": sheet_id, "endRowIndex": max(rows, old_rows), "endColumnIndex": max(columns, old_columns)}
    requests = []
    if sheet is None:
        requests.append({"addSheet": {"properties": {**properties, "title": table.name, "index": index}}})
    else:
        requests.append({"updateSheetProperties": {"properties": properties, "fields": "gridProperties"}})
    requests.append({"updateCells": {
        "range": managed,
        "rows": [{"values": [{"userEnteredValue": item} if (item := entered(value)) else {}
                             for value in row]} for row in table.rows],
        "fields": "userEnteredValue",
    }})
    header = {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4, "endColumnIndex": columns}
    requests.append({"repeatCell": {"range": header, "cell": {"userEnteredFormat": {
        "backgroundColor": {"red": 0.14, "green": 0.27, "blue": 0.36},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "wrapStrategy": "WRAP",
    }}, "fields": "userEnteredFormat"}})
    requests.append({"setBasicFilter": {"filter": {"range": {
        **header, "endRowIndex": rows,
    }}}})
    if rows > 4:
        for col in table.prices:
            requests.append({"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": rows,
                          "startColumnIndex": col, "endColumnIndex": col + 1},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat",
            }})
    for col, width in enumerate(table.widths):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + 1},
            "properties": {"pixelSize": width * 8}, "fields": "pixelSize",
        }})
    return requests


def publish(api, draft, path, state, *, dry_run=False, allow_shrink=False):
    spreadsheet_id = state["spreadsheet"]
    remote = read_remote(api, spreadsheet_id, draft.title)
    prior = state["sheets"]
    expected = {s.name for s in draft.sheets}
    check_managed(remote, prior, expected)
    if set(prior) - expected:
        raise CommandError("The draft omits an existing managed worksheet; tabs are never deleted.")
    ids = {name: s["properties"]["sheetId"] for name, s in remote.items()}
    next_id = max(ids.values(), default=0) + 1
    requests, actions = [], []
    for index, table in enumerate(draft.sheets):
        sheet = remote.get(table.name)
        previous = prior.get(table.name)
        if previous and (len(table.rows) < previous["rows"] or len(table.widths) < previous["columns"]) and not allow_shrink:
            raise CommandError(f"{table.name} would clear published cells. Review the draft and use --allow-shrink.")
        if sheet is None:
            ids[table.name] = next_id
            next_id += 1
        if sheet is None or not previous or remote_values(sheet) != desired_values(table):
            actions.append(f"{'Create' if sheet is None else 'Update'} {table.name}")
            requests.extend(sheet_requests(table, ids[table.name], sheet, previous, index))
        if sheet is None or sheet["properties"].get("index", 0) != index:
            actions.append(f"Order {table.name} at position {index + 1}")
    if any(action.startswith("Order ") for action in actions):
        # Move each sheet to the front in reverse order (index semantics are pre-move).
        for table in reversed(draft.sheets):
            requests.append({"updateSheetProperties": {
                "properties": {"sheetId": ids[table.name], "index": 0}, "fields": "index",
            }})
    if dry_run or not requests:
        return actions
    if read_remote(api, spreadsheet_id, draft.title) != remote:
        raise CommandError("Spreadsheet changed while planning. Publication stopped.")
    api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=spreadsheet_id, body={"requests": requests})
    result = read_remote(api, spreadsheet_id, draft.title)
    if set(result) != expected or any(
        result[table.name]["properties"].get("sheetId") != ids[table.name]
        or result[table.name]["properties"].get("index", 0) != index
        or result[table.name].get("protectedRanges")
        or result[table.name]["properties"].get("gridProperties", {}).get("frozenRowCount") != 4
        or not result[table.name].get("basicFilter")
        or remote_values(result[table.name]) != desired_values(table)
        for index, table in enumerate(draft.sheets)
    ):
        raise CommandError("Google post-write verification failed; publication fingerprints were not advanced.")
    state["sheets"] = {
        table.name: {"id": ids[table.name], "rows": len(table.rows), "columns": len(table.widths),
                     "fingerprint": fingerprint(result[table.name])}
        for table in draft.sheets
    }
    write_private(path, json.dumps(state, indent=2))
    return actions


RECOVERY_CAUTION = "A manual Drive search cannot guarantee that no matching spreadsheet exists."


def record_recovery(path, draft, previous, decision, spreadsheet_id=None):
    name = f"{path.stem}-{uuid4().hex}.json"
    record = {
        "generation": draft.key, "title": draft.title, "decision": decision,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "previous_reservation": previous, "spreadsheet": spreadsheet_id,
    }
    write_private(path.parent / "recovery-audit" / name, json.dumps(record, indent=2))
    return name


def check_release_audit(path, state):
    name = state["release_audit"]
    if not isinstance(name, str) or not re.fullmatch(rf"{re.escape(path.stem)}-[0-9a-f]{{32}}\.json", name):
        raise CommandError("Invalid release audit reference; preserve the reservation and reconcile.")
    try:
        audit = json.loads((path.parent / "recovery-audit" / name).read_text())
    except (OSError, ValueError) as exc:
        raise CommandError("Release audit is unavailable; preserve the reservation and reconcile.") from exc
    previous = {key: value for key, value in state.items() if key != "release_audit"}
    if (not isinstance(audit, dict) or audit.get("decision") != "owner-confirmed-no-spreadsheet"
            or audit.get("generation") != state["generation"] or audit.get("previous_reservation") != previous):
        raise CommandError("Release audit does not match this reservation; reconcile before creating.")


def release_reservation(draft, path, *, authorized=False):
    if not authorized:
        raise CommandError("Release requires --confirm-recovery after checking Drive.")
    state = read_registry(path, draft.key, allow_pending=True)
    if not state or state["spreadsheet"] is not None or "release_audit" in state:
        raise CommandError("Release requires an unreleased creation reservation without a spreadsheet ID.")
    audit = record_recovery(path, draft, state, "owner-confirmed-no-spreadsheet")
    write_private(path, json.dumps({**state, "release_audit": audit}, indent=2))
    return audit


def recover_registry(api, draft, path, spreadsheet_id, *, authorized=False):
    """Verify a known remote draft, then update only its local registry."""
    if not authorized:
        raise CommandError("Adoption requires --confirm-recovery and the exact spreadsheet ID.")
    if not FILE_ID.fullmatch(spreadsheet_id):
        raise CommandError("Supply the exact spreadsheet ID from its Google Sheets URL.")
    previous = read_registry(path, draft.key, allow_pending=True)
    if previous and previous["sheets"]:
        raise CommandError("Trusted fingerprints already exist; recovery cannot replace them.")
    if previous and previous["spreadsheet"] not in (None, spreadsheet_id):
        raise CommandError("Recovery ID differs from the recorded spreadsheet.")
    remote = read_remote(api, spreadsheet_id, draft.title)
    if set(remote) != {table.name for table in draft.sheets} or any(
        remote[table.name]["properties"].get("index", 0) != index
        for index, table in enumerate(draft.sheets)
    ):
        raise CommandError("Recovery requires the exact expected worksheet names and order.")
    exact = all(remote_values(remote[table.name]) == desired_values(table) for table in draft.sheets)
    if exact:
        if any(sheet.get("protectedRanges") for sheet in remote.values()):
            raise CommandError("Recovery requires an unprotected, exact copy of the current draft.")
    else:
        # Reuse the publisher's strict pristine-tab checks. Partial drafts and manual edits are refused.
        check_managed(remote, {}, {table.name for table in draft.sheets})
    if not exact and previous and previous["spreadsheet"] == spreadsheet_id:
        return False
    state = dict(schema=1, generation=draft.key, mode="draft", spreadsheet=spreadsheet_id, sheets={})
    if exact:
        state["sheets"] = {
            table.name: {"id": remote[table.name]["properties"]["sheetId"], "rows": len(table.rows),
                         "columns": len(table.widths), "fingerprint": fingerprint(remote[table.name])}
            for table in draft.sheets
        }
    record_recovery(path, draft, previous, "adopt-exact-draft" if exact else "adopt-empty-spreadsheet", spreadsheet_id)
    write_private(path, json.dumps(state, indent=2))
    return exact
