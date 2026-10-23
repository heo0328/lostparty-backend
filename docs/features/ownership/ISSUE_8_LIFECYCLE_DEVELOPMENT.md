# Issue #8 — L1a/L1b 구현·검증·인계

> **정책/구현 후속:** [본인 원정대 API 목록 갱신](ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md)은76번째확정에따라본인등록의일상갱신과비퇴역현재claim의suspect해소에별도외부세대증거를요구하지않는다. 아래모든live refresh차단/복구근거대기는당시이력이며소유이전·퇴역/claim해제는계속별도다.
> **현재 서버 반영 완료(2026-10-16):** 사용자 진행 지시로 사용하던 Docker/포트8000/기존DB에 0007~0009와 최신 P2 API를 반영했다. 기존 전 테이블의 원래 컬럼/행 내용 동일·애플리케이션 모델 정합·API/DB healthy·health/P2 OpenAPI 전체일치 및 신규 GET4개 인증차단401을 확인했다. 아래 미적용/별도승인 대기는 각 단계 당시 이력이다. DB내용 초기화·새환경 채택·실provider/소유인수는 수행하지 않았다.

> **2026-10-16 실행 기준 정정:** [최신 지시](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)에 따라 현재 사용하던 환경과 개발자료로 개발을 계속한다. 아래 별도8001 구성·채택/기본 재인수 안내는 작업 이력이며 현재 실행 순서가 아니다. 별도환경 삭제/재설정도 실행하지 않는다. 현재 필요한 기능별 schema/API 작업과 개발자료 초기화를 구분한다. Flutter 별도DB/키 연결은 원래 연결로 복구됐고 최종1524PASS다.

2026-10-15. [범위 한정 수용/착수](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6185091368) 기준. 브랜치 `feat/representative-selection`에서 기존 대표 API와 문서를 보존해 이어간다. 실제 단위별 SHA·push·검증 결과는 아래 게시 기록과 같은 Issue 회신이 기준이다.

## 실행 경계

이번은 코드·migration 파일·**격리 tmpfs PostgreSQL** 검증·원격 게시만 수행한다. **개발/운영 DB에 0007 적용·실자료 backfill/삭제·실행 API 재시작·배포는 하지 않는다.** 현재 실행 서버는 대표 구현 구간이며 새 코드는 실제 DB 적용/서버 전환 승인 전 바로 호출 가능한 상태로 안내하지 않는다. 개발용 API 이미지 빌드는 실행 중 컨테이너를 바꾸지 않는다. 신규 기능의 전체 schema 검증은 `docker run --rm --network none ... app.openapi()`로 최신 이미지와 원본을 비교한다. `scripts/check_openapi.py`는 기존 실행API와 비교하므로 이 단계에선 사용하지 않는다.

## L1a — ID/상태·이름 점유·세대 캐시·쓰기 차단

`0007_character_lifecycle`은 UUID/account FK·대표/활동 FK를 보존한다. Character lifecycle_state/revision 추가, 기존 suspect/missing은 suspect로만 backfill하며 retired 전환하지 않는다. 현재 이름 점유는 별도 NameClaim PK(server,name)/unique character_id/복합FK로 분리한다. 기존 이름 unique를 제거하기 전에 충돌 사전진단/claim 생성·backfill을 수행하며, 충돌 시 원문 식별정보 없이 고정 오류로 중단한다. 종료 ID의 tombstone과 당시 회원 귀속 간략 이력/회원 history revision 기반을 추가한다. 기존 캐시 테이블/행은 보존하며 새 scoped cache/lease로 복사하지 않는다.

모든 지원 쓰기는 기존 game transaction advisory lock→현재 회원/세션→등록·원정대/캐릭터·claim→설정/멱등결과 순으로 보호하고 이름 claim 유일성/FK를 DB에서도 보장한다. 외부 요청 동안 이 lock을 보유하지 않는다. 등록/메인·소유/roster·각캐릭터 lifecycle/status·claim ID/revision snapshot은 외부 호출 전/결과반영 전에 검사한다. 장비 challenge도 시작 snapshot·credential version을 보관하며 낡은 challenge로 같은ID/권한을 되살리지 않는다.

내부 BindingEvidence는 신뢰된 adapter/모의 시험의 account/revision·동일세대 근거를 표현한다. **실제 provider fetch는 이를 생성하지 않는다.** 이름 중첩은 충돌 탐지에만 사용하며, 기존 account를 이름만으로 자동 선택/소유 이전하지 않는다. 연결 근거 없는 canonical refresh/start는409 ACCOUNT_BINDING_EVIDENCE_PENDING으로 보류할 수 있다. live proof=false 경계·PROVIDER_EVIDENCE_PENDING/ROSTER_EVIDENCE_PENDING은 유지한다. 신규 추가는 긍정 관찰+신뢰된 연결로 검증하고 소멸용 전체성을 일괄 요구하지 않는다. suspect는 이름 재출현만으로 복구하지 않는다. 실제 reconcile는 누락을suspect로만 낮추며 퇴역/claim해제를 호출하지 않는다.

