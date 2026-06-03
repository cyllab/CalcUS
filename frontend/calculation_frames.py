"""Storage for calculation frame XYZ payloads.

New frames are written to ``CalculationFrame`` rows for the ``database`` backend
or to the calculation output GCS bucket for the ``gcs`` backend. In both cases,
``Calculation.frame_file_manifest`` stores frame metadata.
"""

import logging
import os

from django.conf import settings

from .models import CalculationFrame

CONTENT_TYPE = "chemical/x-xyz"
LEGACY_EMPTY_VALUES = ("", "{}", "null")
FRAME_METADATA_DEFAULTS = {"RMSD": 0, "converged": False, "energy": 0}
logger = logging.getLogger(__name__)


class CalculationFrameStorageError(Exception):
    pass


def _backend_name():
    return settings.CALCULATION_OUTPUT_STORAGE_BACKEND.lower()


def _manifest(calc):
    manifest = getattr(calc, "frame_file_manifest", None) or {}
    return manifest if isinstance(manifest, dict) else {}


def _stored_manifest(calc):
    if not getattr(calc, "pk", None):
        return _manifest(calc)
    manifest = (
        calc.__class__.objects.filter(pk=calc.pk)
        .values_list("frame_file_manifest", flat=True)
        .first()
    )
    return manifest if isinstance(manifest, dict) else {}


def _has_xyz(xyz):
    return (xyz or "").strip() not in LEGACY_EMPTY_VALUES


def _gcs_key(calc, frame_number):
    return "/".join(
        part.strip("/")
        for part in [
            settings.CALCULATION_OUTPUT_PREFIX,
            "calculation_frames",
            str(calc.pk or calc.id),
            f"{int(frame_number)}.xyz",
        ]
        if part
    )


def _xyz(payload):
    if isinstance(payload, dict):
        return payload.get("xyz_structure") or ""
    return payload or ""


def _metadata(frame_number, payload=None):
    metadata = {"number": int(frame_number), **FRAME_METADATA_DEFAULTS}
    if isinstance(payload, dict):
        for field in FRAME_METADATA_DEFAULTS:
            metadata[field] = payload.get(field, metadata[field])
    return metadata


def _frame_payloads(frames):
    payloads = {}
    for frame_number, payload in frames.items():
        frame_number = int(frame_number)
        xyz = _xyz(payload)
        payloads[str(frame_number)] = {
            "xyz_structure": xyz,
            "size": len(xyz.encode("utf-8")),
            "content_type": CONTENT_TYPE,
            **_metadata(frame_number, payload),
        }
    return payloads


def _legacy_records(calc, frame_numbers=None):
    qs = calc.calculationframe_set.values(
        "number", "xyz_structure", "RMSD", "converged", "energy"
    )
    if frame_numbers is not None:
        qs = qs.filter(number__in=[int(number) for number in frame_numbers])

    return {
        str(row["number"]): {
            "number": int(row["number"]),
            "xyz_structure": row["xyz_structure"],
            "RMSD": row["RMSD"],
            "converged": row["converged"],
            "energy": row["energy"],
        }
        for row in qs
        if _has_xyz(row["xyz_structure"])
    }


def _manifest_record(calc, frame_number, entry):
    return {
        **_metadata(frame_number, entry),
        "xyz_structure": get_backend(entry.get("backend")).read(
            calc, frame_number, entry
        ),
    }


class DatabaseCalculationFrameStorageBackend:
    name = "database"

    def save_many(self, calc, frames):
        manifest = _stored_manifest(calc).copy()
        for frame_number, frame in frames.items():
            obj, _ = calc.calculationframe_set.get_or_create(
                number=int(frame_number),
                defaults={"parent_calculation": calc},
            )
            obj.xyz_structure = frame["xyz_structure"]
            obj.RMSD = frame["RMSD"]
            obj.converged = frame["converged"]
            obj.energy = frame["energy"]
            obj.save()

            manifest[frame_number] = {
                "backend": self.name,
                "frame_id": str(obj.pk),
                **{k: v for k, v in frame.items() if k != "xyz_structure"},
            }
        calc.frame_file_manifest = manifest
        calc.save(update_fields=["frame_file_manifest"])
        return manifest

    def read(self, calc, frame_number, entry):
        if entry.get("frame_id"):
            try:
                return (
                    CalculationFrame.objects.only("xyz_structure")
                    .get(pk=entry["frame_id"])
                    .xyz_structure
                )
            except CalculationFrame.DoesNotExist:
                pass

        key = str(int(frame_number))
        records = _legacy_records(calc, frame_numbers=[key])
        if key not in records:
            raise FileNotFoundError(key)
        return records[key]["xyz_structure"]


