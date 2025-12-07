"""
데이터 모델 정의
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TaskMessage:
    """
    SQS 메시지로 수신하는 작업 요청 DTO

    JSON 예시:
    {
        "requestId": "uuid-string",
        "functionId": "func-01",
        "runtime": "python",  // "python", "cpp", "nodejs", "go"
        "s3Bucket": "code-bucket-name",
        "s3Key": "func-01/v1.zip",
        "timeoutMs": 5000,
        "memoryMb": 128,
        "input": {"key": "value"}  // 사용자 함수에 stdin으로 전달될 입력 데이터
    }
    """
    request_id: str
    function_id: str
    runtime: str  # "python", "cpp", "nodejs", "go"
    s3_bucket: str
    s3_key: str
    timeout_ms: int = 10000
    memory_mb: Optional[int] = None
    input: Optional[dict] = None  # Controller에서 전달받는 input 데이터 (stdin으로 전달)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskMessage":
        """딕셔너리에서 TaskMessage 생성"""
        return cls(
            request_id=data.get("requestId", ""),
            function_id=data.get("functionId", ""),
            runtime=data.get("runtime", "python"),
            s3_bucket=data.get("s3Bucket", ""),
            s3_key=data.get("s3Key", ""),
            timeout_ms=data.get("timeoutMs", 10000),
            memory_mb=data.get("memoryMb"),
            input=data.get("input"),  # input 필드 추가
        )

    def __str__(self) -> str:
        input_preview = str(self.input)[:50] + "..." if self.input and len(str(self.input)) > 50 else str(self.input)
        return (
            f"TaskMessage[requestId={self.request_id}, functionId={self.function_id}, "
            f"runtime={self.runtime}, s3Bucket={self.s3_bucket}, s3Key={self.s3_key}, "
            f"timeoutMs={self.timeout_ms}, memoryMb={self.memory_mb}, input={input_preview}]"
        )


@dataclass
class ExecutionResult:
    """
    Docker 컨테이너 실행 결과를 담는 DTO
    """
    request_id: str
    function_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_millis: int
    success: bool
    peak_memory_bytes: Optional[int] = None
    optimization_tip: Optional[str] = None
    output_files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Redis 전송용 딕셔너리 변환"""
        result = {
            "requestId": self.request_id,
            "functionId": self.function_id,
            "status": "SUCCESS" if self.success else "FAILED",
            "exitCode": self.exit_code,
            "durationMillis": self.duration_millis,
            "stdout": self.stdout or "",
            "stderr": self.stderr or "",
        }

        if self.peak_memory_bytes is not None:
            result["peakMemoryBytes"] = self.peak_memory_bytes
            result["peakMemoryMB"] = self.peak_memory_bytes // (1024 * 1024)

        if self.optimization_tip:
            result["optimizationTip"] = self.optimization_tip

        if self.output_files:
            result["outputFiles"] = self.output_files

        return result

    def __str__(self) -> str:
        return (
            f"ExecutionResult[requestId={self.request_id}, functionId={self.function_id}, "
            f"exitCode={self.exit_code}, durationMillis={self.duration_millis}, "
            f"success={self.success}, peakMemoryBytes={self.peak_memory_bytes}]"
        )

