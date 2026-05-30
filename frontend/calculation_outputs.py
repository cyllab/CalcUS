"""Storage helpers for calculation output files.

New calculations should store only a manifest on ``Calculation`` and keep the
actual log contents in the configured backend.  The old ``output_files`` DB field
is still read as a fallback so existing calculations keep working during the
migration.
"""

import json
import os
import re
from pathlib import Path

from django.conf import settings

LEGACY_EMPTY_VALUES = ("", "{}", "null")


class CalculationOutputStorageError(Exception):
    pass


def _backend_name():
    return getattr(settings, "CALCULATION_OUTPUT_STORAGE_BACKEND", "database").lower()


def _bucket_name():
    return getattr(settings, "CALCULATION_OUTPUT_BUCKET", "")


def _prefix():
    return getattr(settings, "CALCULATION_OUTPUT_PREFIX", "")


def _safe_output_name(name):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("._")
    return safe or "calc"


def _object_name(calc, name):
    parts = [
        _prefix(),
        "calculations",
        str(calc.pk or calc.id),
        f"{_safe_output_name(name)}.log",
    ]
    return "/".join(part.strip("/") for part in parts if part)


def _legacy_outputs(calc):
    raw = (calc.output_files or "").strip()
    if raw in LEGACY_EMPTY_VALUES:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest(calc):
    manifest = getattr(calc, "output_file_manifest", None) or {}
    return manifest if isinstance(manifest, dict) else {}


class DatabaseCalculationOutputBackend:
    name = "database"

    def list(self, calc, manifest):
        return {
            name: {
                "backend": self.name,
                "name": name,
                "size": len(content or ""),
                "content_type": "text/plain",
            }
            for name, content in _legacy_outputs(calc).items()
        }

    def read(self, calc, name, metadata):
        try:
            return _legacy_outputs(calc)[name]
        except KeyError as exc:
            raise FileNotFoundError(name) from exc

    def save_many(self, calc, outputs):
        calc.output_files = json.dumps(outputs)
        calc.output_file_manifest = {}
        calc.save(update_fields=["output_files", "output_file_manifest"])
        return {}

    def delete_many(self, calc, manifest, save=True):
        calc.output_files = ""
        calc.output_file_manifest = {}
        if save:
            calc.save(update_fields=["output_files", "output_file_manifest"])


