# Issue #13 — F6 현재주 재개 일정 확인 계약 제안 1

2026-10-23 / Backend / `feat/raid-recruitment` / **계약 제안 당시 기록**.

> [Flutter120](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356264877)이 아래 세 소비 방식을 모두 수용했다. 합의 후 구현/검증·실행 인계 상태는 [개발 안내](ISSUE_13_WEEKLY_RESUME_REVIEW_DEVELOPMENT.md)를 따른다. 아래의 미합의/미구현·검토요청 표기는 제안 당시 기록이다.

[Flutter115 질문](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355333496)·[Backend116 확인](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355428620)에 대응한다. 기준은 게시된 구현 `07c2b671d67e5dfcef5f873ef55ffcb54f87b365`다. 아래는 새 제안이며 현재 실행 OpenAPI/168경로·DB0029·기본0.4.1/policy4·서버/키를 변경하지 않는다. 구현/실제 서버 시험 요청이 아니다.

## 1. 범위와 재사용 경로

현재주 재개의 **생성 전 확인 → 제안 원본 확인 → 응답**을 하나의 확인 흐름으로 보완한다. 별도 endpoint를 만들지 않고 기존 두 경로를 확장하는 안이다. 일정 배열을 GET URL로 보내지 않는다.

| 기존 동작 | 제안하는 확장 |
|---|---|
| POST `/v2/raid-rooms/{room_id}/weekly-resume-proposals` | `?preview_only=true`는 기존 Resume 본문을 읽어 생성 전 미리보기만 반환. query 생략/false는 기존 제안 제출 |
| GET `/v2/me/raid-rooms/{room_id}/plan` | `include_resume_display=true`일 때 weekly_resume 제안 각각에 `resume_review` 추가 |
| POST `/v2/raid-schedule-proposals/{proposal_id}/responses` | 보호된 재개 제안에 응답할 때 optional `resume_context_token` 사용 |

두 query는 문자열 `true|false`만 허용한다. 기본false이며 빈값/null/다른값/중복은400이다. 다른 경로나 일반 일정 제안에 flag/새 필드를 확장하지 않는다. **이 POST preview 방식의 소비 가능 여부를 협의한다.**

### 생성 전 POST preview

- 본문은 현재 Resume의 필수 CAS·실제T·`schedule_groups`를 그대로 사용한다. `resume_context_token`은 포함하지 않는다(포함 시400).
- `schedule_groups=null`은 서버가 현재 유지할 의도를 해석한 결과, `[]`는 명시적으로 일정그룹 없음이다. null과[]를 서로 바꾸지 않는다. 명시 배열도 같은 preview에서 검증한다.
- 인증·현재T/참가/공대장·함께하기·중단 source 조건은 기존 생성 권한 안에서 검사한다. N이나 다른 세대의 재개로 바꾸지 않는다. 잘못된 요청/권한은 기존400/401/403/404/409 경로로 거절한다.
- READ ONLY/REPEATABLE READ로 수행한다. Proposal/Vote/command 원장·새 Round/Assignment/Session·동의/예약을 **생성하지 않는다**. 내부 DB 검증을 위해 생성 후 rollback하는 방식도 사용하지 않는다.
- preview에는 Idempotency-Key가 필요 없다. 제공했으면 UUID4/중복 header 형식만 검증하며 명령 원장에는 저장하지 않는다. 생략/false 제출에는 기존처럼 key가 필수다.
- 성공200은 `{scope: 기존 Scope, data: {kind:"weekly_resume_preview", resume_review: ResumeReview}}`다. `scope`는 현재 source cycle/revision이며 가짜 proposal/session UUID를 발급하지 않는다. 실제 제출 ACK는 기존 Ack 그대로다. query에 따라 두 응답을 구분하고 OpenAPI에는 두200형태를 명시한다.

## 2. 읽기 DTO

모든 새 객체는 additionalProperties=false다. 아래 표의 필드는 별도 optional 표기가 없으면 필수이며 nullable은 명시null을 포함한다.

`ResumeReview = {display: ResumeDisplay, confirmation: ResumeConfirmation|null}`.

