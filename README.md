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
# 직접 실행
nanogrid-agent

# 또는 모듈로 실행
python -m nanogrid_agent

# 설정 파일 지정
nanogrid-agent --config /path/to/config.yaml
```

## EC2 배포

```bash
# 백그라운드 실행
nohup nanogrid-agent > /var/log/nanogrid-agent.log 2>&1 &

# systemd 서비스로 등록 (권장)
sudo cp nanogrid-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nanogrid-agent
sudo systemctl start nanogrid-agent
```

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NANOGRID_CONFIG` | 설정 파일 경로 | `./config.yaml` |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `SQS_QUEUE_URL` | SQS 큐 URL | - |
| `REDIS_HOST` | Redis 호스트 | `127.0.0.1` |
| `REDIS_PORT` | Redis 포트 | `6379` |

