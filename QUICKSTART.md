# NanoGrid Agent - EC2 빠른 실행 가이드

## 🎯 가장 빠른 방법

```bash
cd ~/NanoGrid-Agent
chmod +x run.sh
./run.sh
```

## 📋 수동 실행 (3단계)

### 1단계: 설치
```bash
cd ~/NanoGrid-Agent
pip3 install -e .
```

### 2단계: 실행
```bash
# 테스트용 (포그라운드)
nanogrid-agent --config ~/NanoGrid-Agent/config.yaml

# 또는 백그라운드 실행
nohup nanogrid-agent --config ~/NanoGrid-Agent/config.yaml > ~/nanogrid.log 2>&1 &
```

### 3단계: 로그 확인
```bash
tail -f ~/nanogrid.log
```

## ⚠️ 문제 해결

### "ModuleNotFoundError: No module named 'nanogrid_agent'"
```bash
cd ~/NanoGrid-Agent
pip3 install -e .
```

### Docker 권한 오류
```bash
sudo usermod -aG docker $USER
# 재접속 필요
```

### 프로세스 확인 및 종료
```bash
# 확인
ps aux | grep nanogrid-agent

# 종료
pkill -f nanogrid-agent
```

## 🔧 대안 실행 방법

설치 없이 직접 실행:
```bash
cd ~/NanoGrid-Agent
python3 -m nanogrid_agent --config ~/NanoGrid-Agent/config.yaml
```

## 📊 상태 확인

```bash
# 프로세스 확인
ps aux | grep nanogrid-agent

# 로그 확인
tail -f ~/nanogrid.log

# Docker 컨테이너 확인
docker ps
```

## 🚀 프로덕션 배포 (systemd)

```bash
sudo cp ~/NanoGrid-Agent/nanogrid-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nanogrid-agent
sudo systemctl start nanogrid-agent
sudo systemctl status nanogrid-agent
```

로그 확인:
```bash
sudo journalctl -u nanogrid-agent -f
```

