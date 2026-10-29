# LostParty Backend 기능 지도

2026-10-29 기준. main/dev1b6f57b·checkout feat/group-management. 그룹1차 구현·격리검증·개발환경 반영과 실행검증 완료. 실제source5d24244/이미지507cd78a·DB0034, 기본123/140·two-cycle185/206이다. [구현·반영기록](../features/groups/implementation-2026-10-28.md)·[NEXT_WORK](NEXT_WORK.md)를 따른다. Native #12 전체27/#16 전체17은 연결구현·자동검증을 자체보고했고 실제연동/기기인수는미완료다. 다음Flutter/사용자 인수·Backend차이대응이며복구승계/활동자동추가·병합/운영배포는별도다.

후속초대후보검색/전투력: #12전체29/30을받아ASCII대소문자무시정확검색·opt-in역할별character_spec후보구현/격리검증을완료했다. [검증집계](../features/groups/invite-candidates-verification-2026-10-29.json)·구현기록참조. 이후속도5d24244/507cd78a·DB0034로개발반영·실행검증완료했다. 기본DTO보존·migration/provider/중복저장없음. 다음Native실제검색/profile/초대수락기기인수·Backend차이대응이다.

2026-10-30 후속: [최초그룹연결/목록표시계약](../features/groups/raid-link-contract.md)·[동일참가자예시](../features/groups/raid-link-examples.json)를같은목적브랜치에서구현·격리검증·계약인계완료했다(source6dac5ab, #12전체38/#16전체24). 기존그룹잔여기기시험은Native#12전체36/#16전체21사용자보고통과이며재시험대기로돌리지않는다. 새최초연결/목록이름·소속표시수정은개발미반영·기기미확인이고실행source5d24244/DB0034는유지한다. 상세12조합에서대상group_member는조회자소속과무관하게일치해Backend누락미재현·프로필위치예시인계다.

레이드 모집 1차 구현·보고된 정상 흐름/표시의 사용자 기기 인수 완료, [Issue13 전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)으로 closed/completed다. 모집 관련 추가 Backend 요청은 없다. 차후 정밀도 소비·알럿·UX/소켓 등은 [보완 대장](../features/recruitment/follow-up-backlog.md)에 보존하며 현재 착수/인수 선행 조건이 아니다. 이전 미완료/종료 차단 판단과 사용자 정정은 [DEV_LOG](DEV_LOG.md)에서 확인한다.

| 기능 | 상태·기준 |
|---|---|
| [로그인·계정](../features/login-account/README.md) | Google/자체 세션·복구·회원 설정·개인 게임키·한도 구현. 추가 공급자·탈퇴/운영정책은 별도 미완료. |
| [원정대·캐릭터](../features/rosters/README.md) | 등록/갱신·소유 인증/V2분쟁·현재/퇴역 읽기·전투력/분석·대표/활동/표시·일괄조회 구현. V2분쟁 실인수 보류, 생명주기 증거/활동 자동추가·명시제외 후속은 별도. |
| [레이드·주간 기록](../features/raids/README.md) | 공개 카탈로그·서버 주차·개인 완료/주간 summary 구현. 최신 게임패치 검증과 실제 이용 통계 집계는 별도 미완료. |
| [그룹](../features/groups/README.md) | 생성/가입/초대·코드/차단·관리조회·그룹장 이전/일반탈퇴 구현·dev통합. 1차 표시조회/활동/집계·해산/추방/대표변경·공통방안내/기존레이드보존 구현·격리검증·개발반영완료. 안내된기존그룹정상흐름은사용자기기보고통과. 최초연결/목록표시후속과복구승계는별도. |
| [모집·일정](../features/recruitment/README.md) | C/N 생성·참가/관리·일정/조율·완료/탈퇴·검색/후보·표시·분 단위 명시 시각과 재신청 보완까지 구현/개발 반영. 1차 사용자 기기 인수 완료·Issue13 종료. [기존 모집 통합](../features/recruitment/integration-checkpoint-2026-10-27.md)·[재신청 통합](../features/recruitment/reapplication-integration-2026-10-27.md). 다른 관련 Issue 상태는 추적표를 따르며 이번에 일괄 종료하지 않는다. |
| [공통 개발·운영](../engineering/README.md) | 기존DB0034/source5d24244/이미지507cd78a 개발반영. [실행집계](../engineering/operations/records/invite-candidates-rollout.json):114업무표1,833행/sequence·설정/키보존·소스272/runtime31/두계약전체일치·HTTP6/READONLY대소문자18조회/worker/healthy확인. |

개발 계약은 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../openapi/openapi.yaml)다. two-cycle은 실행 구성,0034는 현재 개발 DB마이그레이션 단계다. 구현·합성 검증·실제 서비스 읽기/HTTP·사용자 기기·성능/운영 인수는 구분한다. 현재 문서 정리로 미수행 성능/실회원 원ACK 동일 키 검증을 완료로 바꾸지 않는다.

주제별 미완료는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 과거 결정/검증/장애·통합은 [DEV_LOG](DEV_LOG.md)를 따른다. [AGENTS](../../AGENTS.md)·[협업 규칙](../engineering/collaboration/api-collaboration.md)·[문서 대응표](../engineering/documentation/README.md)를 작업 기준으로 사용한다.
