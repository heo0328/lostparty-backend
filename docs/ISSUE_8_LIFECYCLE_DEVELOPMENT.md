# Issue #8 — L1a/L1b 구현·검증·인계

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

L1a 게시 후 별도 구현/인계한다. V2 refresh/lookup-recovery·실소멸 적용·기기삭제는 이번 범위가 아니다.

## 검증·게시 기록

진행 중. 초기 직접 영향 168개 실행에서167PASS/1FAIL(52.07초·기존경고1). 실패는 테스트가 점유중인 canonical 이름을 직접 바꾸던 방식이 새 NameClaim FK에 거절된 것으로, 같은ID 개명이 아닌 200명중 누락1/신규1의 모의 관찰로 테스트를 수정했다. 이 초기 결과를 전체통과로 표시하지 않는다. 최신 단위별 최종결과는 후속 기록에 남긴다.

추가185개 실행에서는183PASS/2FAIL(61.00초·기존경고1). 둘은 테스트의 활동선택에suspect를빼면서대표로보내던 입력과 원문수치1700.00을1700으로기대하던항목으로, suspect를선택집합에포함해사용차단을검증하고수치문자열보존을검사하도록수정했다. 장비challenge의시작키version고정·매외부호출전context검사도보완후최종검증중이다.

L1a 최종: 최신 API/test 이미지의 격리 PostgreSQL17에서 `test_character_lifecycle`, 계정/대표/전투력/회원키/제한복원 직접영향 회귀 및 metadata 비교 **185 passed, 1 기존경고, 60.71초**. 초기 실패2회와 구분하며 최종 실행은 모두통과했다. network-none 이미지 OpenAPI는 기존 paths/components 전체불변·lifecycle정책추가만반영/원본일치 확인. 실제DB migration·실자료backfill·API재시작/배포·실provider호출은하지않았다. L1a게시후 L1b를이어간다.
