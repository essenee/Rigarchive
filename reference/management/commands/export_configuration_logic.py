"""Read-only model-year configuration review workbook."""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.utils.timezone import localdate

from reference.admin import factory_body_configuration_label
from reference.configuration_logic_queries import (
    authored_observations, catalogue_options, option_rows, sort_by_trim_price,
)
from reference.models import VehicleDefinition


PARENT_HEADERS = (
    "#", "Trim", "Body Configuration", "Drivetrain", "Engine Code",
    "Engine Variant", "Engine Name", "VehicleDefinition PK", "Slug", "Market", "Base MSRP",
)
OPTION_HEADERS = (
    "Transmission", "Engine Output Variant", "Horsepower", "Torque (lb-ft)",
    "Package", "Availability / Applicability", "Source Reference",
)
PARENT_WIDTHS = (6, 26, 22, 13, 14, 21, 23, 20, 38, 16, 15)
OPTION_WIDTHS = (24, 22, 12, 13, 24, 40, 36)


def source_rows(year, config_count, group_count, path, receipts):
    yield ("RigArchive export", "VehicleDefinition and related records", None, year,
           config_count, group_count, "Canonical database selection")
    if path is None:
        yield ("Manufacturer comparison pending", None, None, year, None, None,
               "Record the reviewed source and compare equivalent model-year and market scopes.")
        return
    raw = path.read_bytes()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    pinned = [r for r in receipts.values() if r.raw_artifact_hash == digest]
    if not pinned:
        raise CommandError("Reviewed observations do not match any in-scope authoring receipt.")
    review = json.loads(raw)
    configurations = review["configurations"]
    groups = set()
    for row in configurations:
        if "selected_toyota_model" in row:
            model = row["selected_toyota_model"]
            groups.add((model["trim"], model["cab"], model["bed"]))
        else:
            groups.add((row["manufacturer_marketed_trim"], row["cab"], row["bed"]))
    yield ("Retained manufacturer review", pinned[0].raw_artifact_reference,
           review["observed_on"], year, len(configurations), len(groups), review["scope"])
    yield ("Count difference", "RigArchive minus retained review", None, year,
           config_count - len(configurations), group_count - len(groups),
           f"{len(pinned)} active RigArchive rows have receipts pinned to this review. "
           "Check market and generation scope before adjudicating differences.")
    for source in review["sources"]:
        yield (source["title"], source["url"], review["observed_on"], year,
               None, None, source["observation"])


def write_workbook(stream, configurations, comparison):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    workbook.remove(workbook.active)
    first = configurations[0]
    model = first.generation.vehicle_model
    groups = {(v.trim_name, v.factory_body_configuration_id) for v in configurations}
    generations = sorted({v.generation.name for v in configurations})
    heading = f"MY{first.model_year}  {model.manufacturer.name} {model.name}"
    summary = f"{len(configurations)} canonical configurations  ·  {len(groups)} trim/body groups"
    generation_line = "Generation · " + ", ".join(generations)
    if len({v.market for v in configurations}) == 1:
        generation_line += f"  ·  {first.get_market_display()}"
    receipts = authored_observations(configurations)
    published = catalogue_options(configurations)

    def append(sheet, values):
        sheet.append(values)
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                # Database and evidence text must stay literal in Excel.
                cell.data_type = "s"

    def setup(name, headers, widths, freeze, note):
        sheet = workbook.create_sheet(name)
        for value in (heading, generation_line, summary, f"Generated {localdate():%Y-%m-%d}  ·  {note}"):
            append(sheet, (value,))
        append(sheet, headers)
        sheet.freeze_panes = freeze
        sheet.sheet_view.showGridLines = False
        for column, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(column)].width = width
        sheet["A1"].font = Font(name="Calibri", size=18, bold=True, color="17324D")
        sheet.row_dimensions[1].height = 27
        sheet.row_dimensions[5].height = 30
        for cell in sheet[5]:
            cell.fill = PatternFill("solid", fgColor="23445D")
            cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        return sheet

    inventory = setup("Vehicle Configurations", PARENT_HEADERS, PARENT_WIDTHS, "C6",
                      "Trim order uses lowest recorded base MSRP. See Factory Options for reviewed Engine alternatives.")
    options = setup("Factory Options", ("Parent #", *PARENT_HEADERS[7:9], *OPTION_HEADERS),
                    (10, 20, 39, *OPTION_WIDTHS), "C6", "Option-level records and unresolved availability")
    logic = setup("Configuration Logic", (*PARENT_HEADERS, *OPTION_HEADERS),
                  (*PARENT_WIDTHS, *OPTION_WIDTHS), "D6", "One numbered group per canonical definition")
    sources = setup("Source References",
                    ("Source Name", "URL / Document ID", "Review Date", "Model Year",
                     "Configurations", "Trim/Body Groups", "Verification Notes"),
                    (36, 58, 16, 12, 16, 18, 65), "B6", "Compare aligned market and model-year scopes")

    def style_rows(sheet, start, number, height):
        for row in sheet.iter_rows(min_row=start):
            sheet.row_dimensions[row[0].row].height = height
            for cell in row:
                cell.alignment = Alignment(vertical="center", wrap_text=True)
                if number % 2 == 0:
                    cell.fill = PatternFill("solid", fgColor="EFF4F7")

    bodies = {v.factory_body_configuration_id: v.factory_body_configuration
              for v in configurations if v.factory_body_configuration_id}
    body_labels = {pk: factory_body_configuration_label(body) for pk, body in bodies.items()}
    for number, vehicle in enumerate(configurations, 1):
        engine = vehicle.engine
        parent = (
            number, vehicle.trim_name, body_labels.get(vehicle.factory_body_configuration_id, "Unspecified"),
            vehicle.get_drivetrain_display(), engine.engine_code if engine else None,
            (engine.internal_variant_key or None) if engine else "Unresolved",
            engine.name if engine else vehicle.engine_name, vehicle.pk, vehicle.slug,
            vehicle.get_market_display(), vehicle.base_msrp,
        )
        append(inventory, parent)
        style_rows(inventory, inventory.max_row, number, 32)
        inventory.cell(inventory.max_row, len(parent)).number_format = "#,##0.00"
        option_start = options.max_row + 1
        logic_start = logic.max_row + 1
        children = option_rows(vehicle, published[vehicle.pk], receipts.get(vehicle.pk))
        for index, child in enumerate(children):
            append(options, (number, vehicle.pk, vehicle.slug, *child))
            append(logic, (*(parent if index == 0 else (None,) * len(parent)), *child))
        style_rows(options, option_start, number, 39)
        style_rows(logic, logic_start, number, 39)
        logic.cell(logic_start, len(parent)).number_format = "#,##0.00"
        if len(children) > 1:
            for column in range(1, len(parent) + 1):
                logic.merge_cells(start_row=logic_start, end_row=logic.max_row,
                                  start_column=column, end_column=column)

    for row in source_rows(first.model_year, len(configurations), len(groups), comparison, receipts):
        append(sources, row)
        style_rows(sources, sources.max_row, sources.max_row, 52)

    for sheet in (inventory, options, sources):
        sheet.auto_filter.ref = f"A5:{get_column_letter(sheet.max_column)}{sheet.max_row}"
    for sheet in workbook:
        sheet.print_title_rows = "1:5"
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3 if sheet is logic else sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
    workbook.save(stream)


