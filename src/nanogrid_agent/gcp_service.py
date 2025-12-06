"""
GCP Storage 서비스

코드를 GCP Cloud Storage에 저장
"""

import os
import structlog

from .config import AgentConfig

logger = structlog.get_logger()


class GcpStorageService:
    """GCP Cloud Storage에 코드 업로드"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._client = None
        self._bucket = None

    def _get_bucket(self):
        """GCP Storage bucket lazy 초기화"""
        if self._bucket is None:
            try:
                from google.cloud import storage

                self._client = storage.Client()
                bucket_name = self.config.gcp.bucket_name
                self._bucket = self._client.bucket(bucket_name)
                logger.info("GCP Storage initialized", bucket=bucket_name)
            except ImportError:
                logger.error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
                raise
            except Exception as e:
                logger.error("Failed to initialize GCP Storage", error=str(e))
                raise
        return self._bucket

    def upload_code(self, job_id: str, code: str, extension: str = "py") -> str:
        """
        코드를 GCP Storage에 업로드

        Args:
            job_id: 작업 ID
            code: 업로드할 코드 문자열
            extension: 파일 확장자 (기본값: py)

        Returns:
            업로드된 GCS URI (gs://bucket/path)
        """
        if not self.config.gcp.enabled:
            logger.debug("GCP Storage is disabled, skipping upload")
            return ""

        try:
            bucket = self._get_bucket()
            blob_path = f"codes/{job_id}.{extension}"
            blob = bucket.blob(blob_path)

            blob.upload_from_string(code, content_type="text/plain")

            gcs_uri = f"gs://{self.config.gcp.bucket_name}/{blob_path}"
            logger.info(
                "Code uploaded to GCP",
                job_id=job_id,
                gcs_uri=gcs_uri,
            )
            return gcs_uri

        except Exception as e:
            logger.error(
                "Failed to upload code to GCP",
                job_id=job_id,
                error=str(e),
            )
            raise

    def download_code(self, job_id: str, extension: str = "py") -> str:
        """
        GCP Storage에서 코드 다운로드

        Args:
            job_id: 작업 ID
            extension: 파일 확장자 (기본값: py)

        Returns:
            코드 문자열
        """
        if not self.config.gcp.enabled:
            logger.warning("GCP Storage is disabled")
            return ""

        try:
            bucket = self._get_bucket()
            blob_path = f"codes/{job_id}.{extension}"
            blob = bucket.blob(blob_path)

            code = blob.download_as_text()
            logger.info(
                "Code downloaded from GCP",
                job_id=job_id,
                blob_path=blob_path,
            )
            return code

        except Exception as e:
            logger.error(
                "Failed to download code from GCP",
                job_id=job_id,
                error=str(e),
            )
            raise

    def close(self) -> None:
        """리소스 정리"""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

