# 현재 작업과 다음 실행

기준일 2026-10-16. **#8 Backend L1a/L1b·P1/P2 구현·격리검증·원격 인계 완료, Flutter S1~S3/A1/A2/B/C 코드 연결·모의 자동검증 완료 보고. 기존 테스트 자료/Firebase 시스템은 폐기·미승계 기준이며, 별도 새 빈 DB/최신 P2 API 구성과 장비 관찰 도구 준비를 완료했다. 실제 게임 검증은 사용자 결정으로 나중에 진행한다.** Issue #8은 OPEN이며 실소유/canonical 증거 보류와 Flutter 실인수는 남아 있다.

## 현재 기준

| 구간 | 구현/계약·상태 |
|---|---|
| 통합 기준 | dev `821c758`, main `e6c72e4`. #1~#7 CLOSED, #6/#7까지 dev 통합·게시 완료 |
| #8 작업 브랜치 | `feat/representative-selection`, 게시 HEAD `906e0ef`(P2 인계 기록). #8 구간은 dev/main 미통합 |
| 대표 선택 | `cd3e003`: GET/PUT·cooldown 제거, 개발 API 적용·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184483999) 완료 |
| L1a/L1b | `6f3d029`/`c91af2e`: 생명주기/세대 기반·V2 현재/이력 조회, 격리검증·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6186143574) 완료 |
| P1/P2 | `6e4f625`/`7027f0b`: 역할요약·개인설정/원정대 표시·내부 정리, 격리검증·[P1](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6194881739)/[P2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6195735441) 인계 완료 |
| 실제 실행 환경 | 원본8000/DB0006 healthy 유지. 새 `lostparty-fresh-dev` API8001/DB0009 healthy·P2 계약 전체일치·사용자/등록/캐릭터/개인자료 각0건 확인. 구자료 import 없음. [구성](../ISSUE_8_LOCAL_TRANSITION_READINESS.md) |
| Flutter 최신 | [D 완료 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790)1528PASS 보고, 소비 P2 `7027f0b`. `feature/scoped-account-cache`/기준 `cc6a0b0`, D 포함 미커밋·미push·dev 미반영·새 인계 SHA 없음 |

Flutter C는 앱 수명 실행기·canonical 회원 주목록·역할/개인설정 복원·진행/상세 재시도와 서버 전송 재시도·충돌 해결 UI까지 연결했다. C 당시 구 기기자료 별도 경로가 남았으나 아래 제품/UX 기준으로 D 정리 대상과 필요한 공유 로직을 구분한다. 기본 `BACKEND_LIFECYCLE_READS_ENABLED=false`이고 실서버/provider·기기/재설치 인수는 미확인이다. 대표 왕관 변경·활동 선택의 별도 연동/인수는 이 읽기·개인설정 연결 완료로 간주하지 않는다.

## 개발/베타/운영 기준과 추가 확인

[Flutter 방침 대조 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206739088)을 수신했다. 개발 중 자료 생성/삭제→베타 직전 개발 사용자/서버 기록 전체초기화→문제없으면 베타 자료를 보존해 운영으로 이어간다. 현재 즉시 모든 자료 삭제를 지시한 것으로 확대하지 않는다. Firebase/구자료 승계·보존형 백업/복원리허설은 필수조건에서 제외한다.

[제품/UX 공유](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206946439)와 [인수 경계 답변](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206873992)을 대조해 [Backend 검토 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207049997)을 회신했다. 기능/비로그인 UX는 유지하고 Firebase 전용 연결/실행·구자료 승계만을 위한 의존을 분리한다. Drift/로컬DB·정수ID·순수분석mapper는 그 자체가 폐기 대상이 아니다. [D 완료 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790): 환경별 새 로컬DB/guest키·구자료 진입 제거, 제품 기능 유지. 최종1528PASS/lib-test분석0 보고이며 미커밋·미push·실기기 미확인이다.

추가 canonical 인수 질문은 답변 수신으로 해소됐고 현재 추가 제품 질문/P2 계약 변경 요청이 없다. 새 로그인/키/설정/preview·보류 안내와 실제 소유/canonical·활동 대상 준비가 필요한 저장/자동갱신/복원 실인수를 분리한다. live proof는 Backend 후속으로 남지만 독립적인 D/새 DB 구성 준비를 막지 않는다. Flutter는 실제 D 결과/새 계약 차이가 생길 때 회신하며 같은 정책 대조를 반복 요청하지 않는다.

