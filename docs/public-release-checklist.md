# Public Release Checklist

GitHub push 전에 아래 항목을 모두 확인합니다.

- [ ] `data/sample/` 외 실제 데이터가 저장소에 없음
- [ ] 실제 도로명·상세주소 없음
- [ ] 수취인/발송인 이름 없음
- [ ] 전화번호 없음
- [ ] 등기·소포 실번호 없음
- [ ] 직원명·사번 없음
- [ ] `.env`, API Key, 비밀번호 없음
- [ ] 내부 문서 원문(HWP/HWPX/PDF/XLSX) 없음
- [ ] 비공개 GIS 파일 없음
- [ ] `python scripts/check_public_safety.py` 결과 PASS
- [ ] `git status` 확인
- [ ] `git diff --cached` 확인
- [ ] README에서 샘플데이터가 완전 합성임을 명시
- [ ] 프로그램 화면 캡처에도 실제 정보가 보이지 않음

## 권장 공개 순서

1. 새 GitHub 저장소 생성
2. 이 스타터 폴더만 첫 커밋
3. GitHub에서 파일 목록 재확인
4. 이후 기능별로 작은 단위 커밋
5. 실제 운영버전과 공개버전의 데이터 폴더를 분리 유지