class GCSCalculationFrameStorageBackend:
    name = "gcs"

    def __init__(self):
        self.bucket_name = settings.CALCULATION_OUTPUT_BUCKET
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage

            if os.getenv("STORAGE_EMULATOR_HOST"):
                from google.auth.credentials import AnonymousCredentials

                self._client = storage.Client(
                    project=getattr(settings, "GCP_PROJECT_ID", None) or "calcus-test",
                    credentials=AnonymousCredentials(),
                )
            else:
                self._client = storage.Client(
                    project=getattr(settings, "GCP_PROJECT_ID", None)
                )
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
            if os.getenv("STORAGE_EMULATOR_HOST") and not self._bucket.exists():
                self._bucket = self.client.create_bucket(self.bucket_name)
        return self._bucket

    def save_many(self, calc, frames):
        manifest = _stored_manifest(calc).copy()
        for frame_number, frame in frames.items():
            key = _gcs_key(calc, frame_number)
            blob = self.bucket.blob(key)
            blob.upload_from_string(frame["xyz_structure"], content_type=CONTENT_TYPE)
            manifest[frame_number] = {
                "backend": self.name,
                "bucket": self.bucket_name,
                "key": key,
                "generation": blob.generation,
                **{k: v for k, v in frame.items() if k != "xyz_structure"},
            }
        calc.frame_file_manifest = manifest
        calc.save(update_fields=["frame_file_manifest"])
        return manifest

    def read(self, calc, frame_number, entry):
        return (
            self.client.bucket(entry.get("bucket") or self.bucket_name)
            .blob(entry["key"])
            .download_as_text()
        )

    def delete_many(self, manifest):
        from google.api_core.exceptions import NotFound

        for entry in manifest.values():
            try:
                (
                    self.client.bucket(entry.get("bucket") or self.bucket_name)
                    .blob(entry["key"])
                    .delete()
                )
            except NotFound:
                pass


_BACKENDS = {
    "database": DatabaseCalculationFrameStorageBackend,
    "gcs": GCSCalculationFrameStorageBackend,
}


def get_backend(name=None):
    backend_name = (name or _backend_name()).lower()
    try:
        return _BACKENDS[backend_name]()
    except KeyError as exc:
        raise CalculationFrameStorageError(
            f"Unknown calculation frame storage backend: {backend_name}"
        ) from exc


def has_frames(calc):
    return bool(_manifest(calc) or _legacy_records(calc))


def list_frame_files(calc):
    manifest = _manifest(calc)
    if manifest:
        return manifest
    return {
        frame_number: {
            "backend": "database",
            "size": len(record["xyz_structure"].encode("utf-8")),
            "content_type": CONTENT_TYPE,
            **_metadata(frame_number, record),
        }
        for frame_number, record in _legacy_records(calc).items()
    }


def read_frame_record(calc, frame_number):
    frame_number = str(int(frame_number))
    manifest = _manifest(calc)

    if frame_number in manifest:
        try:
            return _manifest_record(calc, frame_number, manifest[frame_number])
        except (CalculationFrameStorageError, FileNotFoundError, KeyError) as exc:
            logger.warning(
                "Falling back to legacy CalculationFrame.xyz_structure for "
                "calculation %s frame %s after manifest read failed: %s",
                getattr(calc, "pk", None),
                frame_number,
                exc,
            )

    records = _legacy_records(calc, frame_numbers=[frame_number])
    if frame_number not in records:
        raise FileNotFoundError(frame_number)

    if not manifest:
        logger.warning(
            "Serving legacy CalculationFrame.xyz_structure for calculation %s "
            "frame %s because no frame_file_manifest is present",
            getattr(calc, "pk", None),
            frame_number,
        )
    return records[frame_number]


def read_all_frame_records(calc):
    manifest = _manifest(calc)
    records = _legacy_records(calc)
    if records and not manifest:
        logger.warning(
            "Serving %s legacy CalculationFrame.xyz_structure frame(s) for "
            "calculation %s because no frame_file_manifest is present",
            len(records),
            getattr(calc, "pk", None),
        )
    for frame_number in manifest:
        records[frame_number] = read_frame_record(calc, frame_number)
    return records


def save_frame_files(calc, frames, backend_name=None):
    return get_backend(backend_name).save_many(calc, _frame_payloads(frames))


def flush_legacy_frame_payloads(
    calc, frame_numbers=None, backend_name=None, clear_legacy=True
):
    records = _legacy_records(calc, frame_numbers=frame_numbers)
    if not records:
        return _manifest(calc)

    backend_name = (backend_name or _backend_name()).lower()
    manifest = save_frame_files(calc, records, backend_name=backend_name)
    if clear_legacy and backend_name != "database":
        calc.calculationframe_set.filter(number__in=[int(n) for n in records]).update(
            xyz_structure=""
        )
    return manifest


def delete_frame_files(calc, save=True):
    manifest = _manifest(calc)
    backends = {entry.get("backend", _backend_name()) for entry in manifest.values()}
    unknown_backends = backends - {"database", "gcs"}
    if unknown_backends:
        raise CalculationFrameStorageError(
            f"Unknown calculation frame storage backend: {sorted(unknown_backends)[0]}"
        )
    if "gcs" in backends:
        get_backend("gcs").delete_many(
            {k: v for k, v in manifest.items() if v.get("backend") == "gcs"}
        )

    calc.frame_file_manifest = {}
    if save:
        calc.save(update_fields=["frame_file_manifest"])