## 다음 실행과 담당

1. **Backend/사용자 — 실제 장비 관찰 후 근거 검토.** [관찰 CLI](../ISSUE_8_OWNERSHIP_READINESS.md) 준비·자동65PASS. 사용자 응답은 “도구 준비 후 나중에 검증”. 준비 시 숨김 로컬 입력으로 장착→지정 부위 해제→재장착을 관찰한다. live proof/canonical 연결·퇴역은 여전히 보류이며 결과를 검토한 뒤 필요한 서버 증거 구현/계약을 정한다. 단순 bool/seed로 해제하지 않는다.
2. **Backend — 새 빈 환경 준비 완료.** [구성](../ISSUE_8_LOCAL_TRANSITION_READINESS.md): 별도 project/volume, 8001 API·0009/P2 일치, 각 사용자자료0건. 기존8000/0006은 유지했다. 원본 삭제/자료복원/운영배포는 없다. 이후 변경은 새 환경을 대상으로 명시한다.
3. **Flutter/사용자 — D 이후 기본 실인수·게시.** [D 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790) 1528PASS는 Flutter 모의/임시SQLite 검증 보고다. 새 API8001에 도달하는 모바일/에뮬레이터 주소를 확인한 뒤 로그인·키·설정·preview/보류 안내·guest 새 자료 흐름을 검증한다. 기본OFF를 임의로 성공 조건으로 바꾸지 않는다. D 포함 실제 커밋 SHA·push/dev 상태는 아직 미회신이다.
4. **양측 — 소유 필요 실인수는 준비 후.** 실제 소유/canonical·현재 등록/roster·활동 대상이 준비된 후 역할/표시 저장·자동갱신/나이스단 OFF 제외·재로그인/새 기기 복원을 확인한다. 활동/왕관 UI는 별도 미완료다. 빈0건/fixture로 완료 처리하지 않는다.

## 검증 근거와 완료 경계

- Backend L1a 185PASS, L1b 113PASS/보완57PASS, P1 108PASS/최종171PASS, P2 수정후128PASS/최종143PASS는 각각 별도 격리 PostgreSQL/mock 실행이다. 실제 결과/초기 실패와 보완은 [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [P1](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [P2](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) 안내와 DEV_LOG가 기준이다.
- Flutter [A1](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196135272) 1432PASS, [A2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196639685) 전체1479PASS 이후 국소47/2PASS, [B](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197379381) 전체1514PASS 이후 B35PASS, [C](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822) 최종전체1524PASS 보고다. 각 실행을 합산하지 않는다. 최종 lib/test 분석 문제0, 저장소 전체 analyze는 기존 사용자 tools의 info3건이 남는다. 임시 SQLite/모의 backend·provider HTTP 결과이며 Backend 자동검증/실기기 인수와 구분한다.
- live 소유/장비 proof·소멸 확정/퇴역/claim 해제는 보류다. 내부 모의 retirement 정리 구현을 실제 자료 삭제·provider 전체성 증명으로 확대하지 않는다. 전체 자동 갱신의 코드 연결과 실제 운영/사용자 완료는 별도다.

## 다른 범위와 보존

#7 회원키 `9e1a255`·Flutter `8644c81`/dev `cc6a0b0` 게시·현재 구간 사용자 정상 보고와 Completed 종료는 확인 완료다. #6 회원설정 `79255f0`·Flutter `2e0764f`/dev `5cee9648` 게시·사용자3흐름·CLOSED, #5 전투력 `39188d5`·Flutter `6beb55e`/dev `ccc6b23` 게시·사용자3흐름·CLOSED다. 같은 정상 결과의 반복 시험을 요청하지 않는다.

#3/#4에서 분리한 활동/장비·삭제 후 로컬 보존, [인증 후속](../ISSUE_2_FOLLOWUP.md), 재설치/별도기기·실provider 한도/헤더·운영 TLS·탈퇴/약관·모집/파티/그룹·운영 배포는 각 후속 범위다. 완료 작업 브랜치 feat/member-settings는 정리됐으며 진행 중 #8 브랜치는 미통합이므로 유지한다.

이번 구간은 도구·새 환경 구성을 검증해 작업 브랜치에 게시·같은 Issue에 인계한다. P2 REST/OpenAPI 계약 변경은 없다. Git 통합/운영배포/자료삭제/Issue 종료는 수행하지 않는다.
