"""Storage for calculation output logs.

The database backend keeps the existing ``Calculation.output_files`` JSON field.
The GCS backend stores logs in the calculation output bucket and records metadata
in ``Calculation.output_file_manifest``.
"""

import json
import os

from django.conf import settings

from .helpers import clean_filename

CONTENT_TYPE = "text/plain"
LEGACY_EMPTY_VALUES = ("", "{}", "null")


class CalculationOutputStorageError(Exception):
    pass


def _backend_name():
    return settings.CALCULATION_OUTPUT_STORAGE_BACKEND.lower()


def _manifest(calc):
    manifest = getattr(calc, "output_file_manifest", None) or {}
    return manifest if isinstance(manifest, dict) else {}


def _legacy_outputs(calc):
    raw = (calc.output_files or "").strip()
    if raw in LEGACY_EMPTY_VALUES:
        return {}
    try:
        outputs = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return outputs if isinstance(outputs, dict) else {}


def _gcs_key(calc, name):
    filename = clean_filename(str(name)).strip("._") or "calc"
    return "/".join(
        part.strip("/")
        for part in [
            settings.CALCULATION_OUTPUT_PREFIX,
            "calculations",
            str(calc.pk or calc.id),
            f"{filename}.log",
        ]
        if part
    )


class DatabaseCalculationOutputBackend:
    name = "database"

    def save_many(self, calc, outputs):
        calc.output_files = json.dumps(outputs)
        calc.output_file_manifest = {}
        calc.save(update_fields=["output_files", "output_file_manifest"])
        return {}

    def read(self, calc, name, metadata):
        try:
            return _legacy_outputs(calc)[name]
        except KeyError as exc:
            raise FileNotFoundError(name) from exc


class GCSCalculationOutputBackend:
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

    def save_many(self, calc, outputs):
        manifest = {}
        for name, content in outputs.items():
            text = content or ""
            key = _gcs_key(calc, name)
            blob = self.bucket.blob(key)
            blob.upload_from_string(text, content_type=CONTENT_TYPE)
            manifest[name] = {
                "backend": self.name,
                "bucket": self.bucket_name,
                "key": key,
                "size": len(text.encode("utf-8")),
                "content_type": CONTENT_TYPE,
                "generation": blob.generation,
            }
        calc.output_file_manifest = manifest
        calc.save(update_fields=["output_file_manifest"])
        return manifest

    def read(self, calc, name, metadata):
        return (
            self.client.bucket(metadata.get("bucket") or self.bucket_name)
            .blob(metadata["key"])
            .download_as_text()
        )

    def delete_many(self, manifest):
        from google.api_core.exceptions import NotFound

        for metadata in manifest.values():
            try:
                (
                    self.client.bucket(metadata.get("bucket") or self.bucket_name)
                    .blob(metadata["key"])
                    .delete()
                )
            except NotFound:
                pass


_BACKENDS = {
    "database": DatabaseCalculationOutputBackend,
    "gcs": GCSCalculationOutputBackend,
}


def get_backend(name=None):
    backend_name = (name or _backend_name()).lower()
    try:
        return _BACKENDS[backend_name]()
    except KeyError as exc:
        raise CalculationOutputStorageError(
            f"Unknown calculation output storage backend: {backend_name}"
        ) from exc


def has_outputs(calc):
    return bool(_manifest(calc) or _legacy_outputs(calc))


def read_all_output_files(calc):
    manifest = _manifest(calc)
    if not manifest:
        return _legacy_outputs(calc)
    return {
        name: get_backend(metadata.get("backend")).read(calc, name, metadata)
        for name, metadata in manifest.items()
    }


def save_output_files(calc, outputs, backend_name=None):
    outputs = {str(name): content or "" for name, content in outputs.items()}
    return get_backend(backend_name).save_many(calc, outputs)


def delete_output_files(calc, save=True):
    manifest = _manifest(calc)
    backends = {
        metadata.get("backend", _backend_name()) for metadata in manifest.values()
    }
    unknown_backends = backends - {"database", "gcs"}
    if unknown_backends:
        raise CalculationOutputStorageError(
            f"Unknown calculation output storage backend: {sorted(unknown_backends)[0]}"
        )
    if "gcs" in backends:
        get_backend("gcs").delete_many(
            {k: v for k, v in manifest.items() if v.get("backend") == "gcs"}
        )

    calc.output_files = ""
    calc.output_file_manifest = {}
    if save:
        calc.save(update_fields=["output_files", "output_file_manifest"])


def flush_legacy_output_files(calc, backend_name=None, clear_legacy=False):
    outputs = _legacy_outputs(calc)
    if not outputs:
        return {}

    backend_name = (backend_name or _backend_name()).lower()
    manifest = save_output_files(calc, outputs, backend_name=backend_name)
    if clear_legacy and backend_name != "database":
        calc.output_files = ""
        calc.save(update_fields=["output_files"])
    return manifest
