from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI

from .quality import QualityReport
from . import settings


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is not None:
        return _client

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_ai_summary(report: QualityReport) -> str:
    """
    ✅ '요약' + '권장 액션'만 출력 (짧고 명확)
    ✅ 검사 범위는 4개만:
    - 결측
    - 중복
    - 이상치(IQR)
    - 비즈니스 룰 위반(0/음수, 금액 불일치, 날짜 문제 포함)
    """
    client = get_client()
    report_dict = report.to_dict()
    report_json = json.dumps(report_dict, ensure_ascii=False, indent=2)

    prompt = f"""
당신은 데이터 품질(Data Quality) 담당자입니다.
아래 JSON은 하루치 CSV 데이터에 대한 품질 점검 결과입니다.

이 리포트의 목적은 "조언"이 아니라,
실무에서 바로 적용할 수 있는 **데이터 처리 정책**을 제시하는 것입니다.

이 프로젝트는 아래 4가지 품질 신호만 다룹니다:
1) 결측(missing)
2) 중복(duplicates)
3) 이상치(outlier, IQR)
4) 비즈니스 룰 위반(business_rule)
   - 0/음수 값
   - amount 불일치(amount != quantity * unit_price)
   - 날짜 형식 오류(invalid_date_format)
   - 기준일 불일치(non_base_date)

⚠️ 매우 중요한 작성 규칙:
- "검토하세요", "고려하세요", "강화하세요" 같은 **조언형 표현을 사용하지 마세요**.
- 각 항목은 반드시 **명확한 처리 기준(정책)** 형태로 작성하세요.
- 문장은 "~한다", "~제외한다", "~분리한다"처럼 **결정형**으로 끝나야 합니다.
- 실제 운영·분석 단계에서 바로 실행 가능한 행동만 작성하세요.
- JSON에 명시적으로 존재하지 않는 비즈니스 의미(예: 환불, 취소)는 절대 단정하지 마세요.
- 0 또는 음수 값은 의미 해석을 하지 말고,
  "정상 데이터에서 제외한다" 또는 "별도 검토 대상으로 분리한다"처럼 중립적으로 표현하세요.
- '환불', '취소'라는 단어는 JSON에 해당 컬럼이나 플래그가 없는 한 사용하지 마세요.

출력 형식은 반드시 아래 두 섹션만 포함해야 합니다.

## 요약
- 3~5줄
- 전체 데이터 품질 상태와 가장 중요한 리스크를 요약
- 수치(건수/비율)를 반드시 포함

## 권장 데이터 처리 정책
- 5~8개의 bullet point
- 각 bullet은 하나의 **명확한 정책 문장**
- 조언형 표현 금지
- 비즈니스 의미를 단정하지 말 것

예시(형식 참고용, 의미 단정 금지):
- "amount 불일치 행은 분석 대상에서 제외한다."
- "0 또는 음수 수량, 단가, 금액 행은 정상 주문 데이터로 간주하지 않는다."
- "날짜 형식 오류 행은 분석 대상에서 제외한다."

아래는 품질 점검 결과 JSON입니다:

```json
{report_json}
```
"""
    response = client.chat.completions.create(
    model=settings.OPENAI_MODEL,
    messages=[
    {"role": "system", "content": "너는 데이터 품질 분석가야. 비개발자도 이해할 수 있게 짧고 명확하게 써."},
    {"role": "user", "content": prompt},
    ],
    temperature=0.2,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""

  
  