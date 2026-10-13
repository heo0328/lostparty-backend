# 현재 작업과 다음 실행 계획

기준 확인일: 2026-10-14. 현재 작업 그룹은 **Issue #2 Google 인증 계약 인계와 공동 연동 검증**입니다. 문서 체계 정비는 완료했으며 상세 이력은 [DEV_LOG](DEV_LOG.md)에 기록합니다.

## 목표·근거·범위

합의된 Backend 구현을 Flutter가 사용할 계약으로 인계하고 실제 Google·Android 연결을 검증합니다.

- 요구·합의: [Issue #2](https://github.com/heo0328/lostparty-backend/issues/2), [최종 동의](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149615842).
- 원본: [OpenAPI](../../openapi/openapi.yaml). 로컬 계약 커밋 `519c609495966a3d785c6671c09bf513b28875a6`.
- 포함: 6개 인증 API 계약 인계, 실행 조건·검증 범위 공유, Flutter 연동 및 공동 인수 결과 확인.
- 제외: 신규 업무 API·탈퇴·약관 정책 구현, Firebase 이관·연결·삭제, Flutter 소스 직접 변경, 운영 배포·외부 공개, 개발 DB 초기화.

## 현재 상태

| 단계 | 상태 |
|---|---|
| 요구 검토·계약 합의 | 완료, Issue 최종 동의 근거 있음 |
| Backend 구현·자동 검증 | 완료, 로컬 인증 API·migration·46개 테스트 및 계약 비교 기록 있음 |
| 로컬 커밋 | 완료, `feat/2-google-auth`의 `519c609` |
| 원격 게시·통합 | 작업 브랜치와 dev 게시·통합 완료. main은4ad3052 유지 |
| 계약 인계 | [dev 통합·계약 SHA 인계](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6151318353) 완료. Flutter 소비 확인 대기 |
| Flutter 적용·실제 Google·Android 인수 | emulator Google 로그인 성공 보고 및 회원/identity 저장 확인. 전체 세션·실기기 인수는 대기 |
| 운영 배포 | 미실행 |

이 문서 작성 시 코드 테스트나 서버·DB 검증을 반복하지 않았습니다. 위 자동 검증은 [기록된 이전 결과](DEV_LOG.md)를 기준으로 합니다.

## 다음 실행 순서

1. Flutter가 계약 커밋519c609을 사용했는지 확인합니다. dev 통합·원격 계약 인계는 완료했습니다.
2. 로그인 유지 선택별 앱 재시작, refresh 복구·현재 기기 logout·늦은 응답 격리를 공동 검증합니다. 실제 emulator 로그인·회원 저장은 확인했으며 실패 조사 상세는 DEV_LOG에 있습니다.
3. 실기기/release 검증은 해당 등록·접속 조건을 확인한 뒤 진행합니다. main 통합·운영 배포는 별도 승인 범위입니다.
4. 결과·실패·미검증을 DEV_LOG에 추가하고 AI_CONTEXT의 핵심 상태를 갱신합니다. 완료 후 다음 승인된 그룹으로 계획을 교체합니다.

## 남은 입력·결정과 완료 조건

- 작업 브랜치·dev commit/push/통합은 사용자 승인으로 완료. main 통합·배포는 별도 승인 범위.
- debug Android OAuth ID는 확정·로컬 allowlist 적용 완료. .env·키는 push하지 않으므로 다른 환경에서 별도 준비합니다. release 등록은 후속.
- emulator 로그인 성공 보고와 서버 요청·회원 저장을 확인했습니다. 실기기/release는 미검증.
- Google 실인증·Flutter 적용: 공동 인수 증거 필요. mock 통과로 완료 처리하지 않음.
- 출시 전 후속: release 서명/Play 등록, 탈퇴·재가입·정지 운영 정책·약관 URL, 운영 HTTPS·배포 준비. 이번 그룹에 구현을 확대하지 않음.

완료 조건은 원격 계약/정확한 SHA 인계, Flutter 소비 확인, 공동 접속·Google·세션 흐름 검증과 남은 한계 보고입니다. 외부 검증 대기와 Backend 코드 완료를 구분하고 Issue는 임의로 닫지 않습니다.
