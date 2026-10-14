# LostParty Backend 프로젝트 지도

기준일 2026-10-15. 실행 계획은 [NEXT_WORK](NEXT_WORK.md), 완료·장애·검증 이력은 [DEV_LOG](DEV_LOG.md)에 둡니다. 이 지도에 긴 계획이나 실행 결과를 복제하지 않습니다.

| 영역 | 핵심 상태·기준 위치 |
|---|---|
| 실행 기반 | Python 3.12·FastAPI·PostgreSQL 17·Docker Compose. [README](../../README.md), [개발 흐름](../DEVELOPMENT_WORKFLOW.md) |
| 기존 health | DB 연결 /health 유지. `app/main.py`, [원본 OpenAPI](../../openapi/openapi.yaml) |
| Google 인증·세션 | 6개 API·DB migration·검증/인계 완료, #2 Backend1차범위Completed. emulator 로그인·회원저장/모바일기본흐름 보고확인,전체세션/실기기/release는별도후속. `app/auth`, `app/core`, [인증 개발 안내](../AUTH_DEVELOPMENT.md) |
| API·데이터 정책 | [합의 계약](../ISSUE_2_AUTH_CONTRACT_DRAFT.md), [복구 설계](../ISSUE_2_REFRESH_RECOVERY.md), [Issue #2](https://github.com/heo0328/lostparty-backend/issues/2) |
| 인증 후속 #2 | 탈퇴/재가입·약관·운영 정지 정책/구현, 실기기/release·전체세션·운영 인수는 [후속 목록](../ISSUE_2_FOLLOWUP.md) AUTH-F01~F06으로 추적. #2 Backend1차 완료와 분리 |
| 설계 근거 | [초기 모델 제안](../ISSUE_2_GOOGLE_AUTH_PROPOSAL.md), [구현 계획 이력](../ISSUE_2_IMPLEMENTATION_PLAN.md).현재 할 일은 NEXT_WORK가 기준 |
| 테스트·migration | `tests`, `compose.test.yaml`, `alembic/versions/0001_auth.py`. 실행 방법은 인증 개발 안내, 검증 기록은 DEV_LOG |
| 협업 | [API_COLLABORATION](../API_COLLABORATION.md)·[작업 단계/진행 경계](../API_COLLABORATION_WORKFLOW.md). Backend Issues와 계약 SHA 기준, #1 연결테스트Completed·#2 Backend1차Completed·#3/#4 OPEN, Flutter 소스 직접 수정 없음 |
| 내 계정 복원 #3 | 로컬12 API·0002의11테이블·원본OpenAPI 구현, 격리PostgreSQL114테스트·로컬계약 비교 확인. 작업 브랜치 구현/계약254cb5d 게시, Flutter 두GET/계약SHA·1159검증/빈등록인수 보고확인. 등록후속 lease헤더보완·대상10개통과/로컬적용,보완구현db0f3ae게시·현재 키/실응답 상태는 #4 기준. [등록후속 계획](../ISSUE_3_REGISTRATION_FOLLOWUP_PLAN.md)·[실행/인계](../ISSUE_3_DEVELOPMENT.md)·[설계](../ISSUE_3_IMPLEMENTATION_PLAN.md)·[Issue #3](https://github.com/heo0328/lostparty-backend/issues/3) |
| 등록관리 실연동 #4 | 기존 API 재사용, 수동siblings형태진단CLI·대상13개검증. local/runtime key반영·사용자 실 siblings 4개/parser 통과 확인. 빈 label POST/PATCH 계약·구현 및 대상16개 통과, 게시 SHA d3cb697bb6ebb988b63bd99c588bc1b64a93650d. Flutter d3cb697 소비·1193자동검증/빈이름 사용자인수 보고 확인,Flutter 구현5fe636e/dev266a7e2 게시보고 확인·삭제후로컬보존 후속. [작업계획](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md)·[실검증 안내](../ISSUE_4_LIVE_VALIDATION.md)·[Issue #4](https://github.com/heo0328/lostparty-backend/issues/4) |
| 전투력 수집 #5 | 1700공통기준·POST/cache/GET상태·0003 구현·대상42개/후속3개·로컬적용완료. 게시SHA 39188d5dca2d394f4e8b3fcbfe332274812285bf·Flutter1204/후속70자동·신규3흐름사용자확인보고,Flutter 구현6beb55e/devccc6b23·push인계확인 완료. [실행](../ISSUE_5_DEVELOPMENT.md). [기본값](../GAME_DEFAULTS.md)·[계획](../ISSUE_5_COMBAT_POWER_PLAN.md)·[Issue5](https://github.com/heo0328/lostparty-backend/issues/5) |
| 회원 설정 #6 | GET/PUT·기본false/version·0004 구현/대상22개·로컬적용완료. Backend 79255f0 게시·Flutter 연결/자동검증 보고 확인, Flutter Git 게시·사용자 실인수 대기. [최신 회신](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6170276194). [실행/계약](../ISSUE_6_MEMBER_SETTINGS.md)·[Issue6](https://github.com/heo0328/lostparty-backend/issues/6) |
| 회원별 Lost Ark 키 #7 | [Issue #7](https://github.com/heo0328/lostparty-backend/issues/7) [계약 제안](../ISSUE_7_LOSTARK_KEY_CONTRACT_DRAFT.md) Flutter 수용 후 Backend 구현 완료. 암호화 저장/전 호출 개인 키 전환·회원·키 버전 cache/결과 fencing·token별 quota. 구현/대상180개·로컬0005 적용 완료·Flutter 연결/실인수 후속. [실행](../ISSUE_7_DEVELOPMENT.md) |
| 후속 기능 | 탈퇴·약관·모집·파티·그룹·Apple/Discord·WebSocket은 구현에 없음 |
| 운영 | Lightsail 배포 예정, 운영 HTTPS·배포·키 관리 준비는 완료로 간주하지 않음 |

인증 1차는 main/dev에 통합됐으며 이후 계정 업무·새label·진단/후속문서는 dev에 통합·게시됐습니다. 완료 작업 브랜치는 push 확인 후 정리하며, 다음 작업은 최신 dev에서 분기합니다. 계약 소비·전체 Flutter 인수·운영 배포 완료와 저장소 최신화를 구분합니다.

현재 브랜치는 `feat/member-settings`(dev4eb23f5 기준). #6 회원설정 GET/PUT·0004 구현/검증·79255f0 push 완료. Flutter 연결/자동검증 완료 보고를 확인했으며 Flutter 게시 SHA·사용자 실인수는 대기한다. 로컬DB0004/API적용완료,기존DTO변경없음·실기기복원인수후속. #5구현39188d5·양측Git인계/사용자인수와#4/#3/#2후속을보존한다.

#7은 기존 feat/member-settings에서 함께 구현, 회원별 키 저장 및 전 외부 호출 전환 완료. 공용 JWT 제거·독립 암호화/HMAC 준비·새 credential0, 인계용 게시 후 Flutter 연결/실provider 확인이 후속이다. dev/main 통합은 미수행.

#7 추가: [호출대기/키기기복원 제안](../ISSUE_7_RETRY_RESTORE_CONTRACT_DRAFT.md). 38d66da 구현/push완료 후 provider제한retry시간·별도본인원문restore요구를확인,Flutter 추가계약 수용 후Backend 보완구현/검증,로컬0006·새게시후Flutter연결/실인수.
