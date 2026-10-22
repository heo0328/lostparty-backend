# Issue #13 — 그룹원 활동 캐릭터 필터 후보 계약 초안1

> **구현/개발 반영 완료(2026-10-22):** [개발 안내](ISSUE_13_GROUP_CHARACTER_CANDIDATES_DEVELOPMENT.md)의 후보GET/검색token·검증/168경로 실행 상태가 현재 기준이다. 아래 미구현/미반영·다음구현 표기는 계약검토 당시 기록이다.

> **2026-10-22 소비 보완:** [전체102번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339166701)가 공개범위/계열null 소비·nullable/페이지·검색token을 수용했다. §5의 페이지 밖 선택 재검증은 [보완2판](ISSUE_13_GROUP_CHARACTER_CANDIDATES_ADDENDUM.md)이 구체화한다. 같은정책 재채택 대기 없이 다음 Backend 구현이며 현재 서버/후보 API는 미변경·미구현이다. 아래 계열 소비 질문/초안 대기는 당시 기록이다.

2026-10-22 / Backend / feat/raid-recruitment. [Flutter96 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6336402066)·[97 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6337065372)·[99 초안 검토 접수](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6337772851)에 대응한다.

**검토용이며 미구현·서버 미반영이다.** 현재0.4.1/policy4·canonical SHA·두 실행 OpenAPI를 변경하지 않는다. 기계 판독 가능한 [추가 경로 OpenAPI/합성 예시](design/issue13-group-character-candidates.draft.openapi.json)를 함께 제공한다. 이 파일은 기존 전체 계약을 대체하지 않는다. 구현 완료 후에만 실행 계약/소비 SHA를 별도로 인계한다.

## 1. 공개 범위 변경 제안

기존 [기술경계4판 §3.1](ISSUE_13_R0_TECHNICAL_BOUNDARIES_R4.md)은 개인 전체 roster를 공개하지 않고 방 projection만 사용한다. 이번에는 **선택한 단일 그룹의 현재 회원끼리, 현재 인증 소유 중인 활동 캐릭터의 아래 허용 필드만** 읽는 것을 추가 제안한다. 그룹에 연결된 방에 아직 참가하지 않은 활동 캐릭터도 후보에 포함한다. 기존 방 projection만으로 충족할 수 없던 부분이다. **기존 합의로 이미 허용된 공개라고 간주하지 않으며 이 범위의 수용 여부를 Flutter가 대조한다.**

- 비회원·과거 회원·그룹 초대/신청만 가진 사람·공개 연결 방의 외부 참가자에게 후보 조회 권한을 주지 않는다. 현재 정상 인증 회원이며 선택 그룹의 현재 회원이어야 한다. 그룹장만의 기능이 아니다.
- 각 대상은 현재 active 회원이다. 활성 Registration, owner 일치/verified Account, 해당 회원의 현재 Configuration/Activity, confirmed/active Character와 현재 NameClaim 일치를 모두 요구한다. 여러 원정대의 활동 캐릭터를 합치고 canonical character_id로 중복 제거한다. preview/미인증/등록해제/소유상실/suspect/missing/retired/claim 불일치/비활동 캐릭터는 제외한다.
- 활동 수동 선택 자체의1700 하한을 새로 만들지 않는다. 레이드/난이도·주간 완료/자리/일정·현재 방 참가 여부로 후보를 줄이지 않는다. 후보는 검색 조건이며 참가 가능 보증이나 소유 이전/참가/예약 동의가 아니다.
- 개인 preferences.visible/display_order/visible_count는 본인 화면 표시값이다. 타인 공개 동의로 재해석하거나 이 값으로 후보를 임의 제한하지 않는다. **이 제안은 활동 선택과 그룹 가입을 후보 공개 조건으로 삼는 변경**이다. 별도 공개 동의가 필요하다고 판단하면 이 초안에서 정책을 조정하고 구현한다. 새로운 설정 쓰기 기능은 이번에 제안하지 않는다.
- 회원 대표표시는 기존 FilterMember.display를 그대로 사용한다(갱신 시점은 그룹 snapshot, null 허용). 이를 현재 원정대 대표와 같다고 보증하지 않는다. 그룹 내 membership UUID와 opaque member_ref만 연결한다. user/account/registration ID·연락처·장비/분석 원문·개인설정·전체 소유 이력은 응답하지 않는다. 후보 UUID/이름으로 소유자를 다른 그룹까지 연결하는 API를 추가하지 않는다.