`ResumeConfirmation = {context_token: string(1..4096), issued_at: UTC datetime, expires_at: UTC datetime}`. 유효기간은 최대120초·현재주 종료 이전이다. confirmation=null은 확인 가능한 신규 응답 권한이 없다는 뜻이며 token을 추정하지 않는다.

### ResumeDisplay

| 필드 | 타입/의미 |
|---|---|
| version | literal 1 |
| status | ready / stale / legacy_unverifiable |
| room_id, room_cycle_id | UUID, 해당 실제 방/cycle |
| target_cycle_key, target_generation | canonical C key / 현재 동일 generation의 양의int |
| proposal_id | UUID 또는null. 생성 전은null |
| proposal_revision, proposal_plan_revision | 양의int 또는null. 생성 전은null |
| origin | explicit / retained / legacy_unknown. null 해석과 명시 배열의 출처를 보존 |
| settings_revision | 고정한 target settings revision. 기존 제안에서 입증 불가하면null |
| basis_revision | 고정 일정/설정/원천의64hex digest. 기존 제안에서 입증 불가하면null |
| display_revision | 현재 actor/flow·고정 근거·표시 영향/권한을 결합한64hex digest |
| items | ResumeItem[] |
| groups | ResumeGroup[] |
| effect | ResumeEffect |
| permission | 기존 Permission `{allowed,reason,next_change_at}`; token 유무와 실행가능 여부를 구별 |

ready는 표시 근거가 갖춰졌다는 뜻이지 재개가 이미 적용됐다는 뜻이 아니다. pending/적격/유효한 source에만 confirmation을 발급한다. applied/obsolete도 저장된 근거는 표시하되 permission=false·confirmation=null이다. pending 중 고정 근거와 현재 source/설정이 어긋나면 stale·permission=false(`PROPOSAL_CONTEXT_CHANGED`)·confirmation=null이며 새 제안이 필요하다.

GET opt-in의 확장 위치는 `data.proposals[i].resume_review`이며 **kind=weekly_resume일 때만** 존재한다. true면 각 재개 제안에 반드시 제공한다. 생략/false에는 새 필드가 없고 명시null도 넣지 않는다. 일반 일정 제안에는 추가하지 않는다. 기존 plan 접근 권한을 유지하고 더 넓은 조회 권한을 주지 않는다. 표시 가능과 응답 가능은 별개다.

### ResumeItem

`{item_id, source_round_id, raid_id, difficulty_id, catalog_version, duration_minutes, duration_source}`.

IDs는 실제 source item/중단 round UUID다. duration_minutes는 고정한 양의 분/int 또는null(legacy 미입증), duration_source는 근거 문자열 또는null이다. item_id UUID ASC로 정렬한다. 이름은 기존 catalog에서 raid_id/difficulty_id/catalog_version으로 표시하며 다른 회원 캐릭터/제출표·예약 원문을 추가 공개하지 않는다. 여기의 source_round_id를 적용 후 새 round ID로 사용하지 않는다.

### ResumeGroup / ResumeAlternative

Group:
`{group_ref, planning_mode, occurrence_mode, day_scope, required, auto_confirm_additional_members, alternatives}`.

