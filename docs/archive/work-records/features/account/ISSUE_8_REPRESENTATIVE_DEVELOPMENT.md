> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [activity-and-presentation](../../../../features/rosters/activity-and-presentation/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 대표 빠른 선택 — 구현·인계

2026-10-15. [계약](ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md)·[Flutter 수용/착수 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184322765) 기준. 구현은 `feat/representative-selection`, dev/main 미통합이다. 실제 구현/OpenAPI SHA·원격 push는 같은 Issue 인계 댓글과 문서 마지막 게시 기록이 기준이다.

## 제공 범위

GET/PUT `/v1/me/game-accounts/{registration_id}/representative`. GET은 본인소유 등록의 현재대표/10필드 응답·REPEATABLE READ·쓰기없음, 비메인도 조회 가능. PUT은 현재 본인소유 메인·선택된confirmed canonical 대상·기대 registration/settings/ownership/roster 네revision을 검사한다. 요청5필드/엄격revision/unknownquery·GETbody 거절, UUIDv4 멱등key, no-store. 대표변경만settings_version+1·활동/Configuration.state/다른설정보존, stale no-op거절·유효no-op version유지. 삭제404·소유상실403·현재비메인409 MAIN_REGISTRATION_CHANGED·메인복귀/기대revision불일치409 REVISION_CONFLICT, 다른원정대ID404·비활동/사용불가409·설정없음409. 기존 SQLAlchemy handler가 일시DB장애503 SERVICE_UNAVAILABLE을 원문없이 처리한다.

기존 전체설정PUT도5분판정 제거·모든현재settings응답next_change_at=null. 기존timestamp 대량수정/테이블/migration없음. 기존settings완료replay는 폐지된 next_change_at만null로 투영하고 저장이력/과거대표/version은 불변. 새대표replay는 원래성공/과거is_main 그대로이며 세션·현재등록/소유재검사 후 반환한다. 메인여부/과거expectedrevision으로 성공재실행하지 않는다. 현재값은GET우선.

provider/키복호화0·기존인증/키/전투력DTO불변, 대표변경으로 인증/활동 생성없음. 현재live장비proof보류 때문에 소유/활동이 없는 실제회원은 사용할 수 없으며 별도 선행 연결/실인수다. 이 구간은 lifecycle/NameClaim/퇴역/자동삭제/V2·파티구현을 포함하지 않는다.

## 검증 결과

1. 최신API/test이미지·격리tmpfs PostgreSQL17: `tests/test_representative.py tests/test_game_accounts.py tests/test_auth.py::test_model_migration_consistency` **75 passed, 1 기존경고, 30.09초**. 대표권한/활동·4revision·read-only·no-op/replay/멱등·설정과공유version경합·메인전환/복귀·삭제/타인등록/소유상실·세션폐기/만료/정지·대상ID/비활동/suspect/missing·재구성상태보존·fencing rollback/lease/expiry·strictDTO와직접영향계정업무·migration/metadata일치 확인.
2. 과거settings replay시각null 보완·추가동시성/빈활동/교차원정대ID 후 최신이미지 표적: `tests/test_representative.py tests/test_game_accounts.py::test_ownership_first_seed_no_cooldown_atomicity tests/test_auth.py::test_schema_contract` **37 passed, 1 기존경고, 11.33초**. 두 실행은 별도이며112개단일검증으로 표현하지 않는다. Google는mock, 원정대/활동상태는격리fixture이며실provider/실기기사용자인수는없다.
3. 원본OpenAPI 비교시 기존path/schema는불변·새representative경로2operation/DTO2개·정책/cooldown만차이 검토. 개발API만최신이미지재생성/healthy, `python3 scripts/check_openapi.py` **전체일치PASS**. test-db중지. 개발DB에 migration/fixture/실대표변경·키파일수정/외부호출·자료삭제/초기화없음. 운영배포없음.
4. `git diff --check` 통과. 구현/인계 전 같은 범위로 문서/기존#7종료기록도 보존해 게시한다.

## 재검증 방법

```bash
docker compose build api
docker compose -f compose.test.yaml build tests
docker compose -f compose.test.yaml run --rm tests pytest -q -p no:cacheprovider tests/test_representative.py tests/test_game_accounts.py tests/test_auth.py::test_model_migration_consistency tests/test_auth.py::test_schema_contract
docker compose -f compose.test.yaml stop test-db
```

이 명령은 격리test DB를 사용한다. 실행API에 적용할 때만 API서비스를재생성하고 원본OpenAPI를비교한다. DBmigration은없고개발DB자료는검증fixture대상이아니다.

## 담당별 후속

Backend: 인계상시승인으로검증구간commit/push·원격확인후정확한SHA/branch/dev미통합·계약변경/검증/미확인을같은Issue에회신한다. Flutter: 원격원본계약소비·strictDTO/왕관/알럿·현재GET/응답유실/전체설정draft경합·회원/메인late응답연결, 자동검증/사용자결과를같은Issue로회신한다. 소유/활동·서버ID/기기ID매핑 선행은Flutter후속이며이API로우회하지않는다. Backend추가수정은재현/새요청이있을때수행한다. #8전체lifecycle증거조사/계약대조는별도남는다.

## 실제 게시 기록

구현/원본OpenAPI `cd3e003eb058ee5de761563d25c418d0e45ac526`·feat/representative-selection 일반push/원격일치 확인. [같은Issue 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184483999) 게시완료. dev/main미통합. 다음은Flutter계약소비/연결/자동검증·실사용회신이며live소유/활동/IDmapping선행은별도유지한다. 이게시결과문서만추가커밋/push하며기능재검증/서버재실행은반복하지않는다.