## 2. 읽기 경로와 정확한 입력

`GET /v2/groups/{group_id}/raid-room-character-candidates`

| 입력 | 규칙 |
|---|---|
| group_id | 선택한 한 그룹 UUID path |
| filter_context_token | 필수64자리 소문자 hex. GET `/v2/me/raid-room-filter-context`에 `group_ids=[선택group_id]` JSON 배열 query를 보내 받은 값. 여러 그룹 context를 이 조회에 재사용하지 않는다 |
| limit | optional int1..100, 기본50. 아래 논리행 개수이며 회원 수가 아니다. 상한은 초안 제안이며 구현 측정 후 바뀌면 소비 대조한다 |
| cursor | optional non-null string1..2048. 첫 페이지는 생략. null/빈문자열/미정의 query·중복 query는400 |

target_cycle_key·room_ids·다른 회원 ID를 받지 않는다. C/N 공통 후보이며 target는 후속 검색 요청에만 지정한다. 읽기 전용·Idempotency-Key 없음, provider/Armory 호출·원천 갱신·DB 토큰 저장·세션 갱신 없음. 성공200, 기존 인증/오류 envelope·Cache-Control:no-store를 사용한다. 유효하지 않은 Idempotency-Key/미정의 헤더 처리까지 새 정책을 추가하지는 않는다.

매 요청 한 REPEATABLE READ/READ ONLY snapshot에서 인증→현재 그룹 접근→단일 그룹 context 재구성·비교→현재 후보/표시/전투력 조회→cursor 검증→페이지 응답을 수행한다. 읽은 뒤 다른 요청에서 발생한 권한 변경까지 소급 막는다는 보증은 하지 않는다. 다음 페이지·검색은 다시 현재 권한을 검사한다.

## 3. 응답·정렬·빈 후보·페이지

최상위는 `group_id,filter_context_token,scope_digest,candidate_token,evaluated_at,groups,next_cursor`이며 모두 필수, next_cursor만 nullable다. 이름 groups는 **회원별 묶음 목록**이며 각 원소는 `member_ref,alias,display,continues_from_previous,continues_on_next,characters`다. alias는 `{group_id,group_membership_id}`이며 단일 그룹 FilterContext의 aliases 원소와 정확히 대응한다. 여러 원정대가 섞여도 한 회원 묶음이다. 시간은 UTC RFC3339다.

- 회원은 group_membership_id UUID 정규문자열 ASC. 이름·대표표시명으로 합치거나 정렬키를 만들지 않는다.
- 회원 내부는 저장 item_level을 Decimal 수치 DESC/null LAST→character_id 정규 UUID ASC. `"999.9"`와 `"1000.0"`을 문자열로 정렬하지 않는다. 값은 유한한 비음수 십진 문자열만 허용하고 잘못된 기존 값은 null이다.
- 논리행은 각 후보 캐릭터1개, 후보0인 현재 회원은 empty marker1개다. 전체 정렬 후 limit+1행을 읽고 페이지를 자른 뒤 회원별로 묶는다. 따라서 큰 회원 묶음은 페이지 사이에서 나뉠 수 있다. 같은 member_ref 묶음은 플래그대로 이어 붙이고 character_id로 중복 검사한다. 빈 회원도 characters=[]/두 플래그false로 한 번만 표시하며 회원 전체 조건(character_ids=[])은 선택 가능하다. 전체 group가 비정상 상태일 때 정상 빈 목록으로 숨기지 않는다.
- 다음 페이지로 이어지는 회원은 continues_on_next=true, 앞 페이지에서 이어진 회원은 continues_from_previous=true다. 중간 조각은 둘 다true일 수 있다. 페이지의 논리행 수 합계는 limit 이하이고 후보 배열/회원 묶음을 묵시적으로 잘라 완료로 표시하지 않는다. 전체 페이지 조회를 화면 진입에 강제하지 않으며 사용자 명시 더보기를 사용한다.
- cursor는 조회자·세션 식별의 불투명 digest/그룹·context scope·candidate_token·limit·마지막 순번에 서명 바인딩한다. raw user/account ID·미공개 정렬 원천을 평문에 넣지 않는다. 다른 actor/session/group/limit 또는 손상/위조는400 INVALID_REQUEST, 같은 요청의 후보 세대 변경은409 CURSOR_STALE. 다음 페이지는 동일 filter_context_token/limit을 유지한다.

