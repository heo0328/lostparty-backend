# 현재 작업과 다음 실행

기준일 2026-10-16. **현재 사용하던 로컬 개발환경과 개발자료로 개발을 계속한다. 완료한 앱 실행·Google 로그인·키/설정·캐릭터 갱신·원정대 저장과 #8 구현을 유지한다. 새 환경 채택·초기 설정·기본 기능 전체 재인수로 되돌리지 않는다.**

최상위 실행 기준은 [긴급 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)이다. [Backend 실행 기준 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207867594)도 게시했다. 이전 [통합 정리](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207398915)의 새8001 채택/기초 재인수 순서와 이를 수용한 Backend6207472610은 철회된 순서다.

## 유지할 완료 결과와 현재 상태

| 구간 | 상태 |
|---|---|
| 통합 기준 | dev `821c758`, main `e6c72e4`. #1~#7 CLOSED. #8은 dev/main 미통합 |
| #8 Backend | 대표 `cd3e003`, L1a/L1b `6f3d029`/`c91af2e`, P1/P2 `6e4f625`/`7027f0b` 구현·격리검증·원격 인계 완료. P2 계약 유지 |
| 현재 작업 브랜치 | `feat/representative-selection`, 준비구현 `4bdaea6`, 최신 게시 문서 HEAD `ee0023a`. 현재 개발 서버 반영/정정 문서 인계 준비 |
| 사용하던 개발환경 | 기존 Docker/포트8000/DB 자료를 유지해 0007~0009·최신P2 API 반영 완료. DB0009·API/DB healthy·health ok·OpenAPI 전체일치·기존 전 테이블의 원래 컬럼/행 내용 동일 확인. 초기화/새환경 전환 없음 |
| 별도8001 환경 | 구성했던 작업 이력이며 현재 개발의 기본 경로/채택 대상/선행조건이 아니다. 이번 정정으로 컨테이너/volume을 삭제·재설정하지 않는다 |
| Flutter 최신 | [정정 완료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428): 별도 BackendLocalData/DB/guest키 namespace 연결·전용시험4개 제거, 원래 AccountDatabase/SecureApiTokenStore 연결 복구. **최종1524PASS·lib/test분석0**. feature/scoped-account-cache 미커밋·미push·dev미반영 |
| 소유 증거 | 관찰 도구 자동65PASS/게시 완료. 실제 게임 관찰은 사용자 결정대로 나중. live 소유/canonical·퇴역은 미완료/보류. 이를 기존 기능 전체 미완료로 확대하지 않는다 |

## 다음 개발과 담당

1. **현재 서버 반영 완료 후 미완료 개발을 이어간다.** 기존8000/DB에 #8 구조·API 반영 및 영향 검증은 완료됐다. 완료 흐름을 재개발하거나 근거 없이 반복 시험하지 않는다. Backend는 기존 #8 완료 코드와 실제 미완료 서버 경로를 구분해 직접 필요한 구현 단위를 정한다. 실제 소유/원정대 연결 서버 후속 중 게임 관찰 없이 진행 가능한 개발을 구분하며, 자료/환경 변경이 필요한 경우 해당 기능의 구체적 필요만 다룬다.
2. **Flutter 독립 미구현 연결을 이어간다.** [순서 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207523104) 기준으로 활동 선택/대표 왕관 등 기존 합의된 남은 연결 범위를 대조한다. 새 UX 결정·기능 전체 재설계·새환경 인수 대기를 요구하지 않는다. 실제 작업 구간/게시 SHA는 아직 미회신이다.
3. **실제 장비 관찰은 나중에 수행한다.** [관찰 CLI](../ISSUE_8_OWNERSHIP_READINESS.md)는 준비됐다. 관찰 결과와 서버에서 검증 가능한 증거/연결 규칙을 검토해야 하며 ready_for_review만으로 인증을 확정하지 않는다. 이 후속으로 독립 개발을 막지 않는다.
4. **변경한 구간의 영향 검증만 수행한다.** 실제 소유/canonical·현재 등록/roster·활동 대상이 필요한 새 기능 실검증만 조건 충족 후 진행한다. 기존 완료 흐름을 처음부터 재인수하지 않는다. Flutter 변경분의 게시/통합 상태는 구현 완료와 별도로 추적한다.

## 자료 수명 기준

현재 개발자료를 유지해 개발 → 사용자 모집/베타 준비 → **사용자가 베타 시작 직전 시점을 지시할 때 대상 개발 DB의 사용자/기록 내용 초기화** → 이미 구현된 기능 동작 확인 → 큰 문제가 없으면 베타 자료를 운영에 보존한다. 지금 초기화/삭제·새 환경 채택·재설치·구자료 복사/복원을 실행하지 않는다. Firebase 전용 구현 제거는 제품 기능·현재 개발자료 제거와 구분한다. 별도8001 구성과 보존형 백업/복원 계획을 필수 절차로 확대했던 판단은 폐기했다.

## 검증 근거와 완료 경계

- Backend L1a 185PASS, L1b 113PASS/보완57PASS, P1 108PASS/최종171PASS, P2 수정후128PASS/최종143PASS는 각각 별도 격리 PostgreSQL/mock 실행이다. 실제 결과/초기 실패와 보완은 [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [P1](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [P2](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) 안내와 DEV_LOG가 기준이다.
- Flutter [A1](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196135272) 1432PASS, [A2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196639685) 전체1479PASS 이후 국소47/2PASS, [B](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197379381) 전체1514PASS 이후 B35PASS, [C](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822) 최종전체1524PASS 보고다. 각 실행을 합산하지 않는다. 최종 lib/test 분석 문제0, 저장소 전체 analyze는 기존 사용자 tools의 info3건이 남는다. 임시 SQLite/모의 backend·provider HTTP 결과이며 Backend 자동검증/실기기 인수와 구분한다.
- live 소유/장비 proof·소멸 확정/퇴역/claim 해제는 보류다. 내부 모의 retirement 정리 구현을 실제 자료 삭제·provider 전체성 증명으로 확대하지 않는다. 전체 자동 갱신의 코드 연결과 실제 운영/사용자 완료는 별도다.

## 다른 범위와 보존

#7 회원키 `9e1a255`·Flutter `8644c81`/dev `cc6a0b0` 게시·현재 구간 사용자 정상 보고와 Completed 종료는 확인 완료다. #6 회원설정 `79255f0`·Flutter `2e0764f`/dev `5cee9648` 게시·사용자3흐름·CLOSED, #5 전투력 `39188d5`·Flutter `6beb55e`/dev `ccc6b23` 게시·사용자3흐름·CLOSED다. 같은 정상 결과의 반복 시험을 요청하지 않는다.

#3/#4에서 분리한 활동/장비·삭제 후 로컬 보존, [인증 후속](../ISSUE_2_FOLLOWUP.md), 재설치/별도기기·실provider 한도/헤더·운영 TLS·탈퇴/약관·모집/파티/그룹·운영 배포는 각 후속 범위다. 완료 작업 브랜치 feat/member-settings는 정리됐으며 진행 중 #8 브랜치는 미통합이므로 유지한다.
