# LostParty Backend 기능 지도

2026-10-28 기준. main/dev1b6f57b·checkout feat/group-management. **사용자승인으로그룹핵심표시/활동/집계·DB0034확장표를구현·격리검증했다.** [구현기록](../features/groups/implementation-2026-10-28.md)·[NEXT_WORK](NEXT_WORK.md)를따른다. 선택70개는68PASS후실패2개수정/해당2PASS·두계약전체일치(기본119/136·two-cycle181/202)이며실제개발서버/DB·Flutter기기인수아니다. 다음은#12핵심인계후같은브랜치그룹관리/기존레이드보존구현·검증이다. 그룹장전용레이드명령·복구승계·활동자동추가는제외한다.

레이드 모집 1차 구현·보고된 정상 흐름/표시의 사용자 기기 인수 완료, [Issue13 전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)으로 closed/completed다. 모집 관련 추가 Backend 요청은 없다. 차후 정밀도 소비·알럿·UX/소켓 등은 [보완 대장](../features/recruitment/follow-up-backlog.md)에 보존하며 현재 착수/인수 선행 조건이 아니다. 이전 미완료/종료 차단 판단과 사용자 정정은 [DEV_LOG](DEV_LOG.md)에서 확인한다.

| 기능 | 상태·기준 |
|---|---|
| [로그인·계정](../features/login-account/README.md) | Google/자체 세션·복구·회원 설정·개인 게임키·한도 구현. 추가 공급자·탈퇴/운영정책은 별도 미완료. |
| [원정대·캐릭터](../features/rosters/README.md) | 등록/갱신·소유 인증/V2분쟁·현재/퇴역 읽기·전투력/분석·대표/활동/표시·일괄조회 구현. V2분쟁 실인수 보류, 생명주기 증거/활동 자동추가·명시제외 후속은 별도. |
| [레이드·주간 기록](../features/raids/README.md) | 공개 카탈로그·서버 주차·개인 완료/주간 summary 구현. 최신 게임패치 검증과 실제 이용 통계 집계는 별도 미완료. |
| [그룹](../features/groups/README.md) | 생성/가입/초대·코드/차단·관리조회·그룹장 이전/일반탈퇴 구현·dev통합. Flutter 연결/실기기와 해산·추방/대표변경·표시조회/활성방공통목록 후속 미완료. 1차 계약 제안 문서 작성·구현 전. |
| [모집·일정](../features/recruitment/README.md) | C/N 생성·참가/관리·일정/조율·완료/탈퇴·검색/후보·표시·분 단위 명시 시각과 재신청 보완까지 구현/개발 반영. 1차 사용자 기기 인수 완료·Issue13 종료. [기존 모집 통합](../features/recruitment/integration-checkpoint-2026-10-27.md)·[재신청 통합](../features/recruitment/reapplication-integration-2026-10-27.md). 다른 관련 Issue 상태는 추적표를 따르며 이번에 일괄 종료하지 않는다. |
| [공통 개발·운영](../engineering/README.md) | 격리 PostgreSQL 검증·의존성 고정·구조화 로그 사용. 현재 개발 실행sourcec1f86d8/이미지581a1a5e·DB0033·현재178/199/기본116/133. [재신청 반영](../engineering/operations/reapplication-history-rollout.md)의 소스262/runtime31/계약·health/worker/READONLY/HTTP 근거를 재사용하며 이번 문서 통합에서 서버를 재실행하지 않는다. |

개발 계약은 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../openapi/openapi.yaml)다. two-cycle은 실행 구성,0033은 DB마이그레이션 단계다. 구현·합성 검증·실제 서비스 읽기/HTTP·사용자 기기·성능/운영 인수는 구분한다. 현재 문서 정리로 미수행 성능/실회원 원ACK 동일 키 검증을 완료로 바꾸지 않는다.

주제별 미완료는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 과거 결정/검증/장애·통합은 [DEV_LOG](DEV_LOG.md)를 따른다. [AGENTS](../../AGENTS.md)·[협업 규칙](../engineering/collaboration/api-collaboration.md)·[문서 대응표](../engineering/documentation/README.md)를 작업 기준으로 사용한다.
