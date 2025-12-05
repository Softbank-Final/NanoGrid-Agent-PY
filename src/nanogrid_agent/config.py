"""
설정 관리 모듈

YAML 파일 또는 환경 변수에서 설정을 로드
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class AwsConfig:
    region: str = "ap-northeast-2"


@dataclass
class SqsConfig:
    queue_url: str = ""
    wait_time_seconds: int = 20
    max_number_of_messages: int = 10


@dataclass
class S3Config:
    code_bucket: str = ""
    user_data_bucket: str = ""


@dataclass
class DockerConfig:
    python_image: str = "python-base"
    cpp_image: str = "gcc-base"
    work_dir_root: str = "/workspace-root"
    default_timeout_ms: int = 10000
    output_mount_path: str = "/output"


@dataclass
class WarmPoolConfig:
    enabled: bool = True
    python_size: int = 2
    cpp_size: int = 1


@dataclass
class PollingConfig:
    enabled: bool = True
    fixed_delay_seconds: float = 1.0


@dataclass
class RedisConfig:
    host: str = "127.0.0.1"
    port: int = 6379
    password: str = ""
    result_prefix: str = "result:"


@dataclass
class OutputConfig:
    enabled: bool = True
    base_dir: str = "/tmp/output"
    s3_prefix: str = "outputs"


@dataclass
class AgentConfig:
    """에이전트 통합 설정"""
    aws: AwsConfig = field(default_factory=AwsConfig)
    sqs: SqsConfig = field(default_factory=SqsConfig)
    s3: S3Config = field(default_factory=S3Config)
    docker: DockerConfig = field(default_factory=DockerConfig)
    warm_pool: WarmPoolConfig = field(default_factory=WarmPoolConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    task_base_dir: str = "/tmp/task"

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """딕셔너리에서 설정 로드"""
        config = cls()

        if "aws" in data:
            config.aws = AwsConfig(**data["aws"])
        if "sqs" in data:
            config.sqs = SqsConfig(**data["sqs"])
        if "s3" in data:
            config.s3 = S3Config(**data["s3"])
        if "docker" in data:
            config.docker = DockerConfig(**data["docker"])
        if "warm_pool" in data:
            config.warm_pool = WarmPoolConfig(**data["warm_pool"])
        if "polling" in data:
            config.polling = PollingConfig(**data["polling"])
        if "redis" in data:
            config.redis = RedisConfig(**data["redis"])
        if "output" in data:
            config.output = OutputConfig(**data["output"])
        if "task_base_dir" in data:
            config.task_base_dir = data["task_base_dir"]

        return config

    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """YAML 파일에서 설정 로드"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data or {})

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """환경 변수에서 설정 로드"""
        config = cls()

        # AWS
        config.aws.region = os.getenv("AWS_REGION", config.aws.region)

        # SQS
        config.sqs.queue_url = os.getenv("SQS_QUEUE_URL", config.sqs.queue_url)
        config.sqs.wait_time_seconds = int(os.getenv("SQS_WAIT_TIME_SECONDS", config.sqs.wait_time_seconds))
        config.sqs.max_number_of_messages = int(os.getenv("SQS_MAX_MESSAGES", config.sqs.max_number_of_messages))

        # S3
        config.s3.code_bucket = os.getenv("S3_CODE_BUCKET", config.s3.code_bucket)
        config.s3.user_data_bucket = os.getenv("S3_USER_DATA_BUCKET", config.s3.user_data_bucket)

        # Docker
        config.docker.python_image = os.getenv("DOCKER_PYTHON_IMAGE", config.docker.python_image)
        config.docker.cpp_image = os.getenv("DOCKER_CPP_IMAGE", config.docker.cpp_image)
        config.docker.work_dir_root = os.getenv("DOCKER_WORK_DIR_ROOT", config.docker.work_dir_root)
        config.docker.default_timeout_ms = int(os.getenv("DOCKER_TIMEOUT_MS", config.docker.default_timeout_ms))

        # Warm Pool
        config.warm_pool.enabled = os.getenv("WARM_POOL_ENABLED", "true").lower() == "true"
        config.warm_pool.python_size = int(os.getenv("WARM_POOL_PYTHON_SIZE", config.warm_pool.python_size))
        config.warm_pool.cpp_size = int(os.getenv("WARM_POOL_CPP_SIZE", config.warm_pool.cpp_size))

        # Redis
        config.redis.host = os.getenv("REDIS_HOST", config.redis.host)
        config.redis.port = int(os.getenv("REDIS_PORT", config.redis.port))
        config.redis.password = os.getenv("REDIS_PASSWORD", config.redis.password)
        config.redis.result_prefix = os.getenv("REDIS_RESULT_PREFIX", config.redis.result_prefix)

        # Output
        config.output.enabled = os.getenv("OUTPUT_ENABLED", "true").lower() == "true"
        config.output.base_dir = os.getenv("OUTPUT_BASE_DIR", config.output.base_dir)
        config.output.s3_prefix = os.getenv("OUTPUT_S3_PREFIX", config.output.s3_prefix)

        # Task
        config.task_base_dir = os.getenv("TASK_BASE_DIR", config.task_base_dir)

        return config

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AgentConfig":
        """설정 로드 (YAML 파일 우선, 환경 변수 fallback)"""
        # 1. 명시적 경로
        if config_path and Path(config_path).exists():
            config = cls.from_yaml(config_path)
        # 2. 환경 변수로 지정된 경로
        elif os.getenv("NANOGRID_CONFIG") and Path(os.getenv("NANOGRID_CONFIG")).exists():
            config = cls.from_yaml(os.getenv("NANOGRID_CONFIG"))
        # 3. 기본 경로
        elif Path("config.yaml").exists():
            config = cls.from_yaml("config.yaml")
        # 4. 환경 변수에서 로드
        else:
            config = cls.from_env()

        # 환경 변수로 오버라이드 (우선순위 높음)
        env_config = cls.from_env()

        # SQS URL이 환경 변수에 있으면 오버라이드
        if os.getenv("SQS_QUEUE_URL"):
            config.sqs.queue_url = env_config.sqs.queue_url
        if os.getenv("REDIS_HOST"):
            config.redis.host = env_config.redis.host

        return config