- group_ref는64hex opaque 표시키. planning/occurrence/day_scope/required/auto_confirm_additional_members는 해당 고정 의도의 기존 의미/nullable 타입 그대로다.
- Alternative: `{alternative_ref, weekday, starts_local, leader_latest_start_local, item_ids, session_id, starts_at, ends_at, time_state, materialization}`.
- alternative_ref는64hex, weekday1..7, local 시각은기존HH:mm 또는null, item_ids는 해당 의도의 **순서를 유지한** UUID배열이다. groups/alternatives는 ref ASC, item_ids 순서는 바꾸지 않는다.
- session_id는항상null이다. 실제C의 날짜와 고정 duration으로 UTC starts_at/ends_at을 계산한다. 수요일00:00~05:55는 그 주차의 끝 날짜로 계산한다. 종료시각은 기존 duration 정책·구간검사를 따르며 임의 기본값으로 채우지 않는다.
- time_state는 bounded(시작/끝)/start_only(시작만 입증)/undetermined(둘 다null). legacy start_only는 과거 duration을 현재 설정에서 추정하지 않기 위한 표시다. 신규 수동 일정의 적용에 필요한 duration/구간 근거가 없으면 confirmation을 발급하지 않고 기존 도메인 오류로 거절한다.
- materialization은 on_apply(수동each 또는단일one_of), after_group_selection(수동복수one_of), after_coordination(조율), not_scheduled(미지정)다. 조율/미지정은 미리 시각을 확정하지 않는다. any_current_cycle 조율의 alternatives=[]와 groups=[]도 정상이다. groups=[]는 일정/시간동의 없음이며 실제 재개 대상 자체가 없다는 뜻은 아니다.
- refs는 UI 연결키이며 POST에 넣지 않는다. 적용 ACK 뒤 권한 있는 현재T plan에서 실제 새 ID를 읽고 이름/순서로 preview와 매칭하지 않는다.

### ResumeEffect

다음 필드는 전부 필수다.

| 필드 | 타입/의미 |
|---|---|
| eligible_count, accepted_count, required_votes | 현재 서버 집계 int. 생성전 accepted_count=0, 생성후 제안자표 반영. 적용후는 적용 receipt 집계 |
| new_round_count, new_assignment_count | 현재 source로 예상하는 새 개수. applied는 적용근거 기준 |
| completed_preserved_count | 보존되는 완료 Assignment 개수 |
| superseded_proposal_count | 제출로 대체될 기존 pending 재개제안 개수. 저장 후는 제안 당시 대체 개수 |
| creator_accept_on_submit | 2명 이상 제출 시 제안자accept 여부 bool. 저장 후는 당시 방식 |
| my_immediate_session_count_on_accept | 해당 actor가 수락하고 적용될 때 즉시 시간동의 대상이 될 수동실제세션 수. 실제생성/예약성공 보장은 아님 |

legacy에서 고정 근거 없이는 입증 불가능한 effect 값은null이다. eligible/accepted/required는 기존 집계를 계속 제공한다. 수치는 회원 개인정보/개별 투표원문으로 확장하지 않는다.

**현재 정책을 그대로 설명한다:** 적용 시 현재 유효한 중단 대상의 참가관계가 재연결될 수 있다(거절/미응답자를 자동 탈퇴시키는 투표가 아님). 수락자의 실제 해당 수동세션 참가분만 새 시간동의/예약이 가능하고 거절/미응답은 자동 시간동의하지 않는다. 복수후보/조율 등은 이후 별도 확정이 필요하다. 집계/현재 영향은 읽기 시점 값이며 불변 제안 입력과 구별한다. 최종 대상/자격/정족수/주차·시각은 적용 때 서버가 다시 검사한다.

## 3. 제출·응답 binding과 저장

### 신규 제안 생성

1. Flutter가 제출할 기존 Resume 본문을 먼저 복사한다. 같은 본문으로 preview_only=true를 호출한다.
2. 반환 일정/미정·영향·제안자accept를 확인한다. `confirmation`이 있을 때만 동일 본문에 `resume_context_token`을 추가해 query 생략/false로 제출한다. 새 Idempotency-Key를 사용한다.
3. 서버는 token을 actor/room/C/cycle/generation·flow=create·resume_context_token을 제외한 원본문의 정규화hash(null/[]/item순서 구분)·고정설정/해석그룹·source rounds/assignments/회원rev·supersede 대상·집계/권한·기존CAS에 결합하고 제출 때 다시 대조한다. 큰목록은 token에 싣지 않고 digest로 묶어4096bytes 이하를 유지한다.
4. 새 제안 content에 `review_version=1`, origin·정규화된 그룹·시각/duration/카탈로그/설정근거·source/확인근거 digest와 필요한 영향근거를 고정한다. 기존 JSONB의 새 버전으로 표현하며 추가DDL은 계획하지 않는다. 기존 불변 trigger를 해제하거나 과거 행을 갱신하지 않는다.
5. 2명 이상이면 검증된 생성 확인에 근거해 기존 제안자accept를 기록한다. 1명이면 기존대로 제안기록 후 **별도 본인응답**이다. 생성 ACK는 recorded이며 적용 성공으로 표시하지 않는다.

