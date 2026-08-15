"""
Automated Test Suite for Public Source Acquisition Adapters (RA-013).

Tests NHTSA vPIC and EPA FuelEconomy.gov acquisition adapters using controlled
response fixtures and isolated mock transport. Confirms zero network connectivity during normal test execution.
"""

from pathlib import Path
from django.test import TestCase

from reference.ingestion.acquisition import (
    EPAAdapter,
    NHTSAAdapter,
    SourceParseError,
    TransportError,
)
from reference.ingestion.contracts import SourceAssertionSet
from reference.ingestion.validation import validate_artifact


class AcquisitionAdaptersTestCase(TestCase):
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "acquisition"

    def _create_mock_transport(self, status_code: int, file_path: Path):
        """Helper to create a mock HTTP transport callable reading from fixture file."""
        def mock_transport(url: str, headers: dict, timeout_seconds: int):
            with open(file_path, "rb") as f:
                body = f.read()
            return status_code, body, {"Content-Type": "application/json"}
        return mock_transport

    def _create_error_transport(self, status_code: int, error_body: bytes = b"Server Error"):
        """Helper to create a mock HTTP transport returning error status codes."""
        def mock_transport(url: str, headers: dict, timeout_seconds: int):
            return status_code, error_body, {"Content-Type": "text/plain"}
        return mock_transport

    # --- 1. NHTSA Adapter Tests ---

    def test_nhtsa_adapter_construction(self):
        adapter = NHTSAAdapter(timeout_seconds=5)
        self.assertEqual(adapter.source_id, "nhtsa_vpic")
        self.assertEqual(adapter.timeout_seconds, 5)
        self.assertIn("RigArchive-Ingestion", adapter.user_agent)

    def test_nhtsa_acquire_models_success(self):
        fixture_path = self.fixtures_dir / "nhtsa" / "get_models_toyota_2020.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = NHTSAAdapter(transport=mock_transport)
        results = adapter.acquire_models_for_make_year("Toyota", 2020, target_model="4Runner")

        self.assertEqual(len(results), 1)
        sas = results[0]
        self.assertIsInstance(sas, SourceAssertionSet)

        # Validate against RA-012 contract validator
        validate_artifact(sas)

        self.assertEqual(sas.provenance.source_id, "nhtsa_vpic")
        self.assertEqual(sas.provenance.native_record_id, "11982")
        self.assertEqual(sas.provenance.target_context["make"], "Toyota")
        self.assertEqual(sas.provenance.target_context["model"], "4Runner")
        self.assertEqual(sas.provenance.target_context["model_year"], 2020)

        # Verify extracted raw assertions
        assertion_map = {a.attribute_key: a.raw_value for a in sas.source_assertions}
        self.assertEqual(assertion_map["make_id"], 448)
        self.assertEqual(assertion_map["make_name"], "Toyota")
        self.assertEqual(assertion_map["model_id"], 11982)
        self.assertEqual(assertion_map["model_name"], "4Runner")

    def test_nhtsa_transport_error_handling(self):
        mock_transport = self._create_error_transport(500, b"NHTSA Service Unavailable")
        adapter = NHTSAAdapter(transport=mock_transport)

        with self.assertRaises(TransportError) as ctx:
            adapter.acquire_models_for_make_year("Toyota", 2020)
        self.assertIn("HTTP 500", str(ctx.exception))

    def test_nhtsa_malformed_json_handling(self):
        def bad_json_transport(url, headers, timeout):
            return 200, b"{ invalid json payload ", {}

        adapter = NHTSAAdapter(transport=bad_json_transport)
        with self.assertRaises(SourceParseError) as ctx:
            adapter.acquire_models_for_make_year("Toyota", 2020)
        self.assertIn("invalid JSON", str(ctx.exception))

    # --- 2. EPA Adapter Tests ---

    def test_epa_adapter_construction(self):
        adapter = EPAAdapter(timeout_seconds=8)
        self.assertEqual(adapter.source_id, "epa_fueleconomy")
        self.assertEqual(adapter.timeout_seconds, 8)
        self.assertIn("RigArchive-Ingestion", adapter.user_agent)

    def test_epa_acquire_vehicle_by_id_success(self):
        fixture_path = self.fixtures_dir / "epa" / "vehicle_42101.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = EPAAdapter(transport=mock_transport)
        sas = adapter.acquire_vehicle_by_id("42101", make="Toyota", model="4Runner 4WD", model_year=2020)

        self.assertIsInstance(sas, SourceAssertionSet)
        validate_artifact(sas)

        self.assertEqual(sas.provenance.source_id, "epa_fueleconomy")
        self.assertEqual(sas.provenance.native_record_id, "42101")
        self.assertEqual(sas.provenance.target_context["make"], "Toyota")
        self.assertEqual(sas.provenance.target_context["model"], "4Runner 4WD")

        # Verify extracted raw assertions
        assertion_map = {a.attribute_key: a.raw_value for a in sas.source_assertions}
        self.assertEqual(assertion_map["model_year"], "2020")
        self.assertEqual(assertion_map["make"], "Toyota")
        self.assertEqual(assertion_map["model"], "4Runner 4WD")
        self.assertEqual(assertion_map["drive_descriptor"], "Part-time 4WD")
        self.assertEqual(assertion_map["engine_displacement_liters"], "4.0")
        self.assertEqual(assertion_map["engine_cylinders"], "6")
        self.assertEqual(assertion_map["transmission_descriptor"], "Automatic 5-spd")
        self.assertEqual(assertion_map["vehicle_class"], "Small Sport Utility Vehicle 4WD")

    def test_epa_transport_error_handling(self):
        mock_transport = self._create_error_transport(404, b"Not Found")
        adapter = EPAAdapter(transport=mock_transport)

        with self.assertRaises(TransportError) as ctx:
            adapter.acquire_vehicle_by_id("99999")
        self.assertIn("HTTP 404", str(ctx.exception))

    def test_epa_malformed_json_handling(self):
        def bad_json_transport(url, headers, timeout):
            return 200, b"<html>Error Page</html>", {}

        adapter = EPAAdapter(transport=bad_json_transport)
        with self.assertRaises(SourceParseError) as ctx:
            adapter.acquire_vehicle_by_id("42101")
        self.assertIn("invalid JSON", str(ctx.exception))