내부 retirement transaction은 모의 완전 evidence에서만 시험한다. 이력unique·당시회원 귀속·최종정상profile 값/null·활동/대표 재구성·claim해제·ID tombstone/summary 정리·revision 증가를 함께 처리한다. 공개 endpoint/클라이언트·관리자 boolean 우회가 없다. 운영 보관기간은 새로 결정하지 않는다. 파티/공동 Snapshot 테이블을 새로 만들거나 삭제하지 않는다.

캐시 경계:
- canonical power/lease: 회원+character_id+lifecycle_revision+credential_version.
- preview power/lease: 회원+등록ID/version+서버/이름+credential_version. preview refresh는 동일 세대임을 증명하지 못하므로 새 generation에서 지난 값은null로 시작한다.
- summary/fetch: 회원+키version+등록/소유/캐릭터·claim snapshot scope+lookup. 등록 전 명시 검색은 별도 direct-preview scope이며 canonical/등록 자료와 합류하지 않는다.
- 같은 canonical ID의 정당한 이전 정상 수치/시각은 표시용 보존 가능하나 현재 eligibility/lease는 새세대를 검사한다. 새ID나 provenance 없는 옛 이름cache에 그값을이식하지않는다. worker는DB쓰기를하지않으며실패/만료정리도동일scope/generation일때만lease를해제한다.

V1 영향은 새필드/enum 추가가 아니라 사용 제한과 출처 분리다. preview·등록자료조회·표시용profile은 유지, 근거없는 canonical 연결/복구409, suspect/missing/retired·claim불일치의power/대표명령409 CHARACTER_UNUSABLE, 전체 활동설정은기존대상검증404 CHARACTER_NOT_FOUND, 변경된원정대/claim/challenge409 REVISION_CONFLICT. 과거멱등성공은역사응답이며자료를재적용하지않는다. retired는운영목록/count/대표요약에서제외하고 L1b이력으로조회한다. 대표공유settingsversion·cooldown0/next_change_atnull은보존한다.

## L1b — 현재 상태/이력 읽기

GET `/v2/me/game-accounts/{registration_id}/characters`, GET `/v2/me/character-retirements`를 추가했다. V2 refresh/lookup-recovery·실소멸 적용·기기삭제는 이번 범위가 아니다.

두 경로는 Bearer/no-store·외부호출/키복호화/기본행생성 없음, limit기본/최대50·cursor optional·알수없는/중복query/GETbody400이다. 원본OpenAPI의4개DTO는 모든필드필수이며 값없음은nullable로명시한다.

현재상태 envelope11필드: registration_id, game_account_id(UUID|null), is_main, registration_version, ownership_status, ownership_revision(int|null), roster_revision, settings(전체SettingsOut), items, next_cursor(string|null), server_fetched_at. settings_version은settings안에있다. item은기존CharacterOut관찰필드에lifecycle_state(preview/active/suspect/retired), lifecycle_revision(int|null), usable, blocked_reason을추가한다. preview/소유상실은character_id/lifecycle_revision필수null·usablefalse·OWNERSHIP_REQUIRED. 정상canonical은기존UUID/현재세대, suspect는CHARACTER_UNUSABLE·claim불일치는IDENTITY_CONFLICT. retired는운영목록에서제외한다.

usable은본인소유·현재상태·claim의기본자격이며활동선택/레이드/일정전체허가가아니다. Flutter는전체settings.activity와함께확인하고최종명령이현재자격을재검사한다. 구조cursor는회원/경로·등록/main/소유/roster/캐릭터·claim/settingsrevision에묶여바뀌면409CURSOR_STALE. 관찰용power값은rosterrevision없이갱신될수있으므로여러페이지의수치까지같은시각snapshot을보장하지않는다.

이력envelope는items/next_cursor/history_revision. item12필드: history_id, character_id, game_account_id, server_name, character_name, class_name, combat_power(string|null), item_level(string|null), power_fetched_at(UTC|null), item_level_fetched_at(UTC|null), retired_at(UTC), lifecycle_revision. 이력은퇴역당시회원귀속으로고정해현재owner변경으로타인에게공개하지않는다. 회원historyrevision/cursor가새이력시stale, 다른회원cursor400/임의user_id400. 이력없음은빈items/next_cursornull/revision1이며head행을생성하지않는다. 기기정리ACK/쓰기API는없다.

## 검증·게시 기록

진행 중. 초기 직접 영향 168개 실행에서167PASS/1FAIL(52.07초·기존경고1). 실패는 테스트가 점유중인 canonical 이름을 직접 바꾸던 방식이 새 NameClaim FK에 거절된 것으로, 같은ID 개명이 아닌 200명중 누락1/신규1의 모의 관찰로 테스트를 수정했다. 이 초기 결과를 전체통과로 표시하지 않는다. 최신 단위별 최종결과는 후속 기록에 남긴다.

