import os
import uuid
from unittest import skipUnless

from django.test import TransactionTestCase, override_settings

from .calculation_outputs import get_backend, read_all_output_files, save_output_files
from .models import Calculation, CalculationOrder, User


@skipUnless(
    os.getenv("STORAGE_EMULATOR_HOST"),
    "fake-gcs-server is required for GCS calculation output cleanup tests",
)
class GCSCalculationOutputDeletionTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email=f"output-cleanup-{uuid.uuid4()}@example.com", password="password1234"
        )
        self.order = CalculationOrder.objects.create(
            name="Output cleanup order", author=self.user
        )
        self.prefix = f"delete-test-{uuid.uuid4()}"

    def _create_calc_with_gcs_outputs(self, order=None, outputs=None):
        calc = Calculation.objects.create(order=order or self.order)
        save_output_files(
            calc,
            outputs
            or {
                "calc": f"primary log contents for {calc.pk}",
                "extra": f"secondary log contents for {calc.pk}",
            },
            backend_name="gcs",
        )
        calc.refresh_from_db()

        backend = get_backend("gcs")
        blobs = [
            backend.client.bucket(metadata["bucket"]).blob(metadata["key"])
            for metadata in calc.output_file_manifest.values()
        ]
        self.assertTrue(all(blob.exists() for blob in blobs))
        return calc, blobs

    def _settings(self):
        return override_settings(
            CALCULATION_OUTPUT_STORAGE_BACKEND="gcs",
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=self.prefix,
        )

    def test_gcs_outputs_are_deleted_when_calculation_is_deleted(self):
        with self._settings():
            calc, blobs = self._create_calc_with_gcs_outputs()

            self.assertEqual(
                read_all_output_files(calc)["calc"],
                f"primary log contents for {calc.pk}",
            )

            calc.delete()

            self.assertFalse(any(blob.exists() for blob in blobs))

    def test_gcs_outputs_are_deleted_when_calculation_is_bulk_deleted(self):
        with self._settings():
            calc, blobs = self._create_calc_with_gcs_outputs()

            Calculation.objects.filter(pk=calc.pk).delete()

            self.assertFalse(any(blob.exists() for blob in blobs))

    def test_gcs_outputs_are_deleted_when_order_cascades_delete(self):
        with self._settings():
            calc_1, blobs_1 = self._create_calc_with_gcs_outputs(
                outputs={"calc": "first calculation log"}
            )
            calc_2, blobs_2 = self._create_calc_with_gcs_outputs(
                outputs={"calc": "second calculation log", "extra": "second extra log"}
            )
            all_blobs = blobs_1 + blobs_2

            self.order.delete()

            self.assertFalse(
                Calculation.objects.filter(pk__in=[calc_1.pk, calc_2.pk]).exists()
            )
            self.assertFalse(any(blob.exists() for blob in all_blobs))

    def test_missing_gcs_output_does_not_block_calculation_delete(self):
        with self._settings():
            calc, blobs = self._create_calc_with_gcs_outputs()
            blobs[0].delete()
            self.assertFalse(blobs[0].exists())
            self.assertTrue(blobs[1].exists())

            calc.delete()

            self.assertFalse(Calculation.objects.filter(pk=calc.pk).exists())
            self.assertFalse(any(blob.exists() for blob in blobs))