class LocalCalculationOutputBackend:
    name = "local"

    @property
    def root(self):
        return Path(
            getattr(
                settings,
                "CALCULATION_OUTPUT_LOCAL_ROOT",
                os.path.join(settings.BASE_DIR, "scratch", "calculation_outputs"),
            )
        )

    def _path(self, calc, name):
        return self.root / _object_name(calc, name)

    def _path_from_metadata(self, metadata):
        return self.root / metadata["path"]

    def save_many(self, calc, outputs):
        manifest = {}
        for name, content in outputs.items():
            path = self._path(calc, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            text = content or ""
            path.write_text(text, encoding="utf-8")
            rel_path = str(path.relative_to(self.root))
            manifest[name] = {
                "backend": self.name,
                "path": rel_path,
                "size": len(text.encode("utf-8")),
                "content_type": "text/plain",
            }
        calc.output_file_manifest = manifest
        calc.save(update_fields=["output_file_manifest"])
        return manifest

    def list(self, calc, manifest):
        return manifest

    def read(self, calc, name, metadata):
        return self._path_from_metadata(metadata).read_text(encoding="utf-8")

    def delete_many(self, calc, manifest, save=True):
        for metadata in manifest.values():
            if metadata.get("backend") != self.name or "path" not in metadata:
                continue
            try:
                self._path_from_metadata(metadata).unlink()
            except FileNotFoundError:
                pass
        calc.output_file_manifest = {}
        if save:
            calc.save(update_fields=["output_file_manifest"])


class GCSCalculationOutputBackend:
    name = "gcs"

    def __init__(self):
        bucket_name = _bucket_name()
        if not bucket_name:
            raise CalculationOutputStorageError(
                "CALCULATION_OUTPUT_BUCKET/CALCUS_OUTPUT_BUCKET must be set for GCS output storage"
            )
        self.bucket_name = bucket_name
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
            bucket = self.client.bucket(self.bucket_name)
            # fake-gcs-server starts without buckets by default; create the test
            # bucket automatically only when using the emulator.
            if os.getenv("STORAGE_EMULATOR_HOST") and not bucket.exists():
                bucket = self.client.create_bucket(self.bucket_name)
            self._bucket = bucket
        return self._bucket

    def save_many(self, calc, outputs):
        manifest = {}
        for name, content in outputs.items():
            text = content or ""
            key = _object_name(calc, name)
            blob = self.bucket.blob(key)
            blob.upload_from_string(text, content_type="text/plain")
            manifest[name] = {
                "backend": self.name,
                "bucket": self.bucket_name,
                "key": key,
                "size": len(text.encode("utf-8")),
                "content_type": "text/plain",
                "generation": blob.generation,
            }
        calc.output_file_manifest = manifest
        calc.save(update_fields=["output_file_manifest"])
        return manifest

    def list(self, calc, manifest):
        return manifest

    def read(self, calc, name, metadata):
        bucket_name = metadata.get("bucket") or self.bucket_name
        key = metadata["key"]
        bucket = self.client.bucket(bucket_name)
        return bucket.blob(key).download_as_text()

    def delete_many(self, calc, manifest, save=True):
        from google.api_core.exceptions import NotFound

        for metadata in manifest.values():
            if metadata.get("backend") != self.name or "key" not in metadata:
                continue
            bucket_name = metadata.get("bucket") or self.bucket_name
            try:
                self.client.bucket(bucket_name).blob(metadata["key"]).delete()
            except NotFound:
                pass
        calc.output_file_manifest = {}
        if save:
            calc.save(update_fields=["output_file_manifest"])


_BACKENDS = {
    "database": DatabaseCalculationOutputBackend,
    "local": LocalCalculationOutputBackend,
    "filesystem": LocalCalculationOutputBackend,
    "gcs": GCSCalculationOutputBackend,
}


def get_backend(name=None):
    selected = (name or _backend_name()).lower()
    try:
        return _BACKENDS[selected]()
    except KeyError as exc:
        raise CalculationOutputStorageError(
            f"Unknown calculation output storage backend: {selected}"
        ) from exc


def _backend_for_metadata(metadata):
    return get_backend(metadata.get("backend", _backend_name()))


def has_outputs(calc):
    return bool(_manifest(calc) or _legacy_outputs(calc))


def list_output_files(calc):
    manifest = _manifest(calc)
    if manifest:
        return manifest
    return DatabaseCalculationOutputBackend().list(calc, manifest)


def read_output_file(calc, name):
    manifest = _manifest(calc)
    if name in manifest:
        return _backend_for_metadata(manifest[name]).read(calc, name, manifest[name])
    return DatabaseCalculationOutputBackend().read(calc, name, {})


def read_all_output_files(calc):
    manifest = _manifest(calc)
    if manifest:
        return {name: read_output_file(calc, name) for name in manifest.keys()}
    return _legacy_outputs(calc)


def save_output_files(calc, outputs, backend_name=None):
    """Persist output file contents and update the manifest.

    ``outputs`` is a mapping of logical log name (``calc``, ``freq``...) to text
    content.  For non-database backends, the DB stores only metadata.  For the
    database backend, this intentionally preserves the legacy behavior.
    """

    normalized = {str(name): content or "" for name, content in outputs.items()}
    return get_backend(backend_name).save_many(calc, normalized)


def delete_output_files(calc, save=True):
    manifest = _manifest(calc)
    if manifest:
        for backend_name in {
            meta.get("backend", _backend_name()) for meta in manifest.values()
        }:
            backend_manifest = {
                name: meta
                for name, meta in manifest.items()
                if meta.get("backend", _backend_name()) == backend_name
            }
            get_backend(backend_name).delete_many(calc, backend_manifest, save=save)
        return
    DatabaseCalculationOutputBackend().delete_many(calc, manifest, save=save)


def migrate_legacy_output_files(calc, backend_name=None, clear_legacy=False):
    outputs = _legacy_outputs(calc)
    if not outputs:
        return {}
    selected_backend = (backend_name or _backend_name()).lower()
    manifest = save_output_files(calc, outputs, backend_name=backend_name)
    if clear_legacy and selected_backend != "database":
        calc.output_files = ""
        calc.save(update_fields=["output_files"])
    return manifest
