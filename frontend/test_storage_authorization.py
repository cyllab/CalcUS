import os
import uuid
from unittest import skipUnless

from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings

from .models import (
    Calculation,
    CalculationOrder,
    Ensemble,
    Molecule,
    Project,
    Property,
    Structure,
    User,
)
from .storage_backends.calculation_frames import (
    get_backend as get_frame_backend,
    save_frame_files,
)
from .storage_backends.calculation_outputs import (
    get_backend as get_output_backend,
    save_output_files,
)
from .storage_backends.property_storage import (
    get_backend as get_property_backend,
    save_property_files,
)


class StoredPayloadAuthorizationMixin:
    def setUp(self):
        self.owner = User.objects.create_user(
            email=f"storage-owner-{uuid.uuid4()}@example.com",
            password="password1234",
        )
        self.other_user = User.objects.create_user(
            email=f"storage-other-{uuid.uuid4()}@example.com",
            password="password1234",
        )
        self.project = Project.objects.create(name="Private project", author=self.owner)
        self.molecule = Molecule.objects.create(
            name="Private molecule", project=self.project
        )
        self.ensemble = Ensemble.objects.create(
            name="Private ensemble", parent_molecule=self.molecule
        )
        self.structure = Structure.objects.create(
            parent_ensemble=self.ensemble,
            xyz_structure="1\nprivate\nHe 0 0 0\n",
        )
        self.order = CalculationOrder.objects.create(
            name="Private order",
            author=self.owner,
            project=self.project,
            structure=self.structure,
        )
        self.calc = Calculation.objects.create(
            order=self.order,
            structure=self.structure,
            status=2,
        )
        self.prop = Property.objects.create(
            parent_structure=self.structure,
            uvvis="Wavelength,Absorbance\n300,1\n",
            ir_spectrum="Wavenumber,Intensity\n-1000,0.5\n",
            freq_animations=["1\nCalcUS\nHe 0 0 0 0 0 1\n"],
        )
        self.request_factory = RequestFactory()

    def _request(self, method="get", data=None):
        request = getattr(self.request_factory, method)("/", data or {})
        request.user = self.other_user
        return request


@override_settings(CALCULATION_OUTPUT_STORAGE_BACKEND="database")
class StoredPayloadAuthorizationTests(StoredPayloadAuthorizationMixin, TestCase):
    def test_unauthorized_user_cannot_download_output_files(self):
        from .views import download_log

        save_output_files(self.calc, {"calc": "private output log"})

        response = download_log(self._request(), self.calc.pk)

        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_cannot_read_frame_payloads(self):
        from .views import get_calc_frame

        save_frame_files(
            self.calc,
            {1: "1\nprivate frame\nHe 0 0 0\n"},
        )

        response = get_calc_frame(self._request(), self.calc.pk, 1)

        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_cannot_read_property_payloads(self):
        from .views import get_vib_animation, ir_spectrum, uvvis

        uvvis_response = uvvis(self._request(), self.prop.pk)
        ir_response = ir_spectrum(self._request(), self.prop.pk)
        vib_response = get_vib_animation(
            self._request("post", {"id": str(self.prop.pk), "num": "0"})
        )

        self.assertEqual(uvvis_response.status_code, 404)
        self.assertEqual(ir_response.status_code, 404)
        self.assertEqual(vib_response.status_code, 403)


@skipUnless(
    os.getenv("STORAGE_EMULATOR_HOST"),
    "fake-gcs-server is required for GCS storage authorization tests",
)
class GCSStoredPayloadAuthorizationTests(
    StoredPayloadAuthorizationMixin, TransactionTestCase
):
    def _settings(self):
        return override_settings(
            CALCULATION_OUTPUT_STORAGE_BACKEND="gcs",
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=f"storage-auth-{uuid.uuid4()}",
        )

    def test_unauthorized_user_cannot_download_gcs_output_files(self):
        from .views import download_log

        with self._settings():
            save_output_files(self.calc, {"calc": "private output log"})
            self.calc.refresh_from_db()
            metadata = self.calc.output_file_manifest["calc"]
            blob = (
                get_output_backend("gcs")
                .client.bucket(metadata["bucket"])
                .blob(metadata["key"])
            )
            self.assertTrue(blob.exists())

            response = download_log(self._request(), self.calc.pk)

        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_cannot_read_gcs_frame_payloads(self):
        from .views import get_calc_frame

        with self._settings():
            manifest = save_frame_files(
                self.calc,
                {1: "1\nprivate frame\nHe 0 0 0\n"},
            )
            blob = (
                get_frame_backend("gcs")
                .client.bucket(manifest["bucket"])
                .blob(manifest["key"])
            )
            self.assertTrue(blob.exists())

            response = get_calc_frame(self._request(), self.calc.pk, 1)

        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_cannot_read_gcs_property_payloads(self):
        from .views import get_vib_animation, ir_spectrum, uvvis

        with self._settings():
            save_property_files(
                self.prop,
                {
                    "uvvis": "Wavelength,Absorbance\n300,1\n",
                    "ir_spectrum": "Wavenumber,Intensity\n-1000,0.5\n",
                    "freq_animations": ["1\nCalcUS\nHe 0 0 0 0 0 1\n"],
                },
                backend_name="gcs",
            )
            self.prop.refresh_from_db()
            backend = get_property_backend("gcs")
            for metadata in self.prop.property_file_manifest.values():
                blob = backend.client.bucket(metadata["bucket"]).blob(metadata["key"])
                self.assertTrue(blob.exists())

            uvvis_response = uvvis(self._request(), self.prop.pk)
            ir_response = ir_spectrum(self._request(), self.prop.pk)
            vib_response = get_vib_animation(
                self._request("post", {"id": str(self.prop.pk), "num": "0"})
            )

        self.assertEqual(uvvis_response.status_code, 404)
        self.assertEqual(ir_response.status_code, 404)
        self.assertEqual(vib_response.status_code, 403)
