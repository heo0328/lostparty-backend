# LostParty Backend 프로젝트 지도

기준일 2026-10-16. 실행 계획은 [NEXT_WORK](NEXT_WORK.md), 완료·장애·검증 이력은 [DEV_LOG](DEV_LOG.md)에 둡니다. 이 지도에 긴 계획이나 실행 결과를 복제하지 않습니다.

| 영역 | 핵심 상태·기준 위치 |
|---|---|
| 실행 기반 | Python 3.12·FastAPI·PostgreSQL 17·Docker Compose. [README](../../README.md), [개발 흐름](../DEVELOPMENT_WORKFLOW.md) |
| 기존 health | DB 연결 /health 유지. `app/main.py`, [원본 OpenAPI](../../openapi/openapi.yaml) |
| Google 인증·세션 | 6개 API·DB migration·검증/인계 완료, #2 Backend1차범위Completed. emulator 로그인·회원저장/모바일기본흐름 보고확인,전체세션/실기기/release는별도후속. `app/auth`, `app/core`, [인증 개발 안내](../AUTH_DEVELOPMENT.md) |
| API·데이터 정책 | [합의 계약](../ISSUE_2_AUTH_CONTRACT_DRAFT.md), [복구 설계](../ISSUE_2_REFRESH_RECOVERY.md), [Issue #2](https://github.com/heo0328/lostparty-backend/issues/2) |
| 인증 후속 #2 | 탈퇴/재가입·약관·운영 정지 정책/구현, 실기기/release·전체세션·운영 인수는 [후속 목록](../ISSUE_2_FOLLOWUP.md) AUTH-F01~F06으로 추적. #2 Backend1차 완료와 분리 |
| 설계 근거 | [초기 모델 제안](../ISSUE_2_GOOGLE_AUTH_PROPOSAL.md), [구현 계획 이력](../ISSUE_2_IMPLEMENTATION_PLAN.md).현재 할 일은 NEXT_WORK가 기준 |
| 테스트·migration | `tests`, `compose.test.yaml`, `alembic/versions/0001_auth.py`. 실행 방법은 인증 개발 안내, 검증 기록은 DEV_LOG |
| 협업 | [API_COLLABORATION](../API_COLLABORATION.md)·[작업 단계/진행 경계](../API_COLLABORATION_WORKFLOW.md). Backend Issues와 계약 SHA 기준, #1 연결테스트Completed·#2 Backend1차Completed·#3/#4 Completed(Flutter 주도 후속 분리), Flutter 소스 직접 수정 없음 |
| 내 계정 복원 #3 | 로컬12 API·0002의11테이블·원본OpenAPI 구현, 격리PostgreSQL114테스트·로컬계약 비교 확인. 작업 브랜치 구현/계약254cb5d 게시, Flutter 두GET/계약SHA·1159검증/빈등록인수 보고확인. 등록후속 lease헤더보완·대상10개통과/로컬적용,보완구현db0f3ae게시·현재 키/실응답 상태는 #4 기준. [등록후속 계획](../ISSUE_3_REGISTRATION_FOLLOWUP_PLAN.md)·[실행/인계](../ISSUE_3_DEVELOPMENT.md)·[설계](../ISSUE_3_IMPLEMENTATION_PLAN.md)·[Issue #3](https://github.com/heo0328/lostparty-backend/issues/3) |
| 등록관리 실연동 #4 | 기존 API 재사용, 수동siblings형태진단CLI·대상13개검증. local/runtime key반영·사용자 실 siblings 4개/parser 통과 확인. 빈 label POST/PATCH 계약·구현 및 대상16개 통과, 게시 SHA d3cb697bb6ebb988b63bd99c588bc1b64a93650d. Flutter d3cb697 소비·1193자동검증/빈이름 사용자인수 보고 확인,Flutter 구현5fe636e/dev266a7e2 게시보고 확인·삭제후로컬보존 후속. [작업계획](../ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md)·[실검증 안내](../ISSUE_4_LIVE_VALIDATION.md)·[Issue #4](https://github.com/heo0328/lostparty-backend/issues/4) |
| 전투력 수집 #5 | 1700공통기준·POST/cache/GET상태·0003 구현·대상42개/후속3개·로컬적용완료. 게시SHA 39188d5dca2d394f4e8b3fcbfe332274812285bf·Flutter1204/후속70자동·신규3흐름사용자확인보고,Flutter 구현6beb55e/devccc6b23·push인계확인 완료. [실행](../ISSUE_5_DEVELOPMENT.md). [기본값](../GAME_DEFAULTS.md)·[계획](../ISSUE_5_COMBAT_POWER_PLAN.md)·[Issue5](https://github.com/heo0328/lostparty-backend/issues/5) |
| 회원 설정 #6 | Backend79255f0·Flutter2e0764f/dev5cee9648 게시·사용자3흐름 확인, Issue CLOSED. 전체자동빌드/새환경은 별도. [최종 인계](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6170736672)·[실행](../ISSUE_6_MEMBER_SETTINGS.md) |
| 회원별 Lost Ark 키 #7 | [Issue #7](https://github.com/heo0328/lostparty-backend/issues/7) [계약 제안](../ISSUE_7_LOSTARK_KEY_CONTRACT_DRAFT.md) Flutter 수용 후 Backend 구현 완료. 암호화 저장/전 호출 개인 키 전환·회원·키 버전 cache/결과 fencing·token별 quota. Backend9e1a255·로컬0006 게시, Flutter1246/후속12 자동검증·연결 보고 확인, 현재 구간 사용자 정상·Flutter 구현8644c81/devcc6a0b0 push 확인. [회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6173350024). [실행](../ISSUE_7_DEVELOPMENT.md) |
| 캐릭터 생명주기 #8 | [공식 증거 조사](../ISSUE_8_PROVIDER_EVIDENCE_REVIEW.md) 완료. 대표 GET/PUT·cooldown 제거 cd3e003은 개발 API 적용·인계 완료. L1a6f3d029(격리185PASS)·L1bc91af2e(V2조회2개, 113PASS/보완57PASS 별도)는 작업브랜치 push·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6186143574) 완료·dev미통합. [실행/전환 준비](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md). 기존8000 API/DB에0009·P2반영/기존자료유지·live proof/퇴역은 보류 |
| Flutter 계정 연결 #8 | [C 완료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822): S1~S3/A1/A2/B/C 앱 실행·회원 주목록/복원/진행 UI 연결·모의HTTP/SQLite 최종전체1524PASS, lib/test 분석0(전체 analyze 기존tools info3). feature/scoped-account-cache 미커밋·미push·기본OFF·실서버/기기 미인수. D 별도저장 연결 철회·원래DB/키 연결 복구·최종1524PASS 보고/미게시. 기본 재인수 없이 개발 계속 |
| Flutter R1 기본조회/상세분리 #8 | [결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209153163) 최종1542PASS/분석0·미게시. [Backend 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209205051) 방향수용. [서버권한/비노출](../ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md) 구현·격리256PASS·기존8000반영, live소유증거/실기기인수와구분 |
| Flutter 대표 왕관 E1 #8 | [구현보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208245362)·[Backend 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208670274): 대표전용연결 방향 수용, 복구경계보완필요답변수신·6209360031/6209491349대로별도복구UX없이공유저장내부처리. 1531통과/fixture1실패→보완후18/18통과·미게시. E2활동편집은독립후속 |
| 활동1700·초기대표 연결 #8 | [서버검증](../ISSUE_8_ACTIVITY_SELECTION_DEVELOPMENT.md) 전체선택/대표변경공통1700·ineligible/선택보존·192PASS/기존8000반영. [Flutter 연결6209931176](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209931176) 최종1560PASS·기존관리/초기draft/명시PUT/인증전환완료보고·미게시/기본OFF/실인수미확인. 새endpoint/자동대표재선정없음 |
| 역할요약·개인표시 복원 #8 | P1 6e4f625 게시/인계 완료. [P2 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6195124835)으로 개인설정/원정대표시·0009·내부퇴역정리 구현·격리128PASS/별도최종143PASS. 구현/OpenAPI `7027f0b` push·[인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6195735441) 완료/dev미통합·Flutter A1/A2/C 계약 소비·모의 연결 완료 보고, 실환경 인수 후속. [P2 실행/호환](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md). 역할요약 wire유지·preferences 실제복원 전환·현재8000/기존DB에0009·P2적용/health·계약·자료동일확인 |
| 개발/자료 기준 #8 | [최신 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428): 현재 사용하던 환경·개발자료로 개발 계속. 베타 시작 직전 사용자 지시 시 DB 내용만 초기화. 새8001 채택/기초재인수 선행 철회·기존완료 유지. 별도환경 삭제/재설정 없음 |
| 소유 준비 #8 | [관찰 CLI](../ISSUE_8_OWNERSHIP_READINESS.md) 자동65PASS. 사용자 실제게임관찰은 나중이며 독립개발 선행조건 아님. live소유/canonical/퇴역 미완료 |
| 소유 인증 대상 검사 #8 | [보완](../ISSUE_8_VERIFICATION_CONTEXT_DEVELOPMENT.md): 시작대상/목록고정·확인시불일치/엄격True아닌표식보류, 격리250PASS·기존8000반영. 실제증거발급/live연결·실기기는미완료. 게임관찰나중기준유지 |
| 소유/사용캐릭터 UI연결 검토 #8 | [서버단계/미완료](../ISSUE_8_OWNERSHIP_FLOW_REVIEW.md) 대조·[Flutter 재검토요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208702210) 게시. 등록→인증진입/성공→기존관리화면·활동저장1560PASS 연결보고/검토완료, 미게시/기본OFF/실인수미확인. 새 인증완료/실인수 주장 없음 |
| 후속 기능 | 탈퇴·약관·모집·파티·그룹·Apple/Discord·WebSocket은 구현에 없음 |
| 운영 | Lightsail 배포 예정, 운영 HTTPS·배포·키 관리 준비는 완료로 간주하지 않음 |

인증 1차는 main/dev에 통합됐으며 이후 계정 업무·새label·진단/후속문서는 dev에 통합·게시됐습니다. 완료 작업 브랜치는 push 확인 후 정리하며, 다음 작업은 최신 dev에서 분기합니다. 계약 소비·전체 Flutter 인수·운영 배포 완료와 저장소 최신화를 구분합니다.

현재 통합 구간은 회원설정 #6과 개인 Lost Ark 키/복원/호출대기 #7이다. 결과 문서를 포함해 dev772b90e로 통합 후 결과 기록72f6301까지 push 완료, 현재 feat/representative-selection에서 #8 대표·L1a/L1b·P1/P2 구현/게시를 완료했고 준비구현4bdaea6까지 push·[결과인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207306535)됐다. Flutter A1/A2/B/C·D 잔여정리 완료 및 별도저장 연결 복구/최종1524PASS 보고 후 현재 환경의 미완료 개발을 이어가며 feat/member-settings는 로컬·원격 정리했다. main은 유지한다. 실제 Git 결과는 DEV_LOG와 Issue #7 인계 댓글이 기준이다.

#7 Backend9e1a255·로컬0006·Flutter8644c81/devcc6a0b0 push·현재 구간 사용자 정상 보고 확인. Backend 추가 수정 없음. 재설치/별도기기·실provider한도/헤더·운영TLS는 후속 미확인, 역할요약/개인표시 저장과 자동갱신 실행·회원목록 코드는 #8 P1/P2 및 Flutter A1/A2/B/C로 연결 보고됐으나 실환경 전환/운영 인수는 별도다. Issue #7은 사용자 지시로 Completed 종료했다([종료 기록](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6183029637)).
