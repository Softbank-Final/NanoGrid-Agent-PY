"""
Redis 결과 발행 서비스

실행 결과를 Redis Pub/Sub으로 전송
"""

import json
from datetime import timedelta

import redis
import structlog

from .config import AgentConfig
from .models import ExecutionResult


logger = structlog.get_logger()


class RedisResultPublisher:
    """Redis Pub/Sub을 통해 실행 결과를 Controller에게 전송"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._client: redis.Redis = None

    def _get_client(self) -> redis.Redis:
        """Redis 클라이언트 lazy 초기화"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                password=self.config.redis.password or None,
                decode_responses=True,
            )
        return self._client

    def publish_result(self, result: ExecutionResult) -> None:
        """
        실행 결과를 Redis Pub/Sub 채널로 전송

        Args:
            result: 실행 결과
        """
        request_id = result.request_id
        channel = f"{self.config.redis.result_prefix}{request_id}"

        try:
            client = self._get_client()

            # JSON 직렬화
            payload = result.to_dict()
            json_message = json.dumps(payload, ensure_ascii=False)

            logger.info(
                "Publishing result to Redis",
                channel=channel,
                request_id=request_id,
                redis_host=self.config.redis.host,
            )

            # Redis Publish
            subscriber_count = client.publish(channel, json_message)

            if subscriber_count > 0:
                logger.info(
                    "Result published successfully",
                    request_id=request_id,
                    subscribers=subscriber_count,
                )
            else:
                logger.warning(
                    "Result published but NO SUBSCRIBERS",
                    channel=channel,
                    request_id=request_id,
                )

            # 비동기 모드 지원: 결과를 Redis에 저장 (TTL 10분)
            job_key = f"job:{request_id}"
            client.setex(job_key, timedelta(seconds=600), json_message)
            logger.info("Job result saved", key=job_key, ttl_seconds=600)

        except Exception as e:
            logger.error(
                "Failed to publish result to Redis",
                request_id=request_id,
                channel=channel,
                error=str(e),
            )
            # Redis 전송 실패해도 Worker는 계속 동작

    def close(self) -> None:
        """Redis 연결 종료"""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

