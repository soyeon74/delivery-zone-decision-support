# Architecture

```text
[PUBLIC / LOCAL INPUT]
  ├─ route_master
  ├─ multi-month delivery results
  └─ workload metrics
          │
          ▼
[1. Validation]
  schema / null / duplicate / route IDs
          │
          ▼
[2. Delivery Activity]
  records / address-day visits / mail type
          │
          ▼
[3. Candidate Analysis]
  route boundary / adjacency / continuity
          │
          ▼
[4. Workload Simulation]
  sender before/after
  receiver before/after
  multi-month representative effect
          │
          ▼
[5. GIS + Report]
  map / comparison table / HTML report
          │
          └─ optional local LLM explanation
```

## 역할 분리

- `src/validation.py` : 입력검증
- `src/activity.py` : 배달활동 집계
- `src/candidates.py` : 인접 후보 계산
- `src/simulation.py` : 업무강도 시뮬레이션
- `src/reporting.py` : 결과표·HTML 보고서
- `app/` : Streamlit UI

## 개인정보 설계

실제 운영버전에서는 원자료를 외부에 전송하지 않는 로컬 처리 구조를 전제로 합니다.
공개 GitHub 버전은 완전 합성자료만 사용합니다.
