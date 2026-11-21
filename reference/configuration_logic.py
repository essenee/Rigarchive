"""Build draft generation datasets without writing canonical data."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import CommandError
from django.db.models import Q

from reference.admin import factory_body_configuration_label
from reference.body_identity import canonical_json
from reference.configuration_logic_queries import (
    authored_observations, catalogue_options, option_rows, sort_by_trim_price,
)
from reference.models import Generation


HEADERS = (
    "#", "VehicleDefinition PK", "Manufacturer Model Code", "Trim", "Body Configuration",
    "Cab", "Nominal Bed", "Drivetrain", "Engine Code", "Engine Variant",
    "Registered Engine Name", "Base MSRP", "Slug", "Market", "Transmission",
    "Conditional Output Variant", "Alternate Model Code", "Alternate MSRP", "Package",
    "Applicability", "Provenance",
)
WIDTHS = (6, 19, 21, 26, 24, 16, 14, 14, 15, 24, 24, 15, 40, 18, 22, 24, 18, 16, 24, 48, 44)
LEGACY_BODY_COLUMNS = frozenset({5, 6})
GENERATION_COLUMN_ORDER = (0, 1, 2, 3, 4, 7, 8, 9, 10, 14, 11, 12, 13, 15, 16, 17, 18, 19, 20)
SOURCE_HEADERS = (
    "Model Year", "Organization", "Source", "URL / Document ID", "Acquired / Reviewed",
    "Source Type", "Evidence ID", "Verification Status", "Notes",
)


@dataclass(frozen=True)
class Sheet:
    name: str
    rows: tuple
    widths: tuple
    prices: tuple = ()
    header_row: int = 4
    workbook_title: str | None = None
    hidden_columns: tuple = ()
    numbering: bool = False

    @property
    def title(self):
        return self.workbook_title or self.rows[0][0]


@dataclass(frozen=True)
class GenerationDraft:
    key: str
    title: str
    sheets: tuple[Sheet, ...]


def select_generation(manufacturer, model, identifier):
    match = Q(slug=identifier)
    if str(identifier).isascii() and str(identifier).isdigit():
        match |= Q(pk=int(identifier))
    try:
        return Generation.objects.select_related("vehicle_model__manufacturer").get(
            match, vehicle_model__name__iexact=model,
            vehicle_model__manufacturer__name__iexact=manufacturer,
        )
    except (Generation.DoesNotExist, Generation.MultipleObjectsReturned) as exc:
        raise CommandError("Generation is missing or ambiguous for this manufacturer and model.") from exc


def verified_observation(receipt, review):
    snapshot = receipt.resolution_snapshot_json.copy()
    expected = snapshot.pop("snapshot_hash", None)
    if expected != "sha256:" + hashlib.sha256(canonical_json(snapshot).encode()).hexdigest():
        return {}
    observation = snapshot.get("observation")
    if observation and observation in review.get("configurations", ()):
        return observation
    return {}


def pinned_review(receipt):
    root = Path(settings.BASE_DIR).resolve()
    path = (root / receipt.raw_artifact_reference).resolve()
    if not path.is_relative_to(root):
        return None
    try:
        raw = path.read_bytes()
        if receipt.raw_artifact_hash != "sha256:" + hashlib.sha256(raw).hexdigest():
            return None
        data = json.loads(raw)
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and data.get("record_type") == "human-reviewed-factory-observations":
        return data
    return None


def draft_year(title, year, configurations, *, authored_rows=(), authored_sources=()):
    """Research drafts can supply validated display rows without ORM insertion."""
    status = "Draft — awaiting research and review"
    data, sources = [], []
    if configurations:
        status = "Draft — database-derived; review pending"
        configs = sort_by_trim_price(configurations)
        receipts = authored_observations(configs)
        catalogue = catalogue_options(configs)
        reviews = {}
        labels = {}
        for number, vehicle in enumerate(configs, 1):
            engine = vehicle.engine
            body = vehicle.factory_body_configuration
            if body and body.pk not in labels:
                labels[body.pk] = factory_body_configuration_label(body)
            receipt = receipts.get(vehicle.pk)
            observation = {}
            if receipt:
                pin = (receipt.raw_artifact_reference, receipt.raw_artifact_hash)
                if pin not in reviews:
                    reviews[pin] = pinned_review(receipt)
                if reviews[pin] is not None:
                    observation = verified_observation(receipt, reviews[pin])
            selected = observation.get("selected_toyota_model") or {}
            if (selected.get("variant") != (engine.internal_variant_key if engine else None)):
                selected = {}
            parent = (
                number, vehicle.pk, selected.get("code"), vehicle.trim_name,
                labels.get(body.pk) if body else None, body.get_cab_configuration_display() if body and body.cab_configuration else None,
                body.bed_length.designation if body and body.bed_length_id else None,
                vehicle.get_drivetrain_display(), engine.engine_code if engine else None,
                engine.internal_variant_key if engine else None, engine.name if engine else None,
                float(vehicle.base_msrp) if vehicle.base_msrp is not None else None,
                vehicle.slug, vehicle.get_market_display(),
            )
            evidence = f"Authoring receipt {receipt.pk}" if observation else "RigArchive database; source match unavailable"
            data.append((*parent, vehicle.transmission or selected.get("transmission"), None, None, None, None,
                         "Stored configuration" if not selected else "Recorded model selection", evidence))
            alternatives = observation.get("alternate_toyota_models", ())
            for model in alternatives:
                data.append((number, vehicle.pk, None, *([None] * 11), model.get("transmission"),
                             model.get("variant"), model.get("code"), float(model["price"]), None,
                             "Reviewed transmission alternative", evidence))
            children = option_rows(vehicle, catalogue.get(vehicle.pk, []), receipt if observation else None)
            for transmission, variant, _, _, package, note, source in children:
                if source is not None:
                    data.append((number, vehicle.pk, None, *([None] * 11), transmission, variant,
                                 None, None, package, note, source))
        sources.append((year, "RigArchive", "Active VehicleDefinitions", None, None, "Derived database draft",
                        None, "Review pending", f"{len(configs)} definitions. Blank model codes indicate missing linked evidence."))
        for (file, digest), review in reviews.items():
            if review is None:
                sources.append((year, "RigArchive", "Retained observation unavailable or invalid", file, None,
                                "Observation", digest, "Evidence gap", "Observation fields were omitted."))
                continue
            sources.append((year, "RigArchive", "Retained factory observations", file, review.get("observed_on"),
                            "Human observation", digest, "Receipt hash verified", review.get("scope")))
            for source in review.get("sources", ()):
                url = source.get("url")
                host = urlparse(url).hostname if url else None
                official = bool(host and (host == "toyota.com" or host.endswith(".toyota.com")))
                source_title = source.get("title")
                archived = source_title == "Toyota Full Line Pricing" and not official
                organization = "Toyota" if official or archived else None
                kind = ("Manufacturer reference" if official else
                        "Manufacturer schedule on third-party host" if archived else "Reference cited by observation")
                note = source.get("observation")
                if source.get("revision_date"):
                    note = f"Document revision {source['revision_date']}. {note or ''}"
                sources.append((year, organization, source_title, url, review.get("observed_on"),
                                kind, digest, "Original bytes not verified", note))
    elif authored_rows:
        status = "Draft — supplied research; review pending"
        data.extend(authored_rows)
        sources.extend(authored_sources or [
            (year, None, "Research sources unavailable", None, None, None, None,
             "Evidence gap", "No provenance was supplied with this research draft.")
        ])
    else:
        sources.append((year, None, "Research pending", None, None, None, None, "Evidence gap",
                        "No generation-level draft was verified for this model year."))
    return Sheet(f"MY{year}", ((title,), (status,), (), HEADERS, *data), WIDTHS, (11, 17)), sources


def generation_title(generation):
    model = generation.vehicle_model
    generation_name = "4th Generation" if generation.name.casefold() == "fourth generation" else generation.name
    return f"{model.manufacturer.name} {model.name} — {generation_name} — Configuration Logic"


def generation_draft(generation):
    title = generation_title(generation)
    by_year = {}
    for vehicle in generation.vehicle_definitions.filter(is_active=True).select_related(
        "generation", "engine", "factory_body_configuration__bed_length",
    ).order_by("pk"):
        by_year.setdefault(vehicle.model_year, []).append(vehicle)
    last = max(by_year, default=generation.start_year)
    sheets, sources = [], []
    for year in range(last, generation.start_year - 1, -1):
        configurations = by_year.get(year, [])
        # Sparse legacy rows lack the body and registry evidence needed for this review.
        if configurations and not any(v.engine_id and v.factory_body_configuration_id for v in configurations):
            configurations = []
        sheet, evidence = draft_year(title, year, configurations)
        sheets.append(sheet)
        sources.extend(evidence)
    sheets.append(Sheet("Source References", ((title,), ("Draft provenance",), (), SOURCE_HEADERS, *sources),
                        (14, 18, 32, 60, 20, 29, 42, 28, 65)))
    return GenerationDraft(str(generation.uuid), title, tuple(sheets))


def export_generation(options):
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    if options["reviewed_observations"] is not None:
        raise CommandError("Generation export uses receipt-pinned evidence; --reviewed-observations applies to --year.")
    generation = select_generation(options["manufacturer"], options["model"], options["generation"])
    from reference.configuration_logic_google import read_registry
    from reference.configuration_logic_revisions import current_draft, load_revision, sheet_cells

    registry = Path(settings.BASE_DIR) / ".configuration-logic" / f"{generation.uuid}.json"
    state = read_registry(registry, str(generation.uuid), allow_pending=True)
    draft = current_draft(generation, registry, state)
    captured = load_revision(state, registry) or {}
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = draft.title
    for table in draft.sheets:
        sheet = workbook.create_sheet(table.name)
        for row in table.rows:
            sheet.append(row)
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                if cell.row >= table.header_row:
                    cell.alignment = Alignment(wrap_text=True, vertical="center")
                if cell.row == table.header_row:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="23445D")
                elif cell.row > table.header_row and cell.column - 1 in table.prices:
                    cell.number_format = "#,##0.00"
        if table.header_row > 1:
            for cell in sheet[1]:
                if cell.value is not None:
                    cell.font = Font(size=16, bold=True, color="17324D")
            for cell in sheet[2]:
                if cell.value is not None:
                    cell.font = Font(bold=True)
        if table.name in captured:
            for (row, col), data in sheet_cells(captured[table.name]).items():
                if col >= len(table.widths):
                    continue
                cell = sheet.cell(row + 1, col + 1)
                if data.get("note"):
                    cell.comment = Comment(data["note"], "RigArchive")
                number_format = data.get("userEnteredFormat", {}).get("numberFormat", {})
                if number_format.get("type") in {"NUMBER", "CURRENCY", "PERCENT", "DATE", "TIME", "DATE_TIME", "SCIENTIFIC", "TEXT"}:
                    if number_format.get("pattern"):
                        cell.number_format = number_format["pattern"]
        sheet.freeze_panes = f"A{table.header_row + 1}"
        sheet.sheet_view.showGridLines = False
        for index, width in enumerate(table.widths, 1):
            sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.auto_filter.ref = f"A{table.header_row}:{get_column_letter(len(table.widths))}{len(table.rows)}"
        sheet.print_title_rows = f"1:{table.header_row}"
        for row in range(table.header_row, len(table.rows) + 1):
            sheet.row_dimensions[row].height = 32 if table.prices else 48
    model = generation.vehicle_model
    output = options["output"] or (
        Path(settings.BASE_DIR) / "scratch" /
        f"{model.manufacturer.slug}-{model.slug}-{generation.slug}-configuration-logic.xlsx"
    )
    if output.suffix.lower() != ".xlsx":
        raise CommandError("Output must have an .xlsx extension.")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            try:
                workbook.save(stream)
            except Exception:
                output.unlink()
                raise
    except OSError as exc:
        raise CommandError(f"Cannot write XLSX: {exc}") from exc
    return output
