import os
import uuid
from io import StringIO
from unittest import skipUnless

from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings

from .models import Property
from .storage_backends.property_storage import (
    get_backend,
    read_property_file,
    save_property_files,
)


class DatabasePropertyStorageTests(TestCase):
    @override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="database")
    def test_database_backend_roundtrip_uses_legacy_fields(self):
        prop = Property.objects.create(
            uvvis="Wavelength,Absorbance\n300,1\n",
            freq_animations=["2\nCalcUS\nH 0 0 0 0 0 1\n"],
        )

        prop.refresh_from_db()
        self.assertEqual(prop.property_file_manifest, {})
        self.assertEqual(
            read_property_file(prop, "uvvis"), "Wavelength,Absorbance\n300,1\n"
        )
        self.assertEqual(
            read_property_file(prop, "freq_animations"), ["2\nCalcUS\nH 0 0 0 0 0 1\n"]
        )

    @override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="database")
    def test_save_property_files_database_backend_updates_legacy_fields(self):
        prop = Property.objects.create()

        save_property_files(prop, {"mo_diagram": "diagram"}, backend_name="database")
        prop.refresh_from_db()

        self.assertEqual(prop.mo_diagram, "diagram")
        self.assertEqual(prop.property_file_manifest, {})

    @override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="gcs")
    def test_manifest_read_failure_falls_back_to_legacy_database_field(self):
        prop = Property.objects.create(uvvis="legacy uvvis")
        prop.property_file_manifest = {
            "uvvis": {"backend": "unsupported", "key": "missing"}
        }

        with self.assertLogs(
            "frontend.storage_backends.property_storage", level="WARNING"
        ) as logs:
            self.assertEqual(read_property_file(prop, "uvvis"), "legacy uvvis")

        self.assertIn("Falling back to legacy Property.uvvis", logs.output[0])

    @override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="database")
    def test_database_backend_mode_ignores_manifest_and_reads_legacy_field(self):
        prop = Property.objects.create(uvvis="legacy uvvis")
        prop.property_file_manifest = {
            "uvvis": {"backend": "unsupported", "key": "missing"}
        }

        self.assertEqual(read_property_file(prop, "uvvis"), "legacy uvvis")


@skipUnless(
    os.getenv("STORAGE_EMULATOR_HOST"),
    "fake-gcs-server is required for GCS property storage tests",
)
class GCSPropertyStorageTests(TransactionTestCase):
    def _settings(self, prefix=None):
        return override_settings(
            CALCULATION_OUTPUT_STORAGE_BACKEND="gcs",
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=prefix or f"property-gcs-{uuid.uuid4()}",
        )

    def _create_legacy_property(self, **kwargs):
        defaults = {
            "uvvis": "Wavelength,Absorbance\n300,1\n",
            "ir_spectrum": "Wavenumber,Intensity\n-1000,0.5\n",
            "freq_animations": ["2\nCalcUS\nH 0 0 0 0 0 1\n"],
        }
        defaults.update(kwargs)
        with override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="database"):
            return Property.objects.create(**defaults)

    def test_gcs_backend_stores_payloads_and_clears_legacy_fields(self):
        with self._settings():
            prop = Property.objects.create(
                uvvis="Wavelength,Absorbance\n300,1\n",
                freq_animations=["2\nCalcUS\nH 0 0 0 0 0 1\n"],
            )
            prop.refresh_from_db()

            self.assertEqual(prop.uvvis, "")
            self.assertEqual(prop.freq_animations, [])
            self.assertIn("uvvis", prop.property_file_manifest)
            self.assertIn("freq_animations", prop.property_file_manifest)
            self.assertEqual(
                read_property_file(prop, "uvvis"), "Wavelength,Absorbance\n300,1\n"
            )
            self.assertEqual(
                read_property_file(prop, "freq_animations"),
                ["2\nCalcUS\nH 0 0 0 0 0 1\n"],
            )

    def test_gcs_payloads_are_deleted_with_property(self):
        with self._settings():
            prop = Property.objects.create(uvvis="Wavelength,Absorbance\n300,1\n")
            prop.refresh_from_db()
            backend = get_backend("gcs")
            metadata = prop.property_file_manifest["uvvis"]
            blob = backend.client.bucket(metadata["bucket"]).blob(metadata["key"])
            self.assertTrue(blob.exists())

            prop.delete()

            self.assertFalse(blob.exists())

    def test_migrate_property_files_dry_run_does_not_upload_or_update_manifest(self):
        prop = self._create_legacy_property()
        stdout = StringIO()

        with self._settings():
            call_command("migrate_property_files", dry_run=True, stdout=stdout)

        prop.refresh_from_db()
        self.assertIn(
            "Would process 3 legacy Property field payload(s)", stdout.getvalue()
        )
        self.assertEqual(prop.property_file_manifest, {})
        self.assertEqual(prop.uvvis, "Wavelength,Absorbance\n300,1\n")
        self.assertEqual(prop.freq_animations, ["2\nCalcUS\nH 0 0 0 0 0 1\n"])

    def test_migrate_property_files_to_gcs_keeps_legacy_without_clear_flag(self):
        prop = self._create_legacy_property()
        prefix = f"property-migrate-keep-{uuid.uuid4()}"

        with self._settings(prefix=prefix):
            stdout = StringIO()
            call_command("migrate_property_files", batch_size=1, stdout=stdout)
            prop.refresh_from_db()
            backend = get_backend("gcs")
            uvvis_metadata = prop.property_file_manifest["uvvis"]
            freq_metadata = prop.property_file_manifest["freq_animations"]
            uvvis_blob = backend.client.bucket(uvvis_metadata["bucket"]).blob(
                uvvis_metadata["key"]
            )
            freq_blob = backend.client.bucket(freq_metadata["bucket"]).blob(
                freq_metadata["key"]
            )

            self.assertIn("Uploaded 3 field payload(s)", stdout.getvalue())
            self.assertTrue(uvvis_blob.exists())
            self.assertTrue(freq_blob.exists())
            self.assertEqual(
                uvvis_metadata["key"], f"{prefix}/properties/{prop.pk}/uvvis.txt"
            )
            self.assertEqual(
                freq_metadata["key"],
                f"{prefix}/properties/{prop.pk}/freq_animations.json",
            )
            self.assertEqual(
                read_property_file(prop, "uvvis"), "Wavelength,Absorbance\n300,1\n"
            )
            self.assertEqual(
                read_property_file(prop, "freq_animations"),
                ["2\nCalcUS\nH 0 0 0 0 0 1\n"],
            )

        prop.refresh_from_db()
        self.assertEqual(prop.uvvis, "Wavelength,Absorbance\n300,1\n")
        self.assertEqual(prop.freq_animations, ["2\nCalcUS\nH 0 0 0 0 0 1\n"])

    def test_migrate_property_files_to_gcs_can_clear_legacy_fields(self):
        prop = self._create_legacy_property()

        with self._settings():
            call_command("migrate_property_files", clear_legacy=True)
            prop.refresh_from_db()

            self.assertEqual(prop.uvvis, "")
            self.assertEqual(prop.ir_spectrum, "")
            self.assertEqual(prop.freq_animations, [])
            self.assertEqual(
                read_property_file(prop, "uvvis"), "Wavelength,Absorbance\n300,1\n"
            )
            self.assertEqual(
                read_property_file(prop, "ir_spectrum"),
                "Wavenumber,Intensity\n-1000,0.5\n",
            )
            self.assertEqual(
                read_property_file(prop, "freq_animations"),
                ["2\nCalcUS\nH 0 0 0 0 0 1\n"],
            )
