from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
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
class OutlierSummary:
    method: str
    iqr_multiplier: float
    outlier_count_by_column: Dict[str, int]


@dataclass
class QualityReport:
    """
    ✅ 검사 범위(4개)
    - missing (결측)
    - duplicates (중복)
    - outlier (이상치)
    - business_rule (비즈니스 룰 위반: 0/음수, 금액 불일치, 날짜 문제 포함)
    """
    has_file: bool
    message: str
    missing: MissingSummary | None = None
    outlier: OutlierSummary | None = None
    row_issues: Dict[str, List[Dict[str, Any]]] | None = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "has_file": self.has_file,
            "message": self.message,
        }
        if self.missing:
            result["missing"] = asdict(self.missing)
        if self.outlier:
            result["outlier"] = asdict(self.outlier)
        if self.row_issues is not None:
            result["row_issues"] = self.row_issues
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


# ======================
#  Row-level issue collectors (4개 검사)
# ======================

def collect_missing_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """결측값이 포함된 행 전체를 row 단위로 반환."""
    mask = df.isna()
    has_missing = mask.any(axis=1)

    rows: List[Dict[str, Any]] = []
    for idx in df.index[has_missing]:
        row = df.loc[idx]
        missing_cols = mask.loc[idx][mask.loc[idx]].index.tolist()
        row_dict = row.to_dict()
        row_dict["row_index"] = int(idx) if isinstance(idx, int) else idx
        row_dict["missing_columns"] = missing_cols
        rows.append(row_dict)
    return rows


def collect_duplicate_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """order_id 기준 중복 행을 모두 반환."""
    if "order_id" not in df.columns:
        return []

    dup_mask = df.duplicated(subset=["order_id"], keep=False)
    dup_df = df[dup_mask]

    rows: List[Dict[str, Any]] = []
    for idx, row in dup_df.iterrows():
        row_dict = row.to_dict()
        row_dict["row_index"] = int(idx) if isinstance(idx, int) else idx
        rows.append(row_dict)
    return rows


def collect_business_rule_rows(
    df: pd.DataFrame,
    file_dt: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    ✅ 비즈니스 룰 위반 행만 반환 (여기에 날짜/금액 무결성까지 포함)

    포함 규칙:
    - quantity <= 0
    - unit_price <= 0
    - amount <= 0
    - amount != quantity * unit_price
    - order_date 파싱 실패 -> invalid_date_format
    - (file_dt가 주어지면) order_date != 기준일 -> non_base_date
    """
    rows: List[Dict[str, Any]] = []

    qty = pd.to_numeric(df.get("quantity"), errors="coerce") if "quantity" in df.columns else pd.Series([pd.NA] * len(df))
    price = pd.to_numeric(df.get("unit_price"), errors="coerce") if "unit_price" in df.columns else pd.Series([pd.NA] * len(df))
    amount = pd.to_numeric(df.get("amount"), errors="coerce") if "amount" in df.columns else pd.Series([pd.NA] * len(df))

    base_date = file_dt.date() if file_dt is not None else None

    parsed_date = None
    if "order_date" in df.columns:
        parsed_date = pd.to_datetime(df["order_date"].astype(str), errors="coerce", infer_datetime_format=True)

    for idx, row in df.iterrows():
        issues: List[str] = []

        q = qty.loc[idx] if idx in qty.index else pd.NA
        p = price.loc[idx] if idx in price.index else pd.NA
        a = amount.loc[idx] if idx in amount.index else pd.NA

        # 1) 0/음수 규칙
        if pd.notna(q) and q <= 0:
            issues.append("quantity <= 0")
        if pd.notna(p) and p <= 0:
            issues.append("unit_price <= 0")
        if pd.notna(a) and a <= 0:
            issues.append("amount <= 0")

        # 2) 금액 무결성
        if pd.notna(q) and pd.notna(p) and pd.notna(a):
            if a != q * p:
                issues.append("amount != quantity * unit_price")

        # 3) 날짜 규칙(기준일 불일치만 필요)
        if parsed_date is not None:
            d = parsed_date.loc[idx]
            if pd.isna(d):
                issues.append("invalid_date_format")
            else:
                if base_date is not None and d.date() != base_date:
                    issues.append("non_base_date")

        if issues:
            row_dict = row.to_dict()
            row_dict["row_index"] = int(idx) if isinstance(idx, int) else idx
            row_dict["issues"] = issues
            rows.append(row_dict)

    return rows


def run_quality_checks(df: pd.DataFrame, dt: Optional[datetime] = None) -> QualityReport:
    """
    ✅ 4개만 검사:
    - 결측
    - 중복
    - 이상치(IQR)
    - 비즈니스 룰 위반 (날짜/금액 무결성 포함)
    """
    missing = check_missing(df)
    outlier = check_outliers_iqr(df)

    row_issues = {
        "missing": collect_missing_rows(df),
        "duplicates": collect_duplicate_rows(df),
        "business_rule": collect_business_rule_rows(df, file_dt=dt),
    }

    return QualityReport(
        has_file=True,
        message="파일을 정상적으로 점검했습니다.",
        missing=missing,
        outlier=outlier,
        row_issues=row_issues,
    )
