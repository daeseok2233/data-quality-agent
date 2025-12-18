# dq-agent  
### Daily Data Quality Automation Agent

**매일 유입되는 CSV 데이터를 대상으로  
데이터 품질(결측·중복·이상치·비즈니스 룰 위반)을 자동 점검하는 도구입니다.**

분석·모델링 이전 단계에서  
데이터 상태를 **매일 자동으로 검증**합니다.

---

## ❓ Why dq-agent?

이 프로젝트는  
**모델을 최신 데이터로 지속적으로 업데이트하기 전에,  
데이터 전처리와 품질 검증을 자동화하기 위해 시작했습니다.**

일별 CSV 데이터에 대해  
결측, 중복, 이상치, 룰 위반 여부를 매번 수동으로 점검하는 과정을  
자동화하는 것이 목적입니다.

---

## 🎯 What it does

다음 **4가지 데이터 품질 항목**을 자동 점검합니다.

- **Missing**
  - 컬럼별 결측 개수/비율 계산
  - 결측이 포함된 행 추출

- **Duplicates**
  - `order_id` 기준 중복 행 탐지

- **Outlier (IQR)**
  - 수치 컬럼에 대해 IQR 기반 이상치 탐지

- **Business Rule**
  - 음수/0 값
  - `amount != quantity * unit_price`
  - 날짜 형식 오류
  - 기준일과 다른 날짜 데이터

모든 문제는 **행 단위로 분리되어 리포트로 출력**됩니다.

---

## 🔄 Data Flow (Input → Output)

### Input
- 일별 CSV 파일  
  예: `data/sales_YYYY_MM_DD.csv`
  
  [sales_2025_12_18.csv](https://github.com/user-attachments/files/24230013/sales_2025_12_18.csv)
```csv
order_id,order_date,customer_id,product_id,quantity,unit_price,amount
1001,2025-10-25,C001,P001,2,30000,60000
1002,2025-10-25,C002,P002,1,15000,15000
1003,2025-10-24,C003,P001,3,30000,90000
1004,2025/10/25,,P003,5,50000,10
1005,2025-12-31,C005,P004,1,40000,40000
1006,2024-01-01,C006,P005,1,10000,10000
1007,2025-10-25,C007,P006,0,25000,0
1008,2025-10-25,C008,P007,-1,25000,-25000
1009,2025-10-25,C009,P008,2,0,0
1010,2025-10-25,C010,P009,1,9999999,9999999
1002,2025-10-25,C002,P002,1,15000,15000
1011,invalid_date,C011,P010,1,12000,12000
```
## 📊 Output

- `reports/quality_report_YYYY_MM_DD.md`
- `reports/quality_report_YYYY_MM_DD.json`
- `reports/quality_report_YYYY_MM_DD.html`

리포트에는 문제 유형별 요약과 **문제가 발생한 실제 행 데이터**가 포함됩니다.

[quality_report_2025_12_18.html](https://github.com/user-attachments/files/24229470/quality_report_2025_12_18.html)
  
---

## ⏰ Automation

Linux `cron`을 이용해 **매일 자동 실행**되도록 구성했습니다.

```bash
0 6 * * * /home/daeseok/dq-agent/run_daily.sh
```
---

## 📁 Repository Structure
```
dq-agent/
├── src/dq_agent/          # 메인 패키지
│   ├── main.py            # 엔트리 포인트 (모듈 실행)
│   ├── quality.py         # 데이터 품질 점검 로직
│   ├── reporting.py       # 마크다운 / HTML 리포트 생성
│   ├── ai_reporting.py    # LLM 기반 리포트 요약
│   └── settings.py        # 경로 및 설정 관리
│
├── data/                  # 입력 CSV 데이터
├── reports/               # 생성된 리포트 (md / html)
├── logs/                  # 실행 로그
│
├── run_daily.sh           # 일일 자동 실행 스크립트
├── README.md
└── .env                   # 환경 변수 (API Key 등)
```
---
## 배포

1. Clone Repository
```
git clone https://github.com/daeseok2233/data-quality-agent.git
cd data-quality-agent
```
2. Create & Activate Virtual Environment
```
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```
3. Install Dependencies
```
uv pip install pandas python-dateutil pytest openai python-dotenv markdown
```

4️. Environment Variables (.env)

프로젝트 루트에 .env 파일을 생성하고 아래와 같이 설정합니다.
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4.1-mini
ENABLE_AI_REPORT=true
```
5️. Set PYTHONPATH
```
export PYTHONPATH=./src     # Windows: set PYTHONPATH=./src
```
6️. Run Application
```
uv run python -m dq_agent.main
```
---
## Conclusion

이 프로젝트는 매일 생성·적재되는 CSV 데이터의 품질을 자동으로 점검하고,
그 결과를 사람이 바로 이해할 수 있는 리포트(Markdown / HTML) 형태로 제공하는
데이터 품질 점검 에이전트입니다.

결측치, 스키마 불일치, 이상치와 같은 반복적인 데이터 검증 작업을 자동화함으로써
사람의 수작업 검수 부담을 줄이고, 선택적으로 AI 요약 리포트를 결합하여
의사결정에 필요한 핵심 정보만 빠르게 파악할 수 있도록 설계했습니다.

## 📚 What I Learned

이 프로젝트를 진행하며 단순히 기능 구현을 넘어서,
**“실제로 다른 사람이 사용할 수 있는 소프트웨어를 만든다는 관점”**에서
여러 설계·구현·배포 경험을 쌓을 수 있었습니다.

1. 패키지 구조 기반 Python 프로젝트 설계

src/ 구조와 python -m 실행 방식을 사용하며
import 안정성과 확장 가능한 코드 구조의 중요성을 체감했습니다.

단일 스크립트가 아닌 서비스 단위 코드 구성 방식을 경험했습니다.

2. 설정과 로직의 분리

환경 변수(.env)와 설정 파일(settings.py)을 분리하여
코드 변경 없이 동작을 제어할 수 있도록 설계했습니다.

AI 기능을 ENABLE_AI_REPORT 옵션으로 분리하며
기능 토글(feature toggle) 설계 패턴을 적용해 보았습니다.

3. 자동 리포트 파이프라인 설계 경험

데이터 입력 → 품질 점검 → 요약 → 리포트 생성까지
엔드투엔드 파이프라인을 직접 구성했습니다.

Markdown과 HTML을 동시에 생성하여
개발자·비개발자 모두를 고려한 결과물을 설계했습니다.

4. cron 기반 자동화 설계 경험
cron과 shell script(run_daily.sh)를 활용하여
데이터 품질 점검 작업을 일 단위로 자동 실행하는 흐름을 구성했습니다.

수동 실행을 전제로 한 코드가 아니라,
무인 실행 환경에서도 안정적으로 동작하는 프로그램 설계의 중요성을 배웠습니다.

로그 디렉토리(logs/)를 분리하여
자동화 환경에서의 디버깅 및 실행 이력 관리 방식을 경험했습니다.
