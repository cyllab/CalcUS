"""Storage for calculation frame XYZ payloads.

The database backend keeps using legacy ``CalculationFrame`` rows.  The GCS
backend stores all frames for a calculation as one multi-XYZ object in the
calculation output bucket and records frame metadata on
``Calculation.frame_file_manifest``.
"""

import logging

from ..models import CalculationFrame
from .gcs import (
    GCSBucketBackend,
    output_storage_backend_name,
    storage_key,
)

CONTENT_TYPE = "chemical/x-xyz"
LEGACY_EMPTY_VALUES = ("", "{}", "null")
FRAME_METADATA_DEFAULTS = {"RMSD": 0, "converged": False, "energy": 0}
logger = logging.getLogger(__name__)


class CalculationFrameStorageError(Exception):
    pass


def _backend_name():
    return output_storage_backend_name()


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


def _gcs_key(calc):
    return storage_key("calculation_frames", calc.pk or calc.id, "frames.xyz")


def _is_multi_manifest(manifest):
    return manifest.get("format") == "multi_xyz" and isinstance(
        manifest.get("frames"), (list, dict)
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
        explicit_metadata = bool(
            isinstance(payload, dict)
            and set(payload).intersection(FRAME_METADATA_DEFAULTS)
        )
        payloads[str(frame_number)] = {
            "xyz_structure": xyz,
            **_metadata(frame_number, payload),
            "_explicit_metadata": explicit_metadata,
        }
    return payloads


def _multi_xyz(frames):
    return "".join(
        (frames[frame_number]["xyz_structure"] or "").rstrip() + "\n"
        for frame_number in sorted(frames, key=int)
    )


def _split_multi_xyz(contents):
    lines = contents.splitlines(keepends=True)
    frames = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        try:
            atom_count = int(lines[index].strip().split()[0])
        except (TypeError, ValueError) as exc:
            raise CalculationFrameStorageError(
                "Invalid multi-XYZ frame header"
            ) from exc

        end = index + atom_count + 2
        if end > len(lines):
            raise CalculationFrameStorageError("Truncated multi-XYZ frame payload")
        frames.append("".join(lines[index:end]))
        index = end
    return frames


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
    xyz = get_backend(entry.get("backend")).read(calc, frame_number, entry)
    return {**_metadata(frame_number, entry), "xyz_structure": xyz}


def _manifest_records(calc, manifest):
    if not manifest:
        return {}
    if _is_multi_manifest(manifest):
        return get_backend(manifest.get("backend")).read_records(calc, manifest)
    return {
        str(frame_number): _manifest_record(calc, frame_number, entry)
        for frame_number, entry in manifest.items()
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
                **{
                    k: v
                    for k, v in frame.items()
                    if k != "xyz_structure" and not k.startswith("_")
                },
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


class GCSCalculationFrameStorageBackend(GCSBucketBackend):
    name = "gcs"

    def save_many(self, calc, frames):
        contents = _multi_xyz(frames)
        key = _gcs_key(calc)
        self.upload_text(key, contents, CONTENT_TYPE)

        sorted_frame_numbers = sorted(frames, key=int)
        needs_full_metadata = any(
            frames[frame_number].get("_explicit_metadata")
            and (
                frames[frame_number].get("energy", 0) != 0
                or frames[frame_number].get("converged", False)
                != (index == len(sorted_frame_numbers) - 1)
            )
            for index, frame_number in enumerate(sorted_frame_numbers)
        )
        if needs_full_metadata:
            frame_metadata = {
                frame_number: {
                    "frame_index": index,
                    **{
                        key: frames[frame_number].get(key, default)
                        for key, default in FRAME_METADATA_DEFAULTS.items()
                    },
                }
                for index, frame_number in enumerate(sorted_frame_numbers)
            }
        else:
            frame_metadata = [
                frames[frame_number].get("RMSD", 0)
                for frame_number in sorted_frame_numbers
            ]

        manifest = {
            "backend": self.name,
            "bucket": self.bucket_name,
            "key": key,
            "format": "multi_xyz",
            "frames": frame_metadata,
        }
        calc.frame_file_manifest = manifest
        calc.save(update_fields=["frame_file_manifest"])
        return manifest

    def read_multi_xyz(self, manifest):
        return self.download_text(manifest)

    def read_records(self, calc, manifest):
        xyz_frames = _split_multi_xyz(self.read_multi_xyz(manifest))
        frame_metadata = manifest["frames"]
        records = {}

        if isinstance(frame_metadata, dict):
            for frame_number, metadata in frame_metadata.items():
                try:
                    xyz = xyz_frames[int(metadata["frame_index"])]
                except (IndexError, KeyError, ValueError) as exc:
                    raise FileNotFoundError(frame_number) from exc
                records[str(frame_number)] = {
                    **_metadata(frame_number, metadata),
                    "xyz_structure": xyz,
                }
            return records

        for index, rmsd in enumerate(frame_metadata):
            frame_number = str(index + 1)
            try:
                xyz = xyz_frames[index]
            except IndexError as exc:
                raise FileNotFoundError(frame_number) from exc
            records[frame_number] = {
                "number": index + 1,
                "xyz_structure": xyz,
                "RMSD": rmsd,
                "converged": index == len(frame_metadata) - 1,
                "energy": 0,
            }
        return records

    def read(self, calc, frame_number, entry):
        contents = self.download_text(entry)
        if entry.get("format") != "multi_xyz":
            return contents

        try:
            index = entry.get("frame_index", int(frame_number) - 1)
            return _split_multi_xyz(contents)[int(index)]
        except (IndexError, KeyError, ValueError) as exc:
            raise FileNotFoundError(frame_number) from exc

    def delete_many(self, manifest):
        entries = [manifest] if _is_multi_manifest(manifest) else manifest.values()
        self.delete_blobs(entries)


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
    if _is_multi_manifest(manifest):
        return manifest["frames"]
    if manifest:
        return manifest
    return {
        frame_number: {
            "backend": "database",
            **_metadata(frame_number, record),
        }
        for frame_number, record in _legacy_records(calc).items()
    }


def read_frame_record(calc, frame_number):
    frame_number = str(int(frame_number))
    manifest = _manifest(calc)

    if manifest:
        try:
            records = _manifest_records(calc, manifest)
            if frame_number in records:
                return records[frame_number]
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
    if manifest:
        records.update(_manifest_records(calc, manifest))
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
    if _is_multi_manifest(manifest):
        backends = {manifest.get("backend", _backend_name())}
    else:
        backends = {
            entry.get("backend", _backend_name()) for entry in manifest.values()
        }

    unknown_backends = backends - {"database", "gcs"}
    if unknown_backends:
        raise CalculationFrameStorageError(
            f"Unknown calculation frame storage backend: {sorted(unknown_backends)[0]}"
        )
    if "gcs" in backends:
        get_backend("gcs").delete_many(
            manifest
            if _is_multi_manifest(manifest)
            else {k: v for k, v in manifest.items() if v.get("backend") == "gcs"}
        )

    calc.frame_file_manifest = {}
    if save:
        calc.save(update_fields=["frame_file_manifest"])
