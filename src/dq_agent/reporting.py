from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json

from .quality import QualityReport
from . import settings

try:
    from .ai_reporting import generate_ai_summary
except ImportError:
    generate_ai_summary = None  # AI 리포트 생성 기능이 없는 경우


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json_report(report: QualityReport, dt: datetime | None = None) -> Path:
    if dt is None:
        dt = datetime.today()

    ensure_dir(settings.REPORT_DIR)
    file_name = f"quality_report_{dt.strftime('%Y_%m_%d')}.json"
    file_path = settings.REPORT_DIR / file_name

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    return file_path


def _make_table_from_rows(rows, highlight_missing: bool = False, max_rows: int = 20) -> str:
    """
    row_issues rows(list[dict]) -> markdown table
    - highlight_missing=True면 missing_columns에 포함된 컬럼을 **굵게**
    - max_rows: 표 길이 제한
    """
    if not rows:
        return "- (해당 없음)"

    rows_to_show = rows[:max_rows]
    hidden = len(rows) - len(rows_to_show)

    # 가독성: 핵심 컬럼만 우선 노출
    preferred = [
        "row_index",
        "order_id",
        "order_date",
        "customer_id",
        "product_id",
        "quantity",
        "unit_price",
        "amount",
        "issues",
    ]

    meta_keys = {"missing_columns"}
    all_keys = set()
    for r in rows_to_show:
        all_keys.update(r.keys())

    keys = [k for k in preferred if k in all_keys]
    # 혹시 누락된 키가 있으면 뒤에 붙임(안정성)
    for k in sorted(all_keys):
        if k not in keys and k not in meta_keys:
            keys.append(k)

    header = "| " + " | ".join(keys) + " |\n"
    sep = "| " + " | ".join(["---"] * len(keys)) + " |\n"
    lines = [header, sep]

    for r in rows_to_show:
        row_missing = set(r.get("missing_columns", [])) if highlight_missing else set()
        issues_list = r.get("issues", [])
        issues_str = ", ".join(str(x) for x in issues_list) if isinstance(issues_list, list) else (str(issues_list) if issues_list else "")

        cells = []
        for k in keys:
            if k == "issues":
                val = issues_str
            else:
                val = r.get(k, "")
                if highlight_missing and k in row_missing:
                    val = f"**{val}**"
            cells.append(str(val))

        lines.append("| " + " | ".join(cells) + " |")

    table = "\n".join(lines)
    if hidden > 0:
        table += f"\n\n- (표에는 상위 {len(rows_to_show)}건만 표시했습니다. 나머지 {hidden}건은 JSON에서 확인하세요.)"

    return table


def generate_markdown_from_report(report: QualityReport, dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.today()

    title_date = dt.strftime("%Y-%m-%d")

    if not report.has_file:
        return f"""# 데이터 품질 리포트 - {title_date}

## 상태 요약
- ❌ 파일 없음
- 메시지: {report.message}
"""

    data = report.to_dict()
    missing = data.get("missing", {})
    outlier = data.get("outlier", {})
    row_issues = data.get("row_issues", {}) or {}

    # ===== 카운트 (4개만) =====
    missing_cnt = sum(missing.get("missing_by_column", {}).values()) if missing else 0
    dup_cnt = len(row_issues.get("duplicates", []))
    br_cnt = len(row_issues.get("business_rule", []))
    outlier_cnt = sum(outlier.get("outlier_count_by_column", {}).values()) if outlier else 0

    has_issue = any([missing_cnt, dup_cnt, outlier_cnt, br_cnt])
    status = "⚠️ 이슈 발견" if has_issue else "✅ 이상 없음"

    # ===== 결측 요약 =====
    missing_by_column = missing.get("missing_by_column", {})
    missing_ratio_by_column = missing.get("missing_ratio_by_column", {})
    missing_lines = [
        f"- {col}: {missing_by_column.get(col, 0)}개 ({missing_ratio_by_column.get(col, 0.0):.2%})"
        for col in missing_by_column
    ]
    missing_block = "\n".join(missing_lines) if missing_lines else "- (컬럼 없음)"

    # ===== 이상치 요약 =====
    outlier_lines = []
    for col, cnt in outlier.get("outlier_count_by_column", {}).items():
        outlier_lines.append(f"- {col}: 이상치 **{cnt}**건")
    outlier_block = "\n".join(outlier_lines) if outlier_lines else "- (수치형 컬럼 없음)"

    # ===== 행 단위 이슈 테이블 =====
    missing_rows_md = _make_table_from_rows(row_issues.get("missing", []), highlight_missing=True)
    dup_rows_md = _make_table_from_rows(row_issues.get("duplicates", []))
    business_rule_rows_md = _make_table_from_rows(row_issues.get("business_rule", []))

    md = f"""# 데이터 품질 리포트 - {title_date}

## 1. 상태 요약
- 상태: {status}
- 메시지: {report.message}
- 이슈 개요: 결측 **{missing_cnt}** / 중복 **{dup_cnt}** / 이상치 **{outlier_cnt}** / 룰 위반 **{br_cnt}**

## 2. 결측치 점검
{missing_block}

## 3. 이상치(IQR) 점검
- 방법: {outlier.get('method', 'iqr')}
- IQR 배수: {outlier.get('iqr_multiplier', 1.5)}
{outlier_block}

## 4. 문제가 있는 행 상세

### 4-1. 결측값 포함 행
(굵게 표시된 값은 결측 컬럼입니다.)
{missing_rows_md}

### 4-2. 중복 order_id 행
{dup_rows_md}

### 4-3. 비즈니스 룰 위반 행
(0/음수 값, 금액 불일치, 날짜 형식 오류, 기준일 불일치 포함)
{business_rule_rows_md}
"""
    return md


def save_markdown_report(report: QualityReport, dt: datetime | None = None) -> Path:
    if dt is None:
        dt = datetime.today()

    ensure_dir(settings.REPORT_DIR)
    file_name = f"quality_report_{dt.strftime('%Y_%m_%d')}.md"
    file_path = settings.REPORT_DIR / file_name

    md = generate_markdown_from_report(report, dt=dt)

    # AI 요약 리포트 추가
    if (
        settings.ENABLE_AI_REPORT
        and settings.OPENAI_API_KEY
        and generate_ai_summary is not None
    ):
        try:
            ai_md = generate_ai_summary(report)
            md += "\n\n---\n\n## AI 요약\n\n" + ai_md + "\n"
        except Exception as e:
            md += f"\n\n---\n\n**[AI 요약 생성 실패]**: {e}\n"

    with file_path.open("w", encoding="utf-8") as f:
        f.write(md)

    return file_path
