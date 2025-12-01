# src/dq_agent/reporting.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
from textwrap import indent

from .quality import QualityReport
from . import settings


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


def generate_markdown_from_report(report: QualityReport, dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.today()

    title_date = dt.strftime("%Y-%m-%d")

    if not report.has_file:
        md = f"""# 데이터 품질 리포트 - {title_date}

## 상태 요약
- 오늘 날짜에 해당하는 CSV 파일이 존재하지 않습니다.
- 메시지: {report.message}
"""
        return md

    data = report.to_dict()
    missing = data.get("missing", {})
    schema = data.get("schema", {})
    dt_info = data.get("datetime", {})
    outlier = data.get("outlier", {})

    missing_by_column = missing.get("missing_by_column", {})
    missing_ratio_by_column = missing.get("missing_ratio_by_column", {})
    missing_lines = [
        f"- {col}: {missing_by_column.get(col, 0)}개 ({missing_ratio_by_column.get(col, 0.0):.2%})"
        for col in missing_by_column
    ]
    missing_block = "\n".join(missing_lines) if missing_lines else "- (컬럼 없음)"

    schema_block = f"""- 필수 컬럼: {schema.get('required_columns', [])}
- 누락된 필수 컬럼: {schema.get('missing_required_columns', [])}
- 추가 컬럼: {schema.get('extra_columns', [])}
"""

    dt_lines = []
    for col in dt_info.get("datetime_columns", []):
        success = dt_info.get("parse_success_count", {}).get(col, 0)
        fail = dt_info.get("parse_fail_count", {}).get(col, 0)
        dt_lines.append(f"- {col}: 파싱 성공 {success}건 / 실패 {fail}건")
    dt_block = "\n".join(dt_lines) if dt_lines else "- (날짜/시간 컬럼 없음)"

    outlier_lines = []
    for col, cnt in outlier.get("outlier_count_by_column", {}).items():
        outlier_lines.append(f"- {col}: 이상치 {cnt}건")
    outlier_block = "\n".join(outlier_lines) if outlier_lines else "- (수치형 컬럼 없음)"

    md = f"""# 데이터 품질 리포트 - {title_date}

## 1. 상태 요약
- 메시지: {report.message}

## 2. 결측치 점검
{missing_block}

## 3. 스키마 점검
{schema_block}

## 4. 날짜/시간 컬럼 점검
{dt_block}

## 5. 이상치(IQR) 점검
- 방법: {outlier.get('method', 'iqr')}
- IQR 배수: {outlier.get('iqr_multiplier', 1.5)}
{outlier_block}
"""
    return md


def save_markdown_report(report: QualityReport, dt: datetime | None = None) -> Path:
    if dt is None:
        dt = datetime.today()

    ensure_dir(settings.REPORT_DIR)
    file_name = f"quality_report_{dt.strftime('%Y_%m_%d')}.md"
    file_path = settings.REPORT_DIR / file_name

    md = generate_markdown_from_report(report, dt=dt)
    with file_path.open("w", encoding="utf-8") as f:
        f.write(md)

    return file_path
