"""ADR-0013 pure sparse identity primitives; no persistence or import authority.

Inputs are reviewed designations, not evidence approval. Scope keys and alias maps
must come from the reviewed registry/workflow; this module never synthesizes them.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from django.core.exceptions import ValidationError

from reference.powertrain import validate_powertrain


BODY_CONTRACT = "factory-body-semantic/2"
BASELINE_CONTRACT = "vehicle-definition-body/2"
DIMENSIONS = frozenset({
    "body_style", "wheelbase_designation", "body_length_designation",
    "roof_height_designation", "door_configuration", "side_door_arrangement",
    "body_code",
})
SCOPE_KEYS = frozenset({"manufacturer_key", "model_key", "generation_key"})
TOKEN = re.compile(r"[a-z0-9]+(?:[-._][a-z0-9]+)*", re.ASCII)
HASH = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def canonical_json(value):
    """Canonical UTF-8 JSON text; callers validate contract shapes first."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Value is not canonical JSON.") from exc


def semantic_digest(preimage):
    """Hash only a validated successor preimage, never historical artifacts."""
    validate_preimage(preimage)
    return "sha256:" + hashlib.sha256(canonical_json(preimage).encode("utf-8")).hexdigest()


def _token(value):
    _require(type(value) is str and len(value) <= 128 and TOKEN.fullmatch(value),
             "Expected a reviewed canonical designation token.")
    return value


def validate_scope(scope):
    _require(type(scope) is dict and set(scope) == SCOPE_KEYS, "Expected exact reviewed Generation scope.")
    for value in scope.values():
        _token(value)


@dataclass(frozen=True)
class ScopedAliases:
    """Caller-supplied reviewed equivalences, scoped to Generation and field.

    Raw source spelling is matched exactly, without automatic text normalization.
    This object does not confer review or canonical write authorization.
    """
    scope: dict
    dimensions: dict


def normalize_dimensions(scope, dimensions, *, aliases=None):
    validate_scope(scope)
    _require(type(dimensions) is dict and set(dimensions) <= DIMENSIONS,
             "Unsupported body dimension.")
    if aliases is not None:
        _require(isinstance(aliases, ScopedAliases), "Expected scoped reviewed aliases.")
        validate_scope(aliases.scope)
        _require(scope == aliases.scope, "Alias registry scope mismatch.")
        _require(type(aliases.dimensions) is dict and set(aliases.dimensions) <= DIMENSIONS - {"body_code"},
                 "Invalid alias registry fields; codes require explicit namespace/token pairs.")
        for mapping in aliases.dimensions.values():
            _require(type(mapping) is dict, "Invalid alias mapping.")
            for raw, token in mapping.items():
                _require(type(raw) is str and bool(raw.strip()), "Empty alias spelling.")
                _token(token)
    result = {}
    for key, value in dimensions.items():
        if value is None or (type(value) is str and not value.strip()):
            continue
        if key == "body_code":
            _require(type(value) is dict and set(value) == {"namespace", "token"},
                     "Identity-bearing body code requires namespace and token.")
            result[key] = {k: _token(v) for k, v in value.items()}
        else:
            if aliases is not None and type(value) is str:
                value = aliases.dimensions.get(key, {}).get(value, value)
            result[key] = _token(value)
    return result


def body_preimage(scope, dimensions, *, aliases=None):
    """Build a nonempty sparse frozen basis; null fields simply disappear."""
    normalized = normalize_dimensions(scope, dimensions, aliases=aliases)
    _require(bool(normalized), "An empty body cannot establish a parent identity.")
    return {"identity_contract": BODY_CONTRACT, "profile_family": "factory-body",
            "scope": dict(scope), "dimensions": normalized}


def baseline_preimage(*, scope, model_year, trim_name, drivetrain, market,
                      canonical_powertrain, body_digest=None, series_digest=None):
    """Structured-engine successor; optional parents do not assert absence findings."""
    validate_scope(scope)
    validate_powertrain(canonical_powertrain, complete=True)
    value = {
        "identity_contract": BASELINE_CONTRACT, "scope": dict(scope),
        "model_year": model_year, "trim_name": trim_name, "drivetrain": drivetrain,
        "market": market, "canonical_powertrain": dict(canonical_powertrain),
        "body_digest": body_digest,
        "series": None if series_digest is None else {"digest": series_digest},
    }
    validate_preimage(value)
    return value