## 4. 캐릭터와 전투력 DTO

`CandidateCharacter`의 전 필드는 필수이며 nullable를 명시한다.

| 필드 | 타입·출처 |
|---|---|
| character_id | canonical UUID. 검색 member_conditions[].character_ids의 원문 |
| server_name / character_name | 현재 canonical Character의 string |
| class_name | 저장 Character.summary.class_name string/null |
| role_family | dealer/support/null. **현재 Backend에 직업→계열 분류 원천이 없으므로 초안1에서는null**. selected_role·preferred_role·P1의 저장 역할을 직업 계열로 오인하지 않는다. 아래 소비 질문 참조 |
| item_level | 정상 십진문자열/null. Character.summary의 저장값, 관찰 미상/파싱불가 null |
| item_level_source | stored_character_summary / unavailable. P1 분석 레벨로 대체하지 않는다 |
| summary_fetched_at | Character.fetched_at, UTC |
| ownership_revision / lifecycle_revision | 현재 양의 revision. 타인 selection/쓰기 CAS를 만드는 권한이 아니다 |
| ownership_state / activity_state / lifecycle_state | 각각 owned / selected / active 고정. 상태가 달라지면 후보에서 제외 |
| dealer / support | 각 `CandidatePower`를 항상 제공. 다른 역할 값으로 대체하지 않는다 |

`CandidatePower={value,source,trust,observed_at,saved_at,power_revision,integrity_status}`. 모두 필수다. source는 `stored_role_success / unavailable / not_disclosed`, trust는 `client_submitted / null`, value는 정상 십진문자열/null, 시간/revision/integrity_status는 nullable다.

- 공개범위 수용 후, 현재 회원+character UUID+**현재 ownership_revision**의 RolePowerSuccess만 사용한다. 값이 있으면 source=stored_role_success/trust=client_submitted이며 source_summary의 integrity_status도 보인다. 서버/provider 보증치로 표시하지 않는다. analyzed build/각인/장비/issues 원문은 응답하지 않는다. 실패 후 보존된 성공값을 최신 성공 관찰로 제공하되 saved_at/observed_at으로 시점을 구별한다. 낮아진 최신 성공도 그대로 사용한다.
- 해당 역할의 성공 원천이 없으면 value/source= null/unavailable, 나머지 nullable 필드도null. dealer가 없다고 support를 복사하거나0을 만들지 않는다. 비공개 정책이 적용되면 source=not_disclosed와 전 값null로 **원천 없음과 구분**한다. 초안1은 위에 한정한 수치 공개를 제안하며 캐릭터별 추가 비공개 설정을 이미 구현했다고 가정하지 않는다.
- RolePowerSuccess 관찰의 observed_lifecycle_revision이 현재 Character.lifecycle_revision과 다르면 unavailable로 한다. 소유수명/퇴역 캐릭터의 이전 값을 다시 공개하지 않는다. 후보의 최신 저장표시가 실제 게임 현재치라는 보증은 없다.

