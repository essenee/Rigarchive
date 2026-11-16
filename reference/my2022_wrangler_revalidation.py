"""Bounded, read-only MY2022 canonical agreement; never selects a Generation.

The approved manufacturer-based Matrix is the authority, with retained Edmunds
corroboration. This is a new evaluation, not historical proof reconstruction.
No function in this module executes imports or writes a database.
"""
import copy
import json
from datetime import datetime

from django.core.exceptions import ValidationError

from reference.powertrain import BASE_FIELDS, FIELDS, decimal_string, record_powertrain, validate_powertrain
from reference.my2021_wrangler_revalidation import (
    EvidenceUnavailable, byte_hash, digest, identity, metadata, need, retained,
)

PROFILE = 'my2022-approved-matrix-revalidation/1'
MATRIX_DIGEST = 'sha256:e92f9ab6d7b585406e86f697e9cae8400233fc874f4ea884bec718b9148c56cb'
BASIS = 'docs/research/my2022_revalidation_basis_20261116'
MATRIX_SHA = 'sha256:dc2198af761f1087b12cd70016247d231479d31b60a526b56ff4ad436850abc2'
APPROVAL_SHA = 'sha256:cfa305e2754a9bfea82b0ac1b2e4f911b50ed920d12dcbe1133b9e3e7ea44b8c'
SUCCESS = {'EXACT_AGREEMENT', 'NORMALIZED_AGREEMENT'}
TOP_KEYS = {'version', 'original_execution', 'revalidation', 'evidence', 'nonidentity_claim_hashes', 'record_hash'}


def load_basis(root=None):
    from reference.ingestion.matrix import compute_matrix_digest
    from reference.ingestion.matrix_approval import validate_matrix_approval
    raw = retained(BASIS + '/matrix.json', root)
    approval_raw = retained(BASIS + '/approval.json', root)
    need(byte_hash(raw) == MATRIX_SHA and byte_hash(approval_raw) == APPROVAL_SHA,
         'Approved MY2022 basis bytes changed.')
    matrix, approval = json.loads(raw), json.loads(approval_raw)
    validate_matrix_approval(matrix, approval)
    need(compute_matrix_digest(matrix) == MATRIX_DIGEST, 'Incorrect MY2022 Matrix digest.')
    need(matrix['model_years'] == [2022] and matrix['market'] == 'US'
         and len(matrix['rows']) == 55, 'Incorrect MY2022 scope.')
    return matrix


def matching_row(matrix, receipt):
    matches = [row for row in matrix['rows'] if row['target_slug'] == receipt.target_slug
               and row['model_year'] == receipt.target_model_year]
    if not matches:
        raise EvidenceUnavailable('Missing MY2022 Matrix match.')
    need(len(matches) == 1, 'Missing or ambiguous MY2022 Matrix match.')
    return matches[0]


