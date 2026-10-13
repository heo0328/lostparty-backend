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
| Backend 구현·자동 검증 | 완료, 로컬 인증 API·migration·44개 테스트 및 계약 비교 기록 있음 |
| 로컬 커밋 | 완료, `feat/2-google-auth`의 `519c609` |
| 원격 게시·통합 | 작업 브랜치 게시 완료. main/dev는 `4ad3052`, 통합 미실행 |
| 계약 인계 | 구현 결과 댓글은 게시됨. 커밋 후 계약 SHA·원격 접근 가능한 계약 인계는 대기 |
| Flutter 적용·실제 Google·Android 인수 | emulator Google 로그인 성공 보고 및 회원/identity 저장 확인. 전체 세션·실기기 인수는 대기 |
| 운영 배포 | 미실행 |

이 문서 작성 시 코드 테스트나 서버·DB 검증을 반복하지 않았습니다. 위 자동 검증은 [기록된 이전 결과](DEV_LOG.md)를 기준으로 합니다.

## 우선 처리: 실제 로그인 실패 조사

에뮬레이터에서 challenge201 이후 Google 교환401이 발생했습니다. API·키·공개키 접근은 정상이며 새 실제 요청에서 azp_allowlist 거절로 원인을 확인했습니다. 민감값 없는 진단을 추가한 서버로 갱신했고 회귀45개가 통과했습니다. debug 공개 client ID를 확인해 개발 allowlist에 등록하고 API 재생성을 완료했습니다. 회귀46개와 실행 설정·계약 비교가 통과했습니다. 사용자가 실제 emulator 로그인 완료를 보고했고 DB 회원/identity 저장을 확인했습니다. 다음은 Flutter 앱 재시작·로그인 유지 선택·refresh/로그아웃·늦은 응답 격리의 공동 검증입니다. 토큰 전달이나 nonce 검증 우회는 하지 않습니다.

## 다음 실행 순서

1. 작업 브랜치의 인증 구현과 문서 게시는 완료했습니다. 다음은 계약 SHA 인계이며 main/dev 통합은 아직 하지 않았습니다.
2. PR·main/dev 통합이 요청되면 최신 원격 상태와 승인 범위를 확인하고 기존 Git 절차를 따릅니다. force push하지 않습니다.
3. Issue #2에 접근 가능한 원본 계약과 **계약 파일을 변경한 커밋 SHA** `519c609...`를 인계합니다. 이후 문서 커밋이나 계약 내용 SHA-256과 혼동하지 않습니다. 추가 코드/계약 수정 시 검증과 SHA를 갱신합니다.
4. 기존 /health 유지, 신규 6개 /v1 경로, strict 400·오류 code·60초/추가2회·409·현재 session logout의 호환성 영향을 설명합니다. Firebase principal은 새 회원으로 자동 호환되지 않습니다.
5. Flutter에서 계약 소비 SHA·화면/bootstrap·secure pending·single-flight·재시작·늦은 응답 격리 결과를 요청합니다. Windows localhost→WSL·emulator 10.0.2.2와 실제 Google 서명·nonce·azp를 공동 검증합니다.
6. 결과·실패·미검증을 DEV_LOG에 추가하고 AI_CONTEXT의 기능 상태를 갱신합니다. 모두 완료 후 다음 승인된 작업 그룹으로 이 문서를 교체합니다.

## 남은 입력·결정과 완료 조건

- 작업 브랜치 commit/push는 사용자 승인으로 완료. main/dev 통합·배포는 별도 승인 범위.
- Android OAuth client ID: 실제 azp 검증에 필요하면 확정된 공개 값을 요청. 미확인 값을 추정 허용하지 않음.
- 로컬 접속: WSL 루프백 검증 이력은 있으나 Windows·emulator·실기기 접근은 미확인.
- Google 실인증·Flutter 적용: 공동 인수 증거 필요. mock 통과로 완료 처리하지 않음.
- 출시 전 후속: release 서명/Play 등록, 탈퇴·재가입·정지 운영 정책·약관 URL, 운영 HTTPS·배포 준비. 이번 그룹에 구현을 확대하지 않음.

완료 조건은 원격 계약/정확한 SHA 인계, Flutter 소비 확인, 공동 접속·Google·세션 흐름 검증과 남은 한계 보고입니다. 외부 검증 대기와 Backend 코드 완료를 구분하고 Issue는 임의로 닫지 않습니다.
