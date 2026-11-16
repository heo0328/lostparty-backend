# character-analysis-refresh-1 — Backend 최종 계약 제안

2026-11-16 / [Issue55](https://github.com/heo0328/lostparty-backend/issues/55). **Native 전체5 설계 수용에 따라 Backend도 후보1을 같은 character-analysis-refresh-1 기준으로 공동 확정한다. 현재 로컬 구현·회귀 검증 중이며 실제 서버에는 미적용이다.** [전체2 Native](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6909842470)의 수정과 사용자 승인 계획을 반영한다. 호출 조사·공개 기능/키 방향의 원본은 [설계](server-processing-design.md), 정확 DTO는 [후보 JSON Schema](analysis-refresh.schema.json), 합성 wire 예시는 [examples](analysis-refresh.examples.json)다. [현재 OpenAPI](../../../../openapi/openapi.yaml)와 [구현·검증 기록](server-processing-implementation.md)을 함께 갱신했다.

[전체4 Backend 최종계약 후보1 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910288469)에 정확 명세·전체 Schema/합성 예시·검증 집계를 게시하고 실제 순번/원문 일치를 재조회했다. 이 댓글이 원격 설계 인계본이며 repo 문서는 미게시다. [전체5 Native 설계 수용](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910545522)을 수신했다. 후보1 wire/Schema/examples 변경 없이 설계 기준으로 확정하며 아래 구현 단위로 연결한다.

## 1. 범위·자료의 단일 원본

기준 소스 Backend cda4db3 / Native 302243fb. 작업 구간은 `서버 분석 최종 계약·영향표 인계`, checkout은 `refactor/lostark-server-processing`이다. 문서는 미커밋·미push·새 소비SHA 없음이다. 이 단계는 조사/계약 제안까지이며 기능 코드·키/DB/운영 변경은 하지 않는다. 구버전/옛 pending/과거 분석 승계를 위한 shim·다중 writer/reader는 만들지 않는다.

새 역할 분석은 회원+canonical character UUID+ownership_revision+role의 **최신 head 하나**를 원본으로 한다. source=server_analysis, trust=server_computed이며 로아 자체가 분석을 인증했다는 뜻은 아니다. 별도 RolePowerSuccess의 마지막 nonnull fallback을 제거하고 모집 비교·그룹/후보/신청 표시까지 같은 head를 읽는다.

- 수집+형식/대상검증+역할판정 성공이면 낮은 수치·세팅error·확실한 source 미제공null도 최신값/시각·issues로 저장한다. clean만 저장하지 않는다. 전투력0은 문자열 "0"으로 저장하며 미제공과 구분한다.
- 통신·응답형식·서버/이름/직업 대상 불일치·역할판정 실패는 해당 역할의 summary/detail/version/saved_at을 모두 유지한다. 파싱 불가 수치를 미제공null로 바꾸지 않는다.
- 딜러/서포터 head는 독립이다. 반대역할과 preferred_role·활동·대표·소유권은 변경하지 않는다. preferred_role은 기존 preferences API로 표시/선호만 바꾼다.
- 기존 자동/수동 실행 시점을 유지한다. 화면 열기·필터·참가·상세 펼치기는 새 provider 호출을 만들지 않는다. 로아 정기 전체 수집 job이나 새로운 작업 플랫폼은 도입하지 않는다.

## 2. POST 요청·경계

`POST /v2/me/character-analysis/refresh`, 회원 Bearer 필수, query 없음, Content-Type application/json. 바깥 Idempotency-Key는 필요 없으며 **항목 command_id가 명령 키**다. 모든 API 응답 Cache-Control:no-store를 유지한다.

```json
{
  "items": [{
    "command_id": "00000000-0000-4000-8000-000000000101",
    "character_id": "00000000-0000-4000-8000-000000000001",
    "expected_ownership_revision": 1,
    "expected_lifecycle_revision": 1,
    "expected_summary_versions": {"dealer": 1, "support": 1},
    "trigger": "manual"
  }]
}
```

필드 전부 필수·추가 필드/중복 JSON key 금지. items1..50, command_id는 UUIDv4, character_id는 canonical UUID, version은 strict 정수1..2147483647(bool 금지), trigger는 automatic/manual이다. 같은 요청의 command_id/character_id 중복은 전체400이다. raw·요청/강제저장 역할·클라이언트 summary·개인 키를 받지 않는다. 수신 UTF-8 body 상한524288bytes, 초과413. 형식400/크기413·전체 인증401/회원403은 **reserve/업무 쓰기 전** envelope 오류이며 기존 GameErrorOut 형태를 사용한다. 문서 Schema만으로 표현되지 않는 중복ID/byte검사는 HTTP 경계에서 수행한다.

### 대상·역할·동시성 검사

1. 전체 요청 형식을 검증하고 회원 인증한다. 각 항목은 replay/진행중 기록부터 확인하되 현재 접근권한·소유수명 검사를 생략하지 않는다. 현재 owned 등록·NameClaim·usable/active/confirmed·입력 소유/수명 revision을 외부 호출 전에 검사한다. 한 항목의 권한 실패는 다른 성공을 rollback하지 않는다.
2. automatic은 최신 등록/활동/usable/lifecycle과 회원 nice_group_auto_refresh_enabled로 대상 재검증한다. 나이스단은 전체 소유 원정대 active 목록에서1700 이상 동일직업2명 기준이며 OFF면 해당 자동대상만 제외한다. manual은 같은 소유·usable 조건을 검사하되 자동 나이스단 제외로 막지 않는다. Native는 기존 앱/회원 수명당 실행과 목록 갱신→대상 확정 순서를 유지한다. 원정대/설정 변경 중 늦은 자동 결과도 최종 현재 자격 재검사로 차단한다.
3. 새 관찰을 수집하고 고정 분석 카탈로그로 역할을 감지한다. 겸용4직업 바드/발키리/도화가/홀리나이트는 detected+detectedRole+관련4티어 노드 근거가 필요하다. 기타 지원 직업은 dealer다. unsupported/ambiguous/판정 불가는 선호역할/강제역할로 대체하지 않는다.
4. 최종 짧은 트랜잭션에서 회원·소유/등록·UUID/NameClaim·수명·현재 자격·서버 키 세대·명령 lease/generation을 다시 검사한다. **감지 역할의 expected_summary_versions만 CAS** 검사하고 반대역할 version 불일치로 거절하지 않는다. 최초 미저장은 version1, 최초 저장2, 새 성공 관찰은 수치가 같아도 관찰시각/분석이 갱신되므로 version을1 증가한다. overflow는409 REVISION_CONFLICT로 거절한다.
5. summary+detail+version/saved_at+명령 완료응답을 같은 트랜잭션으로 저장한다. I/O나 순수 분석 worker는 업무 DB를 쓰지 않는다. 롤백/lease 교체/예산 이후 늦은 결과는 적용하지 않는다.

### 처리 예산·fresh 합류

전체20초 예산(배치 크기에 비례한 대기 보장 아님), 외부 수집 동시2, 마지막1초는 DB 마감에 예약한다. 새 수집 시작 시 현재 transport 최대8초+마감1초를 확보할 수 없는 항목은 시작하지 않는다. transport connect3/read5초·본문상한1MiB·총 deadline/종료 정리는 기존 정책을 재사용하며 응답 직렬화·스케줄링까지20초 hard-real-time을 보장하지 않는다. Native 응답 timeout 권장60초다.

automatic/manual 모두 새 분석 명령은 과거 TTL 결과를 성공으로 반환하지 않는다. 동일 명령의 과거 ACK는 재수집 없이 반환한다. **동시에 실행 중인 fresh 관찰**만 회원+UUID+소유/수명+서버 키 세대 범위에서 합류한다. 합류한 결과도 각 명령의 최종 CAS/권한 검사를 받으므로 둘 다 같은 version으로 저장할 수 없다.

관찰 합류에는 작은 DB `character_analysis_fetch_leases`를 사용한다(추가 후보, 새 큐 아님). 행은 fetch_id·scope_digest·generation·expires_at·state·최소 분석 projection/observed_at이며 raw는 저장하지 않는다. scope 잠금 아래 유효 running만 합류하고, 완료행은 이미 합류한 caller에게만 제공한다. 완료 뒤 시작한 요청은 새 fetch_id를 사용한다. 각 fetch는30초 상한, 완료/실패/만료행은 기존 정리 job에 연결해 제거한다. 늦은 generation 완료는 거절하고 관찰결과 자체가 업무 권한/저장 성공 증명이 되지 않는다. 다른 회원/수명·장비 소유 인증은 합류하지 않는다.

## 3. 응답·오류·명령 수명

전체 검증을 통과한 배치는 HTTP200 `{evaluated_at, items}`이며 items는 입력과 같은 순서/개수다. evaluated_at은 응답 시 서버UTC, 항목 안의 saved_at/분석시각은 원 명령의 시각이다. `status`는 항목 HTTP 의미이며 envelope200과 혼동하지 않는다.

항목 필드는 모두 필수다: `{command_id,character_id,status,state,detected_role,retry,result,error}`. result는 saved일 때만 SavedResult, 나머지는 null이다. error는 saved일 때만 null이며 나머지는 `{code,message,request_id,retry_after_seconds,retry_at}`다. 미해당 retry 값은 null, 재시도 시각은UTC·seconds는 양의 정수다. message는 안전한 code 문자열이며 원문/URL/키/타회원 자료를 포함하지 않는다. 알 수 없는/판정 전 detected_role은 null이다.

| state / status | result·사유 | retry·명령 상태 |
|---|---|---|
| saved /200 | SavedResult: character_id/game_account_id/ownership_revision/lifecycle_revision/role/analysis. analysis는 version/saved_at/summary/detail 전부 포함 | none, 저장과 종결ACK가 원자적. error integrity여도 saved |
| skipped /200 | AUTOMATIC_TARGET_EXCLUDED, detected_role/result null | none. 자격 있는 요청의 자동 제외를 reserve 후 종결ACK로 기록; 역할 head 쓰기0 |
| failed /400,401,403,404,409,429,503 | 확정 실패. result null. CAS 실패 때 감지 역할은 공개 가능 | 새 갱신 가능한 오류는 new_command, 권한/입력/만료는 none. quota/통신오류 자동반복 금지 |
| not_processed /503 | BATCH_NOT_PROCESSED. 해당 항목에 기존 명령기록 없고 예산으로 미착수 | same_command, reserve/종결/외부호출0. 다음 bounded 요청으로 미시도 항목만 이어감 |
| in_progress /409 | REQUEST_IN_PROGRESS, retry_after_seconds=2 | same_command, 다른 유효 lease가 실행 중. 원 명령 변경0 |
| unknown /503 | SERVICE_UNAVAILABLE. DB commit/결과복구를 확인하지 못함 | same_command, 성공/실패 단정 금지. 원ID/body로복구 |

`retry`는 none/same_command/new_command이며 허용된 방법이지 즉시 반복 지시가 아니다. unknown/in_progress는 갱신에 실패했다고 새ID를 만들지 않는다. 응답유실은 전체 items의 원ID/body를 그대로 재전송할 수 있고 완료항목은 ACK, 미시도만 실행된다. 성공ACK 뒤 현재GET이 실패해도 저장성공을 실패로 바꾸지 않는다. 동일 회원 재로그인에도 현재 접근/수명을 재검사하고 Native 세션 세대가 다른 늦은 응답은 폐기한다.

### 오류·재시도 표

| code | status/state | retry·저장 |
|---|---|---|
| INVALID_REQUEST / REQUEST_TOO_LARGE | envelope400/413 | 수정 후 새 명령. reserve0 |
| SESSION_REVOKED 및 기존 인증 code | envelope 또는 항목401/failed | none, 새 쓰기 없음. 실행중 항목은 마감 전 세션 재검사 |
| ACCOUNT_DISABLED / OWNERSHIP_REQUIRED | 403/failed | none, 자료/ACK 접근 제한 |
| CHARACTER_NOT_FOUND | 404/failed | none, 타회원 존재 여부 노출 없음 |
| CHARACTER_UNUSABLE / IDENTITY_CONFLICT | 409/failed | none, 현재 대상 재조회/사용자 조치 |
| REVISION_CONFLICT | 409/failed | new_command, 최신GET/대상 재확인 후 새 갱신. 자동 version치환 재전송 금지 |
| IDEMPOTENCY_CONFLICT / IDEMPOTENCY_EXPIRED | 409/failed | none, 원 명령 변경/재실행 없음. 현재GET·명시 새갱신으로 전환 |
| UPSTREAM_NOT_CONFIGURED / LOSTARK_KEY_REJECTED / SERVER_KEY_CHANGED | 503/failed | new_command, 서버 구성 복구 후. 사용자 개인 키 입력 요구0 |
| RATE_LIMITED | 429/failed | new_command, retry_at/seconds 제공. 현재 attempt 확정종결 |
| UPSTREAM_RATE_LIMITED | 503/failed | new_command, 공유 quota의 retry_at/seconds 제공. 현재 attempt 확정종결 |
| UPSTREAM_BUSY / UPSTREAM_UNAVAILABLE / UPSTREAM_INVALID_RESPONSE / UPSTREAM_RESPONSE_TOO_LARGE | 503/failed | new_command. 안전하게 저장 미실행/rollback이 확인된 경우만 확정실패 |
| ANALYSIS_UNAVAILABLE / ROLE_DETECTION_UNAVAILABLE | 503/failed | new_command, 파싱/역할 실패·이전값 유지. 세팅error는 이 오류가 아님 |
| BATCH_NOT_PROCESSED / REQUEST_IN_PROGRESS / SERVICE_UNAVAILABLE | 위 상태표 | same_command. budget 미시도와 DB 결과불명 혼용 금지 |

### reserve·종결·복구

operation=`character-analysis-refresh`, key=회원+command_id. digest는 정규화된 항목 전체(character_id/revisions/양역할version/trigger 포함)이며 바깥 batch·순서·추적ID는 제외한다. reserve와 짧은 저장은 기존 공통 RequestResult·lease30초/generation 방식을 재사용한다.

- 새 항목은 대상 검사 후 **실제로 처리할 여유가 있을 때만 reserve**한다. pre-reserve 권한/대상 거절은 결과만 반환하고 ledger를 만들지 않는다. reserve 이후 확정실패·skipped는 종결ACK로 저장한다. 공통 helper의 무조건 release/retryable 경로를 새 분석 업무에 그대로 적용하지 않는다.
- 기존 completed는 현재 접근·입력 소유/수명 검사를 한 뒤 원ACK 반환한다. 현재 role version으로 원ACK를 재평가하거나 다시 저장하지 않는다. 기존 running은 in_progress, 만료/retryable은 같은 digest로 generation을 교체해 복구할 수 있다.
- **기존 미확정 기록이 있으면 예산이 부족해도 not_processed로 표시하지 않는다.** 유효 lease는 in_progress, 복구 판정조차 할 수 없으면 unknown이다. commit 결과가 불명확하면 실패ACK를 덮어쓰거나 임의로 lease를 해제하지 않는다.
- completed24시간 뒤는 IDEMPOTENCY_EXPIRED, 기존 tombstone 정리 기준은 유지한다. 새 operation도 생성48시간 이후 미완료를 자동 takeover하지 않고 만료 처리한다. 성공24시간/생성48시간 이후에는 blind retry를 중단하고 현재GET·명시 새갱신을 사용한다. row 정리 이후까지 무기한 exactly-once를 약속하지 않는다. 옛 flutter_analysis pending을 이 operation으로 변환하지 않는다.

## 4. 역할 읽기·상세·모집 비교 DTO

기존 personal-profile/일괄 personal-profiles의 각 역할을 `{version,saved_at,summary,detail}`로 확장한다. 미저장만 version1/나머지null, 저장은 version>=2·summary/detail/saved_at 전부 nonnull이다. role별 상세는 그 head version에 속하며 별도 detail version을 만들지 않는다. bootstrap은 같은 version/saved_at/summary만 투영하며 detail은 넣지 않는다. bootstrap 응답 타입을 personal-profile 전체 DTO에서 요약 DTO로 분리해 상세 자동확장을 막는다. 조회는 read-only·provider0·행 자동생성0이다.

summary는 기존 수치/시각·integrity/issues·규칙/catalog/lifecycle를 유지하되 source=server_analysis다. 숫자는 길이32 이하 비음수 십진문자열(지수/NaN/Infinity 금지), 시각은UTC RFC3339다. 확실히 미제공인 숫자와 관찰시각은 함께null이며 분석시각·saved_at까지null로 만들지 않는다. integrity는 error issue 우선→review/warning→확인가능 clean→unavailable이며 고정 Native mapper 결과를 따른다. role head의 lifecycle와 현재 캐릭터 수명이 다르면 그룹/참가의 유효 수치로 쓰지 않는다.

detail의 전체 필수 필드는 후보 Schema Detail이다. Native 고정 entity enum은 snake_case로 매핑한다.

| 필드 | 타입·의미 |
|---|---|
| detection | status detected/unsupported_class/branch_not_found/ambiguous, catalog_version, nullable class_id/branch_id/branch_display_name/detected_role/matched_tier1_node, matched_related_nodes[] |
| rune_count / equipped_gem_count / gem_effects_source_available | int>=0 / nullable int>=0 / bool. unknown gem count를0으로 위장하지 않음 |
| gems[] | slot/level 정수, target 문자열, descriptions 문자열배열, category normal/passive_or_identity/unknown, validation_status verified/same_class_target_unverified/foreign_class/unavailable |
| ark_grid_core_points[] | name/grade 문자열, point/minimum_point/recommended_point 비음수정수 |
| ark_grid_conditions[] | core_name/condition_text 문자열, required_passive_names/missing_passive_names 문자열배열 |
| ark_grid_minimum | null 또는 order_sun_point/order_moon_point nullable 정수·required_point14 |
| notices[] | code·severity(info/warning)·정제된 message. 서버 고정 표시자료이며 raw tooltip/HTML을 반환하지 않음 |

rule ID는 lostparty-server-role-analysis-v1, 분석 catalog_version은 실제 고정 분석 카탈로그의 버전이다. examples의 synthetic-catalog-v1은 합성 예시 전용이며 실제 버전으로 게시하지 않는다. 저수치/부족/타직업/조건error도 감지 역할과 정상 파싱된 수치를 가진 저장 성공이다. UI 반올림/시각 포맷·반응형·문구 표현은 Native가 담당하며 분석결과를 다시 계산하지 않는다.

새 PowerComparison은 `{selected_role,requirement,actual,state,source,trust,summary_version,observed_at,saved_at,integrity_status,issues}`다. state는 기존 unrestricted/missing/below/meets, 실제값은 **현재 유효 head의 combat_power만**이다. 저장null/미저장/수명불일치는 actual=null이며 최소조건이 있으면 missing이다. 세팅error를 새 참가차단 정책으로 확대하지 않고 최신 숫자 비교와 경고를 유지한다. summary_version은 미저장1/현재head버전, 이전 power_revision/success_summary_version/success_saved_at/success_issues/current_issues의 이중 원본은 제거한다. context/token/CAS 근거도 같은 summary_version과 수명에 결합한다.

참가/신청 snapshot은 당시 선택역할의 `{version,summary,saved_at}`을 복사해 역사 증거로 유지한다. 현재 head와 snapshot을 섞지 않으며 표시 stale은 version/수명 차이로 판정한다. 과거 snapshot 포맷을 읽는 다중 parser는 추가하지 않는다. 기존 snapshot 자료의 정리 필요성은 아래 영향표대로 별도 대상 승인에 포함한다.

## 5. API·저장·제거 영향표

| 대상 | 변경·단일 책임 | 자료/소비 영향 |
|---|---|---|
| 새 분석 POST | 순수 분석+항목 ledger·현재 권한/CAS, fresh 합류 | Native 직접Armory/로컬raw/summary업로드 경로 대체. 공통 fixture 동등성 후 연결 |
| profile 단건/배치 GET·bootstrap | 저장 head 읽기. full detail DTO와 bootstrap 요약 DTO 분리 | 상세 신규기기 복원 가능, GET/provider0. preferences/presentation 유지 |
| 개인 키 GET/PUT/DELETE/restore | router/service/암복호화/key readiness·전용 setup 제거 | lostark_credentials 및 이전 키 의존 제거 대상. 암호화 자료/기존 secret 파일의 실제 삭제는 이번 실행에서 하지 않음 |
| role-summaries PUT·role-summary-batches POST | 기존 client writer/전용 입력·복구 제거 | 예전 pending/ACK를 새 분석으로 변환하지 않음. 새 operation은 별도 |
| 원정대 등록/preview/refresh·전투력·장비 인증/분쟁 | 기존 업무 endpoint 재사용, 서버 key 공급/세대·공유 quota | 호출 전·저장 전 회원/소유/수명 fence 유지. proof는 fresh·lease/기한·#15 보류 유지 |
| ScopedRosterCache/ScopedRosterLease·ScopedPowerCache | 현재 실제 업무의 scoped_roster_cache/scoped_roster_leases/scoped_character_power_cache에서 회원 credential_version 제거·새 서버 key 세대 범위 반영 | 개인 key버전 PK/캐시자료는 전환정리 후보. 소스의 MemberPreview/MemberFetch는 ScopedRoster* 별칭이며 lostark_keys.models의 옛 동명 모델과 구분 |
| CharacterRoleSummary | 같은 회원/UUID/소유수명/역할 PK, summary+detail JSONB·단일 version/saved_at | 새 source/형식. 이전 Flutter summary를 출처만 바꾸어 승계하지 않음 |
| RolePowerSuccess | capture/별도 테이블·참조 제거 | character_role_power_successes·옛 최고/nonnull fallback 없어짐. 새 head 단일 읽기 |
| 새 character_analysis_fetch_leases | fresh 수집 중복합류만, TTL30초·짧은 정리 | 최소 projection만 임시보관·권한증거/업무저장 아님. 기존 cleanup에 연결, 외부 job 시스템 없음 |
| groups.display / character_candidates / admission_eligibility / application_display | 단일 head에서 수치/시각/integrity 읽기 | stored_role_success/client_submitted·power_revision 제거. 공개 범위/not_disclosed 권한 유지. source는 server_analysis/unavailable/not_disclosed, trust는 server_computed 또는null |
| participation_core·입장/생성/교체/재참가/일정 context | PowerComparison·당시 snapshot·token 근거 전환 | 낮은값/null/수명불일치가 과거 수치로 우회하지 않음. 최신분석 변경 시 context CAS409 |
| 회원/참가 상세 reads·DTO/wire/main 계약 보정·readiness | 현재분석/역사snapshot 조회·단일 version·서버 출처로 수정 | 반대역할/타소유수명 연결 금지. 새 DTO만 실행, 옛 JSON reader를 추가하지 않음 |
| Verification/Proof identity_snapshot·분쟁 worker·진단 CLI | 개인키 capture/check/decrypt 제거·서버 key 세대 검사 | 기존 미완료 개인키 proof/snapshot의 정리/재시작이 필요. baseline 증거/소유/등록/분쟁세대·기한/lease 검사는 유지 |
| 소스/시험/배포 안내·설정 | 개인key·client writer·성공값 테이블의 실제 사용처/전용 시험 제거, 정당한 업무 회귀는 새 생산자로 재작성 | 과거 migration/동결 원문/Git 이력은 재작성하지 않음. #55와 무관한 legacy전체 정리는 확대하지 않음 |

그룹/후보 역할 수치도 `{value,source,trust,summary_version,observed_at,saved_at,integrity_status,issues}`로 단일 head에서 투영한다(그룹의 combat_power 표기 필드는 유지). head가 존재하면 수치가null이어도 server_analysis/server_computed·head 메타데이터를 유지해 source 미제공과 미저장을 구분한다. 미저장은 source=unavailable·메타데이터null, 비공개는 not_disclosed·메타데이터null이며 public API 필드를 늘리지 않는다. history snapshot은 현재 head의 대체 수치로 쓰지 않는다.

현재 운영/개발 데이터를 변환하는 복잡한 이관은 요구하지 않는다. 예상 정리 후보는 옛 역할 summary/성공값·키버전 캐시·진행중 인증/분쟁의 개인키 snapshot·해당 명령 및 옛 형식 모집/신청/참가 snapshot이다. 영향을 받는 연결 자료와 유지할 회원/원정대/그룹/기록 범위를 실행 전 조사해 **자료정리/초기화 범위·행수/참조 영향·복귀 기준을 제시**한다. 그 승인 없이 migration/drop/truncate/키·기기 삭제를 실행하지 않는다. 새 reader에 옛 포맷 fallback을 넣어 이 결정을 우회하지 않는다.

서버 token은 secret_dir의 lostark-api-token 제안 파일 하나에서 공급한다. 현재 개인키 암호화 key는 token 대용이 아니며 공개 응답/로그로 전달하지 않는다. 기존 lostark-fingerprint.key는 서버 token 비공개 fingerprint/세대 식별에 재사용하며 암호화용 lostark-credential.key와 구분한다. 파일/키를 임의 재생성하지 않는다. ProviderLimit/fingerprint별 공유 제한은 재사용하고 HTTP/worker 전 사용자가 공유한다. 자체80회/60초는 프로젝트 제한일 뿐 공급자 한도 보증이 아니다. 설정 단계에서 공식 근거·응답과 대조한다. 실제 token/설정·키/DB 구조 변경 전 [백업 원장](../../../engineering/operations/backup-and-recovery.md)에 따라 대응 파일·기존 사본 재사용/보관 안내를 한다. 지금 신규 token/키/backup은 생성하지 않는다.

## 6. 검증·진행 순서

[후보 문서 검증 집계](analysis-refresh-validation.json): JSON Schema 자체 및 정상4예시·오류18사례 거절·중복ID2사례 거절·요청/응답 상관관계 확인을 통과했다. 후보 Schema/합성 examples는 **문서 형식과 상태조합 검증용**이다. 실제 Python 분석 fixture/golden이나 구현 테스트 통과가 아니다. cross-field 동일성(command/character/result/role/lifecycle/version/UTC), 중복ID·실제 byte 제한, integrity issue 우선순위는 문서 semantic 검증 대상으로 구분한다.

구현 검증 기준은 다음과 같다.

- Native 합성8계열/_hybridBuildFixture와 양역할·보석11/부족/특수/미확인/타직업·source 없음/명시빈목록·룬8/누락·grid 해달14/17/조건·unsupported/ambiguous·수치0/null/쉼표/소수 비교. live raw는 제외한다.
- 고→저/세팅error saved, 성공null→모집missing, 통신/역할실패→head/version/시각 불변, 반대역할version 불일치 허용/감지역할 불일치409, 선호역할 비개입·나이스단 자동제외/수동 허용.
- 항목 부분저장·최종CAS/권한·현재 명령 응답유실·중복/다른body·ACK24h/미완료48h·예산미시도 reserve0·기존미확정 not_processed 금지·실행 중 합류·lease takeover·키교체·quota/Retry-After·늦은worker 쓰기0.
- summary/detail/bootstrap/그룹/후보/참가의 version·수치·시각 일치와 provider0, 현재head와 역사snapshot 분리, 과거 nonnull fallback/옛 writer/개인key 참조0. 웹/Android UI·예시/세션 경계는 Native가 담당한다.

실행 순서는 계약 후보 회신→Native exact JSON/읽기·삭제영향 대조→양측 명세 확정이다. 그 후 별도 구현 구간에서 서버 key/수집/worker·순수 분석/저장/읽기·Native 새요청·옛경로 제거를 함께 완결한다. 실제 DB/설정 전환과 운영 공개는 별도 결정이다. 이번 완료는 Backend 계약 제안 인계이며 양측합의·기능완료·운영반영이 아니다.


## 7. 공동 설계 확정·구현 단위

Native 전체5는 제품/정확 wire·저장/제거 방향을 추가 재설계 요청 없이 수용했다. Backend도 동일 character-analysis-refresh-1을 확정하며 후보1 JSON Schema/examples는 변경하지 않는다. 원격 인계 원본은 전체4의 완전한 계약/Schema/예시와 전체5 수용, [전체6 Backend 확정 회신](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910714179)이다. repo는 미커밋·미push·새 소비SHA 없음, 실제 구현/실행 OpenAPI/분석동등성/기기 통과와 구분한다. 설계 delta가 생기면 같은 Issue에서 먼저 합의한다.

| 구현 단위 | 담당·선행 | 완료 조건 |
|---|---|---|
| B1 서버 수집·순수 분석 기반 | Backend, 현재 고정 Native 규칙/분석카탈로그·합성 fixture 입력 | 단일 서버 키 공급과 quota를 HTTP/worker/진단에 연결하고 기존 업무 권한/수명 유지. 순수 분석의 합성 golden 동등성·키/실패 경계 검증. 실제 키 설정은 별도 환경 작업 |
| B2 분석 명령·단일 head·저장읽기/소비 전환 | Backend, B1 결과 | 새 POST/현재 명령 ledger·fresh합류, summary/detail 단일head와 bootstrap 요약, 그룹/후보/참가/신청/token/snapshot 소비 및 옛 writer/성공값 fallback 제거. 실제 OpenAPI 전체 비교·권한/CAS/예산/응답유실·semantic 회귀 통과. DB 변경은 영향/대상 검토 후 별도 실행 |
| N1 공통 UI/공개 탐색·예시 | Native, 공동설계 확정 | 최신 UI 재사용·기존 공개 API 소비·guest private/provider/쓰기/가짜session0. 로그인/로그아웃·늦은응답/URL/F5/복귀 격리. 독립 구현 가능하나 계약/환경을 바꿔 가짜 writer를 만들지 않음 |
| N2 새 reader/producer·옛 경로 제거 | Native, B2의 실제 게시 계약/구현과 로컬 지원 | 단일 reader/요약/상세·새 명령 상태와 60초 timeout 소비, exact wire 생성근거/fixture 갱신, 개인키/직접 API/옛 raw·summary/pending 및 구페이지 전용 의존 제거. 일부 필드 허용만 느슨하게 풀지 않음 |
| I1 로컬 통합·인계 | 양측, B2/N2 준비 | 실제 실행 OpenAPI·제공 소스/이미지·자료정리 범위를 구분해 로컬 검증. Native/UI 자동 검증과 사용자 기기 인수 구분. 기능 완료 후 운영은 별도 결정 |

Native 독립 정적검사23/23 PASS는 Native 담당 보고이며 범용 Schema 준수·분석golden/서버/DB/provider/기기 시험이 아니다. 감지역할/result.role/detail.detection 역할·summary/detail catalog/lifecycle·identity/version, 오류 state/retry/Retry-After, 입력출력 순서/개수/ID/byte·duplicate, fresh합류 세대/기존합류자와 감지역할CAS는 양측 구현 semantic 경계시험으로 유지한다. 이 조건 확인을 위해 Schema를 임의 완화하거나 새 제품결정을 추가하지 않는다.

현재 준비는 조사/명세·합성 wire검증까지이며 B1/B2/N1/N2/I1 실제 완료를 보고하지 않는다. 다음 Backend는 위 구현 단위의 로컬 실행 계획을 준비한다. 현재 승인 구간의 공동설계 마감이 기능 구현·commit/push·키 설정·DB/기기 초기화·운영 배포 승인으로 확대되지 않는다.

## 8. 구현 진행과 오류 보완

사용자의 후속 구현 지시로 B1/B2를 실행 중이다. 앞 절의 설계 단계 미착수 표기는 당시 경과이며 최신 상태는 [구현 기록](server-processing-implementation.md)이 원본이다. 전체7 Native 요청/전체8 Backend 회신의 공유 장애 억제·공식 오류 검증은 기존 wire/Schema/examples를 변경하지 않는다. 실제 키/DB/운영 적용은 여전히 별도다.
