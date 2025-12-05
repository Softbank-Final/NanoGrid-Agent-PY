# Go Base Image for NanoGrid
FROM golang:1.21-alpine

# 작업 디렉터리 생성
WORKDIR /workspace-root

# 기본 패키지 설치
RUN apk add --no-cache \
    bash \
    git \
    build-base

# Go 환경 변수 설정
ENV GO111MODULE=on \
    CGO_ENABLED=1

# 컨테이너 실행 유지
CMD ["sleep", "infinity"]