def evaluate(receipt, *, evaluated_at, revision, matrix=None):
    """Compare an existing identity, never plan creates or choose canonical parents."""
    stamp = datetime.fromisoformat(evaluated_at.replace('Z', '+00:00'))
    need(stamp.tzinfo is not None, 'Aware revalidation timestamp required.')
    result = dict(receipt_pk=receipt.pk, receipt_uuid=str(receipt.uuid),
                  profile=PROFILE, evaluator_revision=revision, evaluated_at_utc=evaluated_at,
                  matrix_digest=MATRIX_DIGEST, outcome='EVALUATION_BLOCKED', comparisons={},
                  normalizations=[], issues=[])
    try:
        matrix = load_basis() if matrix is None else matrix
        from reference.ingestion.matrix import compute_matrix_digest
        need(compute_matrix_digest(matrix) == MATRIX_DIGEST, 'Unauthenticated MY2022 Matrix.')
        row = matching_row(matrix, receipt)
        result.update(matrix_row_id=row['row_id'], candidate_hash=row['candidate_digest'])
        vehicle = receipt.created_vehicle_definition
        need(vehicle is not None, 'Receipt lacks its canonical VehicleDefinition.')
        from reference.models import ImportExecutionReceipt, VehicleDefinition
        need(ImportExecutionReceipt.objects.filter(created_vehicle_definition=vehicle,
             operation_type='vehicle_definition_import', execution_outcome='created').count() == 1,
             'Ambiguous successful creation receipts.')
        current = identity(vehicle)
        result['identity'] = current
        need(receipt.operation_type == 'vehicle_definition_import' and receipt.execution_outcome == 'created'
             and 3221 <= receipt.pk <= 3275 and receipt.target_model_year == 2022
             and vehicle.model_year == 2022 and vehicle.market == 'US', 'Receipt outside approved MY2022 scope.')
        need(receipt.candidate_reference == row['candidate_reference']
             and receipt.created_vehicle_definition_pk_snapshot == vehicle.pk
             and receipt.created_vehicle_definition_uuid_snapshot == str(vehicle.uuid)
             and receipt.created_vehicle_definition_slug_snapshot == vehicle.slug
             and receipt.resolved_generation_id == vehicle.generation_id,
             'Incorrect candidate or receipt-to-vehicle association.')
        need(all(getattr(receipt, 'target_' + key) == row['target_fields'][key]
                 for key in BASE_FIELDS) and receipt.target_slug == vehicle.slug,
             'Original receipt scalar target mirrors differ.')
        snapshot = receipt.resolution_snapshot_json
        recorded_candidate = (snapshot.get('revalidation', {}).get('candidate_hash')
                              if snapshot.get('version') == PROFILE else snapshot.get('candidate_hash'))
        need(recorded_candidate == row['candidate_digest'], 'Receipt candidate digest differs from approved Matrix.')
        for key, expected in row['target_fields'].items():
            actual = current['fields'][key]
            raw_expected = expected
            if key == 'engine_displacement_liters':
                expected = decimal_string(expected)
                if expected != raw_expected:
                    result['normalizations'].append({'field': key, 'rule': 'existing decimal_string',
                                                     'from': raw_expected, 'to': expected})
            result['comparisons'][key] = {'expected': expected, 'actual': actual, 'equal': actual == expected}
        for key, expected in matrix['parents'].items():
            actual = current['parents'][key]
            result['comparisons'][key] = {'expected': expected, 'actual': actual, 'equal': actual == expected}
        result['comparisons']['slug'] = {'expected': row['target_slug'], 'actual': vehicle.slug,
                                         'equal': vehicle.slug == row['target_slug']}
        need(receipt.target_fields_json == row['target_fields'], 'Original target fields differ from approved Matrix.')
        if not all(item['equal'] for item in result['comparisons'].values()):
            result['outcome'] = 'DISAGREEMENT'
            return result
        validate_powertrain({key: current['fields'][key] for key in FIELDS}, complete=True)
        if all(item['equal'] for item in result['comparisons'].values()):
            matches = VehicleDefinition.objects.filter(generation_id=vehicle.generation_id,
                model_year=2022, market='US', trim_name=vehicle.trim_name, drivetrain=vehicle.drivetrain,
                **{key: current['fields'][key] for key in FIELDS})
            need(list(matches.values_list('pk', flat=True)) == [vehicle.pk],
                 'Duplicate or ambiguous canonical structured identity.')
        # Engine/body associations are fixed current inputs, never inferred from trim strings.
        if vehicle.engine_id:
            need(vehicle.engine.manufacturer_id == vehicle.generation.vehicle_model.manufacturer_id,
                 'Known Engine manufacturer mismatch.')
            need(record_powertrain(vehicle.engine) == record_powertrain(vehicle), 'Known Engine attributes conflict.')
        if vehicle.factory_body_configuration_id:
            need(vehicle.factory_body_configuration.generation_id == vehicle.generation_id, 'Known body parent mismatch.')
        result['outcome'] = ('NORMALIZED_AGREEMENT' if result['normalizations'] else 'EXACT_AGREEMENT') if all(
            x['equal'] for x in result['comparisons'].values()) else 'DISAGREEMENT'
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
        result['outcome'] = ('INSUFFICIENT_EVIDENCE' if isinstance(exc, (OSError, EvidenceUnavailable))
                             else 'EVALUATION_BLOCKED')
        result['issues'].append(str(exc))
    return result


