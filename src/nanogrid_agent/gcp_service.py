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
                from google.oauth2 import service_account

                # credentials_path가 설정되어 있으면 해당 파일 사용
                credentials_path = self.config.gcp.credentials_path
                if credentials_path and os.path.exists(credentials_path):
                    logger.info(f"🔑 Using credentials from: {credentials_path}")
                    credentials = service_account.Credentials.from_service_account_file(credentials_path)
                    self._client = storage.Client(credentials=credentials)
                else:
                    # 환경변수 GOOGLE_APPLICATION_CREDENTIALS 확인
                    env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                    if env_creds:
                        logger.info(f"🔑 Using credentials from env: {env_creds}")
                    else:
                        logger.warning("⚠️ No credentials path configured, using default credentials")
                    self._client = storage.Client()

                bucket_name = self.config.gcp.bucket_name
                logger.info(f"🔄 Getting GCP bucket...")
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

        logger.info("=" * 40)
        logger.info("📤 Starting GCP Upload")
        logger.info(f"  Job ID: {job_id}")
        logger.info(f"  Extension: {extension}")
        logger.info(f"  Code size: {len(code)} bytes")
        logger.info("=" * 40)

        try:
            logger.info("🔄 Getting GCP bucket...")
            bucket = self._get_bucket()

            blob_path = f"codes/{job_id}.{extension}"
            logger.info(f"📁 Blob path: {blob_path}")

            blob = bucket.blob(blob_path)

            logger.info("⬆️ Uploading to GCP Storage...")
            blob.upload_from_string(code, content_type="text/plain")

            gcs_uri = f"gs://{self.config.gcp.bucket_name}/{blob_path}"

            logger.info("=" * 40)
            logger.info("✅ GCP Upload SUCCESS")
            logger.info(f"  GCS URI: {gcs_uri}")
            logger.info("=" * 40)

            return gcs_uri

        except Exception as e:
            logger.error("=" * 40)
            logger.error("❌ GCP Upload FAILED")
            logger.error(f"  Job ID: {job_id}")
            logger.error(f"  Error: {str(e)}")
            logger.error("=" * 40)
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

