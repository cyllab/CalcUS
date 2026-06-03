import os
import tempfile
import uuid
from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command
from django.test import RequestFactory, TransactionTestCase, override_settings

from .calculation_frames import (
    CalculationFrameStorageError,
    GCSCalculationFrameStorageBackend,
    delete_frame_files,
    flush_legacy_frame_payloads,
    has_frames,
    list_frame_files,
    read_all_frame_records,
    read_frame_record,
    save_frame_files,
)
from .models import (
    BasicStep,
    Calculation,
    CalculationFrame,
    CalculationOrder,
    Parameters,
    User,
)


class CalculationFrameStorageTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email=f"frame-storage-{uuid.uuid4()}@example.com",
            password="password1234",
        )
        self.parameters = Parameters.objects.create(charge=0, multiplicity=1)
        self.order = CalculationOrder.objects.create(
            name="Frame storage order", author=self.user, parameters=self.parameters
        )
        self.calc = Calculation.objects.create(
            order=self.order, parameters=self.parameters, status=2
        )
        self.request_factory = RequestFactory()

    def _create_legacy_frames(self, frames=None):
        for number, content in (
            frames
            or {
                1: "2\nframe 1\nH 0 0 0\nH 0 0 1\n",
                2: "2\nframe 2\nH 0 0 0\nH 0 0 2\n",
            }
        ).items():
            CalculationFrame.objects.create(
                parent_calculation=self.calc,
                number=number,
                xyz_structure=content,
                RMSD=number / 10,
                energy=number,
                converged=number == 2,
            )

    def test_legacy_frame_rows_remain_readable(self):
        self._create_legacy_frames()

        with self.assertLogs("frontend.calculation_frames", level="WARNING") as logs:
            record = read_frame_record(self.calc, 1)

        self.assertIn("frame 1", record["xyz_structure"])
        self.assertIn("no frame_file_manifest is present", logs.output[0])
        self.assertEqual(set(read_all_frame_records(self.calc)), {"1", "2"})
        self.assertEqual(set(list_frame_files(self.calc)), {"1", "2"})

    def test_database_backend_uses_calculation_frame_rows(self):
        manifest = save_frame_files(
            self.calc,
            {
                1: {"xyz_structure": "2\ndb frame 1\nH 0 0 0\nH 0 0 1\n", "RMSD": 0.4},
                2: "2\ndb frame 2\nH 0 0 0\nH 0 0 2\n",
            },
            backend_name="database",
        )
        self.calc.refresh_from_db()

        self.assertEqual(set(manifest), {"1", "2"})
        self.assertEqual(self.calc.calculationframe_set.count(), 2)
        self.assertEqual(self.calc.frame_file_manifest["1"]["backend"], "database")
        self.assertIn("frame_id", self.calc.frame_file_manifest["1"])
        self.assertEqual(self.calc.frame_file_manifest["1"]["RMSD"], 0.4)
        self.assertIn("db frame 1", read_frame_record(self.calc, 1)["xyz_structure"])

    @skipUnless(
        os.getenv("STORAGE_EMULATOR_HOST"),
        "fake-gcs-server is required for GCS frame storage tests",
    )
    def test_gcs_backend_uses_output_bucket_and_prefix(self):
        prefix = f"frame-gcs-{uuid.uuid4()}"
        with override_settings(
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=prefix,
        ):
            manifest = save_frame_files(
                self.calc,
                {
                    1: "1\ngcs frame one\nHe 0 0 0\n",
                    2: "1\ngcs frame two\nHe 0 0 1\n",
                },
                backend_name="gcs",
            )
            backend = GCSCalculationFrameStorageBackend()
            blob = backend.client.bucket(manifest["bucket"]).blob(manifest["key"])

            self.assertTrue(blob.exists())
            self.assertEqual(
                blob.download_as_text(),
                "1\ngcs frame one\nHe 0 0 0\n1\ngcs frame two\nHe 0 0 1\n",
            )
            self.assertEqual(manifest["format"], "multi_xyz")
            self.assertEqual(manifest["frames"]["2"]["frame_index"], 1)
            self.assertEqual(
                manifest["key"],
                f"{prefix}/calculation_frames/{self.calc.pk}/frames.xyz",
            )
            self.assertEqual(
                read_frame_record(self.calc, 2)["xyz_structure"],
                "1\ngcs frame two\nHe 0 0 1\n",
            )
            self.assertFalse(self.calc.calculationframe_set.exists())

    def test_flush_legacy_frames_preserves_metadata(self):
        self._create_legacy_frames()

        manifest = flush_legacy_frame_payloads(self.calc, backend_name="database")
        self.calc.refresh_from_db()
        records = read_all_frame_records(self.calc)

        self.assertEqual(set(manifest), {"1", "2"})
        self.assertEqual(records["1"]["RMSD"], 0.1)
        self.assertEqual(records["2"]["energy"], 2)
        self.assertTrue(records["2"]["converged"])

    def test_flush_selected_legacy_frames_only(self):
        self._create_legacy_frames(
            {
                1: "1\nlegacy one\nHe 0 0 0\n",
                2: "1\nlegacy two\nHe 0 0 0\n",
            }
        )

        manifest = flush_legacy_frame_payloads(
            self.calc, frame_numbers=[2], backend_name="database"
        )

        self.assertEqual(set(manifest), {"2"})
        self.assertEqual(set(read_all_frame_records(self.calc)), {"1", "2"})

    def test_manifest_read_falls_back_to_legacy_payload(self):
        self._create_legacy_frames({1: "1\nlegacy fallback\nHe 0 0 0\n"})
        self.calc.frame_file_manifest = {"1": {"backend": "gcs"}}
        self.calc.save(update_fields=["frame_file_manifest"])

        with self.assertLogs("frontend.calculation_frames", level="WARNING") as logs:
            record = read_frame_record(self.calc, 1)

        self.assertIn("legacy fallback", record["xyz_structure"])
        self.assertIn("after manifest read failed", logs.output[0])

    def test_unsupported_backend_is_rejected(self):
        with self.assertRaises(CalculationFrameStorageError):
            save_frame_files(
                self.calc,
                {1: "1\nunsupported\nHe 0 0 0\n"},
                backend_name="s3",
            )
        self.calc.refresh_from_db()
        self.assertEqual(self.calc.frame_file_manifest, {})

    def test_empty_legacy_payloads_are_ignored(self):
        self._create_legacy_frames(
            {
                1: "",
                2: "   ",
                3: "{}",
                4: "null",
                5: "1\nreal frame\nHe 0 0 0\n",
            }
        )

        self.assertTrue(has_frames(self.calc))
        self.assertEqual(set(read_all_frame_records(self.calc)), {"5"})
        self.assertEqual(set(list_frame_files(self.calc)), {"5"})

    def test_delete_frame_files_clears_manifest(self):
        save_frame_files(
            self.calc, {1: "1\nframe\nHe 0 0 0\n"}, backend_name="database"
        )

        delete_frame_files(self.calc)
        self.calc.refresh_from_db()

        self.assertEqual(self.calc.frame_file_manifest, {})

    def test_invalid_or_missing_frame_raises(self):
        with self.assertRaises(ValueError):
            read_frame_record(self.calc, "invalid")
        with self.assertRaises(FileNotFoundError):
            read_frame_record(self.calc, 1)
        with self.assertRaises(ValueError):
            save_frame_files(self.calc, {"not-a-number": "1\ninvalid\nHe 0 0 0\n"})
        self.calc.refresh_from_db()
        self.assertEqual(self.calc.frame_file_manifest, {})

    def test_get_calc_frame_view_uses_frame_storage(self):
        from .views import get_calc_frame

        save_frame_files(
            self.calc, {1: "1\nview frame\nHe 0 0 0\n"}, backend_name="database"
        )
        request = self.request_factory.get("/")
        request.user = self.user

        response = get_calc_frame(request, self.calc.pk, 1)
        missing = get_calc_frame(request, self.calc.pk, 2)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "1\nview frame\nHe 0 0 0\n")
        self.assertEqual(missing.status_code, 404)

    def test_format_frames_view_uses_all_frame_records(self):
        from .views import format_frames

        save_frame_files(
            self.calc,
            {
                1: {
                    "xyz_structure": "1\nfirst\nHe 0 0 0\n",
                    "RMSD": 0.5,
                    "energy": -10,
                    "converged": True,
                },
                2: {
                    "xyz_structure": "1\nsecond\nHe 0 0 1\n",
                    "RMSD": 0.2,
                    "energy": -9,
                    "converged": True,
                },
            },
            backend_name="database",
        )

        response = format_frames(self.calc, self.user)
        payload = response.content.decode()

        self.assertIn("1\nfirst\nHe 0 0 0\n1\nsecond\nHe 0 0 1\n", payload)
        self.assertIn("Frame,RMSD\n1,0.5\n2,0.2\n", payload)
        self.assertIn("Frame,Relative Energy\n1,0.0\n", payload)

    def test_launch_view_validates_requested_frame(self):
        from .views import launch

        request = self.request_factory.post(
            "/", {"calc_id": str(self.calc.pk), "frame_num": "1"}
        )
        request.user = self.user
        missing = launch(request)

        save_frame_files(
            self.calc, {1: "1\nlaunch frame\nHe 0 0 0\n"}, backend_name="database"
        )
        request = self.request_factory.post(
            "/", {"calc_id": str(self.calc.pk), "frame_num": "1"}
        )
        request.user = self.user
        with mock.patch("frontend.views.render") as render:
            render.return_value.status_code = 200
            launch(request)

        self.assertEqual(missing.status_code, 302)
        self.assertEqual(missing.url, "/")
        context = render.call_args.args[2]
        self.assertEqual(context["calc"], self.calc)
        self.assertEqual(context["frame_num"], 1)

    def test_migrate_calculation_frames_command_migrates_legacy_rows(self):
        self._create_legacy_frames({1: "1\nlegacy command\nHe 0 0 0\n"})
        stdout = StringIO()

        call_command(
            "migrate_calculation_frames",
            backend="database",
            batch_size=1,
            stdout=stdout,
        )
        self.calc.refresh_from_db()

        self.assertIn("Migrated frame payloads", stdout.getvalue())
        self.assertIn("1", self.calc.frame_file_manifest)
        self.assertIn("frame_id", self.calc.frame_file_manifest["1"])

    def test_verify_calculation_frame_manifests_accepts_database_entries(self):
        save_frame_files(
            self.calc, {1: "1\nverified\nHe 0 0 0\n"}, backend_name="database"
        )
        stdout = StringIO()

        call_command("verify_calculation_frame_manifests", all=True, stdout=stdout)

        self.assertIn("Failures: 0", stdout.getvalue())

    @skipUnless(
        os.getenv("STORAGE_EMULATOR_HOST"),
        "fake-gcs-server is required for GCS frame cleanup tests",
    )
    def test_calculation_delete_signal_deletes_gcs_frame_files(self):
        prefix = f"frame-delete-{uuid.uuid4()}"
        with override_settings(
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=prefix,
        ):
            manifest = save_frame_files(
                self.calc,
                {1: "1\ndelete frame\nHe 0 0 0\n"},
                backend_name="gcs",
            )
            backend = GCSCalculationFrameStorageBackend()
            blob = backend.client.bucket(manifest["bucket"]).blob(manifest["key"])
            self.assertTrue(blob.exists())

            self.calc.delete()

            self.assertFalse(blob.exists())

    @skipUnless(
        os.getenv("STORAGE_EMULATOR_HOST"),
        "fake-gcs-server is required for GCS frame migration tests",
    )
    def test_switching_from_database_to_gcs_migrates_existing_frame_rows(self):
        save_frame_files(
            self.calc,
            {
                1: {
                    "xyz_structure": "1\ndatabase frame one\nHe 0 0 0\n",
                    "RMSD": 0.8,
                    "energy": -5,
                    "converged": True,
                },
                2: {
                    "xyz_structure": "1\ndatabase frame two\nHe 0 0 1\n",
                    "RMSD": 0.4,
                    "energy": -4,
                    "converged": False,
                },
            },
            backend_name="database",
        )
        self.assertEqual(
            self.calc.calculationframe_set.get(number=1).xyz_structure,
            "1\ndatabase frame one\nHe 0 0 0\n",
        )

        prefix = f"frame-migration-{uuid.uuid4()}"
        with override_settings(
            CALCULATION_OUTPUT_STORAGE_BACKEND="gcs",
            CALCULATION_OUTPUT_BUCKET="calcus-test-outputs",
            CALCULATION_OUTPUT_PREFIX=prefix,
        ):
            manifest = flush_legacy_frame_payloads(self.calc)
            self.calc.refresh_from_db()
            backend = GCSCalculationFrameStorageBackend()
            blob = backend.client.bucket(manifest["bucket"]).blob(manifest["key"])

            self.assertEqual(manifest["backend"], "gcs")
            self.assertEqual(
                manifest["key"],
                f"{prefix}/calculation_frames/{self.calc.pk}/frames.xyz",
            )
            self.assertEqual(manifest["format"], "multi_xyz")
            self.assertTrue(blob.exists())
            self.assertEqual(
                blob.download_as_text(),
                "1\ndatabase frame one\nHe 0 0 0\n1\ndatabase frame two\nHe 0 0 1\n",
            )
            self.assertEqual(
                self.calc.calculationframe_set.get(number=1).xyz_structure, ""
            )
            self.assertEqual(
                self.calc.calculationframe_set.get(number=2).xyz_structure, ""
            )
            record = read_frame_record(self.calc, 2)

        self.assertEqual(record["xyz_structure"], "1\ndatabase frame two\nHe 0 0 1\n")
        self.assertEqual(record["RMSD"], 0.4)
        self.assertEqual(record["energy"], -4)
        self.assertFalse(record["converged"])

    def test_analyse_opt_xtb_writes_frames_through_storage_helper(self):
        from . import tasks

        self.calc.step = BasicStep.objects.create(name="Geometrical Optimisation")
        self.calc.save(update_fields=["step"])

        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = os.path.join(tmpdir, str(self.calc.id))
            os.makedirs(calc_dir)
            with open(os.path.join(calc_dir, "xtbopt.log"), "w") as handle:
                handle.write(
                    "2\ncomment a b 0.12\nH 0 0 0\nH 0 0 1\n"
                    "2\ncomment a b 0.23\nH 0 0 0\nH 0 0 2\n"
                )

            with mock.patch.object(tasks, "CALCUS_SCR_HOME", tmpdir), mock.patch.object(
                tasks, "save_frame_files"
            ) as save:
                tasks.analyse_opt_xtb(self.calc)

        save.assert_called_once()
        payloads = save.call_args.args[1]
        self.assertEqual(set(payloads), {1, 2})
        self.assertEqual(payloads[1]["RMSD"], "0.12")
        self.assertIn("H 0 0 2", payloads[2]["xyz_structure"])
