"""Execute one approved matrix year using exact, freshly planned manifests."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from tempfile import mkdtemp

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from reference.ingestion.attribution import resolve_attribution
from reference.ingestion.contracts import CandidateConfigurationDocument
from reference.ingestion.generation_correspondence import digest, revalidate_resolution
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.workflow import execute_canonical_import_workflow
from reference.ingestion.manifest import build_review_manifest, manifest_to_dict
from reference.ingestion.matrix import canonical_matrix_payload, compute_matrix_digest
from reference.ingestion.matrix_approval import serialize_matrix_approval
from reference.ingestion.serialization import candidate_config_doc_to_dict, serialize_artifact
from reference.models import Generation, GenerationCorrespondenceRevision, ImportExecutionReceipt, VehicleDefinition


class MatrixExecutionError(ValueError):
    """A matrix year cannot safely proceed."""


class MatrixArtifactsUnavailable(MatrixExecutionError):
    """Initial attempt artifacts failed before canonical execution began."""


class MatrixReportingIncomplete(MatrixExecutionError):
    """The transaction committed, but final reporting is incomplete."""


def _identity(record):
    return {"pk": record.pk, "uuid": str(record.uuid), "slug": record.slug}


def _references(plan):
    resolution = plan.generation_resolution
    return (
        sorted([
            {"reference": "|".join(doc[key] for key in ("source_id", "raw_artifact_hash", "assertion_set_id")),
             "digest": digest(doc)}
            for doc in resolution["documents"]
        ], key=lambda ref: ref["reference"]),
        sorted([
            {"reference": item["uuid"], "digest": item["hash"]}
            for item in resolution["correspondences"]
        ], key=lambda ref: ref["reference"]),
    )


class MatrixYear:
    def __init__(self, matrix, approval, year, candidates, *, review_only=False):
        self.matrix = canonical_matrix_payload(matrix)
        if type(year) is not int or year not in self.matrix["model_years"]:
            raise MatrixExecutionError("Year is outside approved scope.")
        self.rows = [row for row in self.matrix["rows"] if row["model_year"] == year]
        if not self.rows:
            raise MatrixExecutionError("No enumerated rows for this year.")
        self.digest = compute_matrix_digest(self.matrix)
        self.approval_bytes = None if review_only else serialize_matrix_approval(self.matrix, approval)
        self.link = {
            "matrix_version": self.matrix["matrix_version"],
            "matrix_digest": self.digest,
            "approval_digest": "sha256:" + sha256(self.approval_bytes).hexdigest() if self.approval_bytes else None,
            "model_year": year,
        }
        self.candidates = candidates

    def _generation(self):
        parents = self.matrix["parents"]
        generation = Generation.objects.select_related("vehicle_model__manufacturer").filter(
            pk=parents["generation"]["pk"],
        ).first()
        if generation:
            model = generation.vehicle_model
            records = {"generation": generation, "vehicle_model": model, "manufacturer": model.manufacturer}
            if all(record.is_active and _identity(record) == parents[key] for key, record in records.items()):
                return generation
        raise MatrixExecutionError("Canonical parent identity or activity changed.")

    def _row_link(self, row):
        link = self.link | {"row_id": row["row_id"]}
        if "generation_binding" in row:
            link["generation_binding"] = row["generation_binding"] | {"generation": self.matrix["parents"]["generation"]}
        return link

    def _validate_binding(self, generation, row, plan):
        binding = row.get("generation_binding")
        if not binding:
            return
        resolution = plan.generation_resolution
        if (resolution.get("basis") != binding["strategy"]
                or resolution.get("resolution_version") != binding["resolution_version"]):
            raise MatrixExecutionError("Generation resolution strategy differs from the approved row.")
        if binding["mode"] == "unique_deterministic":
            if resolution["generation_evidence"] or resolution["correspondences"]:
                raise MatrixExecutionError("Unique Generation resolution cannot substitute explicit source evidence.")
            current = GenerationCorrespondenceRevision.objects.filter(
                vehicle_model_id=generation.vehicle_model_id, market=row["target_fields"]["market"],
                start_year__lte=row["model_year"], end_year__gte=row["model_year"], successor__isnull=True,
                source_id__in={doc["source_id"] for doc in resolution["documents"]},
            )
            for revision in current:
                if all(resolution["fields"].get(k) == v for k, v in revision.restrictions.items()) and (
                    revision.finding in {"ambiguous", "rejected"} or
                    (revision.finding == "established" and revision.generation_id != generation.pk)
                ):
                    raise MatrixExecutionError("Applicable correspondence conflicts with unique Generation resolution.")

    def _row(self, generation, row):
        candidate = self.candidates.get(row["candidate_reference"])
        if (not isinstance(candidate, CandidateConfigurationDocument)
                or candidate.envelope.schema_version != ("2.1.0" if self.matrix["matrix_version"] == "2.1" else "2.0.0")
                or candidate.candidate_reference != row["candidate_reference"]
                or digest(candidate_config_doc_to_dict(candidate)) != row["candidate_digest"]):
            raise MatrixExecutionError("Candidate does not match the approved row.")
        record = VehicleDefinition.objects.filter(generation=generation, slug=row["target_slug"]).first()
        link = self._row_link(row)
        receipts = list(ImportExecutionReceipt.objects.filter(
            Q(resolution_snapshot_json__matrix__matrix_digest=self.digest,
              resolution_snapshot_json__matrix__row_id=row["row_id"])
            | Q(resolved_generation_id=generation.pk, target_slug=row["target_slug"],
                resolution_snapshot_json__has_key="matrix"),
            operation_type="vehicle_definition_import", execution_outcome="created",
        )[:2])
        existing = row["action"] == "reviewed_existing"
        receipt = None
        if existing or record or receipts:
            from reference.ingestion.importing.planner import _fields_match_exact
            exact = record and record.is_active and _fields_match_exact(record, row["target_fields"])
            if existing and exact and _identity(record) == row["existing_record"]:
                status = "reviewed_existing"
            elif not existing and exact and len(receipts) == 1:
                receipt = receipts[0]
                recorded = receipt.resolution_snapshot_json
                if (recorded.get("matrix") != link
                        or recorded.get("candidate_hash") != row["candidate_digest"]
                        or receipt.resolved_generation_id != generation.pk
                        or receipt.target_slug != row["target_slug"]
                        or receipt.candidate_reference != row["candidate_reference"]
                        or receipt.target_fields_json != row["target_fields"]
                        or receipt.created_vehicle_definition_id != record.pk
                        or receipt.created_vehicle_definition_pk_snapshot != record.pk
                        or receipt.created_vehicle_definition_uuid_snapshot != str(record.uuid)
                        or receipt.created_vehicle_definition_slug_snapshot != record.slug):
                    raise MatrixExecutionError("Conflict: completion receipt does not bind the current record.")
                status = "previously_completed"
            else:
                raise MatrixExecutionError("Conflict: occupied slug, drifted existing row or missing completed record.")
        else:
            status = "pending_create"

        plan = plan_candidate_import(candidate)
        if (plan.eligibility_status.value != "eligible"
                or plan.resolved_generation_id != generation.pk
                or plan.target_slug != row["target_slug"]
                or plan.target_vehicle_definition_fields != row["target_fields"]
                or plan.candidate_hash != row["candidate_digest"]
                or _references(plan) != (row["evidence"], row["correspondence"])):
            raise MatrixExecutionError("Planner or evidence binding differs from the approved row.")
        try:
            revalidate_resolution(plan)
        except (ValueError, OSError, ValidationError) as exc:
            raise MatrixExecutionError("Evidence or correspondence revalidation failed.") from exc
        self._validate_binding(generation, row, plan)
        if receipt and "generation_binding" in row:
            prior_resolution = receipt.resolution_snapshot_json.get("generation_resolution") or {}
            if (prior_resolution.get("basis") != plan.generation_resolution["basis"]
                    or prior_resolution.get("resolution_version") != plan.generation_resolution["resolution_version"]
                    or prior_resolution.get("parents") != plan.generation_resolution["parents"]
                    or prior_resolution.get("correspondences") != plan.generation_resolution["correspondences"]):
                raise MatrixExecutionError("Conflict: receipt Generation resolution differs from the approved binding.")
        if status == "pending_create":
            if plan.planned_action.value != "create" or not plan.create_basis or (
                plan.create_basis.value not in row["permitted_create_bases"]
                or plan.adjudication_hash
            ):
                raise MatrixExecutionError("Planner did not establish an approved creation basis.")
        elif plan.planned_action.value != "no_op_exact_match" or plan.existing_vehicle_definition_id != record.pk:
            raise MatrixExecutionError("Conflict: planner does not verify the existing identity.")

        result = {"row_id": row["row_id"], "status": status, "slug": row["target_slug"],
                  "candidate_digest": row["candidate_digest"]}
        if "generation_binding" in row:
            result["generation_binding"] = link["generation_binding"]
            result["source_identity"] = [
                {"source_id": doc["source_id"], "source_locator": doc["source_locator"],
                 "assertion_set_id": doc["assertion_set_id"]}
                for doc in plan.generation_resolution["documents"]
            ]
        if record:
            result["vehicle"] = _identity(record)
        if receipt:
            result.update(receipt={"pk": receipt.pk, "uuid": str(receipt.uuid)}, manifest_digest=receipt.manifest_hash)
        return result, plan

    def status(self):
        generation = self._generation()
        rows = []
        for row in self.rows:
            try:
                result, _ = self._row(generation, row)
            except MatrixExecutionError as exc:
                reason = str(exc)
                result = {"row_id": row["row_id"], "status": "conflict" if reason.startswith("Conflict:") else "blocked",
                          "reason": reason}
            rows.append(result)
        return self.link | {"authorized_count": len(rows), "rows": rows,
                            "counts": dict(Counter(row["status"] for row in rows)), "complete": all(
            row["status"] in {"reviewed_existing", "previously_completed"} for row in rows
        )}


def write_json(path, payload):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _year_statuses(batch):
    statuses = {}
    approval = json.loads(batch.approval_bytes)
    for year in batch.matrix["model_years"]:
        try:
            report = MatrixYear(batch.matrix, approval, year, batch.candidates).status()
            counts = report["counts"]
            statuses[year] = ("complete" if report["complete"] else
                              "conflict" if counts.get("conflict") else
                              "blocked" if counts.get("blocked") else "pending")
        except Exception:
            # Diagnostic only. Never mask the execution failure.
            statuses[year] = "unverified"
    return statuses


def execute_matrix_year(matrix, approval, year, candidates, output_dir, *, execution_operator, execution_agent=None):
    """Persist attempt artifacts and commit only a fully reconciled year."""
    if not isinstance(execution_operator, str) or not execution_operator.strip():
        raise MatrixExecutionError("A nonempty execution operator is required.")
    execution = resolve_attribution(operator=execution_operator.strip(), agent=execution_agent)
    batch = MatrixYear(matrix, approval, year, candidates)
    attribution = {
        "approval_operator": approval["operator"], "execution_operator": execution.director,
        "execution_agent": execution.agent, "execution_interface": "cli",
    }
    attempt = None
    try:
        attempt = Path(mkdtemp(prefix=f"matrix-{year}-", dir=output_dir))
        write_json(attempt / "matrix.json", batch.matrix)
        (attempt / "approval.json").write_bytes(batch.approval_bytes)
        write_json(attempt / "operators.json", attribution)
    except OSError as exc:
        raise MatrixArtifactsUnavailable(
            f"No canonical execution began. Initial artifacts could not be saved "
            f"({type(exc).__name__}) at {attempt or output_dir}. No complete attempt record was written."
        ) from exc
    phase, row_id, manifest_hash = "preflight", None, None
    transaction_started = False
    before_years = _year_statuses(batch)
    completed_before = [y for y, status in before_years.items() if status == "complete"]
    created = set()
    try:
        preflight = batch.status()
        write_json(attempt / "preflight.json", preflight)
        blocked = next((row for row in preflight["rows"] if row["status"] in {"blocked", "conflict"}), None)
        if blocked:
            row_id = blocked["row_id"]
            raise MatrixExecutionError(blocked["reason"])
        for index, row in enumerate(batch.rows):
            candidate = batch.candidates[row["candidate_reference"]]
            (attempt / f"{index:04d}.candidate.json").write_text(serialize_artifact(candidate), encoding="utf-8")
        phase = "execution"
        with transaction.atomic(durable=True):
            transaction_started = True
            generation = batch._generation()
            for index, row in enumerate(batch.rows):
                row_id, manifest_hash = row["row_id"], None
                result, plan = batch._row(generation, row)
                if result["status"] != "pending_create":
                    continue
                candidate = batch.candidates[row["candidate_reference"]]
                doc = candidate.evidence_documents[0]
                native = candidate.source_configuration_identities
                manifest = build_review_manifest(
                    doc["source_id"], doc["raw_artifact_hash"], doc["raw_artifact_reference"],
                    doc, [plan], {row["candidate_reference"]: native[0].native_identifier if native else "not_recorded"},
                )
                manifest_hash = manifest.manifest_hash
                write_json(attempt / f"{index:04d}.manifest.json", manifest_to_dict(manifest))
                outcome, receipt = execute_canonical_import_workflow(
                    plan, manifest, manifest.plans[0], operator_label=execution.director, execution_agent=execution.agent,
                )
                if outcome.outcome.value != "created":
                    raise MatrixExecutionError(f"Unexpected importer outcome: {outcome.outcome.value}.")
                receipt.resolution_snapshot_json["matrix"] = batch._row_link(row)
                receipt.save(update_fields=["resolution_snapshot_json"])
                created.add(row_id)
            phase, row_id, manifest_hash = "transaction_reconciliation", None, None
            if not batch.status()["complete"]:
                raise MatrixExecutionError("Year reconciliation failed before commit.")
    except Exception as exc:
        rollback = "transaction_aborted" if transaction_started else "not_started"
        year_statuses = _year_statuses(batch)
        if year_statuses[year] != "conflict":
            year_statuses[year] = "blocked"
        report = batch.link | attribution | {
            "row_id": row_id, "phase": phase, "category": type(exc).__name__,
            "reason": str(exc) if isinstance(exc, MatrixExecutionError) else "Workflow or infrastructure failure.",
            "rollback": rollback, "manifest_digest": manifest_hash,
            "previously_completed_years": completed_before,
            "completed_during_attempt": [],
            "year_statuses": year_statuses,
        }
        state = "Canonical transaction rolled back." if transaction_started else "No canonical execution began."
        try:
            write_json(attempt / "failure.json", report)
        except OSError as report_error:
            raise MatrixExecutionError(
                f"{state} Failure report could not be saved at {attempt} "
                f"({type(report_error).__name__}); original category: {type(exc).__name__}."
            ) from report_error
        raise MatrixExecutionError(f"{state} See {attempt / 'failure.json'}.") from exc

    try:
        report = batch.status() | attribution
        for row in report["rows"]:
            if row["row_id"] in created and row["status"] == "previously_completed":
                row["status"] = "newly_created"
        report["counts"] = dict(Counter(row["status"] for row in report["rows"]))
        report.update(
            previously_completed_years=completed_before,
            completed_during_attempt=[year] if report["complete"] and year not in completed_before else [],
            year_statuses=_year_statuses(batch),
        )
        write_json(attempt / "result.json", report)
        if not report["complete"]:
            raise MatrixExecutionError("Post-commit verification found unresolved rows.")
    except Exception as exc:
        raise MatrixReportingIncomplete(
            f"Canonical transaction committed, but final reporting is incomplete ({type(exc).__name__}). "
            f"Attempt: {attempt}. Matrix: {batch.digest}. Model year: {year}. "
            "Run read-only reconciliation with the same matrix, approval and candidates before retrying."
        ) from exc
    return attempt, report
