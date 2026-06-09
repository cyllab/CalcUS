"""Storage for heavy Property payloads.

The database backend keeps the existing columns on ``Property``. The GCS backend
stores large payloads in the calculation/property output bucket and records
metadata in ``Property.property_file_manifest``.
"""

import json
import logging
import os

from django.conf import settings

CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_JSON = "application/json"
HEAVY_PROPERTY_FIELDS = (
    "freq_animations",
    "ir_spectrum",
    "esp",
    "molden",
    "mo_diagram",
    "uvvis",
)
ARRAY_FIELDS = {"freq_animations"}
TEXT_EMPTY = ""
ARRAY_EMPTY = []

logger = logging.getLogger(__name__)


class PropertyFileStorageError(Exception):
    pass


def _backend_name():
    return settings.CALCULATION_OUTPUT_STORAGE_BACKEND.lower()


def _bucket_name():
    return settings.CALCULATION_OUTPUT_BUCKET


def _prefix():
    return settings.CALCULATION_OUTPUT_PREFIX


def _validate_field(field):
    if field not in HEAVY_PROPERTY_FIELDS:
        raise PropertyFileStorageError(f"Unknown heavy Property field: {field}")


def empty_value(field):
    _validate_field(field)
    return [] if field in ARRAY_FIELDS else ""


def is_empty_value(field, value):
    _validate_field(field)
    if field in ARRAY_FIELDS:
        return value in (None, "", [])
    return value in (None, "")


def _manifest(prop):
    manifest = getattr(prop, "property_file_manifest", None) or {}
    return manifest if isinstance(manifest, dict) else {}


def _property_queryset(prop):
    from .models import Property

    return Property.objects.filter(pk=prop.pk)


def _stored_manifest(prop):
    if not getattr(prop, "pk", None):
        return _manifest(prop)
    manifest = (
        _property_queryset(prop)
        .values_list("property_file_manifest", flat=True)
        .first()
    )
    return manifest if isinstance(manifest, dict) else {}


def _legacy_value(prop, field):
    value = prop.__dict__[field] if field in prop.__dict__ else getattr(prop, field)
    if value is None:
        return empty_value(field)
    return value


def _serialize(field, value):
    if field in ARRAY_FIELDS:
        return json.dumps(value or [])
    return value or ""


def _deserialize(field, contents):
    if field in ARRAY_FIELDS:
        if contents in (None, ""):
            return []
        value = json.loads(contents)
        return value if isinstance(value, list) else []
    return contents or ""


def _extension(field):
    return "json" if field in ARRAY_FIELDS else "txt"


def _content_type(field):
    return CONTENT_TYPE_JSON if field in ARRAY_FIELDS else CONTENT_TYPE_TEXT


def _gcs_key(prop, field):
    _validate_field(field)
    return "/".join(
        part.strip("/")
        for part in [
            _prefix(),
            "properties",
            str(prop.pk or prop.id),
            f"{field}.{_extension(field)}",
        ]
        if part
    )


def _db_updates_for_fields(fields):
    return {field: empty_value(field) for field in fields}


class DatabasePropertyFileBackend:
    name = "database"

    def save_many(self, prop, values):
        manifest = _stored_manifest(prop).copy()
        for field, value in values.items():
            _validate_field(field)
            setattr(prop, field, value if value is not None else empty_value(field))
            manifest.pop(field, None)

        prop.property_file_manifest = manifest
        updates = {field: getattr(prop, field) for field in values}
        updates["property_file_manifest"] = manifest
        if getattr(prop, "pk", None):
            _property_queryset(prop).update(**updates)
        return manifest

    def read(self, prop, field, metadata):
        return _legacy_value(prop, field)


