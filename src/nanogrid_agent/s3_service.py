"""
S3 코드 저장소 서비스

S3에서 코드 zip 다운로드 및 압축 해제
"""

import shutil
import zipfile
from pathlib import Path

import structlog
import boto3
from botocore.exceptions import ClientError

from .config import AgentConfig
from .models import TaskMessage


logger = structlog.get_logger()


class S3CodeStorageService:
    """S3 기반 코드 저장소 서비스"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.s3_client = boto3.client("s3", region_name=config.aws.region)

    def prepare_working_directory(self, task: TaskMessage) -> Path:
        """
        S3에서 코드를 다운로드하고 작업 디렉터리 준비

        Args:
            task: 작업 메시지

        Returns:
            작업 디렉터리 경로
        """
        request_id = task.request_id
        s3_bucket = task.s3_bucket or self.config.s3.code_bucket
        s3_key = task.s3_key

        logger.info(
            "Preparing working directory",
            request_id=request_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )

        try:
            # 1. 작업 디렉터리 생성
            work_dir = self._create_working_directory(request_id)

            # 2. S3에서 zip 다운로드
            zip_path = self._download_from_s3(s3_bucket, s3_key, work_dir, request_id)

            # 3. zip 압축 해제
            self._extract_zip(zip_path, work_dir, request_id)

            # 4. zip 파일 삭제
            zip_path.unlink(missing_ok=True)

            logger.info("Successfully prepared working directory", work_dir=str(work_dir))
            return work_dir

        except Exception as e:
            logger.error(
                "Failed to prepare working directory",
                request_id=request_id,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                error=str(e),
            )
            raise RuntimeError(f"Failed to prepare working directory: {e}") from e

    def _create_working_directory(self, request_id: str) -> Path:
        """작업 디렉터리 생성"""
        work_dir = Path(self.config.task_base_dir) / request_id

        # 이미 존재하면 삭제 후 재생성
        if work_dir.exists():
            logger.debug("Cleaning existing working directory", work_dir=str(work_dir))
            shutil.rmtree(work_dir)

        work_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Created working directory", work_dir=str(work_dir))
        return work_dir

    def _download_from_s3(
        self, bucket: str, key: str, work_dir: Path, request_id: str
    ) -> Path:
        """S3에서 zip 파일 다운로드"""
        zip_path = work_dir / "code.zip"

        logger.info(
            "Downloading from S3",
            s3_uri=f"s3://{bucket}/{key}",
            dest=str(zip_path),
        )

        try:
            self.s3_client.download_file(bucket, key, str(zip_path))
            file_size = zip_path.stat().st_size
            logger.info("Downloaded zip file", size_bytes=file_size)
            return zip_path

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise RuntimeError(
                f"S3 download failed: s3://{bucket}/{key} - {error_code}"
            ) from e

    def _extract_zip(self, zip_path: Path, target_dir: Path, request_id: str) -> None:
        """zip 파일 압축 해제"""
        logger.info("Extracting zip file", zip_path=str(zip_path), target_dir=str(target_dir))

        extracted_count = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for entry in zf.namelist():
                # 디렉터리 순회 공격 방지
                target_path = (target_dir / entry).resolve()
                if not str(target_path).startswith(str(target_dir.resolve())):
                    logger.warning("Suspicious zip entry, skipping", entry=entry)
                    continue

                if entry.endswith("/"):
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(entry) as src, open(target_path, "wb") as dst:
                        dst.write(src.read())
                    extracted_count += 1

        logger.info("Extracted files", count=extracted_count)

