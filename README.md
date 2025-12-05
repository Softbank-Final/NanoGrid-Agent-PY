# NanoGrid Agent (Python)

경량화된 SQS 기반 코드 실행 에이전트.

## 기능

- **SQS Long Polling**: AWS SQS에서 작업 메시지 수신
- **S3 Code Download**: S3에서 코드 zip 다운로드 및 압축 해제
- **Docker Execution**: Docker 컨테이너에서 코드 실행
- **Warm Pool**: 컨테이너 재사용으로 Cold Start 제거
- **Redis Publish**: 실행 결과를 Redis Pub/Sub으로 전송
- **CloudWatch Metrics**: 메모리 사용량 메트릭 전송
- **Output Binding**: 생성된 파일을 S3에 자동 업로드

## 설치

```bash
# EC2 환경에서 설치
cd ~/NanoGrid-Agent
pip install -e .
```

## 설정

`config.yaml` 파일을 생성하거나 환경 변수로 설정:

```yaml
aws:
  region: ap-northeast-2

sqs:
  queue_url: https://sqs.ap-northeast-2.amazonaws.com/123456789/queue-name
  wait_time_seconds: 20
  max_number_of_messages: 10

s3:
  code_bucket: nanogrid-code-bucket
  user_data_bucket: nanogrid-user-data

docker:
  python_image: python-base
  cpp_image: gcc-base
  work_dir_root: /workspace-root
  default_timeout_ms: 10000

warm_pool:
  enabled: true
  python_size: 2
  cpp_size: 1

redis:
  host: localhost
  port: 6379
  password: ""
  result_prefix: "result:"

output:
  enabled: true
  base_dir: /tmp/output
  s3_prefix: outputs

task_base_dir: /tmp/task
```

## 실행

```bash
# 방법 1: 설치 후 명령어로 실행
cd ~/NanoGrid-Agent
nanogrid-agent

# 방법 2: Python 모듈로 직접 실행 (설치 없이)
cd ~/NanoGrid-Agent
python3 -m src.nanogrid_agent.main

# 방법 3: 설정 파일 지정
nanogrid-agent --config /path/to/config.yaml

# 방법 4: Python으로 직접 실행
cd ~/NanoGrid-Agent
python3 src/nanogrid_agent/main.py
```

## EC2 배포

```bash
# 1. 먼저 패키지 설치
cd ~/NanoGrid-Agent
pip install -e .

# 2. 백그라운드 실행
nohup nanogrid-agent --config ~/NanoGrid-Agent/config.yaml > /var/log/nanogrid-agent.log 2>&1 &

# 3. systemd 서비스로 등록 (권장)
# nanogrid-agent.service 파일을 수정하여 경로 확인 후
sudo cp ~/NanoGrid-Agent/nanogrid-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nanogrid-agent
sudo systemctl start nanogrid-agent

# 서비스 상태 확인
sudo systemctl status nanogrid-agent

# 로그 확인
sudo journalctl -u nanogrid-agent -f
```

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NANOGRID_CONFIG` | 설정 파일 경로 | `./config.yaml` |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `SQS_QUEUE_URL` | SQS 큐 URL | - |
| `REDIS_HOST` | Redis 호스트 | `127.0.0.1` |
| `REDIS_PORT` | Redis 포트 | `6379` |

## 🚀 EC2에서 빠른 실행 가이드

현재 `~/NanoGrid-Agent` 디렉토리에 있다면:

### 빠른 시작 (자동 스크립트)
```bash
cd ~/NanoGrid-Agent
chmod +x run.sh
./run.sh
```
이 스크립트는 자동으로:
- 패키지 설치 확인
- Docker 실행 확인
- AWS 자격증명 확인
- 설정 파일 확인
- 실행 모드 선택 (포그라운드/백그라운드)

### 수동 실행

#### 1단계: 의존성 설치
```bash
cd ~/NanoGrid-Agent
pip3 install -e .
```

#### 2단계: Docker 및 AWS 설정 확인
```bash
# Docker 확인
docker ps

# AWS 자격증명 확인
aws sts get-caller-identity
```

#### 3단계: 실행 방법 선택

#### 방법 A: 직접 실행 (테스트용)
```bash
nanogrid-agent --config ~/NanoGrid-Agent/config.yaml
```

#### 방법 B: 백그라운드 실행
```bash
nohup nanogrid-agent --config ~/NanoGrid-Agent/config.yaml > ~/nanogrid.log 2>&1 &

# 로그 확인
tail -f ~/nanogrid.log
```

#### 방법 C: systemd 서비스 (프로덕션 권장)
```bash
sudo cp ~/NanoGrid-Agent/nanogrid-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nanogrid-agent
sudo systemctl start nanogrid-agent
sudo systemctl status nanogrid-agent
```

## 트러블슈팅

### ❌ "ModuleNotFoundError: No module named 'nanogrid_agent'"
**원인**: 패키지가 설치되지 않음

**해결**:
```bash
cd ~/NanoGrid-Agent
pip3 install -e .
```

### ❌ "FileNotFoundError: config.yaml"
**원인**: config.yaml 파일을 찾을 수 없음

**해결**:
```bash
# 설정 파일 경로 명시
nanogrid-agent --config ~/NanoGrid-Agent/config.yaml

# 또는 현재 디렉토리에서 실행
cd ~/NanoGrid-Agent
nanogrid-agent
```

### ❌ Docker 권한 오류
**원인**: Docker 소켓 접근 권한 부족

**해결**:
```bash
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인하거나 EC2 재접속
```

### ❌ AWS 자격증명 오류
**원인**: AWS 자격증명이 설정되지 않음

**해결**:
```bash
# EC2 IAM Role 확인
aws sts get-caller-identity

# 또는 자격증명 설정
aws configure
```

### 프로세스 관리
```bash
# 실행 중인 프로세스 확인
ps aux | grep nanogrid-agent

# 프로세스 종료
pkill -f nanogrid-agent

# 또는 PID로 종료
kill <PID>
```

### 로그 확인
```bash
# nohup으로 실행한 경우
tail -f ~/nanogrid.log

# systemd로 실행한 경우
sudo journalctl -u nanogrid-agent -f
```
