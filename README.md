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

## 📊 Output

- `reports/quality_report_YYYY_MM_DD.md`
- `reports/quality_report_YYYY_MM_DD.json`

리포트에는  
문제 유형별 요약과 **문제가 발생한 실제 행 데이터**가 포함됩니다.

---

## ⏰ Automation

Linux `cron`을 이용해 **매일 자동 실행**되도록 구성했습니다.

```bash
0 6 * * * /home/daeseok/dq-agent/run_daily.sh