def validate_preimage(value):
    _require(type(value) is dict, "Identity preimage must be an object.")
    contract = value.get("identity_contract")
    if contract == BODY_CONTRACT:
        _require(set(value) == {"identity_contract", "profile_family", "scope", "dimensions"},
                 "Unexpected body preimage fields.")
        _require(value["profile_family"] == "factory-body", "Invalid body family.")
        rebuilt = body_preimage(value["scope"], value["dimensions"])
        _require(rebuilt == value, "Body preimage must omit null dimensions.")
    elif contract == BASELINE_CONTRACT:
        _require(set(value) == {"identity_contract", "scope", "model_year", "trim_name",
                               "drivetrain", "market", "canonical_powertrain", "body_digest", "series"},
                 "Unexpected baseline preimage fields.")
        validate_scope(value["scope"])
        _require(type(value["model_year"]) is int and 1 <= value["model_year"] <= 32767,
                 "Invalid model year.")
        _require(type(value["trim_name"]) is str and bool(value["trim_name"].strip())
                 and len(value["trim_name"]) <= 100, "Invalid canonical trim.")
        _require(value["drivetrain"] in ("2WD", "4WD", "AWD", "UNK"), "Invalid drivetrain.")
        _require(value["market"] in ("US", "CA", "OT"), "Invalid market.")
        validate_powertrain(value["canonical_powertrain"], complete=True)
        if value["body_digest"] is not None:
            _hash(value["body_digest"])
        if value["series"] is not None:
            _require(type(value["series"]) is dict and set(value["series"]) == {"digest"},
                     "Invalid series identity.")
            _hash(value["series"]["digest"])
    else:
        raise ValidationError("Unsupported successor identity contract; historical preimages are not reinterpreted.")


def _hash(value):
    _require(type(value) is str and HASH.fullmatch(value), "Invalid semantic digest.")


@dataclass(frozen=True)
class BodyComparison:
    relation: str
    differing_dimensions: tuple = ()

    @property
    def requires_review(self):
        return self.relation == "conflict"


def compare_bodies(left, right, *, same_configuration=False):
    """Compare frozen bases, not compatibility chains or unspecified wildcards.

    Positive configuration grouping is supplied by the evidence workflow. Different
    known values mean distinct bodies, or conflict if asserted for the SAME grouping.
    """
    for value in (left, right):
        if value is not None:
            validate_preimage(value)
            _require(value["identity_contract"] == BODY_CONTRACT, "Expected body identity.")
    if left is None or right is None:
        return BodyComparison("compatible")
    if left["scope"] != right["scope"]:
        return BodyComparison("conflict" if same_configuration else "distinct", ("scope",))
    differing = tuple(sorted(k for k in left["dimensions"].keys() & right["dimensions"].keys()
                             if left["dimensions"][k] != right["dimensions"][k]))
    if differing:
        return BodyComparison("conflict" if same_configuration else "distinct", differing)
    return BodyComparison("equal" if left == right else "compatible")


@dataclass(frozen=True)
class BodyResolution:
    relation: str
    compatible_digests: tuple = ()

    @property
    def requires_review(self):
        return self.relation == "ambiguous"


def resolve_body_observation(observation, alternatives):
    """Assess the whole supported alternative set, never first-match/union merging.

    A unique compatible result is NOT semantic equality or authorization to attach
    a parent. Known source equivalence/applicability must still support that action.
    """
    if observation is not None:
        compare_bodies(observation, observation)
    matches = set()
    for alternative in alternatives:
        _require(alternative is not None, "Alternatives must be positive supported body identities.")
        comparison = compare_bodies(observation, alternative)
        if comparison.relation in ("equal", "compatible"):
            matches.add(semantic_digest(alternative))
    keys = tuple(sorted(matches))
    if len(keys) > 1:
        return BodyResolution("ambiguous", keys)
    if keys:
        return BodyResolution("uniquely_compatible", keys)
    return BodyResolution("no_body" if observation is None else "distinct_supported_basis")
