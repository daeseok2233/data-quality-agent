#!/usr/bin/env bash
set -euo pipefail

# 프로젝트 루트로 이동 (중요)
cd /home/daeseok/dq-agent

# 로그 디렉토리 생성
mkdir -p logs

# 데이터 품질 점검 실행
uv run python -m dq_agent.main >> logs/cron.log 2>&1
