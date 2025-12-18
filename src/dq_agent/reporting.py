from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import markdown

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
    for k in sorted(all_keys):
        if k not in keys and k not in meta_keys:
            keys.append(k)

    header = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join(["---"] * len(keys)) + " |"
    lines = [header, sep]

    for r in rows_to_show:
        row_missing = set(r.get("missing_columns", [])) if highlight_missing else set()
        issues_list = r.get("issues", [])
        issues_str = (
            ", ".join(str(x) for x in issues_list)
            if isinstance(issues_list, list)
            else (str(issues_list) if issues_list else "")
        )

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
        table += (
            f"\n\n- (표에는 상위 {len(rows_to_show)}건만 표시했습니다. "
            f"나머지 {hidden}건은 JSON에서 확인하세요.)"
        )

    return table


def _make_kv_table(rows: dict, key_name: str = "항목", value_name: str = "값") -> str:
    """
    dict -> markdown table
    예) {"quantity": 2, "amount": 1} -> 표
    """
    if not rows:
        return "- (해당 없음)"

    lines = [f"| {key_name} | {value_name} |", "| --- | --- |"]
    for k, v in rows.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


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
    missing = data.get("missing", {}) or {}
    outlier = data.get("outlier", {}) or {}
    row_issues = data.get("row_issues", {}) or {}

    # ===== 카운트 (4개) =====
    missing_cnt = sum((missing.get("missing_by_column", {}) or {}).values())
    dup_cnt = len(row_issues.get("duplicates", []) or [])
    br_cnt = len(row_issues.get("business_rule", []) or [])
    outlier_cnt = sum((outlier.get("outlier_count_by_column", {}) or {}).values())

    has_issue = any([missing_cnt, dup_cnt, outlier_cnt, br_cnt])
    status = "⚠️ 이슈 발견" if has_issue else "✅ 이상 없음"

    # ===== 표 (4개) =====
    missing_rows_md = _make_table_from_rows(
        row_issues.get("missing", []) or [],
        highlight_missing=True,
    )
    dup_rows_md = _make_table_from_rows(row_issues.get("duplicates", []) or [])
    business_rule_rows_md = _make_table_from_rows(row_issues.get("business_rule", []) or [])

    # 이상치는 "컬럼별 이상치 개수"를 표로
    outlier_counts = outlier.get("outlier_count_by_column", {}) or {}
    outlier_table_data = {k: f"{v}건" for k, v in outlier_counts.items()} if outlier_counts else {}
    outlier_rows_md = _make_table_from_rows(row_issues.get("outliers", []))

    md = f"""# 데이터 품질 리포트 - {title_date}

## 상태 요약
- 상태: {status}
- 메시지: {report.message}
- 이슈 개요: 결측 **{missing_cnt}** / 중복 **{dup_cnt}** / 이상치 **{outlier_cnt}** / 룰 위반 **{br_cnt}**

---

## 결측
(굵게 표시된 값은 결측 컬럼입니다.)

{missing_rows_md}

---

## 중복
{dup_rows_md}

---

## 이상치
{outlier_rows_md}

---

## 룰 위반
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

            # AI가 ## 요약 같은 헤더를 만들면 문서가 커져보일 수 있어,
            # 필요하면 여기서 헤더 레벨을 낮추는 후처리를 넣어도 됨.
            md += "\n\n---\n\n## AI 요약\n\n" + ai_md + "\n"
        except Exception as e:
            md += f"\n\n---\n\n**[AI 요약 생성 실패]**: {e}\n"

    with file_path.open("w", encoding="utf-8") as f:
        f.write(md)

    return file_path


def save_html_from_md(md_path: Path, html_path: Path) -> Path:
    md_text = md_path.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["extra", "toc", "sane_lists"],
    )

    # 테이블이 긴 경우 가로 스크롤을 쉽게 하기 위해 래핑
    html_body = html_body.replace("<table>", '<div class="table-wrap"><table>')
    html_body = html_body.replace("</table>", "</table></div>")

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{md_path.stem}</title>
<style>
:root {{
  --border: #e5e7eb;
}}

body {{
  max-width: 1100px;
  margin: 32px auto;
  padding: 0 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
  line-height: 1.65;
  color: #111827;
}}

h1 {{ font-size: 26px; margin: 0 0 12px; }}
h2 {{ font-size: 18px; margin: 22px 0 10px; padding-top: 8px; border-top: 1px solid var(--border); }}
h3 {{ font-size: 16px; margin: 18px 0 8px; }}

hr {{ border: 0; border-top: 1px solid var(--border); margin: 18px 0; }}

.table-wrap {{ overflow-x: auto; }}
table {{
  width: 100%;
  min-width: 900px;
  border-collapse: separate;
  border-spacing: 0;
  margin: 10px 0 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}}

th, td {{
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  font-size: 14px;
}}

th {{
  background: #f3f4f6;
  position: sticky;
  top: 0;
  z-index: 1;
}}

tbody tr:nth-child(even) td {{ background: #fcfcfd; }}

td {{ word-break: break-word; }}

pre {{
  padding: 12px;
  overflow: auto;
  background: #f6f8fa;
  border-radius: 10px;
  border: 1px solid var(--border);
}}

code {{
  font-family: ui-monospace, Menlo, Consolas, monospace;
}}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return html_path
