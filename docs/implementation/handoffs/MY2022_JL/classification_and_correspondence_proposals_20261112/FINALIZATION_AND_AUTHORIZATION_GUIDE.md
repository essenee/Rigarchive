# MY2022 Jeep Wrangler JL — Finalization & Authorization Guide

**Created**: 2026-11-12  
**Status**: Operator Instructions (Awaiting Human Director Action)  
**Target Handoff**: `docs/implementation/handoffs/MY2022_JL/classification_and_correspondence_proposals_20261112/`  

---

## 1. Overview & Human Review Mandate

All preparatory artifacts in this handoff directory are **draft proposals** explicitly designated with:
* `operator_label = "pending_human_signoff"`
* `reviewer = "pending_human_signoff"`
* `adjudication_decision = "proposed_classifications"`

In accordance with RigArchive project instructions and `AGENTS.md` (Sections 1, 6, and 13), automated agents cannot perform final human review or authorize database modifications. This guide defines the exact sequential workflow required for the human project director to review, finalize, approve, and execute these records.

---

## 2. Step 1: Pre-Execution Physical Snapshot

Before any command capable of modifying `db.sqlite3` is executed, capture a full physical database snapshot:

```bash
.venv/bin/python manage.py snapshot_db
```

* **Target Output**: `backups/snapshots/db_snapshot_YYYYMMDD_HHMMSS.sqlite3`
* **Integrity Gate**: Verify the snapshot was written successfully before proceeding.

---

## 3. Step 2: Generation Correspondence Finalization & Publication

### A. Review and Approval
The 72 proposal files in `correspondence_proposals/*.review.json` represent the 72 missing source-scoped model keys across 18 manufacturer order guides.

To finalize a proposal draft for human signoff:
1. Open the target draft `.review.json`.
2. Replace `"reviewer": "pending_human_signoff"` with the human reviewer identifier (e.g. `"project_owner"` or your verified initials/name).
3. Update `"reviewed_at"` with the current UTC ISO timestamp.
4. Recompute and update `"content_hash"` using `digest(payload)`.

### B. Execution Command
To publish an approved correspondence revision to `db.sqlite3`:

```bash
.venv/bin/python manage.py publish_generation_correspondence \
    --review docs/implementation/handoffs/MY2022_JL/classification_and_correspondence_proposals_20261112/correspondence_proposals/<proposal_file>.review.json \
    --operator project_owner \
    --agent codex
```

* **Interactive Gate**: The CLI displays the payload and prompts:
  `Authorize publishing this exact correspondence revision? [y/N]: `
  Enter `y` to confirm.
* **Database Effect**: Creates 1 `GenerationCorrespondenceRevision` and 1 `ImportExecutionReceipt`.
* **Batch Alternative**: For all 72 verified proposals, an authorized batch publication script utilizing `publish_correspondence(...)` with `authorized=True` and explicit director attribution may be executed under separate owner approval.

---

## 4. Step 3: Classification Adjudication Approval

### A. Review of Adjudication Proposals
The 55 proposal files in `classification_proposals/JL22-*.proposed.adjudication.1.1.json` reconcile all 112 missing powertrain fields across the 6 engine families.

### B. Execution via Management Command
To approve a classification proposal and generate a classified Candidate 2.1.0 revision:

```bash
.venv/bin/python manage.py adjudicate_canonical_import \
    --classification-review docs/implementation/handoffs/MY2022_JL/classification_and_correspondence_proposals_20261112/classification_proposals/<cand_ref>.proposed.adjudication.1.1.json \
    --operator project_owner \
    --output docs/implementation/handoffs/MY2022_JL/classification_and_correspondence_proposals_20261112/approved_adjudications/<cand_ref>.approved.adjudication.1.1.json \
    --candidate-output docs/implementation/handoffs/MY2022_JL/classification_and_correspondence_proposals_20261112/classified_candidates/<cand_ref>.candidate.2.1.0.json
```

* **Interactive Gate**: The command displays the adjudication payload and prompts:
  `Type APPROVE CLASSIFICATIONS to approve these exact conclusions: `
  Typing `APPROVE CLASSIFICATIONS` updates `operator_label = "project_owner"`, `adjudication_decision = "approved_classifications"`, generates the approved adjudication artifact, and emits the updated Candidate 2.1.0 file.
* **Zero Database Writes**: This step produces immutable JSON artifacts on disk; zero database writes are performed.

---

## 5. Step 4: Engine Proof 2.0 & Matrix 2.1 Certification

Once all 55 candidates possess complete 5-field powertrain identity documents and generation correspondence is active:
1. Generate 55 `EngineProof` 2.0 artifacts with verified peer absence.
2. Construct the MY2022 Generation Trim Matrix.
3. Run the read-only planner:
   ```bash
   .venv/bin/python manage.py plan_candidate_import ...
   ```
4. Verify that all 55 candidates return:
   * `eligibility_status = "eligible"`
   * `planned_action = "create"`
   * `target_slug` uniquely populated (0 collisions)

---

## 6. Step 5: Authorized Canonical Import Execution

Under separate, explicit owner authorization:
* Execute atomic transaction importing the 55 configurations into `VehicleDefinition`.
* Persist 55 `ImportExecutionReceipt` records.
* Invariant: `VehicleDefinition` records advance from 934 to 989; receipts advance from 3,148 to 3,203.
