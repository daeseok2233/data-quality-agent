# src/dq_agent/main.py
from __future__ import annotations
from datetime import datetime

import sys
import pandas as pd

from . import settings
from .quality import QualityReport, run_quality_checks
from .reporting import save_json_report, save_markdown_report, save_html_from_md


def run_for_date(dt: datetime | None = None) -> QualityReport:
    if dt is None:
        dt = datetime.today()

    file_path = settings.get_today_file_path(dt)
    if not file_path.exists():
        # 파일이 없는 경우
        report = QualityReport(
            has_file=False,
            message=f"오늘 날짜에 해당하는 파일이 존재하지 않습니다: {file_path.name}",
        )
        save_json_report(report, dt=dt)
        save_markdown_report(report, dt=dt)
        return report

    # 파일 로드
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        report = QualityReport(
            has_file=False,
            message=f"파일을 읽는 도중 오류 발생: {e}",
        )
        save_json_report(report, dt=dt)
        save_markdown_report(report, dt=dt)
        return report

    # 품질 점검 실행 👉 날짜 정보 함께 전달
    report = run_quality_checks(df, dt=dt)

    # 결과 저장 (JSON + Markdown)
    save_json_report(report, dt=dt)
    md_path = save_markdown_report(report, dt=dt)

    # Markdown -> HTML 변환 추가
    html_path = md_path.with_suffix(".html")
    save_html_from_md(md_path, html_path)
    return report


def main():
    """
    사용법:
      python -m dq_agent.main              # 오늘 날짜 기준
      python -m dq_agent.main 2025-10-31   # 특정 날짜 지정 (옵션)
    """
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        dt = datetime.today()

    report = run_for_date(dt)
    print(report.to_dict())


if __name__ == "__main__":
    main()
