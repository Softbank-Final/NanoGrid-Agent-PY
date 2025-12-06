"""
NanoGrid Agent 메인 진입점

EC2에서 백그라운드로 실행되는 에이전트
"""

import argparse
import signal
import sys
from typing import Optional

import docker
import structlog


def configure_logging() -> None:
    """구조화된 로깅 설정"""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def main(config_path: Optional[str] = None) -> int:
    """
    에이전트 메인 함수

    Args:
        config_path: 설정 파일 경로 (optional)

    Returns:
        종료 코드
    """
    # 로깅 설정
    configure_logging()
    logger = structlog.get_logger()

    logger.info("=" * 50)
    logger.info("NanoGrid Agent Starting...")
    logger.info("=" * 50)

    try:
        # 설정 로드
        from .config import AgentConfig
        config = AgentConfig.load(config_path)

        logger.info("Configuration loaded")
        logger.info(f"  AWS Region: {config.aws.region}")
        logger.info(f"  SQS Queue: {config.sqs.queue_url}")
        logger.info(f"  Redis: {config.redis.host}:{config.redis.port}")
        logger.info(f"  Warm Pool: {'enabled' if config.warm_pool.enabled else 'disabled'}")
        logger.info(f"  GCP Storage: {'enabled' if config.gcp.enabled else 'disabled'}")

        # Docker 클라이언트 초기화
        docker_client = docker.from_env()
        logger.info("Docker client initialized")

        # 서비스 초기화
        from .docker_service import DockerService, WarmPoolManager
        from .s3_service import S3CodeStorageService
        from .redis_publisher import RedisResultPublisher
        from .cloudwatch_publisher import CloudWatchMetricsPublisher
        from .gcp_service import GcpStorageService
        from .sqs_poller import SqsPoller

        # Warm Pool Manager
        warm_pool = WarmPoolManager(config, docker_client)
        warm_pool.initialize()

        # 서비스들
        s3_service = S3CodeStorageService(config)
        docker_service = DockerService(config, docker_client, warm_pool)
        redis_publisher = RedisResultPublisher(config)
        cloudwatch_publisher = CloudWatchMetricsPublisher(config)

        # GCP 서비스 초기화
        gcp_service = None
        if config.gcp.enabled:
            logger.info("=" * 40)
            logger.info("🌐 Initializing GCP Storage Service")
            logger.info(f"  Bucket: {config.gcp.bucket_name}")
            logger.info(f"  Credentials: {config.gcp.credentials_path}")
            logger.info("=" * 40)
            gcp_service = GcpStorageService(config)
            logger.info("✅ GCP Storage Service initialized")
        else:
            logger.info("⏭️ GCP Storage is disabled")

        # SQS Poller
        poller = SqsPoller(
            config=config,
            s3_service=s3_service,
            docker_service=docker_service,
            redis_publisher=redis_publisher,
            cloudwatch_publisher=cloudwatch_publisher,
            gcp_service=gcp_service,
        )

        # 시그널 핸들러 설정
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            poller.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("=" * 50)
        logger.info("NanoGrid Agent is ready!")
        logger.info("=" * 50)

        # 폴링 시작 (블로킹)
        poller.start()

        # 정리
        logger.info("Shutting down...")
        warm_pool.cleanup()
        redis_publisher.close()
        if gcp_service:
            gcp_service.close()

        logger.info("NanoGrid Agent stopped")
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0

    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        return 1


def cli() -> None:
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="NanoGrid Agent - SQS 기반 코드 실행 에이전트"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="설정 파일 경로 (YAML)",
        default=None,
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="nanogrid-agent 1.0.0",
    )

    args = parser.parse_args()
    sys.exit(main(args.config))


if __name__ == "__main__":
    cli()