def verify_evidence(receipt, result, candidate_reference, manifest_reference, root=None):
    """Verify retained approval/candidate/evidence identity; no historical extraction/adjudication."""
    from reference.ingestion.manifest import compute_manifest_hash
    need(result['outcome'] in SUCCESS, 'Unsuccessful revalidation cannot produce replacement evidence.')
    candidate_raw = retained(candidate_reference, root)
    manifest_raw = retained(manifest_reference, root)
    candidate, manifest = json.loads(candidate_raw), json.loads(manifest_raw)
    need(digest(candidate) == result['candidate_hash'], 'Retained candidate hash differs.')
    need(compute_manifest_hash({k: v for k, v in manifest.items() if k != 'manifest_hash'})
         == manifest['manifest_hash'] == receipt.manifest_hash, 'Execution manifest hash differs.')
    row = matching_row(load_basis(root), receipt)
    documents = candidate['evidence_documents']
    pins = sorted([{'reference': '|'.join(doc[k] for k in ('source_id', 'raw_artifact_hash', 'assertion_set_id')),
                    'digest': digest(doc)} for doc in documents], key=lambda p: p['reference'])
    need(pins == row['evidence'], 'Candidate evidence does not match approved Matrix row.')
    sources = {doc['raw_artifact_reference']: doc['raw_artifact_hash'] for doc in documents}
    need(any(doc['source_id'] == receipt.source_id and doc['raw_artifact_hash'] == receipt.raw_artifact_hash
             for doc in documents), 'Original receipt source anchor differs.')
    for reference, sha in sources.items():
        need(byte_hash(retained(reference, root)) == sha, 'Retained source bytes differ.')
    return {
        'matrix': {'reference': BASIS + '/matrix.json', 'sha256': MATRIX_SHA, 'digest': MATRIX_DIGEST},
        'approval': {'reference': BASIS + '/approval.json', 'sha256': APPROVAL_SHA},
        'candidate': {'reference': candidate_reference, 'sha256': byte_hash(candidate_raw)},
        'execution_manifest': {'reference': manifest_reference, 'sha256': byte_hash(manifest_raw)},
        'sources': [{'reference': ref, 'sha256': sha} for ref, sha in sorted(sources.items())],
    }, {key: sorted({digest(a['raw_value']) for doc in documents for a in doc['assertions']
                      if a['attribute_key'] == key}) for key in ('horsepower', 'torque')}


def build_compact(receipt, result, evidence, claims, archive_entry, archive_sha):
    need(result['outcome'] in SUCCESS and result['receipt_pk'] == receipt.pk,
         'Only successful same-receipt evaluations may be compacted.')
    need(result == evaluate(receipt, evaluated_at=result['evaluated_at_utc'],
                            revision=result['evaluator_revision']), 'Evaluation differs from current identity.')
    need(claims == {'horsepower': [], 'torque': []},
         'Unexpected explicit tuning assertions in this fixed approved MY2022 scope.')
    original = receipt.resolution_snapshot_json
    need(digest(original) == archive_entry['snapshot_canonical_sha256']
         and archive_entry['receipt_pk'] == receipt.pk
         and archive_entry['receipt_uuid'].replace('-', '') == str(receipt.uuid).replace('-', ''),
         'Verified archival identity differs.')
    result = copy.deepcopy(result)
    # Detailed field comparisons belong in the separate evaluation report, not every snapshot.
    result.pop('comparisons')
    compact = {'version': PROFILE, 'original_execution': {
        'metadata_digest': digest(metadata(receipt)), 'candidate_hash': original['candidate_hash'],
        'matrix': original['matrix'], 'attribution': original.get('attribution', {}),
        'historical_snapshot_digest': archive_entry['snapshot_canonical_sha256'],
        'historical_snapshot_utf8_hash': archive_entry['snapshot_raw_sha256'],
        'archive_sha256': archive_sha, 'archive_member': archive_entry['snapshot_member'],
        'policy': 'Historical proof references are archival only; new 2026 Matrix agreement is independently verified.'},
        'revalidation': result, 'evidence': evidence, 'nonidentity_claim_hashes': claims}
    compact['record_hash'] = digest(compact)
    return compact


