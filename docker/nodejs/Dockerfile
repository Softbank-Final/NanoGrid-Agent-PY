# Node.js Base Image for NanoGrid
FROM node:18-alpine

# 작업 디렉터리 생성
WORKDIR /workspace-root

# 기본 패키지 설치
RUN apk add --no-cache \
    bash \
    curl

# npm 글로벌 패키지 (필요시 추가)
# RUN npm install -g typescript

# 컨테이너 실행 유지
CMD ["sleep", "infinity"]

