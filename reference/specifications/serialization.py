"""Validated immutable in-memory artifacts; not an ingestion executor."""
from dataclasses import dataclass

from .canonical import canonical_bytes, loads, require, ContractError
from .artifacts import validate_enrichment, validate_manifest
from .values import validate_assertion, validate_unit_registry


VALIDATORS = {
    'rigarchive.full_specifications_enrichment.v1': validate_enrichment,
    'rigarchive.full_specifications_publication_manifest.v1': validate_manifest,
    'rigarchive.specification_assertion.v1': validate_assertion,
}


def serialize_artifact(payload, **inputs):
    require(type(payload) is dict, 'Artifact object required')
    validator = VALIDATORS.get(payload.get('artifact_type'))
    require(validator is not None, 'Unsupported W2 artifact type; legacy belongs to its original reader')
    validator(payload, **inputs)
    return canonical_bytes(payload)


def deserialize_artifact(raw, **inputs):
    payload = loads(raw)
    serialize_artifact(payload, **inputs)
    return FrozenArtifact(canonical_bytes(payload))


@dataclass(frozen=True)
class FrozenArtifact:
    """Canonical byte snapshot; callers only receive detached dictionaries."""
    _bytes: bytes

    def __post_init__(self):
        require(type(self._bytes) is bytes, 'Immutable artifact bytes required')
        payload = loads(self._bytes)
        require(canonical_bytes(payload) == self._bytes, 'Noncanonical snapshot bytes')

    def to_dict(self):
        return loads(self._bytes)

    def to_bytes(self):
        return self._bytes


def serialize_catalogue(payload, records, registry, **inputs):
    from .catalogue import validate_snapshot
    validate_snapshot(payload, records, validate_unit_registry(registry), **inputs)
    return canonical_bytes(payload)


def deserialize_catalogue(raw, records, registry, **inputs):
    payload = loads(raw)
    return FrozenArtifact(serialize_catalogue(payload, records, registry, **inputs))