def validate_compact(receipt, vehicle=None):
    """Current compact verification requires the approved basis, never the archive or source corpus."""
    compact = receipt.resolution_snapshot_json
    need(isinstance(compact, dict) and set(compact) == TOP_KEYS and compact['version'] == PROFILE,
         'Unsupported MY2022 compact record.')
    need(compact['record_hash'] == digest({k: v for k, v in compact.items() if k != 'record_hash'}),
         'MY2022 compact integrity mismatch.')
    need(compact['original_execution']['metadata_digest'] == digest(metadata(receipt)),
         'Original receipt metadata changed.')
    recorded = compact['revalidation']
    need(recorded['profile'] == PROFILE
         and compact['original_execution']['candidate_hash'] == recorded['candidate_hash']
         and compact['nonidentity_claim_hashes'] == {'horsepower': [], 'torque': []},
         'Compact historical candidate or tuning evidence differs.')
    current = evaluate(receipt, evaluated_at=recorded['evaluated_at_utc'], revision=recorded['evaluator_revision'])
    current.pop('comparisons')
    need(current == recorded and current['outcome'] in SUCCESS, 'MY2022 compact revalidation became stale.')
    need(compact['evidence']['matrix'] == {'reference': BASIS + '/matrix.json', 'sha256': MATRIX_SHA,
                                          'digest': MATRIX_DIGEST}
         and compact['evidence']['approval'] == {'reference': BASIS + '/approval.json', 'sha256': APPROVAL_SHA},
         'MY2022 compact approval pins differ.')
    if vehicle is not None:
        need(vehicle.pk == receipt.created_vehicle_definition_id and identity(vehicle) == recorded['identity'],
             'MY2022 compact peer association differs.')
    return compact


def assess_compact_peer(vehicle, receipt):
    """Scoped ordinary structured-peer compatibility; never reconstructs historical hashes."""
    compact = validate_compact(receipt, vehicle)
    values = record_powertrain(vehicle)
    state = {'record_pk': vehicle.pk, 'record_uuid': str(vehicle.uuid), 'record_slug': vehicle.slug,
             'is_active': vehicle.is_active, 'canonical_state': {k: getattr(vehicle, k) for k in BASE_FIELDS} | values,
             'receipt_uuid': str(receipt.uuid), 'receipt_evidence_digest': digest(compact),
             'document_hashes': [], 'canonical_powertrain': values}
    state['projection_digest'] = digest(state)
    return values, state


def classify_archival_references(edges, successful_receipt_ids):
    """Retire an ordinary historical edge only after both endpoints revalidate.

    Original evidence digests remain untouched; no historical proof translation.
    """
    result = copy.deepcopy(edges)
    for edge in result:
        success = (edge['source_receipt_pk'] in successful_receipt_ids
                   and edge['target_receipt_pk'] in successful_receipt_ids)
        edge['treatment'] = ('ARCHIVAL_ONLY_AFTER_NEW_MATRIX_AGREEMENT' if success
                             else 'BLOCKED_ACTIVE_DEPENDENCY')
        edge['ordinary_current_basis'] = PROFILE if success else None
    return result
