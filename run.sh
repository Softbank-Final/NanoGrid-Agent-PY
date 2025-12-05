#!/bin/bash
# NanoGrid Agent 빠른 실행 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  NanoGrid Agent 실행 스크립트${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}현재 디렉토리: ${NC}$SCRIPT_DIR"
echo ""

# 0. Python 버전 확인
echo -e "${YELLOW}[0/4] Python 버전 확인...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Python 버전: ${NC}$PYTHON_VERSION"

# Python 버전이 3.9 이상인지 확인 (간단한 체크)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}✗ Python 3.9 이상이 필요합니다 (현재: $PYTHON_VERSION)${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Python 버전 확인 완료 (3.9 이상)${NC}"
fi
echo ""

# 1. 패키지 설치 확인
echo -e "${YELLOW}[1/4] 패키지 설치 확인...${NC}"
if ! pip3 show nanogrid-agent > /dev/null 2>&1; then
    echo -e "${YELLOW}패키지가 설치되지 않았습니다. 설치 중...${NC}"
    pip3 install -e . --force-reinstall
    echo -e "${GREEN}✓ 패키지 설치 완료${NC}"
else
    echo -e "${GREEN}✓ 패키지가 이미 설치되어 있습니다${NC}"
fi
echo ""

# 2. Docker 확인
echo -e "${YELLOW}[2/4] Docker 확인...${NC}"
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker가 실행되지 않았거나 권한이 없습니다${NC}"
    echo -e "${YELLOW}다음 명령어로 권한을 추가하세요:${NC}"
    echo -e "  sudo usermod -aG docker \$USER"
    echo -e "  (재로그인 필요)"
    exit 1
else
    echo -e "${GREEN}✓ Docker 실행 중${NC}"
fi
echo ""

# 3. AWS 자격증명 확인
echo -e "${YELLOW}[3/4] AWS 자격증명 확인...${NC}"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}✗ AWS 자격증명이 설정되지 않았습니다${NC}"
    echo -e "${YELLOW}EC2 IAM Role을 확인하거나 'aws configure'를 실행하세요${NC}"
    exit 1
else
    echo -e "${GREEN}✓ AWS 자격증명 확인 완료${NC}"
fi
echo ""

# 4. config.yaml 확인
echo -e "${YELLOW}[4/4] 설정 파일 확인...${NC}"
if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
    echo -e "${RED}✗ config.yaml 파일이 없습니다${NC}"
    exit 1
else
    echo -e "${GREEN}✓ config.yaml 존재${NC}"
fi
echo ""

# 실행 모드 선택
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}실행 모드를 선택하세요:${NC}"
echo -e "  ${GREEN}1${NC}) 포그라운드 실행 (테스트용)"
echo -e "  ${GREEN}2${NC}) 백그라운드 실행"
echo -e "  ${GREEN}3${NC}) 종료"
echo -e "${BLUE}========================================${NC}"
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo -e "${GREEN}포그라운드에서 실행합니다...${NC}"
        echo -e "${YELLOW}Ctrl+C로 종료할 수 있습니다${NC}"
        echo ""
        nanogrid-agent --config "$SCRIPT_DIR/config.yaml"
        ;;
    2)
        LOG_FILE="$HOME/nanogrid.log"
        echo -e "${GREEN}백그라운드에서 실행합니다...${NC}"
        nohup nanogrid-agent --config "$SCRIPT_DIR/config.yaml" > "$LOG_FILE" 2>&1 &
        PID=$!
        echo -e "${GREEN}✓ 백그라운드 실행 시작 (PID: $PID)${NC}"
        echo -e "${YELLOW}로그 파일: ${NC}$LOG_FILE"
        echo ""
        echo -e "${BLUE}로그 확인:${NC} tail -f $LOG_FILE"
        echo -e "${BLUE}프로세스 확인:${NC} ps aux | grep nanogrid-agent"
        echo -e "${BLUE}프로세스 종료:${NC} kill $PID"
        ;;
    3)
        echo -e "${YELLOW}종료합니다${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}잘못된 선택입니다${NC}"
        exit 1
        ;;
esac

