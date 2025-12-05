# Node.js와 Go 런타임 지원

## 개요

NanoGrid Agent가 이제 Python, C++, Node.js, Go 총 4개의 런타임을 지원합니다!

## Docker 이미지 빌드

### 모든 이미지 빌드
```bash
cd ~/NanoGrid-Agent
chmod +x docker/build-new-runtimes.sh
./docker/build-new-runtimes.sh
```

### 개별 빌드
```bash
# Node.js 이미지
docker build -t nodejs-base ./docker/nodejs

# Go 이미지
docker build -t go-base ./docker/go
```

## 설정 업데이트

`config.yaml` 파일을 다음과 같이 업데이트하세요:

```yaml
docker:
  python_image: python-base
  cpp_image: gcc-base
  nodejs_image: nodejs-base   # 추가
  go_image: go-base           # 추가
  work_dir_root: /workspace-root
  default_timeout_ms: 10000
  output_mount_path: /output

warm_pool:
  enabled: true
  python_size: 2
  cpp_size: 1
  nodejs_size: 2   # 추가
  go_size: 1       # 추가
```

## 코드 작성 가이드

### Node.js 함수
프로젝트 구조:
```
function.zip
├── index.js        # 필수: 진입점
├── package.json    # 선택: 의존성
└── ...
```

**index.js 예시:**
```javascript
// index.js
console.log("Hello from Node.js!");

// 파일 읽기/쓰기 예시
const fs = require('fs');
fs.writeFileSync('output.txt', 'Result from Node.js');
```

**package.json 예시:**
```json
{
  "name": "nanogrid-function",
  "version": "1.0.0",
  "dependencies": {
    "axios": "^1.6.0"
  }
}
```

### Go 함수
프로젝트 구조:
```
function.zip
├── main.go         # 필수: 메인 파일
├── go.mod          # 선택: 모듈 정의
├── run.sh          # 필수: 빌드 및 실행 스크립트
└── ...
```

**main.go 예시:**
```go
package main

import (
    "fmt"
    "os"
)

func main() {
    fmt.Println("Hello from Go!")
    
    // 파일 쓰기 예시
    content := []byte("Result from Go")
    os.WriteFile("output.txt", content, 0644)
}
```

**run.sh 예시:**
```bash
#!/bin/bash
set -e

# Go 의존성 다운로드 (go.mod가 있는 경우)
if [ -f "go.mod" ]; then
    go mod download
fi

# 빌드 및 실행
go run main.go
```

**go.mod 예시:**
```go
module nanogrid-function

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
)
```

## SQS 메시지 형식

### Node.js 함수 실행
```json
{
  "requestId": "req-12345",
  "functionId": "func-nodejs-01",
  "runtime": "nodejs",
  "s3Bucket": "nanogrid-code-bucket",
  "s3Key": "functions/nodejs-function.zip",
  "timeoutMs": 5000,
  "memoryMb": 128
}
```

### Go 함수 실행
```json
{
  "requestId": "req-67890",
  "functionId": "func-go-01",
  "runtime": "go",
  "s3Bucket": "nanogrid-code-bucket",
  "s3Key": "functions/go-function.zip",
  "timeoutMs": 10000,
  "memoryMb": 256
}
```

## 런타임별 특징

### Node.js
- **이미지**: `nodejs-base` (Node.js 18 Alpine)
- **진입점**: `index.js`
- **실행 명령**: `node index.js`
- **패키지 관리**: npm (package.json)
- **적합한 용도**: API 호출, 데이터 처리, 웹 스크래핑

### Go
- **이미지**: `go-base` (Go 1.21 Alpine)
- **진입점**: `main.go`
- **실행 명령**: `bash run.sh` (빌드 후 실행)
- **패키지 관리**: Go modules (go.mod)
- **적합한 용도**: 고성능 계산, 동시성 작업, 시스템 프로그래밍

### Python
- **이미지**: `python-base`
- **진입점**: `main.py`
- **실행 명령**: `python main.py`
- **패키지 관리**: pip (requirements.txt)

### C++
- **이미지**: `gcc-base`
- **진입점**: 컴파일된 바이너리
- **실행 명령**: `bash run.sh` (컴파일 후 실행)
- **패키지 관리**: 수동

## 테스트

### 로컬 테스트

#### Node.js 테스트
```bash
# 컨테이너 실행
docker run -it --rm -v $(pwd)/test:/workspace-root nodejs-base sh

# 컨테이너 내부에서
cd /workspace-root
node index.js
```

#### Go 테스트
```bash
# 컨테이너 실행
docker run -it --rm -v $(pwd)/test:/workspace-root go-base sh

# 컨테이너 내부에서
cd /workspace-root
chmod +x run.sh
./run.sh
```

## 문제 해결

### Node.js

**문제**: `Cannot find module 'xxx'`
**해결**: package.json에 의존성을 추가하고 `npm install` 실행

**문제**: Permission denied
**해결**: index.js 파일에 실행 권한이 필요하지 않음 (node가 실행)

### Go

**문제**: `go.mod not found`
**해결**: 외부 패키지를 사용하지 않는다면 go.mod 없이도 실행 가능

**문제**: `run.sh: Permission denied`
**해결**: run.sh 파일에 실행 권한 필요 (`chmod +x run.sh`)

## 성능 비교

| 런타임 | Cold Start | 메모리 사용량 | 적합한 작업 |
|--------|-----------|--------------|------------|
| Python | ~100ms | 낮음 | 데이터 분석, ML |
| Node.js | ~50ms | 매우 낮음 | API, I/O 작업 |
| Go | ~200ms* | 낮음 | 고성능 계산 |
| C++ | ~150ms* | 매우 낮음 | 시스템 프로그래밍 |

*컴파일 시간 포함

## 예제 코드

GitHub에서 각 런타임별 예제를 확인할 수 있습니다:
- [Node.js 예제](./examples/nodejs)
- [Go 예제](./examples/go)
- [Python 예제](./examples/python)
- [C++ 예제](./examples/cpp)

