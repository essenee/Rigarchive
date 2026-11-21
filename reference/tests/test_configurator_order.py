from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from reference.configuration_logic import GENERATION_COLUMN_ORDER, HEADERS, WIDTHS, GenerationDraft, Sheet
from reference.configuration_logic_google import desired_values
from reference.configuration_logic_order import configurator_order_plan
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class ConfiguratorOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Toyota")
        model = VehicleModel.objects.create(manufacturer=maker, name="4Runner")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Sixth Generation", start_year=2025)
        cls.url = reverse("reference:generation-detail", args=[maker.slug, model.slug, cls.generation.slug])
        for year in (2025, 2026):
            for index in range(16):
                VehicleDefinition.objects.create(
                    generation=cls.generation, model_year=year,
                    trim_name=f"Trim {index // 2:02}", drivetrain="4WD" if index % 2 else "2WD",
                    base_msrp=20000 + index,
                )

    def workbook(self, order_by_year):
        sheets, remote = [], {}
        for year, records in order_by_year.items():
            name, title = f"MY{year}", "Toyota 4Runner"
            headers = tuple(HEADERS[i] for i in GENERATION_COLUMN_ORDER)
            rows = [(title,), ("Draft",), (), headers]
            for position, vehicle in enumerate(records, 1):
                row = {0: position, 1: vehicle.pk, 2: str(vehicle.pk), 3: vehicle.trim_name,
                       7: vehicle.drivetrain, 12: vehicle.slug, 13: vehicle.get_market_display()}
                rows.append(tuple(row.get(i) for i in GENERATION_COLUMN_ORDER))
            sheet = Sheet(name, tuple(rows), tuple(WIDTHS[i] for i in GENERATION_COLUMN_ORDER), numbering=True)
            sheets.append(sheet)
            values = desired_values(sheet)
            remote[name] = {"data": [{"rowData": [
                {"values": [{"userEnteredValue": values[r, c]} if (r, c) in values else {}
                            for c in range(len(headers))]} for r in range(len(rows))
            ]}]}
        return GenerationDraft(str(self.generation.uuid), "Toyota 4Runner", tuple(sheets)), remote

    def test_numbered_correspondences_and_rendered_order_for_both_years(self):
        records = self.generation.vehicle_definitions.order_by("pk").in_bulk()
        by_year = {year: [v for v in records.values() if v.model_year == year] for year in (2025, 2026)}
        by_year[2025].reverse()
        by_year[2026] = by_year[2026][5:] + by_year[2026][:5]
        draft, remote = self.workbook(by_year)
        plan = configurator_order_plan(draft, remote, records, by_year)
        self.assertEqual([(e["year"], e["number"], e["pk"]) for e in plan], [
            (year, n, v.pk) for year, group in by_year.items() for n, v in enumerate(group, 1)
        ])
        before = {row["id"]: row for row in VehicleDefinition.objects.values()}
        for assignment in plan:
            VehicleDefinition.objects.filter(pk=assignment["pk"]).update(configurator_order=assignment["number"])
            before[assignment["pk"]]["configurator_order"] = assignment["number"]
        self.assertEqual({row["id"]: row for row in VehicleDefinition.objects.values()}, before)

        for year, group in by_year.items():
            response = self.client.get(self.url, {"year": year})
            self.assertEqual(response.status_code, 200)
            trims = list(dict.fromkeys(v.trim_name for v in group))
            self.assertEqual([g["trim"] for g in response.context["available_trim_groups"]], trims)
            html = response.content.decode()
            offsets = [html.index(f"&amp;trim={trim.replace(' ', '%20')}#configurations") for trim in trims]
            self.assertEqual(offsets, sorted(offsets))
            for trim in trims:
                page = self.client.get(self.url, {"year": year, "trim": trim}).content.decode()
                choices = [v for v in group if v.trim_name == trim]
                offsets = [page.index(f"&amp;configuration={v.slug}#configurations") for v in choices]
                self.assertEqual(offsets, sorted(offsets))

    def test_moved_rows_change_numbers_and_conflicting_slug_is_rejected(self):
        vehicles = self.generation.vehicle_definitions.filter(model_year=2025).in_bulk()
        rows = list(vehicles.values())
        draft, remote = self.workbook({2025: rows})
        before = configurator_order_plan(draft, remote, vehicles, [2025])
        cells = remote["MY2025"]["data"][0]["rowData"]
        cells[4], cells[5] = cells[5], cells[4]
        after = configurator_order_plan(draft, remote, vehicles, [2025])
        self.assertEqual(after[0], {**before[1], "number": 1})
        self.assertEqual(after[1], {**before[0], "number": 2})
        self.assertEqual(after[2:], before[2:])
        column = GENERATION_COLUMN_ORDER.index(12)
        cells[4]["values"][column]["userEnteredValue"] = {"stringValue": "wrong-slug"}
        with self.assertRaisesMessage(CommandError, "exact standalone canonical correspondence"):
            configurator_order_plan(draft, remote, vehicles, [2025])

    def test_nulls_use_deterministic_fallback_after_assigned_numbers(self):
        rows = self.generation.vehicle_definitions.filter(model_year=2025, trim_name="Trim 07")
        rows.filter(drivetrain="4WD").update(configurator_order=1)
        response = self.client.get(self.url, {"year": 2025})
        self.assertEqual(response.context["available_trims"], ["Trim 07", *(f"Trim {i:02}" for i in range(7))])
        response = self.client.get(self.url, {"year": 2025, "trim": "Trim 07"})
        self.assertEqual([v.drivetrain for v in response.context["configuration_browser_choices"]], ["4WD", "2WD"])
