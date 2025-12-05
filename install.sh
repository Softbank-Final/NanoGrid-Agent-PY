#!/bin/bash
# NanoGrid Agent EC2 배포 스크립트

set -e

INSTALL_DIR="/opt/nanogrid-agent"
SERVICE_NAME="nanogrid-agent"

echo "=========================================="
echo "NanoGrid Agent 설치 스크립트"
echo "=========================================="

# 1. 시스템 패키지 설치
echo "시스템 패키지 설치 중..."
sudo yum update -y
sudo yum install -y python3.10 python3.10-pip docker git

# 2. Docker 서비스 시작
echo "Docker 서비스 시작..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# 3. 설치 디렉터리 생성
echo "설치 디렉터리 생성..."
sudo mkdir -p $INSTALL_DIR
sudo chown ec2-user:ec2-user $INSTALL_DIR

# 4. 가상 환경 생성 및 패키지 설치
echo "Python 가상 환경 설정..."
cd $INSTALL_DIR
python3.10 -m venv venv
source venv/bin/activate

echo "패키지 설치 중..."
pip install --upgrade pip
pip install -e .

# 5. 설정 파일 복사
echo "설정 파일 복사..."
cp config.yaml $INSTALL_DIR/config.yaml

# 6. 작업 디렉터리 생성
echo "작업 디렉터리 생성..."
sudo mkdir -p /tmp/task
sudo mkdir -p /tmp/output
sudo chown -R ec2-user:ec2-user /tmp/task /tmp/output

# 7. systemd 서비스 등록
echo "systemd 서비스 등록..."
sudo cp nanogrid-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# 8. 서비스 시작
echo "서비스 시작..."
sudo systemctl start $SERVICE_NAME

echo "=========================================="
echo "설치 완료!"
echo "=========================================="
echo ""
echo "서비스 상태 확인: sudo systemctl status $SERVICE_NAME"
echo "로그 확인: sudo journalctl -u $SERVICE_NAME -f"
echo ""