class Command(BaseCommand):
    help = "Export active model-year vehicle configurations and factory options as an XLSX workbook."
    # This command only reads its selected records. No migration or system-check
    # preflight is needed to run the export.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--manufacturer", required=True)
        parser.add_argument("--model", required=True)
        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument("--year", type=int)
        selection.add_argument("--generation", help="Generation slug or PK.")
        parser.add_argument("--output", type=Path)
        parser.add_argument("--reviewed-observations", type=Path,
                            help="Optional retained authoring evidence for source comparison.")

    def handle(self, *args, **options):
        try:
            import openpyxl  # noqa: F401
        except ImportError as exc:
            raise CommandError("XLSX export requires the optional openpyxl package.") from exc

        if options["generation"]:
            from reference.configuration_logic import export_generation

            output = export_generation(options)
            self.stdout.write(f"Exported generation workbook to {output}")
            return

        manufacturer, model, year = (options[key] for key in ("manufacturer", "model", "year"))
        configurations = list(VehicleDefinition.objects.filter(
            generation__vehicle_model__manufacturer__name__iexact=manufacturer,
            generation__vehicle_model__name__iexact=model,
            model_year=year, is_active=True,
        ).select_related(
            "generation__vehicle_model__manufacturer", "factory_body_configuration__bed_length", "engine",
        ).order_by("generation__name", "generation_id", "trim_name",
                   "factory_body_configuration_id", "drivetrain", "market", "pk"))
        if not configurations:
            raise CommandError(f"No active configurations for MY{year} {manufacturer} {model}.")
        if len({vehicle.generation.vehicle_model_id for vehicle in configurations}) != 1:
            raise CommandError("More than one vehicle model matches the supplied manufacturer and model.")

        output = options["output"] or (
            settings.BASE_DIR / "scratch" / f"{slugify(manufacturer)}-{slugify(model)}-{year}-configuration-logic.xlsx"
        )
        if output.suffix.lower() != ".xlsx":
            raise CommandError("Output must have an .xlsx extension.")
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            stream = output.open("xb")
        except OSError as exc:
            raise CommandError(f"Cannot create {output}: {exc}") from exc
        try:
            with stream:
                write_workbook(stream, sort_by_trim_price(configurations), options["reviewed_observations"])
        except Exception as exc:
            output.unlink()
            if isinstance(exc, OSError):
                raise CommandError(str(exc)) from exc
            raise
        self.stdout.write(f"Exported {len(configurations)} configurations to {output}")
