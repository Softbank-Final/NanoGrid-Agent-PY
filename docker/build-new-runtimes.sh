#!/bin/bash
# Node.js 및 Go Docker 이미지 빌드 스크립트

set -e

echo "=========================================="
echo "  NanoGrid Docker Images Build Script"
echo "=========================================="
echo ""

# Node.js 이미지 빌드
echo "[1/2] Building Node.js base image..."
docker build -t nodejs-base ./docker/nodejs
echo "✓ Node.js image built successfully"
echo ""

# Go 이미지 빌드
echo "[2/2] Building Go base image..."
docker build -t go-base ./docker/go
echo "✓ Go image built successfully"
echo ""

echo "=========================================="
echo "  All images built successfully!"
echo "=========================================="
echo ""
echo "Available images:"
docker images | grep -E "nodejs-base|go-base"
echo ""
echo "To test the images:"
echo "  docker run --rm nodejs-base node --version"
echo "  docker run --rm go-base go version"