**계열 소비 질문:** 현재 Backend는 직업별 dealer/support 분류표를 저장하지 않는다. Flutter가 기존 직업 카탈로그로 class_name의 계열을 표시할 수 있다면 초안1 role_family=null을 그대로 소비하고 해당 카탈로그 버전을 기록한다. 서버 분류가 필수면 기존 Flutter의 분류 원천/버전을 Issue에 공유해 공통 매핑·미지원직업null 규칙을 계약에 고정한다. 소스를 로컬에서 찾아 읽지 않으며 게임 직업을 Backend가 추정해 신규 분류하지 않는다. 이 한 항목은 명시 미결정이고 DTO나 역할별 전투력 저장 출처와 혼동하지 않는다.

## 5. 후보 세대·검색과 연결

candidate_token은 별도 domain의64hex HMAC다. actor/session digest·단일 group/context scope와 **전체 후보 집합**의 회원 상태/활성등록·소유/활동/NameClaim/생명주기 근거 및 허용 표시/전투력 값·revision을 canonical 정렬해 결합한다. offset/limit/evaluated_at만의 변경은 세대를 바꾸지 않는다. 개인 원본/회원 매핑을 토큰 본문에 넣지 않는다. 시간 TTL만으로 권한을 유지하지 않는다. 세대 지문 계산은 전체 scope를 배치 조회하며 API 결과를 N+1로 채우지 않는다. 구현 때 최대 규모의 SQL/rows/bytes/지연을 측정하고 페이지 최대100/응답 최대1MiB(JSON UTF-8) 초안 상한을 검증한다. 초과는413 RESPONSE_TOO_LARGE이며 후보를 조용히 누락하지 않는다.

POST `/v2/raid-rooms/search`에 optional `group_character_candidates_token:string(64hex)`을 **추가 제안**한다. 생략은 기존 동작, 명시null은400이다. 기존 정렬/그룹OR·회원AND·회원 내 캐릭터OR·현재T 검색/서버 페이지 의미는 그대로다. 기존 FilterContext/member_ref의 의미·반환 토큰을 바꾸지 않는다.

- 새 후보 UI에서 비어 있지 않은 character_ids를 보내면 이 토큰을 함께 보낸다. group_ids는 후보의 단일 그룹, filter_context_token은 동일 단일 그룹 context여야 한다. member_conditions는 그 context의 refs이며 각 character_id가 **그 member_ref의 현재 후보**인지 검증한다. 다른 회원의 캐릭터/다른 그룹의 ref/중복UUID는400 INVALID_REQUEST, 후보 세대가 달라졌으면 아래409로 처리한다. current 후보 검증 뒤에도 실제 target 방의 그 회원 assignment 조건을 SQL에서 적용한다. 후보에 있다는 이유로 새 참가나 실제참가i를 만들지 않는다.
- candidate_token을 보내지 않는 기존 소비는 현재 정책을 유지한다. 과거 선택 캐릭터에 대한 가시 방 검색을 하던 기존 요청을 새 소유 조건으로 소급 변경하지 않는다. 새 후보 UI는 token 생략으로 stale 처리를 우회하지 않는다. 기존 경로 자체가 타인 roster 원문을 노출하는 것은 아니다.
- token을 보낸 경우 character_ids=[]만 있는 회원 전체 검색에도 검증한다. 그룹/회원 변경은 context부터, 후보만 변경되면 후보 첫 페이지부터 재취득한다. 재취득 시 명시로 고른 UUID가 같은 ref의 새 후보에 남는지 확인하고, 사라진 선택은 안내·쓰기/해당 검색 보류한다. 이름 매칭/다른 UUID 대체/빈배열 자동전환은 금지한다. 선택 없음을 자동으로 회원 전체 검색으로 넓히지 않는다.
- group_ids 변경/다중그룹 전환은 이 후보 토큰을 폐기한다. 다중 그룹 회원 전체 필터는 기존 계약 그대로 사용할 수 있지만 이 신규 단일 그룹 후보 토큰을 재사용하지 않는다. C↔N 전환 자체는 후보 세대를 바꾸지 않고 검색만 새 target로 수행한다. 계정/세션/환경 전환·로그아웃은 후보/선택/페이지를 폐기하며 늦은 응답을 반영하지 않는다.

