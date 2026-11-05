"""W2 B1 pure contracts. No ORM, acquisition, publication, receipts or UI.

Values/predicates can be validated independently. Enrichment validation requires
explicit retained byte inputs and exact referenced records; no latest lookup or
filesystem reads are performed. State/replay checks consume caller snapshots and
do not authenticate a reviewer, grant authorization, or execute an import.
"""
from .canonical import ContractError, canonical_bytes, content_hash, digest, normalize_decimal
from .artifacts import validate_enrichment, validate_manifest, publication_disposition, PublicationState
from .serialization import serialize_artifact, deserialize_artifact, serialize_catalogue, deserialize_catalogue

__all__ = [
    'ContractError', 'canonical_bytes', 'content_hash', 'digest', 'normalize_decimal',
    'validate_enrichment', 'validate_manifest', 'publication_disposition', 'PublicationState',
    'serialize_artifact', 'deserialize_artifact', 'serialize_catalogue', 'deserialize_catalogue',
]
