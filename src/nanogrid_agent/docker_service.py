"""
Docker 서비스 및 Warm Pool 관리

Docker 컨테이너 실행 및 재사용 관리
"""

import json
import time
from collections import deque
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

import docker
import structlog
from docker.models.containers import Container

from .config import AgentConfig
from .models import TaskMessage, ExecutionResult


logger = structlog.get_logger()


class RuntimeType(Enum):
    """런타임 타입"""
    PYTHON = "python"
    CPP = "cpp"
    NODEJS = "nodejs"
    GO = "go"


class WarmPoolManager:
    """
    Docker Warm Pool Manager

    컨테이너를 미리 생성하고 Pause 상태로 유지하다가
    요청 시 Unpause하여 재사용
    """

    def __init__(self, config: AgentConfig, docker_client: docker.DockerClient):
        self.config = config
        self.client = docker_client
        self.pools: Dict[RuntimeType, deque] = {
            RuntimeType.PYTHON: deque(),
            RuntimeType.CPP: deque(),
            RuntimeType.NODEJS: deque(),
            RuntimeType.GO: deque(),
        }
        self.locks: Dict[RuntimeType, Lock] = {
            RuntimeType.PYTHON: Lock(),
            RuntimeType.CPP: Lock(),
            RuntimeType.NODEJS: Lock(),
            RuntimeType.GO: Lock(),
        }

    def initialize(self) -> None:
        """Warm Pool 초기화 - 컨테이너 미리 생성"""
        if not self.config.warm_pool.enabled:
            logger.info("Warm Pool is disabled")
            return

        logger.info("=" * 40)
        logger.info("Initializing Warm Pool Manager")
        logger.info("=" * 40)

        # Python Pool
        python_size = self.config.warm_pool.python_size
        logger.info(f"Creating {python_size} Python containers for Warm Pool")
        for i in range(python_size):
            container_id = self._create_and_pause_container(RuntimeType.PYTHON)
            self.pools[RuntimeType.PYTHON].append(container_id)
            logger.info(f"  [{i + 1}] Python container created: {container_id[:12]}")

        # C++ Pool
        cpp_size = self.config.warm_pool.cpp_size
        logger.info(f"Creating {cpp_size} C++ containers for Warm Pool")
        for i in range(cpp_size):
            container_id = self._create_and_pause_container(RuntimeType.CPP)
            self.pools[RuntimeType.CPP].append(container_id)
            logger.info(f"  [{i + 1}] C++ container created: {container_id[:12]}")

        # Node.js Pool
        nodejs_size = self.config.warm_pool.nodejs_size
        logger.info(f"Creating {nodejs_size} Node.js containers for Warm Pool")
        for i in range(nodejs_size):
            container_id = self._create_and_pause_container(RuntimeType.NODEJS)
            self.pools[RuntimeType.NODEJS].append(container_id)
            logger.info(f"  [{i + 1}] Node.js container created: {container_id[:12]}")

        # Go Pool
        go_size = self.config.warm_pool.go_size
        logger.info(f"Creating {go_size} Go containers for Warm Pool")
        for i in range(go_size):
            container_id = self._create_and_pause_container(RuntimeType.GO)
            self.pools[RuntimeType.GO].append(container_id)
            logger.info(f"  [{i + 1}] Go container created: {container_id[:12]}")

        logger.info("Warm Pool initialization completed")
        logger.info(f"  - Python Pool: {len(self.pools[RuntimeType.PYTHON])} containers")
        logger.info(f"  - C++ Pool: {len(self.pools[RuntimeType.CPP])} containers")
        logger.info(f"  - Node.js Pool: {len(self.pools[RuntimeType.NODEJS])} containers")
        logger.info(f"  - Go Pool: {len(self.pools[RuntimeType.GO])} containers")
        logger.info("=" * 40)

    def _get_image_name(self, runtime_type: RuntimeType) -> str:
        """런타임 타입에 따른 이미지 이름 반환"""
        if runtime_type == RuntimeType.PYTHON:
            return self.config.docker.python_image
        elif runtime_type == RuntimeType.CPP:
            return self.config.docker.cpp_image
        elif runtime_type == RuntimeType.NODEJS:
            return self.config.docker.nodejs_image
        elif runtime_type == RuntimeType.GO:
            return self.config.docker.go_image
        else:
            raise ValueError(f"Unsupported runtime type: {runtime_type}")

    def _create_and_pause_container(self, runtime_type: RuntimeType) -> str:
        """컨테이너 생성 및 Pause"""
        image_name = self._get_image_name(runtime_type)
        container_name = f"nanogrid-warmpool-{runtime_type.value}-{int(time.time() * 1000)}"

        logger.debug(
            "Creating warm pool container",
            container_name=container_name,
            image=image_name,
        )

        # 볼륨 마운트: /tmp/task → /workspace-root
        host_path = self.config.task_base_dir
        container_path = self.config.docker.work_dir_root

        container = self.client.containers.run(
            image=image_name,
            name=container_name,
            command=["sleep", "infinity"],
            volumes={host_path: {"bind": container_path, "mode": "rw"}},
            detach=True,
        )

        # Pause
        container.pause()
        logger.debug("Paused container", container_id=container.id[:12])

        return container.id

    def acquire_container(self, runtime_type: RuntimeType) -> str:
        """Pool에서 컨테이너 획득 (Unpause 포함)"""
        logger.debug("Acquiring container", runtime=runtime_type.value)

        with self.locks[runtime_type]:
            pool = self.pools[runtime_type]

            # Pool에서 컨테이너 가져오기
            container_id = pool.popleft() if pool else None

            # Pool이 비어있으면 새로 생성
            if container_id is None:
                logger.warning("Pool is empty, creating new container", runtime=runtime_type.value)
                container_id = self._create_and_pause_container(runtime_type)

        # Unpause
        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            logger.info(
                "Acquired and unpaused container",
                container_id=container_id[:12],
                runtime=runtime_type.value,
            )
            return container_id
        except Exception as e:
            logger.error("Failed to unpause container, creating new one", error=str(e))
            self._cleanup_container(container_id)
            container_id = self._create_and_pause_container(runtime_type)
            container = self.client.containers.get(container_id)
            container.unpause()
            return container_id

    def release_container(self, runtime_type: RuntimeType, container_id: str) -> None:
        """컨테이너를 Pool에 반환 (Pause 포함)"""
        logger.debug("Releasing container", container_id=container_id[:12], runtime=runtime_type.value)

        try:
            container = self.client.containers.get(container_id)

            # 상태 확인
            if container.status != "running":
                logger.warning("Container is not running, removing", container_id=container_id[:12])
                self._cleanup_container(container_id)
                return

            # Pause
            container.pause()
            logger.debug("Paused container", container_id=container_id[:12])

            # Pool에 반환
            with self.locks[runtime_type]:
                self.pools[runtime_type].append(container_id)
                pool_size = len(self.pools[runtime_type])

            logger.info(
                "Released container back to pool",
                container_id=container_id[:12],
                runtime=runtime_type.value,
                pool_size=pool_size,
            )

        except Exception as e:
            logger.error("Failed to release container", container_id=container_id[:12], error=str(e))
            self._cleanup_container(container_id)

    def _cleanup_container(self, container_id: str) -> None:
        """컨테이너 정리 (Stop & Remove)"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            logger.debug("Stopped container", container_id=container_id[:12])
        except Exception:
            pass

        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.debug("Removed container", container_id=container_id[:12])
        except Exception as e:
            logger.warning("Failed to remove container", container_id=container_id[:12], error=str(e))

    def cleanup(self) -> None:
        """모든 Pool 컨테이너 정리"""
        logger.info("Cleaning up Warm Pool containers...")

        for runtime_type, pool in self.pools.items():
            logger.info(f"Cleaning up {runtime_type.value} pool ({len(pool)} containers)")
            while pool:
                container_id = pool.popleft()
                self._cleanup_container(container_id)

        logger.info("Warm Pool cleanup completed")


class DockerService:
    """Docker 컨테이너 실행 서비스"""

    def __init__(
        self,
        config: AgentConfig,
        docker_client: docker.DockerClient,
        warm_pool: WarmPoolManager,
    ):
        self.config = config
        self.client = docker_client
        self.warm_pool = warm_pool

    def run_task(self, task: TaskMessage, work_dir: Path) -> ExecutionResult:
        """
        Docker 컨테이너에서 작업 실행

        Args:
            task: 작업 메시지
            work_dir: 작업 디렉터리

        Returns:
            실행 결과
        """
        request_id = task.request_id
        function_id = task.function_id
        runtime = task.runtime

        logger.info(
            "Starting execution",
            request_id=request_id,
            runtime=runtime,
        )

        # RuntimeType 결정
        runtime_type = self._resolve_runtime_type(runtime)
        container_id: Optional[str] = None
        start_time = time.time()

        try:
            # 1. Warm Pool에서 컨테이너 획득
            container_id = self.warm_pool.acquire_container(runtime_type)
            logger.info(
                "Acquired container from Warm Pool",
                container_id=container_id[:12],
                request_id=request_id,
            )

            # 2. Output 디렉터리 생성
            output_dir = self._create_output_directory(request_id)
            logger.debug("Created output directory", output_dir=str(output_dir))

            # 3. 컨테이너 내부 작업 디렉터리 경로
            container_work_dir = f"{self.config.docker.work_dir_root}/{request_id}"
            logger.debug("Container work dir", path=container_work_dir)

            # 3.5. 컨테이너 내부에서 작업 디렉터리 존재 확인 및 동기화
            self._ensure_workdir_in_container(container_id, container_work_dir, work_dir)

            # 4. 런타임별 실행 커맨드
            cmd = self._build_command(runtime)
            logger.info("Executing command", container_id=container_id[:12], cmd=cmd)

            # 5. input 데이터를 JSON 문자열로 변환 (stdin으로 전달)
            stdin_data = None
            if task.input:
                stdin_data = json.dumps(task.input, ensure_ascii=False)
                logger.info(
                    "Input data will be passed via stdin",
                    input_size=len(stdin_data),
                    request_id=request_id,
                )

            # 6. docker exec로 명령 실행 (stdin 전달)
            exit_code, stdout, stderr = self._execute_in_container(
                container_id, container_work_dir, cmd,
                stdin_data=stdin_data  # stdin으로 input 전달
            )

            duration_millis = int((time.time() - start_time) * 1000)

            # 6. 메모리 측정
            peak_memory_bytes = self._measure_memory(container_id)

            # 7. 최적화 팁 생성
            optimization_tip = self._create_optimization_tip(task, peak_memory_bytes)

            logger.info(
                "Execution finished",
                request_id=request_id,
                exit_code=exit_code,
                duration_ms=duration_millis,
                peak_memory_bytes=peak_memory_bytes,
            )

            return ExecutionResult(
                request_id=request_id,
                function_id=function_id,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_millis=duration_millis,
                success=(exit_code == 0),
                peak_memory_bytes=peak_memory_bytes,
                optimization_tip=optimization_tip,
                output_files=[],  # TODO: Output 파일 업로드
            )

        except Exception as e:
            duration_millis = int((time.time() - start_time) * 1000)
            logger.error(
                "Execution failed",
                request_id=request_id,
                error=str(e),
            )

            return ExecutionResult(
                request_id=request_id,
                function_id=function_id,
                exit_code=-1,
                stdout="",
                stderr=f"Execution failed: {e}",
                duration_millis=duration_millis,
                success=False,
            )

        finally:
            # 컨테이너 반환
            if container_id:
                try:
                    self.warm_pool.release_container(runtime_type, container_id)
                    logger.debug("Released container", container_id=container_id[:12])
                except Exception as e:
                    logger.error("Failed to release container", error=str(e))

    def _resolve_runtime_type(self, runtime: str) -> RuntimeType:
        """런타임 문자열을 RuntimeType으로 변환"""
        runtime_lower = runtime.lower()
        if runtime_lower == "python":
            return RuntimeType.PYTHON
        elif runtime_lower in ("cpp", "c++"):
            return RuntimeType.CPP
        elif runtime_lower in ("nodejs", "node", "javascript", "js"):
            return RuntimeType.NODEJS
        elif runtime_lower in ("go", "golang"):
            return RuntimeType.GO
        else:
            raise ValueError(f"Unsupported runtime: {runtime}")

    def _ensure_workdir_in_container(
        self, container_id: str, container_work_dir: str, host_work_dir: Path
    ) -> None:
        """
        컨테이너 내부에서 작업 디렉터리 존재 확인 및 동기화

        볼륨 마운트된 디렉터리가 컨테이너에서 인식되지 않는 경우를 처리
        """
        try:
            container = self.client.containers.get(container_id)

            # 디렉터리 존재 확인
            check_result = container.exec_run(
                cmd=["test", "-d", container_work_dir],
                workdir="/",
            )

            if check_result.exit_code != 0:
                logger.warning(
                    "Work directory not found in container, creating...",
                    container_work_dir=container_work_dir,
                )

                # 디렉터리 생성
                mkdir_result = container.exec_run(
                    cmd=["mkdir", "-p", container_work_dir],
                    workdir="/",
                )

                if mkdir_result.exit_code != 0:
                    logger.error(
                        "Failed to create work directory in container",
                        container_work_dir=container_work_dir,
                        error=mkdir_result.output.decode("utf-8", errors="replace"),
                    )
                    raise RuntimeError(f"Failed to create work directory: {container_work_dir}")

                # 호스트에서 파일 복사 (docker cp 사용)
                import subprocess

                # docker cp로 파일 복사
                cp_cmd = [
                    "docker", "cp",
                    f"{host_work_dir}/.",  # 디렉터리 내용 전체
                    f"{container_id}:{container_work_dir}/"
                ]

                result = subprocess.run(cp_cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(
                        "Failed to copy files to container",
                        stderr=result.stderr,
                    )
                    raise RuntimeError(f"Failed to copy files to container: {result.stderr}")

                logger.info(
                    "Successfully copied files to container",
                    container_work_dir=container_work_dir,
                )
            else:
                # 디렉터리 내용 확인
                ls_result = container.exec_run(
                    cmd=["ls", "-la", container_work_dir],
                    workdir="/",
                )
                logger.debug(
                    "Work directory exists in container",
                    container_work_dir=container_work_dir,
                    contents=ls_result.output.decode("utf-8", errors="replace")[:500],
                )

        except Exception as e:
            logger.error(
                "Failed to ensure work directory in container",
                container_work_dir=container_work_dir,
                error=str(e),
            )
            raise

    def _build_command(self, runtime: str) -> List[str]:
        """런타임별 실행 커맨드 구성"""
        runtime_lower = runtime.lower()
        if runtime_lower == "python":
            return ["python", "main.py"]
        elif runtime_lower in ("cpp", "c++"):
            return ["/bin/bash", "run.sh"]
        elif runtime_lower in ("nodejs", "node", "javascript", "js"):
            return ["node", "index.js"]
        elif runtime_lower in ("go", "golang"):
            return ["/bin/bash", "run.sh"]
        else:
            raise ValueError(f"Unsupported runtime: {runtime}")

    def _execute_in_container(
        self, container_id: str, work_dir: str, cmd: List[str],
        stdin_data: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        컨테이너 내부에서 명령 실행

        Args:
            container_id: Docker 컨테이너 ID
            work_dir: 컨테이너 내부 작업 디렉터리
            cmd: 실행할 명령어
            stdin_data: stdin으로 전달할 데이터 (JSON 문자열)

        Returns:
            (exit_code, stdout, stderr) 튜플
        """
        try:
            container = self.client.containers.get(container_id)

            if stdin_data:
                # stdin 데이터가 있는 경우: API를 통해 stdin 전달
                logger.debug(
                    "Executing with stdin",
                    stdin_size=len(stdin_data),
                    cmd=cmd,
                )

                # exec_create로 실행 환경 생성
                exec_id = self.client.api.exec_create(
                    container_id,
                    cmd=cmd,
                    workdir=work_dir,
                    stdin=True,
                    stdout=True,
                    stderr=True,
                    tty=False,
                )

                # socket 모드로 exec 시작
                socket = self.client.api.exec_start(
                    exec_id['Id'],
                    socket=True,
                    demux=True,
                )

                # stdin으로 데이터 전송
                sock = socket._sock
                sock.sendall(stdin_data.encode('utf-8'))
                sock.shutdown(1)  # SHUT_WR - 쓰기 종료

                # 출력 읽기
                stdout_chunks = []
                stderr_chunks = []

                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        # Docker API의 multiplexed stream 형식 파싱
                        # 처음 8바이트는 헤더: [stream_type(1), 0, 0, 0, size(4)]
                        while len(data) >= 8:
                            stream_type = data[0]
                            size = int.from_bytes(data[4:8], 'big')
                            if len(data) < 8 + size:
                                break
                            payload = data[8:8+size]
                            if stream_type == 1:  # stdout
                                stdout_chunks.append(payload)
                            elif stream_type == 2:  # stderr
                                stderr_chunks.append(payload)
                            data = data[8+size:]
                    except Exception:
                        break

                sock.close()

                # exec 결과 확인
                exec_info = self.client.api.exec_inspect(exec_id['Id'])
                exit_code = exec_info.get('ExitCode', -1)

                stdout = b''.join(stdout_chunks).decode('utf-8', errors='replace')
                stderr = b''.join(stderr_chunks).decode('utf-8', errors='replace')

                logger.debug(
                    "Exec with stdin finished",
                    exit_code=exit_code,
                    stdout_len=len(stdout),
                    stderr_len=len(stderr),
                )

                return exit_code, stdout, stderr

            else:
                # stdin 데이터가 없는 경우: 기존 방식
                # docker exec
                result = container.exec_run(
                    cmd=cmd,
                    workdir=work_dir,
                    demux=True,  # stdout/stderr 분리
                )

                exit_code = result.exit_code
                stdout_bytes, stderr_bytes = result.output

                stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
                stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

                logger.debug(
                    "Exec finished",
                    exit_code=exit_code,
                    stdout_len=len(stdout),
                    stderr_len=len(stderr),
                )

            return exit_code, stdout, stderr

        except Exception as e:
            logger.error("Failed to execute in container", error=str(e))
            return -1, "", f"Execution failed: {e}"

    def _create_output_directory(self, request_id: str) -> Path:
        """Output 디렉터리 생성"""
        output_dir = Path(self.config.output.base_dir) / request_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _measure_memory(self, container_id: str) -> Optional[int]:
        """컨테이너 메모리 사용량 측정"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            memory_stats = stats.get("memory_stats", {})
            usage = memory_stats.get("usage")

            if usage is not None:
                logger.debug("Memory usage measured", container_id=container_id[:12], bytes=usage)
                return usage
            return None

        except Exception as e:
            logger.warning("Failed to measure memory", error=str(e))
            return None

    def _create_optimization_tip(
        self, task: TaskMessage, peak_memory_bytes: Optional[int]
    ) -> Optional[str]:
        """메모리 최적화 팁 생성"""
        if peak_memory_bytes is None:
            return "메모리 사용량 정보를 가져올 수 없습니다."

        allocated_mb = task.memory_mb or 128
        allocated_bytes = allocated_mb * 1024 * 1024
        ratio = peak_memory_bytes / allocated_bytes
        peak_mb = peak_memory_bytes // (1024 * 1024)

        if ratio < 0.3:
            recommended_mb = int(peak_mb * 1.5) or 1
            savings = (1.0 - recommended_mb / allocated_mb) * 100
            return (
                f"💡 Tip: 현재 메모리 설정({allocated_mb}MB)에 비해 실제 사용량({peak_mb}MB)이 "
                f"매우 낮습니다. 메모리를 {recommended_mb}MB 정도로 줄이면 비용을 약 {savings:.0f}% 절감할 수 있습니다."
            )
        elif ratio < 0.7:
            recommended_mb = int(peak_mb * 1.3) or 1
            return (
                f"✅ Tip: 현재 메모리 설정({allocated_mb}MB)이 비교적 여유 있습니다(사용량: {peak_mb}MB). "
                f"더 절감하려면 {recommended_mb}MB로 조정할 수 있습니다."
            )
        elif ratio <= 1.0:
            return (
                f"✅ Tip: 현재 메모리 설정({allocated_mb}MB)이 적절합니다. "
                f"피크 사용량({peak_mb}MB)이 설정 범위 내에 있습니다."
            )
        else:
            recommended_mb = int(peak_mb * 1.2)
            return (
                f"⚠️ Tip: 피크 메모리 사용량({peak_mb}MB)이 현재 설정({allocated_mb}MB)을 초과했습니다. "
                f"안정적인 실행을 위해 메모리를 {recommended_mb}MB 이상으로 늘리는 것을 권장합니다."
            )
