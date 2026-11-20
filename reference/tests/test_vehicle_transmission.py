import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from unittest.mock import patch

from reference.admin import VehicleDefinitionAdminForm
from reference.body_identity import authoring_configuration_key
from reference.configuration_logic import HEADERS, Sheet, WIDTHS
from reference.configuration_logic_authoring import b3_offers
from reference.configuration_logic_layout import catalog
from reference.models import ImportExecutionReceipt, VehicleDefinition
from reference.powertrain import record_powertrain
from reference.services import get_generation_hub_context
from reference.tests import test_pickup_authoring as pickup
from reference.transmission import normalize_source_transmission
from reference.vehicle_authoring import author_configurations, reviewed_transmission_manifest


class VehicleTransmissionTests(TestCase):
    setUpTestData = classmethod(pickup.PickupAuthoringTests.setUpTestData.__func__)
    proposal = pickup.PickupAuthoringTests.proposal

    def test_validation_and_source_normalization(self):
        for value in ("", "8-spd Auto", "6-spd Man", "10-spd Auto", "7-spd DCT", "CVT", "eCVT"):
            row = self.proposal(transmission=value)
            row.full_clean()
        self.assertEqual(normalize_source_transmission("6-Speed Manual"), "6-spd Man")
        self.assertEqual(normalize_source_transmission("8-speed Automatic Transmission"), "8-spd Auto")
        for value in ("8 speed automatic", "0-spd Man", "8-spd CVT", "unknown", "CVT\n"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.proposal(transmission=value).save()
        self.assertFalse(VehicleDefinitionAdminForm().fields["transmission"].required)
        form = VehicleDefinitionAdminForm(data={"transmission": "automatic"})
        self.assertIn("Use a factory designation", form.errors["transmission"][0])

    def test_known_siblings_duplicates_and_legacy_slugs(self):
        original = self.proposal()
        original.save()
        legacy_slug = original.slug
        self.assertNotIn("transmission", json.loads(authoring_configuration_key(original)))
        with self.assertRaisesMessage(ValidationError, "overlapping transmission"):
            self.proposal(transmission="6-spd Man").save()
        original.transmission = "8-spd Auto"
        original.save(update_fields=["transmission"])
        self.assertEqual(original.slug, legacy_slug)
        manual = self.proposal(transmission="6-spd Man", engine=self.manual)
        manual.save()
        self.assertTrue(manual.slug.endswith("-6-spd-man"))
        self.assertNotEqual(authoring_configuration_key(original), authoring_configuration_key(manual))
        with self.assertRaisesMessage(ValidationError, "overlapping transmission"):
            self.proposal(transmission="6-spd Man").save()
        with self.assertRaisesMessage(ValidationError, "overlapping transmission"):
            self.proposal().save()
        self.assertEqual(VehicleDefinition.objects.get(pk=manual.pk).engine_id, self.manual.pk)
        context = get_generation_hub_context(self.gen, config_slug=manual.slug)
        self.assertEqual(context["selected_config"].pk, manual.pk)
        self.assertTrue(any("6-spd Man · 4WD" in row.choice_label for row in context["configuration_browser_choices"]))
        original_key = authoring_configuration_key(manual)
        original_slug = manual.slug
        manual.transmission = "6-Spd Man"
        manual.save(update_fields=["transmission"])
        manual.refresh_from_db()
        self.assertEqual(authoring_configuration_key(manual), original_key)
        self.assertEqual(manual.slug, original_slug)
        with self.assertRaisesMessage(ValidationError, "overlapping transmission"):
            self.proposal(transmission="6-spd Man").save()
        context = get_generation_hub_context(self.gen, config_slug=manual.slug)
        self.assertTrue(any("6-Spd Man · 4WD" in row.choice_label for row in context["configuration_browser_choices"]))
        manual.is_active = False
        manual.save(update_fields=["is_active"])
        self.assertFalse(any(row.pk == manual.pk for row in get_generation_hub_context(
            self.gen, model_year=2026)["configuration_browser_choices"]))

    def test_approved_manifest_staleness_receipts_and_rollback(self):
        with TemporaryDirectory() as temp, override_settings(BASE_DIR=Path(temp)):
            path = Path(temp) / "observations.json"
            authorization = "Exact test offers"
            def proposed():
                return [(self.proposal(transmission="8-spd Auto"), None),
                        (self.proposal(transmission="6-spd Man", engine=self.manual), None)]
            observations = []
            for i, (v, _) in enumerate(proposed()):
                engine = v.engine
                observations.append({"identity": authoring_configuration_key(v), "engine_name": v.engine_name,
                    "base_msrp": None, "transmission_evidence": {"locator": "Synthetic exact offer"},
                    "selected_toyota_model": {"code": str(7542 + i), "variant": engine.internal_variant_key,
                                             "transmission": v.transmission},
                    "engine_options": [{"pk": engine.pk, "uuid": str(engine.uuid), "name": engine.name,
                                        "engine_code": engine.engine_code, "internal_variant_key": engine.internal_variant_key,
                                        "powertrain": record_powertrain(engine)}]})
            raw = json.dumps({"record_type": "human-reviewed-factory-observations", "configurations": observations}).encode()
            path.write_bytes(raw)
            evidence_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
            def approve():
                return reviewed_transmission_manifest(proposed(), evidence_hash=evidence_hash,
                                                      authorization=authorization)["manifest_hash"]
            digest = approve()
            extra = self.proposal(body=self.bodies[0])
            extra.save()
            def execute(pin):
                return author_configurations(proposed(), evidence_reference=path.name, evidence_hash=evidence_hash,
                                             authorization=authorization, operator_label="tester", approved_manifest_hash=pin)
            with self.assertRaisesMessage(ValidationError, "stale or not approved"):
                execute(digest)
            digest = approve()
            with patch.object(ImportExecutionReceipt, "save", side_effect=RuntimeError("receipt failed")):
                with self.assertRaisesMessage(RuntimeError, "receipt failed"):
                    execute(digest)
            self.assertEqual(VehicleDefinition.objects.count(), 1)
            result = execute(digest)
            self.assertEqual([(v.transmission, r.native_identifier) for v,r in result],
                             [("8-spd Auto", "7542"), ("6-spd Man", "7543")])
            self.assertTrue(all(r.manifest_hash == digest and r.resolution_snapshot_json["profile"] ==
                                "human-body-authoring/2" for _,r in result))
            with self.assertRaisesMessage(ValidationError, "stale or not approved"):
                execute(digest)

    def test_b3_alternative_overlays_are_bound_and_provenance_stays_separate(self):
        parent = (1,None,"7594","SR","Double Cab, 5-ft Bed","Double Cab","5-ft","4WD","T24A-FTS",
                  "i-force-228hp","Turbo",36900,None,"United States","8-speed automatic",
                  None,None,None,None,"Retail","Toyota table")
        alternate = (1,None,None,*([None]*11),"6-speed manual","i-force-270hp","7547",36900,None,"Alternative","Toyota table")
        fields = [field for field,_ in catalog("MY2024")[:21]]
        binding = {"header_row":1,"display_order":fields,"rows":[{"row":2,"id":"auto","parent_id":None},
                                                                  {"row":3,"id":"manual","parent_id":"auto"}]}
        table = Sheet("MY2024",(HEADERS,parent,alternate),WIDTHS,header_row=1)
        offers = b3_offers(table,binding)
        self.assertEqual([(r["code"],r["transmission"],r["variant"]) for r in offers],
                         [("7594","8-spd Auto","i-force-228hp"),("7547","6-spd Man","i-force-270hp")])
        self.assertEqual(offers[1]["parent_id"], "auto")
        altered = list(alternate)
        altered[7] = "2WD"
        with self.assertRaisesMessage(ValidationError,"contradicts"):
            b3_offers(Sheet("MY2024",(HEADERS,parent,tuple(altered)),WIDTHS,header_row=1),binding)
