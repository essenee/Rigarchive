   RA-006 — Observation Foundation Architecture



  │ [!NOTE]

  │ Status: Architectural Design Document

  │ Authority: Higher than CURRENT_STATE.md and Handbook for RA-006 decisions.

  │ Scope: Conceptual and architectural specification for integrating observations into RigArchive

  │ without modifying existing repository code, creating applications, or executing migrations.

  ──────

  ## Executive Summary



  The RigArchive repository currently implements:



  1. Core Infrastructure (core): Shared abstract model mixins (UUIDModel, TimestampedModel,

  BaseModel).

  2. Accounts Domain (accounts): Custom user identity (User).

  3. Reference Domain (reference): Canonical vehicle reference models (Manufacturer, VehicleModel,

  Generation, VehicleDefinition).

  4. Presentation Shell (templates/base.html, config/views.py, site.css): Accessible layout,

  navigation, and error handling.

  As established by project governance:

  │ The Reference Domain is the canonical factory configuration model for supported vehicles. It

  │ models stable engineering identities and factory configuration logic so that other records can

  │ be associated with the correct configuration.



  The Reference Domain identifies what configuration a record concerns. It does not represent

  observations, evidence, maintenance history, compatibility knowledge, or derived technical

  conclusions.



  This document specifies RA-006 — Observation Foundation Architecture. An Observation is defined

  as:



  │ A recorded statement about a vehicle configuration together with sufficient context to preserve

  │ how that information entered the archive.



  This intentionally includes physical inspections, measurements, documented observations, manuals,

  service literature, historical documents, and future imported records. Observation represents how

  information is captured by RigArchive rather than restricting it to physical measurement.

  ──────

  ## 1. User Story



  To extend the repository beyond the Reference Domain in the smallest complete vertical slice, we

  define an administrator-focused workflow:



  │ As an archive administrator,

  │ I can record a statement about a specific canonical VehicleDefinition

  │ (including the observation details, event date, archive recorder, and contextual source notes)

  │ so that information entering the archive can be associated with the correct factory

  │ configuration without modifying canonical reference data.



  ### Justification



  • Administrator-focused: Keeps the initial slice simple by avoiding public contribution forms,

  submission queues, anti-spam systems, and public moderation states.

  • Complete vertical slice: Connects an authenticated archive user (accounts) to a canonical

  vehicle identity (reference) through a minimal observation record (observation).

  • Demonstrated need: Enables recording statements from physical inspections, manuals, service

  literature, or historical documents directly against a specific vehicle configuration.

  ──────

  ## 2. Domain Responsibilities & Architectural Boundary



    ┌─────────────────────────────────────────────────────────┐

    │                    Reference Domain                     │

    │    (Canonical Factory Configuration & Identity)         │

    │                                                         │

    │   Manufacturer ──► VehicleModel ──► Generation ──► VehicleDefinition

    └─────────────────────────────────────────────────────────┘

                                    ▲

                                    │  Unidirectional Reference

                                    │  (PROTECT Foreign Key)

    ┌───────────────────────────────┴─────────────────────────┐

    │                   Observation Domain                    │

    │     (Recorded Statements & Capture Context)             │

    │                                                         │

    │   Observation ──► VehicleDefinition                     │

    │   Observation ──► User (recorded_by)                    │

    └─────────────────────────────────────────────────────────┘



  ### Reference Domain Responsibilities



  • Scope: Serves as the canonical factory configuration model for supported vehicles. It models

  stable engineering identities and factory configuration logic.

  • Role: Reference identifies what configuration a record concerns. It does not automatically own

  technical knowledge, measurements, or observations merely because that data originated with a

  manufacturer.

  • Dependency Direction: Zero knowledge of or dependency on Observation or any downstream domain.



  ### Observation Domain Responsibilities



  • Scope: Captures recorded statements about a vehicle configuration together with sufficient

  context to preserve how that information entered the archive.

  • Role: Represents how information (from physical inspections, measurements, manuals, service

  literature, historical documents, or future imports) is captured by RigArchive.

  • Dependency Direction: Unidirectional dependency on reference.VehicleDefinition and accounts.

  User.



  ### Architectural Boundary Rule



  │ Strict Boundary Rule:

  │ Observation records reference VehicleDefinition, but VehicleDefinition has zero knowledge of

  │ Observation. Canonical reference records are never mutated, updated, or flags-changed when

  │ observations are logged.

  ──────

  ## 3. Conceptual Observation Model



  The conceptual model for the Observation domain conforms to ADR-0001 (dual integer PK + UUID

  identity) and inherits from core.models.BaseModel.



    Observation (Inherits core.models.BaseModel)

    ├── id (Integer PK, auto-incrementing database primary key)

    ├── uuid (UUIDField, immutable external identity, auto-generated)

    ├── created_at (DateTimeField, auto-now-add timestamp)

    ├── updated_at (DateTimeField, auto-now timestamp)

    ├── vehicle_definition (FK -> reference.VehicleDefinition, on_delete=PROTECT)

    ├── recorded_by (FK -> accounts.User, on_delete=PROTECT)

    ├── title (Short descriptive summary of the statement)

    ├── description (Primary textual description of the observation)

    ├── observed_on (Optional DateField for when the observation or record occurred)

    └── source_notes (Optional TextField capturing context, literature details, or source

  attribution)



  ### Concept Explanations



  • Dual Identity (id, uuid): Conforms to ADR-0001 and core.models.BaseModel. id provides efficient

  internal database joins and primary key performance, while uuid provides a stable, permanent

  external identifier.

  • Timestamps (created_at, updated_at): Inherited from TimestampedModel via BaseModel for database

  record auditing.

  • vehicle_definition: Links the observation to the target canonical configuration (reference.

  VehicleDefinition). Uses PROTECT deletion to prevent deleting reference entities that have

  associated historical observations.

  • recorded_by: Identifies the authenticated archive user (accounts.User) responsible for creating

  the RigArchive record. Uses PROTECT deletion.

  • title: A concise headline identifying the statement or recorded detail.

  • description: The primary textual description containing the details of the observation.

  • observed_on: Records when the observation, physical inspection, or document review took place

  (which may differ from the database creation timestamp created_at).

  • source_notes: Preserves contextual information about how the information entered the archive,

  including service manual citations, inspection methodology, or historical document details.



  │ [!NOTE]

  │ Domain Invariant Rule:

  │ No additional domain concepts, abstractions, or relationships should be introduced without

  │ explicit justification from the approved user story and repository standards. Incidental Django

  │ implementation details—such as exact field constraints, ordering, indexes, and reverse relation

  │ names—will be resolved during task-level implementation planning.

  ──────

  ## 4. Relationship to Reference



  ### Attachment



  • Observation.vehicle_definition is a unidirectional ForeignKey to reference.VehicleDefinition.

  • Relational protection is set to on_delete=models.PROTECT.



  ### Non-Mutation Principle



  Observations must never modify canonical reference data:



  1. Epistemic Separation: Reference data represents canonical factory configuration models.

  Observations represent statements entering the archive. Conflating the two corrupts the reference

  model baseline.

  2. Data Integrity: A statement or variant observed in real-world inspection or service literature

  does not alter manufacturer factory configuration logic.

  3. Audit Protection: Preserving canonical reference records as immutable targets ensures that

  observations can be added, updated, or removed without corrupting the core reference hierarchy.

  ──────

  ## 5. Provenance Strategy



  The initial Observation foundation separates archive record authorship from source context:



  1. Archive Recorder (recorded_by): The authenticated User account creating and taking

  responsibility for the entry in RigArchive.

  2. System Timestamps (created_at, updated_at): System audit trail recording when the archive

  entry was logged and last updated.

  3. Event Date (observed_on): Optional date identifying when the physical inspection, manual

  review, or document capture occurred.

  4. Attribution & Context (source_notes): Free-form text field capturing real-world observer names,

  manual/literature citations, or inspection context.



  │ [!IMPORTANT]

  │ No Premature Provenance Models:

  │ Do not create separate Observer, Contributor, Source, or Evidence models in RA-006. Real-world

  │ observer or source information remains in contextual text (source_notes) until demonstrated

  │ requirements justify a structured domain concept.

  ──────

  ## 6. Deferred Concepts



  The following candidate concepts are intentionally deferred and out of scope:



  • Evidence

  • Assets / Media

  • Measurements

  • Compatibility

  • Knowledge

  • Vehicle Instances

  • Maintenance

  • User Contribution Workflows



  ### Rationale for Deferral



  These concepts are deferred because:



  1. The first administrator-managed Observation workflow does not require them.

  2. Their correct persistence strategies and application boundaries remain unresolved.

  3. Introducing them now would exceed demonstrated need and violate the principle of speculative

  architecture.

  ──────

  ## 7. Implementation Recommendation for RA-007



  When an implementation task is authorized to follow this design document, the recommended next

  step is:



  ### Milestone 4 — Observation Domain Foundation (RA-007)



  #### Recommended Scope:



  1. Domain Application: Create the Observation domain application registered in INSTALLED_APPS.

  2. Model Implementation: Implement the Observation model inheriting from core.models.BaseModel,

  referencing reference.VehicleDefinition and accounts.User with PROTECT deletion.

  3. Django Admin Interface: Register ObservationAdmin in observation/admin.py providing an

  administrator-only CRUD interface for creating, viewing, and managing observations.

  4. Service Layer Policy: Introduce an application service in observation/services.py only if the

  approved creation workflow requires explicit coordination, transaction management, authorization

  checks, or business logic beyond standard Django model validation and Admin forms. Otherwise,

  standard Django Admin/Form workflows should be used directly.

  5. Verification & Tests: Write unit tests in observation/tests.py verifying:

      • Inheritance from BaseModel (dual integer PK + UUID + timestamps).

      • Relational integrity and PROTECT deletion on vehicle_definition and recorded_by.

      • Model validation rules.

      • Admin accessibility for administrators.





  ──────

  ## Summary Matrix



   Architectural Dimension   | Specification

  ---------------------------|---------------------------------------------------------------------

   Domain Name               | observation

   Definition                | A recorded statement about a vehicle configuration together with

                             | sufficient context to preserve how that information entered the

                             | archive

   Identity Strategy         | Dual Identity (Integer PK + UUIDField via core.models.BaseModel)

   Core Entity               | Observation

   Primary Text Field        | description (contains primary textual description of observation)

   Primary Relation          | FK -> reference.VehicleDefinition (on_delete=PROTECT)

   Recorder Relation         | recorded_by = FK -> accounts.User (on_delete=PROTECT)

   Source / Observer Context | Captured in source_notes text (no separate model)

   Mutation Policy           | Zero mutation of reference data

   Initial Interface         | Administrator Django Admin (Public views deferred)

   Service Layer Policy      | Introduced only if workflow complexity requires it

   Deferred Domains          | Evidence, Assets, Measurements, Compatibility, Knowledge, Vehicle

                             | Instances, Maintenance, Public Workflows
