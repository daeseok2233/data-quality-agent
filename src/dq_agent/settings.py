from pathlib import Path
from datetime import datetime

# 루트 경로 기준으로 상대 경로 처리
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

# 파일 이름 패턴 : sales_YYYYMMDD.csv
FILE_PATTERN = "sales_{date}.csv"

# 스키마/컬럼 관련 설정 
REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
]

DATETIME_COLUMNS = [
    "order_date",
]

NUMERIC_COLUMNS = [
    "amount",
]

# 이상치 탐지용 설정 (IQR 기반)
OUTLIER_IQR_MULTIPLIER = 1.5

def today_str_for_filename(dt: datetime | None = None) -> str:
    """파일명용 날짜 문자열 (YYYY_MM_DD)."""
    if dt is None:
        dt = datetime.today()
    return dt.strftime("%Y_%m_%d")

def get_today_file_path(dt: datetime | None = None) -> Path:
    """오늘자 sales_YYYY_MM_DD.csv 경로 반환."""
    date_str = today_str_for_filename(dt)
    file_name = FILE_PATTERN.format(date=date_str)
    return DATA_DIR / file_name