### 신규 제안 응답

- GET plan?include_resume_display=true에서 해당 제안의 resume_review를 읽고 확인한다. 기존 Respond 본문에 `resume_context_token`만 추가한다. 새 필드는 optional/non-null string1..4096이며 기존 숫자CAS는 그대로 필요하다.
- token은 actor/room/C/cycle/gen·flow=respond·proposal ID/두revision·basis/display digest·현재 target/CM revision·현재 eligible/assignment/집계/권한을 결합한다. accept/reject **둘 다** 같은 확인근거를 요구하며, response 자체는 기존 command 본문/key에 결합한다.
- 기존 일반 일정 제안에 이 token을 보내면400이다. create/다른제안/다른사람 token 교환도400 CONTEXT_INVALID다. expired 새명령은409 COMMAND_CONTEXT_EXPIRED, 현재CAS 변경은 기존 REVISION_CONFLICT/TARGET_CONTEXT_STALE, 고정근거 변화는409 PROPOSAL_CONTEXT_CHANGED로 거절한다. 서버시각/발급/만료/token 자체는 display_revision에 넣지 않는다.
- 신규 보호 제안의 설정·duration/중단round·assignment 핵심근거가 달라지면 새 제안을 요구한다. 현재 설정으로 고정된 끝시각을 조용히 바꾸거나 과거 설정으로 현재 DB를 덮어쓰지 않는다. 새판 적용은 고정근거를 사용하고 현재 핵심설정 일치도 검사한다. 현재 적격자 감소/정족수 재평가의 기존 정책은 유지하되 현재 영향·자격/CAS를 최신 확인에 결합한다.
- 원 성공 ACK는 현재 token 만료·제안상태·주차/자격 재검사보다 먼저 기존 실행원장에서 복구한다(현재 인증은 유지). 결과불명은 원method/path/body/key/token 그대로 재송한다. 확정된 stale/expired 거절만 재조회·재확인·새key로 새명령을 만든다. 성공여부 불명 상태에서 새token/body로 같은key를 덮지 않는다.

## 4. 기존 소비·미결 요청 호환 경계

- query 생략/false의 GET plan 응답과 기존 command-context/다른context/일반 일정응답은 유지한다. 새 optional 본문 필드는 생략과 명시null을 구분하며null은400이다. token 미지정의 구본문을 직렬화/command fingerprint에 새null 필드로 채우지 않아 기존 미결payload hash도 보존한다.
- 새token 없이 생성하는 구 Resume 요청은 기존 경로를 보존하며 구형 content로 기록한다. 구형 제안의 기존 응답/미결 원본문·원ACK도 보존한다. 새 token이 있다가 유효성검사에 실패한 요청을 구경로로 내리지 않는다.
- **review_version=1 제안은 새 응답마다 token 필수다.** 구클라이언트의 token 없는 새응답은400 CONTEXT_INVALID로 거절된다. 신규 보호 제안과 구클라이언트 새명령 사이에 이 소비 제약이 있음을 명시한다. 모든 구클라이언트가 새 제안에 계속 쓸 수 있다고 약속하지 않는다. 이 배포/소비 경계를 Flutter가 확인해야 한다.
- 이미 저장된 구형 content에는 원문그룹은 있어도 당시 settings/duration/출처 전체를 입증할 수 없다. `status=legacy_unverifiable`, basis/settings=null·confirmation=null, permission=false(PROPOSAL_CONTEXT_CHANGED)로 보이고, 입증 가능한 원문/시작만 표시한다. 새 Flutter는 해당 제안에 수락/거절을 새로 보내지 않고 공대장에게 보호된 새제안 생성을 안내한다. 구형 제안에 새token을 붙이는 것은400이며 자동 덮어쓰기/재제안·과거자료 삭제는 없다. 명시 새제안의 기존 supersede 규칙은 유지한다.
- 응답 전체 UTF-8 JSON이1MiB를 넘으면413 RESPONSE_TOO_LARGE다(GET 전체plan 포함). 기존 요청32KiB 한도는 유지하며 제출은 token 포함 전체본문 기준이다. 초과는413 REQUEST_TOO_LARGE, 절단/false 자동재조회 없음·새 preview 개수 제한 추가 없음. 모두 no-store다.

