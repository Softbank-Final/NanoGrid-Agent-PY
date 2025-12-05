#!/bin/bash
set -e

echo "Building and running Go function..."

# Go 모듈이 있으면 의존성 다운로드
if [ -f "go.mod" ]; then
    echo "Downloading dependencies..."
    go mod download
fi

# 빌드 및 실행
go run main.go