## 6. 오류와 재취득 순서

| 상황 | HTTP / code | 다음 동작 |
|---|---|---|
| 무인증/잘못된 access | 401 / 기존 인증 code | 기존 정상 로그인 처리 |
| 정지된 조회 회원 | 403 / 기존 회원상태 code | 기존 회원 처리 |
| 그룹 없음/종료/현재 조회 membership 없음 | 404 / GROUP_NOT_FOUND | 해당 그룹 후보·선택 폐기, 정상 빈 결과로 숨기지 않음 |
| group revision/members_revision/alias 변경 | 409 / FILTER_CONTEXT_STALE | context→후보 첫 페이지→명시선택 재대조 |
| 입력/다른 scope cursor/ref·캐릭터 조합 위조 | 400 / INVALID_REQUEST | 자동 재시도 없음 |
| 후보 세대 변경된 다음 페이지 | 409 / CURSOR_STALE | 이전 후보 페이지를 혼합하지 않고 첫 페이지부터 |
| 검색 시 group_character_candidates_token 불일치 | 409 / GROUP_CHARACTER_CANDIDATES_STALE(신규) | 후보부터 재취득 후 선택 대조, 한 번만 자동 읽기 재시도 |
| payload 초과 / 저장소 장애 | 413 / RESPONSE_TOO_LARGE, 503 / SERVICE_UNAVAILABLE | 일부 성공/0명 정상으로 은폐하지 않음 |

동시 변경의 판정 우선순위는 인증→현재 그룹 접근→context→후보/cursor→입력 대상 결합→검색이다. 대상 회원만 탈퇴하면 context stale, 조회자가 탈퇴하면404. 대상 등록/활동/소유/claim/lifecycle 변경은 후보 token을 바꾼다. 표시/레벨/역할 성공 원천 변경도 페이지 일관성 때문에 후보 token을 바꾸며 이전 페이지와 합치지 않는다. 원래 검색 cursor도 새 token 포함 전체 요청에 바인딩한다.

## 7. 합의 후 구현·검증 및 완료 조건

1. Flutter가 §1 공개범위·§4 nullable/역할 출처·계열 미결정·§3 페이지 조각·§5 추가 검색토큰을 대조한다. 동일 두주차 정책 재채택/기기시험을 요청하는 것이 아니다.
2. Backend는 새 읽기 router/닫힌 DTO/allowlist·권한·배치 원천·cursor/token·검색 optional 확장을 구현한다. 원천 테이블을 재사용하므로 현재 설계에는 DDL/개발자료 변경이 없다. 기존 기본0023 앱에 신규 endpoint를 임의 등록하지 않고 실제two-cycle profile에 반영한다.
3. 격리 PostgreSQL/HTTP로 비회원/탈퇴/재가입·명의이전/NameClaim·활동변경·suspect/퇴역·타인 ref/UUID/다른 세션 cursor·0후보·회원경계 페이지/수치정렬·역할NULL/성공보존·stale 후 검색·기존 검색 회귀·READ ONLY/실행 계약 일치를 검증한다. 최대 규모/배치 측정으로 초안 상한을 확인한다.
4. 검증된 작업 구간 commit/push·원격 확인 후 개발 서버 반영/실행 계약 확인 및 소비SHA·경로·예시를 같은 Issue에 인계한다. 그전에는 이 문서를 소비 가능한 서버라고 안내하지 않는다. Flutter 후보 부분 연결·자동 검증과 실제 정상인증/기기·F3 전체 완료는 각각 따로 기록한다.

현재 완료는 **후보 출처 공백 확인·보완 계약 초안/합성 wire 검증·협업 게시**다. 구현/서버 반영·새 endpoint HTTP·DB 시험·Flutter 소비/실기기 인수는 미완료다.
