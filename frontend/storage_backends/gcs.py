"""Shared Google Cloud Storage helpers for bucket-backed payloads."""

import os

from django.conf import settings


def output_storage_backend_name():
    return settings.CALCULATION_OUTPUT_STORAGE_BACKEND.lower()


def output_bucket_name():
    return settings.CALCULATION_OUTPUT_BUCKET


def output_prefix():
    return settings.CALCULATION_OUTPUT_PREFIX


def storage_key(*parts):
    return "/".join(
        str(part).strip("/")
        for part in [output_prefix(), *parts]
        if part not in (None, "")
    )


class GCSBucketBackend:
    name = "gcs"

    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or output_bucket_name()
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

    def upload_text(self, key, text, content_type):
        blob = self.bucket.blob(key)
        blob.upload_from_string(text, content_type=content_type)
        return blob

    def blob_from_metadata(self, metadata):
        return self.client.bucket(metadata.get("bucket") or self.bucket_name).blob(
            metadata["key"]
        )

    def download_text(self, metadata):
        return self.blob_from_metadata(metadata).download_as_text()

    def delete_blobs(self, metadata_items):
        from google.api_core.exceptions import NotFound

        deleted = set()
        for metadata in metadata_items:
            if not metadata or "key" not in metadata:
                continue
            blob_id = (metadata.get("bucket") or self.bucket_name, metadata["key"])
            if blob_id in deleted:
                continue
            deleted.add(blob_id)
            try:
                self.client.bucket(blob_id[0]).blob(blob_id[1]).delete()
            except NotFound:
                pass