추가185개 실행에서는183PASS/2FAIL(61.00초·기존경고1). 둘은 테스트의 활동선택에suspect를빼면서대표로보내던 입력과 원문수치1700.00을1700으로기대하던항목으로, suspect를선택집합에포함해사용차단을검증하고수치문자열보존을검사하도록수정했다. 장비challenge의시작키version고정·매외부호출전context검사도보완후최종검증중이다.

L1a 최종: 최신 API/test 이미지의 격리 PostgreSQL17에서 `test_character_lifecycle`, 계정/대표/전투력/회원키/제한복원 직접영향 회귀 및 metadata 비교 **185 passed, 1 기존경고, 60.71초**. 초기 실패2회와 구분하며 최종 실행은 모두통과했다. network-none 이미지 OpenAPI는 기존 paths/components 전체불변·lifecycle정책추가만반영/원본일치 확인. 실제DB migration·실자료backfill·API재시작/배포·실provider호출은하지않았다. L1a게시후 L1b를이어간다.

### 실제 L1a 게시

구현/OpenAPI `6f3d029d4e06a70ebed2244040e17b300bbab82c`·작업브랜치일반push/원격일치확인, [선행 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6186038066) 완료. dev/main미통합·실제0007미적용·실행API미재시작이다.

### L1b 최종 검증

최신이미지격리PostgreSQL의V2읽기·L1a/대표/계정직접영향·metadata/스키마 **113 passed, 1 기존경고, 48.64초**. preview필수null·모든DTO필드required·cursor구조차원/settingsstale·claim불일치/소유상실·회원이력격리·모의퇴역historypage·GET쓰기0/외부호출0·V1wire불변을확인했다. L1a185개와별도실행이며누적단일suite로표현하지않는다. network-none이미지에서원본전체일치, L1a대비추가GET2개/DTO4개/읽기정책만변경. 실제DB/실행API미변경·실provider/실기기미인수. L1b를별도게시/인계한다.

L1b 추가 보완: preview의canonical사용불가와표시용profile관찰신선도를분리했다. 같은previewgeneration에서관찰한fresh수치는usable=false여도power_stale=false일수있다. L1a에서생긴eligible=false와신선도의결합을제거해기존표시의미를보존했다. 최신이미지의V2조회·전투력표적 **57 passed, 1 기존경고, 16.29초**. 앞선113개와별도실행이며합산단일검증이아니다. 원본OpenAPIshape는불변이다.

### 실제 L1b 게시

구현/OpenAPI `c91af2e003877daacb833aaa0c109eae11b72816`·feat/representative-selection 일반push/원격일치/clean확인. [L1b별도인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6186143574) 완료. dev/main미통합·실제DB0007미적용·실행API미재시작. Flutter의계약소비/metadata·활동/대표연결회신과후속서버전환준비가다음이다. 게시기록문서만추가커밋/push하며기능검증/서버조작을반복하지않는다.


## 실제 DB/API 전환 기준 — 기존 자료 보존 계획 폐기

2026-10-16 사용자 확인: 현재 테스트 자료와 기존 Firebase 시스템은 폐기하고 새 시스템에 승계하지 않는다. 이전에 이 절에서 요구했던 테스트 DB 백업·격리 복원·기존 행 보존 리허설은 Backend 판단으로 추가한 절차였으며 폐기했다. 이를 다음 작업의 필수조건으로 사용하지 않는다.

Flutter의 P1/P2 요청에 따른 0007~0009 Alembic 파일은 신규 PostgreSQL 구조 정의이고 Firebase 자료 이관 구현은 아니다. 합성 fixture에서 검증한 기존 UUID/FK/권한 동작은 새 시스템의 기능 검증 이력이며 실제 테스트 자료 승계나 Firebase 연동을 뜻하지 않는다.

후속은 테스트 자료를 승계하지 않는 새 DB 초기 구성과 최신 API 실행 환경 기준으로 재정리한다. 현재 실제 DB0006/API대표구간·건강 상태는 읽기 확인했으며 신규구조 실제 적용/DB·볼륨 삭제/Firebase/기기 조작은 실행하지 않았다. [폐기 경위](ISSUE_8_LOCAL_TRANSITION_READINESS.md), 다음 실행은 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다.


## 최신 실행 상태 — 새 환경 준비

위의 DB/API 미적용 표기는 각 구현 인계 당시 기록이다. 2026-10-16 사용자 진행 지시 후 별도 `lostparty-fresh-dev`에 새 빈 DB0009/P2 API8001을 구성했고 health/원본 계약 일치·사용자자료0건을 확인했다. 원본8000/0006은 유지했다. [새 환경](ISSUE_8_LOCAL_TRANSITION_READINESS.md)·[관찰 도구](ISSUE_8_OWNERSHIP_READINESS.md)가 현재 기준이다. 실제 게임 검증은 사용자 결정으로 나중에 진행하며 소유/canonical·퇴역/전체 인수는 보류다. Flutter D는 [1528PASS/미게시 완료 보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790)이며 실기기 인수와 구분한다.
