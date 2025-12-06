#!/bin/bash
set -e

echo "Building and running C++ function..."

# 컴파일
g++ -o main main.cpp -std=c++17

# 실행
./main

