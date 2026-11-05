"""W2 canonical JSON primitives. No Django, storage writes, or legacy reserialization."""
import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID


class ContractError(ValueError):
    """Closed contract, evidence binding or evaluation limit violation."""


def require(ok, message):
    if not ok:
        raise ContractError(message)


def json_tree(value):
    if value is None or type(value) in (str, bool, int):
        if isinstance(value, str):
            try:
                value.encode('utf-8')
            except UnicodeError as exc:
                raise ContractError('Invalid Unicode') from exc
        return
    if type(value) is list:
        for item in value:
            json_tree(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, 'JSON object keys must be strings')
            json_tree(key)
            json_tree(item)
        return
    raise ContractError('New W2 JSON permits no floats or non-JSON objects')


def canonical_bytes(value):
    try:
        json_tree(value)
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, RecursionError) as exc:
        raise ContractError(str(exc)) from exc


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical_bytes(value)).hexdigest()


def content_hash(value, field='content_hash'):
    return digest({k: v for k, v in value.items() if k != field})


def verify_hash(value, field='content_hash'):
    hash_string(value.get(field))
    require(value[field] == content_hash(value, field), f'{field} mismatch')


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    def reject(value):
        raise ContractError(f'Unsupported JSON number: {value}')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_float=reject, parse_constant=reject)
        json_tree(value)
        return value
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError(str(exc)) from exc


def obj(value, fields):
    require(type(value) is dict and set(value) == set(fields), f'Expected exact keys: {sorted(fields)}')
    for key, validator in fields.items():
        validator(value[key])


def string(value):
    require(type(value) is str, 'Expected string')
    json_tree(value)


def text(value):
    string(value)
    require(bool(value), 'Expected nonempty text')


def integer(value):
    require(type(value) is int, 'Expected integer, not Boolean')


def positive(value):
    integer(value)
    require(value > 0, 'Expected positive integer')


def boolean(value):
    require(type(value) is bool, 'Expected Boolean')


def enum(*values):
    def check(value):
        require(type(value) is str and value in values, f'Expected enum {values}')
    return check


def nullable(check):
    return lambda value: None if value is None else check(value)


def array(check, minimum=0, maximum=None, key=None, ordered=False):
    def validate(values):
        require(type(values) is list and len(values) >= minimum, 'Invalid array')
        require(maximum is None or len(values) <= maximum, 'Array limit exceeded')
        for value in values:
            check(value)
        if key is not None:
            keys = [key(v) for v in values]
            require(len(set(keys)) == len(keys), 'Duplicate array identity')
            if ordered:
                require(keys == sorted(keys), 'Noncanonical array order')
    return validate


def uuid(value):
    string(value)
    try:
        require(str(UUID(value)) == value, 'Noncanonical UUID')
    except ValueError as exc:
        raise ContractError('Invalid UUID') from exc


def hash_string(value):
    require(type(value) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', value) is not None, 'Invalid SHA-256')


def token(value):
    require(type(value) is str and len(value) <= 128 and re.fullmatch(r'[a-z0-9]+(?:[-._][a-z0-9]+)*', value) is not None, 'Invalid controlled token')


def decimal_string(value):
    require(type(value) is str and re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?', value) is not None and value != '-0', 'Noncanonical decimal string')


def normalize_decimal(source):
    """Producer utility only: preserve source separately; never coerce binary floats."""
    text(source)
    try:
        value = Decimal(source)
        require(value.is_finite(), 'Nonfinite decimal')
        result = format(value, 'f')
        if '.' in result:
            result = result.rstrip('0').rstrip('.')
        if value == 0:
            result = '0'
        decimal_string(result)
        return result
    except ArithmeticError as exc:
        raise ContractError('Invalid source decimal') from exc


def iso_date(value):
    string(value)
    try:
        require(date.fromisoformat(value).isoformat() == value, 'Noncanonical date')
    except ValueError as exc:
        raise ContractError('Invalid date') from exc


def utc_time(value):
    string(value)
    try:
        parsed = datetime.fromisoformat(value)
        require(value.endswith('+00:00') and parsed.utcoffset() == timezone.utc.utcoffset(parsed), 'Expected UTC +00:00')
        require(parsed.isoformat() == value, 'Noncanonical timestamp')
    except ValueError as exc:
        raise ContractError('Invalid timestamp') from exc


MARKET = enum('US', 'CA', 'OT')
DRIVETRAIN = enum('2WD', '4WD', 'AWD', 'UNK')


def year(value):
    integer(value)
    require(1886 <= value <= 2100, 'Unsupported model year')
