"""
CloudWatch 메트릭 발행 서비스

실행 메트릭을 AWS CloudWatch로 전송
"""

from datetime import datetime

import boto3
import structlog

from .config import AgentConfig


logger = structlog.get_logger()


class CloudWatchMetricsPublisher:
    """CloudWatch 커스텀 메트릭 퍼블리셔"""

    NAMESPACE = "NanoGrid/FunctionRunner"
    METRIC_NAME_PEAK_MEMORY = "PeakMemoryBytes"

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = boto3.client("cloudwatch", region_name=config.aws.region)

    def publish_peak_memory(
        self, function_id: str, runtime: str, peak_memory_bytes: int
    ) -> None:
        """
        피크 메모리 사용량을 CloudWatch에 전송

        Args:
            function_id: 함수 ID
            runtime: 런타임 (python, cpp)
            peak_memory_bytes: 피크 메모리 사용량 (바이트)
        """
        if peak_memory_bytes is None:
            logger.debug("Peak memory is null, skipping CloudWatch publish")
            return

        try:
            logger.info(
                "Publishing peak memory metric to CloudWatch",
                function_id=function_id,
                runtime=runtime,
                bytes=peak_memory_bytes,
            )

            self.client.put_metric_data(
                Namespace=self.NAMESPACE,
                MetricData=[
                    {
                        "MetricName": self.METRIC_NAME_PEAK_MEMORY,
                        "Dimensions": [
                            {"Name": "FunctionId", "Value": function_id},
                            {"Name": "Runtime", "Value": runtime},
                        ],
                        "Timestamp": datetime.utcnow(),
                        "Value": float(peak_memory_bytes),
                        "Unit": "Bytes",
                    }
                ],
            )

            logger.info("Successfully published peak memory metric")

        except Exception as e:
            # CloudWatch 전송 실패는 메인 로직에 영향 없음
            logger.warning(
                "Failed to publish metric to CloudWatch",
                function_id=function_id,
                runtime=runtime,
                error=str(e),
            )

