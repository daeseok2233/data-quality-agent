# src/dq_agent/ai_reporting.py
from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI

from .quality import QualityReport
from . import settings


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """
    OpenAI 클라이언트를 lazy하게 생성해서 재사용.
    API 키가 없으면 RuntimeError를 발생시킨다.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_ai_summary(report: QualityReport) -> str:
    """
    QualityReport 객체를 받아서,
    비전문가가 읽기 좋은 한국어 AI 리포트를 마크다운 형식으로 생성한다.
    """
    client = get_client()
    report_dict = report.to_dict()

    # JSON으로 품질 리포트 내용을 통째로 넘겨주고, 그걸 요약해 달라고 요청
    report_json = json.dumps(report_dict, ensure_ascii=False, indent=2)

    prompt = f"""
당신은 데이터 품질 담당자입니다.
아래 JSON은 하루치 CSV 데이터에 대한 품질 점검 결과입니다.

이 JSON을 바탕으로, 비전문가도 이해할 수 있는 한국어 리포트를 작성해 주세요.

요구사항:
1. 마크다운 형식으로 작성해주세요.
2. 다음과 같은 섹션 구조를 지켜주세요:

## 요약
- 전체 데이터 품질 상태를 3~5줄로 요약합니다.

## 상세 분석
- 결측치가 많은 컬럼 위주로 설명합니다.
- 누락된 필수 컬럼, 추가된 컬럼이 있다면 그 의미를 설명합니다.
- 날짜/시간 파싱 실패가 많은 컬럼이 있다면 그 영향과 원인을 추정합니다.
- 이상치가 많은 수치 컬럼이 있다면 어떤 조치가 필요한지 설명합니다.

## 권장 액션
- 내일 또는 가까운 시일 내에 취하면 좋을 조치들을 bullet point로 3~5개 제안합니다.
- 운영/데이터/분석 관점에서 도움이 될만한 행동을 제안해주세요.

가능하면 JSON 안의 수치(건수, 비율 등)를 적절히 활용해 주세요.

아래는 품질 점검 결과 JSON입니다:

```json
{report_json}
"""
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "너는 데이터 품질 분석가야. 비개발자도 이해할 수 있는 리포트를 한국어로 작성해.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    return content.strip() if content else ""