class GCSPropertyFileBackend:
    name = "gcs"

    def __init__(self):
        self.bucket_name = _bucket_name()
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

    def save_many(self, prop, values):
        manifest = _stored_manifest(prop).copy()
        for field, value in values.items():
            _validate_field(field)
            if is_empty_value(field, value):
                old_metadata = manifest.pop(field, None)
                if old_metadata and old_metadata.get("backend") == self.name:
                    self.delete_many({field: old_metadata})
                continue

            text = _serialize(field, value)
            key = _gcs_key(prop, field)
            blob = self.bucket.blob(key)
            blob.upload_from_string(text, content_type=_content_type(field))
            manifest[field] = {
                "backend": self.name,
                "bucket": self.bucket_name,
                "key": key,
                "field": field,
                "size": len(text.encode("utf-8")),
                "content_type": _content_type(field),
                "generation": blob.generation,
            }

        prop.property_file_manifest = manifest
        if getattr(prop, "pk", None):
            _property_queryset(prop).update(property_file_manifest=manifest)
        return manifest

    def read(self, prop, field, metadata):
        contents = (
            self.client.bucket(metadata.get("bucket") or self.bucket_name)
            .blob(metadata["key"])
            .download_as_text()
        )
        return _deserialize(field, contents)

    def delete_many(self, manifest):
        from google.api_core.exceptions import NotFound

        for metadata in manifest.values():
            if metadata.get("backend") != self.name or "key" not in metadata:
                continue
            try:
                (
                    self.client.bucket(metadata.get("bucket") or self.bucket_name)
                    .blob(metadata["key"])
                    .delete()
                )
            except NotFound:
                pass


_BACKENDS = {
    "database": DatabasePropertyFileBackend,
    "gcs": GCSPropertyFileBackend,
}


def get_backend(name=None):
    backend_name = (name or _backend_name()).lower()
    try:
        return _BACKENDS[backend_name]()
    except KeyError as exc:
        raise PropertyFileStorageError(
            f"Unknown Property file storage backend: {backend_name}"
        ) from exc


def read_property_file(prop, field):
    _validate_field(field)
    if _backend_name() == "database":
        return _legacy_value(prop, field)

    manifest = _manifest(prop)
    metadata = manifest.get(field)
    if metadata:
        try:
            return get_backend(metadata.get("backend")).read(prop, field, metadata)
        except (
            PropertyFileStorageError,
            FileNotFoundError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning(
                "Falling back to legacy Property.%s for property %s after manifest read failed: %s",
                field,
                getattr(prop, "pk", None),
                exc,
            )
    return _legacy_value(prop, field)


def has_property_file(prop, field):
    return not is_empty_value(field, read_property_file(prop, field))


def save_property_files(prop, values, backend_name=None):
    clean_values = {}
    for field, value in values.items():
        _validate_field(field)
        clean_values[field] = value if value is not None else empty_value(field)
    if not clean_values:
        return _manifest(prop)
    return get_backend(backend_name).save_many(prop, clean_values)


def flush_legacy_property_files(
    prop, fields=None, backend_name=None, clear_legacy=True
):
    fields = tuple(fields or HEAVY_PROPERTY_FIELDS)
    values = {
        field: _legacy_value(prop, field)
        for field in fields
        if not is_empty_value(field, _legacy_value(prop, field))
    }
    if not values:
        return _manifest(prop)

    backend_name = (backend_name or _backend_name()).lower()
    manifest = save_property_files(prop, values, backend_name=backend_name)
    if clear_legacy and backend_name != "database" and getattr(prop, "pk", None):
        _property_queryset(prop).update(**_db_updates_for_fields(values.keys()))
        for field in values:
            setattr(prop, field, empty_value(field))
    return manifest


def delete_property_files(prop, save=True):
    manifest = _manifest(prop)
    backends = {
        metadata.get("backend", _backend_name()) for metadata in manifest.values()
    }
    unknown_backends = backends - {"database", "gcs"}
    if unknown_backends:
        raise PropertyFileStorageError(
            f"Unknown Property file storage backend: {sorted(unknown_backends)[0]}"
        )
    if "gcs" in backends:
        get_backend("gcs").delete_many(
            {k: v for k, v in manifest.items() if v.get("backend") == "gcs"}
        )

    prop.property_file_manifest = {}
    for field in HEAVY_PROPERTY_FIELDS:
        setattr(prop, field, empty_value(field))
    if save and getattr(prop, "pk", None):
        _property_queryset(prop).update(
            property_file_manifest={},
            **_db_updates_for_fields(HEAVY_PROPERTY_FIELDS),
        )
