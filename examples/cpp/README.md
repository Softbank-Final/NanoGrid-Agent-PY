# C++ Function Example

NanoGrid에서 C++ 함수를 실행하는 예제입니다.

## 파일 구조

```
cpp/
├── main.cpp    # C++ 소스 코드
├── run.sh      # 빌드 및 실행 스크립트
└── README.md
```

## 실행 방식

Agent는 C++ 런타임 요청 시 `/bin/bash run.sh`를 실행합니다.

`run.sh`에서 컴파일 및 실행을 처리합니다:
```bash
g++ -o main main.cpp -std=c++17
./main
```

## 배포 방법

1. 파일들을 ZIP으로 압축:
```bash
zip function.zip main.cpp run.sh
```

2. S3에 업로드:
```bash
aws s3 cp function.zip s3://nanogrid-code-bucket/functions/<function-id>/v1.zip
```

## 요청 예시

```json
{
  "requestId": "uuid",
  "functionId": "func-id",
  "runtime": "cpp",
  "s3Bucket": "nanogrid-code-bucket",
  "s3Key": "functions/<function-id>/v1.zip",
  "timeoutMs": 10000,
  "memoryMb": 128
}
```

## 주의사항

- `run.sh`는 반드시 포함되어야 합니다
- `run.sh`에 실행 권한이 있어야 합니다 (`chmod +x run.sh`)
- 컴파일러는 `gcc-base` Docker 이미지에 포함된 g++를 사용합니다

