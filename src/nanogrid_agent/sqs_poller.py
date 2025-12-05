"""
SQS Poller - 메시지 수신 및 처리

SQS Long Polling으로 작업 메시지를 수신하고 처리
"""

import json
import time
from typing import Optional

import boto3
import structlog
from botocore.exceptions import ClientError

from .config import AgentConfig
from .models import TaskMessage, ExecutionResult
from .s3_service import S3CodeStorageService
from .docker_service import DockerService
from .redis_publisher import RedisResultPublisher
from .cloudwatch_publisher import CloudWatchMetricsPublisher


logger = structlog.get_logger()


class SqsPoller:
    """SQS Long Polling 기반 작업 수신 및 처리"""

    def __init__(
        self,
        config: AgentConfig,
        s3_service: S3CodeStorageService,
        docker_service: DockerService,
        redis_publisher: RedisResultPublisher,
        cloudwatch_publisher: CloudWatchMetricsPublisher,
    ):
        self.config = config
        self.s3_service = s3_service
        self.docker_service = docker_service
        self.redis_publisher = redis_publisher
        self.cloudwatch_publisher = cloudwatch_publisher

        self.sqs_client = boto3.client("sqs", region_name=config.aws.region)
        self._running = False

    def start(self) -> None:
        """폴링 시작"""
        if not self.config.polling.enabled:
            logger.info("Polling is disabled")
            return

        queue_url = self.config.sqs.queue_url
        if not queue_url:
            logger.error("SQS Queue URL is not configured")
            return

        logger.info("Starting SQS Poller", queue_url=queue_url)
        self._running = True

        while self._running:
            try:
                self._poll_once()
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                self.stop()
            except Exception as e:
                logger.error("Polling error (Agent continues)", error=str(e))
                time.sleep(self.config.polling.fixed_delay_seconds)

    def stop(self) -> None:
        """폴링 중지"""
        logger.info("Stopping SQS Poller...")
        self._running = False

    def _poll_once(self) -> None:
        """한 번 폴링 수행"""
        queue_url = self.config.sqs.queue_url

        logger.debug("Polling SQS", queue_url=queue_url)

        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=self.config.sqs.max_number_of_messages,
                WaitTimeSeconds=self.config.sqs.wait_time_seconds,
            )
        except ClientError as e:
            logger.error("SQS receive failed", error=str(e))
            return

        messages = response.get("Messages", [])

        if not messages:
            logger.debug("No messages received")
            return

        logger.info("Received messages", count=len(messages))

        for message in messages:
            self._process_message(queue_url, message)

    def _process_message(self, queue_url: str, message: dict) -> None:
        """개별 SQS 메시지 처리"""
        message_body = message.get("Body", "")
        receipt_handle = message.get("ReceiptHandle", "")
        task: Optional[TaskMessage] = None

        try:
            # JSON 파싱
            data = json.loads(message_body)
            task = TaskMessage.from_dict(data)

            if not task.request_id:
                logger.error("TaskMessage has no requestId")
                self._delete_message(queue_url, receipt_handle)
                return

            start_time = time.time()

            logger.info("=" * 30)
            logger.info("Received task message")
            logger.info(f"  Request ID: {task.request_id}")
            logger.info(f"  Function ID: {task.function_id}")
            logger.info(f"  Runtime: {task.runtime}")
            logger.info(f"  S3 Location: s3://{task.s3_bucket}/{task.s3_key}")
            logger.info("=" * 30)

            # S3에서 코드 다운로드
            work_dir = self.s3_service.prepare_working_directory(task)
            logger.info("Prepared working directory", work_dir=str(work_dir))

            # Docker 실행
            result = self.docker_service.run_task(task, work_dir)

            total_time = int((time.time() - start_time) * 1000)

            # 실행 결과 로그
            logger.info("=" * 30)
            logger.info(f"Execution result for {task.request_id}")
            logger.info(f"  Exit Code: {result.exit_code}")
            logger.info(f"  Duration: {result.duration_millis}ms")
            logger.info(f"  Total Time: {total_time}ms")
            logger.info(f"  Peak Memory: {result.peak_memory_bytes} bytes")
            logger.info(f"  Success: {result.success}")
            if result.optimization_tip:
                logger.info(f"  Optimization Tip: {result.optimization_tip}")
            logger.info("=" * 30)
            logger.debug(f"Stdout:\n{result.stdout}")
            logger.debug(f"Stderr:\n{result.stderr}")

            # CloudWatch 메트릭 전송
            if result.peak_memory_bytes:
                try:
                    self.cloudwatch_publisher.publish_peak_memory(
                        task.function_id, task.runtime, result.peak_memory_bytes
                    )
                except Exception as e:
                    logger.warning("CloudWatch publish failed", error=str(e))

            # Redis Publish
            try:
                self.redis_publisher.publish_result(result)
                logger.info("✅ Result sent to Redis", request_id=task.request_id)
            except Exception as e:
                logger.error("❌ Redis publish failed", request_id=task.request_id, error=str(e))

            # 메시지 삭제
            self._delete_message(queue_url, receipt_handle)
            logger.info("[DONE][OK]", request_id=task.request_id)

        except json.JSONDecodeError as e:
            logger.error("[FAIL][JSON_PARSE] Message parsing failed", error=str(e))
            self._delete_message(queue_url, receipt_handle)

        except ValueError as e:
            logger.error(
                "[FAIL][RUNTIME_NOT_SUPPORTED]",
                runtime=task.runtime if task else "unknown",
                error=str(e),
            )
            # 메시지 삭제하지 않음 (DLQ로 이동)

        except Exception as e:
            error_type = "UNKNOWN"
            error_msg = str(e)
            if "NoSuchKey" in error_msg or "Not Found" in error_msg:
                error_type = "S3"
            elif "docker" in error_msg.lower() or "container" in error_msg.lower():
                error_type = "DOCKER"

            logger.error(
                f"[FAIL][{error_type}] Execution error",
                request_id=task.request_id if task else "unknown",
                error=error_msg,
            )
            # 메시지 삭제하지 않음 (재시도 가능)

    def _delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """SQS 메시지 삭제"""
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.debug("Message deleted from SQS")
        except ClientError as e:
            logger.error("Failed to delete message", error=str(e))

