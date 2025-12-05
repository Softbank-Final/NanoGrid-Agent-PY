"""
Output 파일 업로더

컨테이너 실행 후 생성된 파일을 S3에 자동 업로드
"""

import shutil
from pathlib import Path
from typing import List

import boto3
import docker
import structlog

from .config import AgentConfig


logger = structlog.get_logger()


class OutputFileUploader:
    """Output Binding - 컨테이너 실행 후 생성된 파일을 S3에 자동 업로드"""

    def __init__(
        self,
        config: AgentConfig,
        docker_client: docker.DockerClient,
    ):
        self.config = config
        self.docker_client = docker_client
        self.s3_client = boto3.client("s3", region_name=config.aws.region)

    def upload_output_files(self, request_id: str, container_id: str) -> List[str]:
        """
        컨테이너 내부의 output 디렉터리에서 파일을 복사하여 S3에 업로드

        Args:
            request_id: 요청 ID
            container_id: 컨테이너 ID

        Returns:
            업로드된 파일의 S3 URL 리스트
        """
        if not self.config.output.enabled:
            logger.debug("Output file upload is disabled")
            return []

        # 컨테이너 내부 output 경로
        container_output_path = (
            f"{self.config.docker.work_dir_root}/{request_id}/output"
        )

        logger.info(
            "Checking container output directory",
            container_output_path=container_output_path,
        )

        # output 디렉터리 존재 확인
        if not self._check_output_exists(container_id, container_output_path):
            logger.debug("No output directory found in container")
            return []

        # 호스트 임시 디렉터리 생성
        output_host_path = Path(self.config.output.base_dir) / request_id
        output_host_path.mkdir(parents=True, exist_ok=True)

        # 컨테이너에서 파일 복사
        self._copy_from_container(container_id, container_output_path, output_host_path)

        # S3로 업로드
        uploaded_urls = self._upload_to_s3(request_id, output_host_path)

        # 정리
        self._cleanup(output_host_path)

        return uploaded_urls

    def _check_output_exists(self, container_id: str, path: str) -> bool:
        """컨테이너 내부에 output 디렉터리가 존재하는지 확인"""
        try:
            container = self.docker_client.containers.get(container_id)
            result = container.exec_run(["test", "-d", path])
            return result.exit_code == 0
        except Exception as e:
            logger.warning("Failed to check output directory", error=str(e))
            return False

    def _copy_from_container(
        self, container_id: str, src_path: str, dest_path: Path
    ) -> None:
        """컨테이너에서 호스트로 파일 복사"""
        try:
            container = self.docker_client.containers.get(container_id)

            # docker cp equivalent
            bits, stat = container.get_archive(src_path)

            # tar 아카이브를 임시 파일로 저장 후 추출
            tar_path = dest_path / "output.tar"
            with open(tar_path, "wb") as f:
                for chunk in bits:
                    f.write(chunk)

            # tar 추출
            import tarfile
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(dest_path)

            # tar 파일 삭제
            tar_path.unlink(missing_ok=True)

            logger.debug("Copied files from container", dest=str(dest_path))

        except Exception as e:
            logger.warning("Failed to copy from container", error=str(e))

    def _upload_to_s3(self, request_id: str, source_dir: Path) -> List[str]:
        """호스트의 파일을 S3로 업로드"""
        uploaded_urls = []
        bucket = self.config.s3.user_data_bucket
        prefix = self.config.output.s3_prefix

        if not bucket:
            logger.warning("S3 user_data_bucket not configured, skipping upload")
            return []

        try:
            # output 디렉터리 내의 모든 파일 찾기
            output_dir = source_dir / "output"
            if not output_dir.exists():
                output_dir = source_dir

            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(output_dir)
                    s3_key = f"{prefix}/{request_id}/{relative_path}"

                    logger.info(
                        "Uploading file to S3",
                        file=str(file_path),
                        s3_key=s3_key,
                    )

                    self.s3_client.upload_file(
                        str(file_path),
                        bucket,
                        s3_key,
                    )

                    url = f"s3://{bucket}/{s3_key}"
                    uploaded_urls.append(url)

            if uploaded_urls:
                logger.info(
                    "Uploaded output files",
                    count=len(uploaded_urls),
                    request_id=request_id,
                )

        except Exception as e:
            logger.error("Failed to upload to S3", error=str(e))

        return uploaded_urls

    def _cleanup(self, path: Path) -> None:
        """임시 디렉터리 정리"""
        try:
            if path.exists():
                shutil.rmtree(path)
                logger.debug("Cleaned up output directory", path=str(path))
        except Exception as e:
            logger.warning("Failed to cleanup", error=str(e))