## 5. 소비 흐름 예시

다음은 순서 예시이며 실제token/회원자료가 아니다. 정확한 Resume/Respond의 나머지 필수CAS는 기존DTO 그대로다.

```text
제안자: 기존 Resume 본문 복사(schedule_groups=null 또는 명시배열/[])
 → POST weekly-resume-proposals?preview_only=true (Key 불필요, 쓰기0)
 → data.kind=weekly_resume_preview / data.resume_review 확인
 → 같은 본문 + resume_context_token / preview query 제거 / 새 Key 제출
 → ACK outcome=recorded (N>=2 제안자accept 기록, N=1 별도응답)

응답자: GET 현재T plan?include_resume_display=true
 → kind=weekly_resume인 proposals[i].resume_review 확인
 → 기존 Respond + resume_context_token / 새 Key
 → ACK outcome=recorded 또는 applied
 → applied 후 현재T plan 재조회, 새 실제ID/본인동의상태 표시

stale/legacy/confirmation=null: 새 응답 차단, 사유 표시/명시 재확인·필요시 공대장 새제안
결과불명: 원 POST/body/key/token 재송, 원ACK 우선
```

정적 날짜예: C=2026-10-21 / 월요일20:00 KST·고정60분이면 시작2026-10-26T11:00:00Z·끝12:00Z다. 같은C의수요일00:05는2026-10-28T00:05 KST(2026-10-27T15:05Z)다. N 개방 미리보기처럼 다음주 key/generation을 만들지 않는다.

## 6. Flutter에 필요한 검토·완료 조건

1. 별도endpoint 없이 기존 POST의 preview query/읽기전용200 응답을 구별하고, 기존 Resume 본문을 복사해 생성확인에 재사용하는 방식이 가능한지 확인한다. preview는Key불필요·제출은Key필수인 점도 포함한다.
2. GET plan opt-in의 제안별 resume_review DTO·legacy/stale 차단·null과[]·제안자accept/별도본인응답·참가재연결과시간동의 구분을 소비할 수 있는지 확인한다.
3. 새 보호제안에는 응답token필수/구클라이언트token없는새응답거절, 구형 제안은 새Flutter에서명시재제안안내라는 호환 경계를 확인한다. 미결 원본문/key·원ACK는 유지한다.

세 가지의 수용/구체적인 소비상 차이만 회신하면 된다. 같은 F5 시험/기존 정책 재검증이나 이번 단계 실제 구현/서버시험을 요청하지 않는다. 합의 뒤 Backend가 schema/구현·격리 권한/상태변경·ACK/호환·크기검증→구간commit/push·원격확인→개발실행/소비SHA를 인계하고, 그 뒤 Flutter가 현재주 재개 UI/응답을 연결한다. [Flutter117 F6-A](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355764602)의 660433d commit/push·단일108mock PASS/분석0 보고는 유지한다(Backend 독립재현 아님). 다음 F6-B 완료/미완료종료 설계·범위준비는 이 재개 협의와 분리하며 F6-A 승인을 B/C 구현승인으로 확대하지 않는다.

정정 범위는 Backend116 그대로 manual 근거해제만이며 완료취소/참가·예약복구 역명령을 추가하지 않는다. F6/실회원·기기·성능·운영인수 완료를 뜻하지 않으며 Issue는 OPEN이다.

정적 대조: 제안에 재사용하는 기존3경로를 router AST/실행 OpenAPI와 대조했고 기존 Resume/Respond/BResumeProposal 필드 및 새표시 미구현 상태, 검토소스/실행계약의 소비07c2b671 바이트일치를 확인했다. 기존 local_start 함수의 AST로 위 KST 날짜2예를 검산했다. HTTP/DB/토큰·원ACK/동시성/크기 동작을 실행 검증한 결과는 아니다.
