# src/dq_agent/quality.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
from datetime import datetime

import pandas as pd
from . import settings


@dataclass
class MissingSummary:
    total_rows: int
    total_columns: int
    missing_by_column: Dict[str, int]
    missing_ratio_by_column: Dict[str, float]


@dataclass
class SchemaSummary:
    required_columns: List[str]
    missing_required_columns: List[str]
    extra_columns: List[str]


@dataclass
class DatetimeSummary:
    datetime_columns: List[str]
    parse_success_count: Dict[str, int]
    parse_fail_count: Dict[str, int]
    # 새로 추가된 필드들
    today_match_count: Dict[str, int]   # 오늘 날짜와 일치하는 값 개수
    non_today_count: Dict[str, int]     # 오늘이 아닌(과거/미래) 값 개수


@dataclass
class OutlierSummary:
    method: str
    iqr_multiplier: float
    outlier_count_by_column: Dict[str, int]


@dataclass
class QualityReport:
    has_file: bool
    message: str
    missing: MissingSummary | None = None
    schema: SchemaSummary | None = None
    datetime: DatetimeSummary | None = None
    outlier: OutlierSummary | None = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "has_file": self.has_file,
            "message": self.message,
        }
        if self.missing:
            result["missing"] = asdict(self.missing)
        if self.schema:
            result["schema"] = asdict(self.schema)
        if self.datetime:
            result["datetime"] = asdict(self.datetime)
        if self.outlier:
            result["outlier"] = asdict(self.outlier)
        return result


def check_missing(df: pd.DataFrame) -> MissingSummary:
    total_rows = len(df)
    total_columns = df.shape[1]
    missing_by_column = df.isna().sum().to_dict()
    missing_ratio_by_column = {
        col: (missing_by_column[col] / total_rows) if total_rows > 0 else 0.0
        for col in df.columns
    }
    return MissingSummary(
        total_rows=total_rows,
        total_columns=total_columns,
        missing_by_column=missing_by_column,
        missing_ratio_by_column=missing_ratio_by_column,
    )


def check_schema(df: pd.DataFrame) -> SchemaSummary:
    existing_cols = set(df.columns)
    required = set(settings.REQUIRED_COLUMNS)

    missing_required = sorted(list(required - existing_cols))
    extra = sorted(list(existing_cols - required))

    return SchemaSummary(
        required_columns=settings.REQUIRED_COLUMNS,
        missing_required_columns=missing_required,
        extra_columns=extra,
    )


def check_datetime_columns(df: pd.DataFrame) -> DatetimeSummary:
    """
    DATETIME_COLUMNS에 대해:
    1) 파싱 성공/실패 건수
    2) 파싱 성공 값 중 '오늘 날짜'와 일치하는 건수
    3) 파싱 성공 값 중 '오늘이 아닌' 건수
    를 계산한다.
    """
    parse_success: Dict[str, int] = {}
    parse_fail: Dict[str, int] = {}
    today_match: Dict[str, int] = {}
    non_today: Dict[str, int] = {}

    today = datetime.today().date()

    for col in settings.DATETIME_COLUMNS:
        if col not in df.columns:
            parse_success[col] = 0
            parse_fail[col] = 0
            today_match[col] = 0
            non_today[col] = 0
            continue

        # 문자열로 변환 후 파싱 시도
        series = df[col].astype(str)
        parsed = pd.to_datetime(
            series,
            errors="coerce",
            infer_datetime_format=True,
        )

        success_mask = parsed.notna()
        success = int(success_mask.sum())
        fail = int((~success_mask).sum())

        # 파싱 성공한 값만 대상으로 오늘/비오늘 분리
        valid_dates = parsed[success_mask].dt.date
        today_count = int((valid_dates == today).sum())
        non_today_count = int((valid_dates != today).sum())

        parse_success[col] = success
        parse_fail[col] = fail
        today_match[col] = today_count
        non_today[col] = non_today_count

    return DatetimeSummary(
        datetime_columns=settings.DATETIME_COLUMNS,
        parse_success_count=parse_success,
        parse_fail_count=parse_fail,
        today_match_count=today_match,
        non_today_count=non_today,
    )


def check_outliers_iqr(df: pd.DataFrame) -> OutlierSummary:
    outlier_counts: Dict[str, int] = {}

    for col in settings.NUMERIC_COLUMNS:
        if col not in df.columns:
            outlier_counts[col] = 0
            continue

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            outlier_counts[col] = 0
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        k = settings.OUTLIER_IQR_MULTIPLIER

        lower = q1 - k * iqr
        upper = q3 + k * iqr

        is_outlier = (series < lower) | (series > upper)
        outlier_counts[col] = int(is_outlier.sum())

    return OutlierSummary(
        method="iqr",
        iqr_multiplier=settings.OUTLIER_IQR_MULTIPLIER,
        outlier_count_by_column=outlier_counts,
    )


def run_quality_checks(df: pd.DataFrame) -> QualityReport:
    """
    한 파일에 대해 전체 품질 점검을 실행하고 QualityReport 반환.
    """
    missing = check_missing(df)
    schema = check_schema(df)
    dt_summary = check_datetime_columns(df)
    outlier = check_outliers_iqr(df)

    return QualityReport(
        has_file=True,
        message="파일을 정상적으로 점검했습니다.",
        missing=missing,
        schema=schema,
        datetime=dt_summary,
        outlier=outlier,
    )

