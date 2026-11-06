from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from reference.ingestion.attribution import Attribution, resolve_attribution


class AttributionTests(SimpleTestCase):
    def test_defaults_configuration_and_overrides(self):
        with TemporaryDirectory() as folder, override_settings(BASE_DIR=folder):
            with patch.dict("os.environ", {"LOGNAME": "sensitive-test-name", "USER": "sensitive-test-name"}):
                self.assertEqual(resolve_attribution(), Attribution("project_owner", "codex"))
            (Path(folder) / ".rigarchive.toml").write_text('[attribution]\ndirector="director_role"\nagent="local_agent"')
            self.assertEqual(resolve_attribution(), Attribution("director_role", "local_agent"))
            self.assertEqual(resolve_attribution(operator="delegate", agent="review_agent"),
                             Attribution("delegate", "review_agent"))

    def test_invalid_config_and_overrides_fail_without_disclosing_values(self):
        with TemporaryDirectory() as folder, override_settings(BASE_DIR=folder):
            with self.assertRaisesRegex(ValueError, "Invalid attribution director"):
                resolve_attribution(operator="")
            path = Path(folder) / ".rigarchive.toml"
            for content in ('[attribution', '[attribution]\nagent=42', '[attribution]\ninterface="other"'):
                with self.subTest(content=content):
                    path.write_text(content)
                    with self.assertRaises(ValueError):
                        resolve_attribution()
