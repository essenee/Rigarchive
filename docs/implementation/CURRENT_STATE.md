RigArchive Project Status Document
Version: 0.1
Date: August 2026
Purpose: Current implementation status and development roadmap
1. Project Overview
RigArchive is a long-term engineering project whose purpose is to build the world's most trusted technical archive of vehicles and their modifications, maintenance, compatibility, measurements, and supporting evidence.
The Project Blueprint defines the architectural vision.
The Engineering Handbook defines implementation standards.
The GitHub repository is the authoritative implementation.
This document summarizes the current implementation status.
2. Current Technology Stack
Backend
Python 3.14
Django 6.0.x
Database
Development
SQLite
Future Production
PostgreSQL
Storage
Development
Local filesystem
Future
Cloud object storage
AWS S3 or Cloudflare R2
Frontend
Django Templates
Vanilla HTML
Vanilla CSS
Minimal JavaScript
No React or SPA framework is planned.
3. Architectural Principles
RigArchive follows the Engineering Handbook architecture.
Presentation

↓

Application Services

↓

Domain Models

↓

Infrastructure
Views remain thin.
Business workflows belong in services.
Models enforce domain invariants.
Infrastructure remains replaceable.
4. Current Django Apps
Implemented
accounts
reference
Planned
core
knowledge
evidence
media
compatibility
maintenance
projects
assets
(The order may evolve as implementation progresses.)
5. Completed Milestones
Milestone 1
Project foundation
Completed.
Includes:
Django project
Git repository
GitHub repository
Development environment
SQLite configuration
Custom User model
Initial migrations
Test infrastructure
Milestone 2
Reference Domain
Completed.
Implemented models
Manufacturer

VehicleModel

Generation

VehicleDefinition
Features
UUID identity
Integer database PKs
Automatic slug generation
Immutable public slugs
Protected foreign keys
Validation rules
Django Admin
Unit tests
Milestone 2A
Public Reference Browser
Completed.
Implemented
Homepage
Manufacturer list
Manufacturer detail
Vehicle model detail
Generation detail
Vehicle definition detail
Features
Nested URLs
Breadcrumb navigation
Responsive layout
Base template
Shared CSS
Public navigation
Example URL
/vehicles/toyota/4runner/fourth-generation/2007-sr5-40l-v6-4wd-us/
6. Current URL Structure
/

↓

Vehicles

↓

Manufacturer

↓

Vehicle Model

↓

Generation

↓

Vehicle Definition
7. Current Testing
Implemented
Model tests
View tests
URL tests
Current status
All tests passing.
Every future model should include tests before merging.
8. Current Coding Standards
Every model includes
UUID
created_at
updated_at
Public URLs use slugs.
UUIDs are permanent identities.
Database relations use integer PKs.
Reference data uses PROTECT deletion.
Views remain thin.
Business logic should migrate into services.
9. Git Workflow
Current workflow
Architecture
↓
Implementation task
↓
Implementation
↓
Tests
↓
Review
↓
Commit
↓
Push
Each architectural concept should become its own commit.
10. Gemini CLI Workflow
The project includes a root-level:
GEMINI.md
Purpose
Provide persistent engineering guidance for Gemini CLI.
It defines:
architecture
coding standards
verification procedure
implementation rules
project conventions
Gemini CLI should load this file before making changes.
11. Implementation Task System
Implementation work is organized under:
docs/
    implementation/
        tasks/
Each task is a self-contained engineering specification describing:
objective
scope
files expected to change
acceptance criteria
verification commands
restrictions
Gemini CLI should inspect the task before editing code.
The first planned task in this system is:
RA-003 — Core Foundation
Objective:
Create the shared core application and move common infrastructure (UUIDs, timestamps, and reusable model behavior) into abstract base classes and mixins while preserving existing functionality.
12. Planned Milestone Map
Milestone 1
Project foundation
✅ Complete
Milestone 2
Reference Domain
✅ Complete
Milestone 2A
Public Reference Browser
✅ Complete
Milestone 3
Core Infrastructure
Planned
Includes
core app

BaseModel

UUID mixin

Timestamp mixin

AutoSlug mixin

refactor reference app
Milestone 4
Knowledge Domain
Planned
Initial design work only.
This domain will become the central knowledge layer of RigArchive.
Milestone 5
Evidence Domain
Planned.
Evidence supporting knowledge.
Milestone 6
Media Domain
Planned.
Images
Files
Attachments
Future cloud storage
Milestone 7
Compatibility
Planned.
Vehicle compatibility knowledge.
Milestone 8
Maintenance
Planned.
Service history
Repair history
Maintenance records
Milestone 9
Projects
Planned.
Build projects
Vehicle ownership
User workflows
13. Current Repository Structure
RigArchive/
│
├── accounts/
├── reference/
├── config/
│
├── templates/
├── static/
├── media/
│
├── docs/
│   └── implementation/
│       └── tasks/
│
├── tests/
│
├── GEMINI.md
│
├── README.md
├── requirements.txt
└── manage.py
14. Current Development Philosophy
RigArchive follows the principle established in the Engineering Handbook:
Build for expansion. Implement for today.
Future capabilities should be anticipated in the architecture but should not be implemented until they provide immediate value.
Examples:
engine_name remains a simple field today rather than introducing an EngineDefinition domain prematurely.
UUIDs and immutable slugs are implemented early because they provide long-term stability with little additional complexity.
The upcoming core app will centralize shared infrastructure before additional business domains are introduced.
15. Current Repository Status
The repository currently contains:
Functional Django project
Passing test suite
Public reference browser
Admin interface
Stable migration history
GitHub remote configured
Gemini CLI project instructions (GEMINI.md)
Task-based implementation workflow (docs/implementation/tasks/)
The next planned implementation task is RA-003 — Core Foundation.