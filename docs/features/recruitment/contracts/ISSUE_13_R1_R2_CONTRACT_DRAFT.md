# 모집 R1/R2 상세 계약 초안

2026-10-19 / Backend / 제안 당시 `feat/group-management`, 코드 기준 `349fb79`. 현재 모집 작업은 이 기준에서 분기한 **`feat/raid-recruitment`**(로컬·미push)로 옮겼으며 게시된 제안 원문/구현 범위는 그대로다.

후행 상태: F1 내부기반을 구현·격리검증했다. [결과안내](../development/ISSUE_13_F1_FOUNDATION.md)·[#13 전체13번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259515470). 아래는 계약 제안 원문이며F1 내부모델/명령이곧사용가능HTTP계약인것은아니다.

공식 제안 원문: [#13 전체12번째 Backend — 상세 계약 설계·게시](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924). 다음 담당은 Backend F1 내부기반 구현과 Flutter Q1~Q3의 기존 소비 충돌 확인이다. 문서 게시와 원격 Git 게시를 구분한다.

**구현 전 설계 제안이다.** 신규 실행 API/OpenAPI·DB는 변경하지 않았다. [작업 구간](../planning/ISSUE_13_R1_R2_WORK_SCOPE.md), [#13 전체11번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259204298) 이후 상세 산출물이다. 아래 경로/DTO·오류·운영 상한과초기지원부분집합은 Backend 설계안이며 Flutter 수용/실연동 완료로 표시하지 않는다. 제품 확정 기준과 아래 검토 항목을 구분한다. 원문은 #13에 게시하며 로컬 문서는 F1 구현 `9664fb4` 이후 설계·진행 기록 커밋에 포함하며 미push다.

## 1. 확정 정책·지원 단계

기준은 #13 본문·[전체1번째 i 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232280402)·[전체6번째 한도 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232799560)·[전체10번째 독립 진행](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259125080)이다. 카탈로그/주차·현재 소유/활동·개인 역할요약·G1/G2/G3·공통한도·개인주간 원장을 재사용한다.

| 동작 | 이번 설계 | 상태/제외 |
|---|---|---|
| R1 조회·생성/생성자 확정참가 | 현재 주차·단일 회차·공개/그룹, 유한 일정 | 상세 API/DB 구현 전 |
| R2 참가 | 파티장 승인형 `leader_only`, 즉시가입 `direct_join` | 다중동의/anyMember/quorum은 미지원 제안 |
| 최소 회복 | 본인탈퇴·파티장즉시이전·마지막1인종료 | 쓰기 공개 전 함께 제공할 계약, R3 전체 아님 |
| R3 고급관리 | 캐릭터교체/추방/자리이동·방간스왑 | 후속 명세/구현. 기존 소멸 캐릭터 자리 보존 |
| R4 | 전체완료/반복·공개전환/다른 그룹 연결 | 완료권한 충돌 등 별도, 임의 확정하지 않음 |
| 실제 통계·V2 영향·G3 해산 | 원천/연결 경계만 식별 | 집계/worker·V2 보류해제·해산 쓰기 미포함 |

한 앱회원은 방당1자리다. 생성자도 한 번만 집계하고 다원정대/캐릭터를 다른 회원으로 보지 않는다. 4인당 support1/dealer3, 당별 dealer 동일직업1을 상한으로 검사하며 8인은2개 당이다. 모집중 일부 자리만 채워져 있어도 이 상한을 검사하며 아직 부족한 서포터를 이유로 방 생성 자체를 막지 않는다. 역할 선택은 사용자의 dealer/support 선택이지 서버 소유권 증거가 아니다.

## 2. 별도 객체와 시간

- `room_id`: 모집방 UUID, 단일 현재 파티장 membership 참조·공개범위/그룹 귀속·생성시각. 이름/게임서버는 신원키가 아니다.
- `round_id`: 방의 특정 레이드/난이도/주차 회차 UUID. R1/R2 최초지원은 방당 한 회차이며 R4 반복을 구현했다고 하지 않는다.
- `membership_id`: 앱회원의 방 참가 유효구간 UUID. `joined_at` 포함/`ended_at` 제외의 구간이고 탈퇴 후 재가입은 새 UUID다. 같은 방의 활성회원 unique.
- `application_id`: 확정 전 신청 UUID. pending은 자리/주간점유/방수 예약이 아니다. 한 회원/방당 논리pending1개, 다른방 복수 신청 가능.
- 주간 `WeeklyState`: `(user_id,character_id,raid_id,cycle_key)` 단위 점유/완료다. `active_party_id`는 room UUID를 참조하고 active 난이도/가입시각은 점유 시각이다. 이것을 현재 membership으로 재사용하지 않는다. 기존 #11 완료+점유 금지 제약 유지.

현재관계/i는 membership의 유효구간에서 얻고 completion_sources.party_id나 주간점유의 유무로 추정하지 않는다. 향후 완료후잔류/다음주관계도 표현할 수 있지만 R1/R2가 완료·자동다음회차를 제공하는 것은 아니다. 주차가 끝나도 자동탈퇴/방수초기화/개인완료 생성은 없다.

시각은 UTC RFC3339 `Z|+00:00`, 서버 DB `clock_timestamp()`가 기준이다. 주차는 KST 수요일06시 `[starts_at,ends_at)`·현재카탈로그 `cycle_key`다. 일시는 밀리초로 반올림하지 않고 수치는 plain decimal 문자열로 비교한다. 미래주차 생성/과거주차 신규참가는 최초 지원에서 거절한다.

`Schedule`: `{starts_at:datetime|null,ends_at:datetime|null}` 모두 required. 유한일정은 둘 다 nonnull/`starts_at<ends_at`이며 반열린구간이다. A.end=B.start는 비중첩이다. 최초지원안은현재주차내의유한일정/서버현재시각보다미래인끝시각으로제한하며주차를넘는일정은지원보류로분리한다. 이미시작했는지만으로실제게임진행/완료를추정하지않는다. 종료불명/미정은 `unknown`으로 표현하고 동시일정 검토 결과도 unknown이다. **미정 일정을 안전하다고 처리하거나 임의 소요시간을 대입하지 않는다.** 최초 확정참가 쓰기는 유한일정에서 진행하는 지원안을 제안하며 불명 일정 명시확인 흐름은 검토항목 Q1이다. 일정 변경 명령은 이번 없음.

## 3. HTTP 목록·권한

모든 `/v1` 응답 no-store, 오류는 기존 `{error:{code,message,request_id}}`다. Bearer401은 WWW-Authenticate:Bearer를 포함한다. UUID path/body 검증, POST UUIDv4 Idempotency-Key, strict DTO/추가필드·미지원/중복query·GET body 거절을 유지한다. 숫자revision은 strict int>=1, bool/실수/문자열 금지. 미구현 동작의 permissions는 false다.

| Method/path | 권한 | 성공 DTO |
|---|---|---|
| GET `/v1/raid-rooms` | public목록은비로그인가능 제안, group목록은로그인·현재그룹원 | 200 RoomPage |
| GET `/v1/raid-rooms/{room_id}` | public요약 또는현재그룹원group요약 | 200 RoomSummary |
| GET `/v1/me/raid-rooms/{room_id}` | 로그인·현재확정참가자, group은현재그룹자격도필요 | 200 RoomDetail |
| GET `/v1/me/raid-room-memberships` | 본인현재/종료관계, 타회원ID입력없음 | 200 MembershipPage |
| GET `/v1/raid-rooms/{room_id}/admission-context` | 로그인·현재본인character/room조회권한·읽기전용 | 200 AdmissionContext |
| POST `/v1/raid-rooms` | 로그인·본인현재소유/활동·모든생성조건 | 201 RoomCommandAck |
| POST `/v1/raid-rooms/{room_id}/applications` | 로그인·참가자격/조회권한·승인형 | 201 ApplicationAck |
| GET `/v1/me/raid-room-applications` | 본인신청목록만 | 200 ApplicationPage |
| GET `/v1/raid-rooms/{room_id}/applications` | 현재파티장·현재조회권한 | 200 ApplicationPage |
| GET `/v1/raid-room-applications/{application_id}` | 원신청자또는현재파티장·현재조회권한 | 200 Application |
| POST `/v1/raid-room-applications/{application_id}/approve` | 현재파티장·현재조회권한 | 200 RoomCommandAck |
| POST `/v1/raid-room-applications/{application_id}/reject` | 현재파티장·현재조회권한 | 200 ApplicationAck |
| POST `/v1/raid-room-applications/{application_id}/withdraw` | 원신청자·정리권한 | 200 ApplicationAck |
| POST `/v1/raid-rooms/{room_id}/join` | 로그인·즉시가입형·모든최종조건 | 200 RoomCommandAck |
| GET `/v1/me/raid-rooms/{room_id}/management` | 현재본인관계의최소정리정보 | 200 RoomManagement |
| POST `/v1/raid-rooms/{room_id}/leave` | 현재본인일반membership | 200 MembershipEndAck |
| POST `/v1/raid-rooms/{room_id}/leadership-transfer` | 현재파티장·유효현재대상 | 200 RoomCommandAck |
| POST `/v1/raid-rooms/{room_id}/end` | 현재파티장·현재확정본인1인 | 200 RoomEndAck |

파티장은 방이 가리키는 membership 하나가 권위다. 그룹장이라도 방 파티장으로 승격하지 않으며 권한있는 그룹원과 방 참가자를 구분한다. public 상세요약은 private roster/신청명단을 주지 않는다. 비그룹원의 group room 요약/상세는404 `ROOM_NOT_FOUND`, 접근권한이 없는 public private상세는403 `ROOM_MEMBERSHIP_REQUIRED`다. 존재여부를 멱등/신청조회로 우회하지 않는다.

## 4. 조회·페이지·출력 DTO

페이지 기본20/최대50, limit은정수, cursor는불투명HMAC문자열<=2048이다. 생성시각 desc+UUID desc의고정정렬을쓴다. room목록은현재주차이며query는`scope=public|group`(기본public), `group_id`(group일때만필수), `raid_id`, `difficulty_id`(raid_id필수), `state=active|ended|all`(기본active), `limit`,`cursor`만허용한다. `/me/raid-room-memberships`는`state=current|ended|all` 기본current, 신청목록은`state=pending|ended|all` 기본pending이다.

cursor는현재cycle/actor/공개범위/group/필터/limit·해당목록head·권한revision에묶는다. 권한상실을먼저검사하고관련membership/방/신청/논리만료변화시409 CURSOR_STALE로첫페이지부터재조회한다. GET은REPEATABLE READ·쓰기/행생성/만료정리/provider호출0이다. 공개head는공개요약에영향있는변경에만연결하고개인목록head와분리해private신청유무를공개하지않는다.

모든 필드는 **required**, nullable는`|null`로표시한다. UUID는문자열, revision은양의정수다. `Permission={allowed:bool,reason:string|null}`, CharacterDisplay/RoleSummary는기존G1/P1형식이다. policy_snapshot은최종DB검사를대체하지않는불투명지문이다.

| DTO | 필드 |
|---|---|
| RoomSummary | room_id:UUID, revision:int, round_id:UUID, round_revision:int, members_revision:int, title:string, state:active\|ended, phase:current\|cycle_closed\|ended, scope:public\|group, group_id:UUID\|null, raid_id:string, difficulty_id:string, catalog_version:string, cycle_key:date-string, admission_mode:leader_only\|direct_join, schedule:Schedule, party_count:1\|2, member_count:int0..8, support_count:int0..2, leader_display:CharacterDisplay\|null, restricted:bool, created_at:datetime |
| RoomPage | items:list[RoomSummary], directory_revision:int, next_cursor:string\|null |
| BuildDisplay | role:dealer\|support, version:int, summary:RoleSummary\|null, saved_at:datetime\|null, stale:bool |
| RoomMember | membership_id:UUID, revision:int, party_no:1\|2, slot_no:int1..4, room_role:leader\|member, selected_role:dealer\|support, character_id:UUID, display:CharacterDisplay, joined_at:datetime, status:valid\|needs_review, status_reason:string\|null, build:BuildDisplay, is_me:bool |
| RoomLimitIssue | code:string, dimension:raid_rooms\|joined_groups\|group_capacity, used:int, limit:int, member_ref:{membership_id:UUID,display:CharacterDisplay\|null}\|null, origin_group_id:UUID\|null |
| RoomAccess | state:normal\|restricted, policy_snapshot:string, evaluated_at:datetime, issues:list[RoomLimitIssue] |
| RoomDetail | room:RoomSummary, members:list[RoomMember]최대8, my_membership_id:UUID, access:RoomAccess, permissions:{apply,join,approve,reject,leave,transfer_leadership,end,complete,change_character,move_slot,repeat,change_scope}:각Permission |
| MembershipRecord | room_id:UUID, round_id:UUID, membership_id:UUID, revision:int, character_id:UUID, selected_role:dealer\|support, party_no:int, joined_at:datetime, ended_at:datetime\|null, end_reason:left\|room_ended\|null, relation:current\|ended, round_cycle_key:date-string, round_phase:current\|cycle_closed\|ended, access_state:full\|recovery_only\|history_only, group_id:UUID\|null |
| MembershipPage | items:list[MembershipRecord], membership_head:int, next_cursor:string\|null |
| Application | application_id:UUID, room_id:UUID, revision:int, state:pending\|accepted\|rejected\|withdrawn\|expired\|cancelled, created_at:datetime, expires_at:datetime, ended_at:datetime\|null, display:CharacterDisplay, character_id:UUID, party_no:int, selected_role:dealer\|support, build:BuildDisplay, permissions:{approve,reject,withdraw}:각Permission |
| ApplicationPage | items:list[Application], applications_revision:int, next_cursor:string\|null |
| RoomManagement | room_id:UUID, revision:int, members_revision:int, my_membership:{membership_id:UUID,revision:int,room_role:leader\|member}, round_id:UUID, round_revision:int, round_phase:current\|cycle_closed\|ended, transfer_candidates:list[{membership_id:UUID,revision:int,display:CharacterDisplay\|null}], permissions:{leave,transfer_leadership,end}:각Permission |

Application은내부user UUID·전체선택입력의등록/소유정보·타인개인한도원문을노출하지않는다. 신청자는본인신청만,파티장은해당방신청만읽는다. MembershipRecord는본인이력만이며그룹탈퇴후현재그룹명단/다른회원상태를붙이지않는다. RoomManagement의그룹자격상실후최소조회와후보공개범위는Q3제안이며full상세우회가아니다.

## 5. 생성·신청·직접참가 입력

별도표기외모두required. 입력actor/user_id·직업/level/power/display/raw프로필은금지한다. decimal은최대32자/비음수plain문자열이며지수/쉼표/NaN을거부한다.

`Selection`:
- registration_id:UUID, character_id:UUID, selected_role:dealer|support, party_no:1|2
- expected_registration_version:int, expected_ownership_revision:int, expected_roster_revision:int, expected_lifecycle_revision:int, expected_role_summary_version:int
- expected_weekly_revision:int(미저장1), expected_limits_revision:int, expected_usage_revision:int

role_summary_version은현재본인소유수명의선택역할P1요약행CAS(미저장1)다. 없는요약을소유권실패로보지않으며P1의수치/무결성을서버검증증거로승격하지않는다.

`RoomCreateIn`:
- title:string trim1..60/제어문자·줄바꿈금지(상한은Backend제안)
- scope:public|group, group_id:UUID|null, expected_group_revision:int|null, expected_group_membership_id:UUID|null, expected_group_membership_revision:int|null
- raid_id:string, difficulty_id:string, expected_catalog_version:string, expected_cycle_key:date-string
- admission_mode:leader_only|direct_join, schedule:Schedule
- min_combat_power:{dealer:decimal|null,support:decimal|null}, selection:Selection

public은group관련4필드모두null, group은모두nonnull이다. party_no는카탈로그party_count범위다. 파티정원/support/직업상한은카탈로그가정하며client가바꾸지못한다. repeat/완료/사용량/권한role을입력받지않는다. 최소전투력분기의판정근거는Q2다. 양역할문턱null인기반을먼저진행하고문턱이있는분기만근거확정전미지원으로분리하는안이며요구폐기가아니다.

`ApplicationCreateIn` / `DirectJoinIn`: selection:Selection, expected_room_revision:int, expected_round_revision:int, expected_members_revision:int, expected_policy_snapshot:string, expected_cycle_key:date-string, expected_catalog_version:string.

미참가자에게RoomDetail을공개해snapshot을얻게하지않는다. 대신다음본인용조회도제안한다.

`GET /v1/raid-rooms/{room_id}/admission-context`의query는`character_id:UUID`, `selected_role:dealer|support`, `party_no:1|2`, `intent:apply|join`모두필수다. 현재본인character와room조회권한을검사하며타인character404, GET쓰기0이다. `AdmissionContext`={room_id:UUID,round_id:UUID,room_revision:int,round_revision:int,members_revision:int,policy_snapshot:string,catalog_version:string,cycle_key:date-string,selection:Selection,eligibility:Permission,evaluated_at:datetime}로모두required다. 현재본인등록/소유/주간·usage/선택역할의revision을서버DB에서해결한다. context는예약/권한증명이아니며쓰기에서재검사한다. policy_snapshot은해당방진행에영향있는원인/관계revision이고본인자격CAS는Selection으로별도검사한다. 파티장은RoomAccess의같은방지문을쓰되타인선택원문을받지않는다.

apply는논리pending과표시snapshot만만들며slot/weekly/usage를바꾸지않는다. TTL은`min(created_at+24h,cycle.ends_at)`의Backend제안이다. 신청당시본인자격은검사하되pending에정원/개인방한도를예약하지않고확정순간재검사한다. 꽉찬방도승인형pending신청은수용하는안을제안하되신청성공을참가허용으로표시하지않는다. context의intent=apply도이구분을반영하며직접join은정원을검사한다. 같은방논리pending1개/다른방복수신청가능, 전체pending목록의일괄정리에중복확정방지를의존하지않는다.

`ApplicationDecisionIn`(approve/reject): expected_application_revision:int, expected_room_revision:int, expected_round_revision:int, expected_members_revision:int, expected_policy_snapshot:string, expected_cycle_key:date-string. approve는원신청Selection과현재신청자DB상태를검사하며승인자가캐릭터/역할/당을바꾸지못한다. source revision이달라지면409 APPLICATION_CONTEXT_CHANGED로pending을보존하고본인철회/새신청으로새판단한다. reject는원캐릭터현재자격을요구하지않는다.

`ApplicationWithdrawIn`: expected_application_revision:int만필수. 본인원신청정리권한은그룹/캐릭터자격상실로막지않는안이다. 파티장의reject와본인의withdraw를구분하고이전ACK를새로운신청관계의권한으로쓰지않는다.

## 6. 최소 ACK·요청/응답 예시

모두required다. ACK는과거명령성공이고현재관계/권한/주간완료증거가아니다.

| DTO | 필드 |
|---|---|
| RoomCommandAck | room_id:UUID, round_id:UUID, actor_membership_id:UUID, affected_membership_id:UUID, room_revision:int, round_revision:int, members_revision:int, actor_membership_revision:int, affected_membership_revision:int, application_id:UUID\|null, application_revision:int\|null, executed_at:datetime |
| ApplicationAck | room_id:UUID, application_id:UUID, application_revision:int, state:pending\|accepted\|rejected\|withdrawn\|expired\|cancelled, executed_at:datetime |
| MembershipEndAck | room_id:UUID, round_id:UUID, membership_id:UUID, membership_revision:int, ended_at:datetime |
| RoomEndAck | room_id:UUID, round_id:UUID, membership_id:UUID, room_revision:int, round_revision:int, membership_revision:int, ended_at:datetime |

create/join의actor=affected=신규본인membership, approve의actor=파티장/affected=확정신청자, transfer의actor=이전파티장/affected=새파티장이다. application참조는approve때만nonnull이고기타RoomCommandAck는두필드null이다. approve가대상회원의private my_membership/계정자료를반환하지않는다. 성공후현재RoomDetail·본인membership/usage/주간을재조회하고탈퇴후private상세403은정상권한종료일수있다.

가상의생성입력(카탈로그ID/버전은설명용이며실제API값아님):

```json
{
  "title": "예시 모집",
  "scope": "public",
  "group_id": null,
  "expected_group_revision": null,
  "expected_group_membership_id": null,
  "expected_group_membership_revision": null,
  "raid_id": "example_raid",
  "difficulty_id": "example_normal",
  "expected_catalog_version": "example-version",
  "expected_cycle_key": "2026-10-14",
  "admission_mode": "leader_only",
  "schedule": {
    "starts_at": "2026-10-19T05:00:00Z",
    "ends_at": "2026-10-19T06:00:00Z"
  },
  "min_combat_power": {
    "dealer": null,
    "support": null
  },
  "selection": {
    "registration_id": "00000000-0000-4000-8000-000000000001",
    "character_id": "00000000-0000-4000-8000-000000000002",
    "selected_role": "dealer",
    "party_no": 1,
    "expected_registration_version": 1,
    "expected_ownership_revision": 1,
    "expected_roster_revision": 1,
    "expected_lifecycle_revision": 1,
    "expected_role_summary_version": 1,
    "expected_weekly_revision": 1,
    "expected_limits_revision": 1,
    "expected_usage_revision": 1
  }
}
```

가상의join입력(실제자료아님):

```json
{
  "selection": {
    "registration_id":"00000000-0000-4000-8000-000000000001",
    "character_id":"00000000-0000-4000-8000-000000000002",
    "selected_role":"dealer","party_no":1,
    "expected_registration_version":1,"expected_ownership_revision":1,
    "expected_roster_revision":1,"expected_lifecycle_revision":1,
    "expected_role_summary_version":1,"expected_weekly_revision":1,
    "expected_limits_revision":1,"expected_usage_revision":1
  },
  "expected_room_revision":3,"expected_round_revision":1,
  "expected_members_revision":2,"expected_policy_snapshot":"opaque-context-from-server",
  "expected_cycle_key":"2026-10-14","expected_catalog_version":"example-version"
}
```

join성공ACK:

```json
{
  "room_id":"00000000-0000-4000-8000-000000000003",
  "round_id":"00000000-0000-4000-8000-000000000004",
  "actor_membership_id":"00000000-0000-4000-8000-000000000005",
  "affected_membership_id":"00000000-0000-4000-8000-000000000005",
  "room_revision":4,"round_revision":2,"members_revision":3,
  "actor_membership_revision":1,"affected_membership_revision":1,
  "application_id":null,"application_revision":null,
  "executed_at":"2026-10-19T04:00:00Z"
}
```

일반member의최소관리GET예시:

```json
{
  "room_id": "00000000-0000-4000-8000-000000000003",
  "revision": 4,
  "members_revision": 3,
  "my_membership": {
    "membership_id": "00000000-0000-4000-8000-000000000005",
    "revision": 1,
    "room_role": "member"
  },
  "round_id": "00000000-0000-4000-8000-000000000004",
  "round_revision": 2,
  "round_phase": "current",
  "transfer_candidates": [],
  "permissions": {
    "leave": {
      "allowed": true,
      "reason": null
    },
    "transfer_leadership": {
      "allowed": false,
      "reason": "ROOM_LEADER_REQUIRED"
    },
    "end": {
      "allowed": false,
      "reason": "ROOM_LEADER_REQUIRED"
    }
  }
}
```

## 7. 자격·슬롯·한도 guard

1. 현재session/User→room/group조회권한·현재membership→room/round상태·CAS/지문→본인등록/소유/NameClaim/usable→활동선택→카탈로그/난이도입장레벨→선택역할source→주간claim/일정→한도/slot을쓰기transaction에서검사한다. client수치를받아판정하지않는다. 나이스단OFF/수동1700미만/대표/표시count를추가제약으로만들지않는다.
2. 입장level은현재정상provider유래Character.summary와난이도카탈로그를Decimal비교한다. 미상은판정불가이며P1 item_level로덮지않는다. P1의role/source/observed_lifecycle_revision/version·saved_at/stale를표시하되임의P1수치로최소문턱을통과시키지않는다. 보석오류/요약없음/OFF만으로일괄가입금지하지않는다.
3. 선택party의빈slot을낮은번호부터배정하는안을제안한다. 같은당dealer동일직업/support상한·마지막자리는최종확정때다시검사하고실패하면전부거절한다. 동의없이다른role/party로자동이동하지않는다. 최대8명검사와전용head를쓰고무제한pending전체를원자변경하지않는다.
4. 기존`raid_weekly.require_available_for_participation`를재사용해완료/점유를검사하고현재roommembership/slot·WeeklyState점유·usage/head·ACK를같이commit한다. 같은캐릭터/raid/cycle의난이도교차참가/완료를차단하고동일user다른캐릭터의유한일정중첩도검사한다. 새로운별도완료원장은없다.
5. 개인방수는현재membership의room UUID distinct수로계산한다. 생성자중복0/모든원정대합산/종료관계제외/주차무초기화다. 현재그룹가입수와정원은기존원본/현재그룹장한도를쓴다. 생성자와현재파티장을권한원본2개로저장하지않는다.

| 원인 | 제한되는 방 | 전파하지 않을 범위 |
|---|---|---|
| MEMBER_RAID_LIMIT_EXCEEDED | 당사자직접참가공개/그룹방 | 미참가방/기존그룹운영 |
| MEMBER_GROUP_LIMIT_EXCEEDED | 당사자직접참가그룹방 | 공개방/기존그룹운영 |
| GROUP_CAPACITY_EXCEEDED | 해당그룹모든그룹방 | 일반공개/다른그룹 |

정확히10/10·5/5·15/15는기존이용정상/증가만차단한다. 초과관련방은다른회원도참가확정·진행불가, 조회/본인철회·기존권한회복은유지하고관련원인모두해소후정상화한다. group정원원인자가room에없으면RoomLimitIssue.member_ref=null로하며일반그룹명단을공개하지않는다. 조회실패/미연결adapter를정상0건으로보지않는다.

## 8. 최소 회복·그룹 탈퇴·주차 경계

`MembershipCAS`: expected_room_revision:int, expected_round_id:UUID, expected_round_revision:int, expected_members_revision:int, expected_membership_id:UUID, expected_membership_revision:int. leave/end/transfer입력의공통필수필드다.

- leave: 현재일반member본인만. 옛캐릭터자격상실을정리선행조건으로하지않는다. membership종료·slot과그관계에묶인WeeklyState점유만해제·본인usage/head갱신을원자처리한다. 다른room/다른membership의점유·과거party/manual완료는손대지않는다. 현재파티장은409 ROOM_LEADER_TRANSFER_REQUIRED.
- transfer: MembershipCAS+target_membership_id:UUID+expected_target_membership_revision:int. 유효현재member/activeUser로즉시이전·이전자는일반member유지의Backend제안이다. 상대수락/쿨다운을새로추가하지않고group전용새파티장에는현재group자격이필요한안이다. group장의정원한도를파티장에게전용하지않는다. slot/캐릭터/사용량은불변이다.
- end: 현재파티장본인1인일때room/round/본인membership을종료하고점유/usage를함께정리한다. 기존pending은room종료로논리cancelled이며무제한bulk종료를요구하지않는다. 이미성립한신청/과거snapshot은보존한다. 방전체완료로대체하지않는다.

**Q3제안:** group탈퇴후기존roommembership은자동삭제하지않고`recovery_only`로둔다. full명단/진행은거절하며본인management/leave/withdraw, 원파티장의최소transfer/end만허용한다. 해당방의현재참가자격문제는`GROUP_MEMBERSHIP_LOST`로진행을막는안을별도로구분한다. 이를개인한도원인의무한그룹전파로구현하지않는다. 최소이전후보는해당room현재유효group회원의membership참조만준다. 이조회범위/잔류/회복처리는확인항목이며확정정책으로선반영하지않는다.

G3그룹탈퇴자체를방잔류때문에차단하지않는다. 신소유회원에게옛자리/권한을넘기거나이름으로재연결하지않으며자동파티장승격은없다. Q3미확정이어도내부원자성/공개방기반은진행하고group전용쓰기공개만분리할수있다.

주차종료시GET은`cycle_closed`만계산하며쓰기0이다. apply/join/approve는409 CYCLE_CHANGED, 기존관계leave/transfer/end는가능하다. 옛점유는옛cycle자료로보존/정리하고새주차에가짜참가·완료를만들지않는다. 현재membership이남으면방수에계속포함한다. 자동회차전환/재개/R4함께하기는미지원이며새주차의일정을이미예약되거나자동무충돌이라고판정하지않는다.

## 9. revision·원자성·원성공 복구

| 변경 | room | round | members | membership | 기타 |
|---|---:|---:|---:|---|---|
| create | 1 | 1 | 1 | 본인1 | directory/본인usage+1·weekly미저장1→2 |
| apply/reject/withdraw | 불변 | 불변 | 불변 | 불변 | applications_head/신청revision갱신 |
| join/approve | +1 | +1 | +1 | 신규1 | directory/본인usage/weekly+1·approve신청갱신 |
| leave | +1 | +1 | +1 | 본인+1/종료 | directory/본인usage+1·대상weekly점유해제+1 |
| transfer | +1 | 불변 | +1 | 이전자/대상각+1 | directory+1·usage/weekly불변 |
| 마지막1인end | +1 | +1 | +1 | 본인+1/종료 | directory/본인usage+1·대상weekly점유해제+1 |

최초DB단계는기존game-mutations-v1→actor User/Session→target User→room/round→membership/weekly→head/ACK순서를통일한다. 한도/그룹관계변경도같은전역lock을따르며외부provider호출은lock안에서하지않는다. 최종DB시각/주차·신청기한·source변화/lease와generation검사실패시slot/점유/사용량/신청/head/ACK전체rollback한다.

논리expired의ended_at은expires_at, room종료로cancelled이면room.ended_at, 명시취소/거절은실제시각이다. GET에서만료행을쓰지않는다. 확정시다른방의pending을전부종료하지않아도주간/일정/currentmember guard가중복을차단한다. 같은방이미참가한경우옛pending은논리cancelled이며승인원성공accepted기록과구분한다.

operation은actor+room-create/apply/join/application-approve/reject/withdraw/room-leave/transfer/end로나누고target+전체입력을digest한다. 기존원성공24h/30slease/generation fencing·REQUEST_IN_PROGRESS/Retry-After2·다른본문IDEMPOTENCY_CONFLICT·만료IDEMPOTENCY_EXPIRED를재사용한다.

최소ACK replay는현재정상session/User·원actor/operation/digest·원membership/application의room/actor귀속과ACK참조를검사한다. 현재group/leader/소유자격은원ACK복구의조건으로삼지않는다. 탈퇴후재가입한새membership을옛leave key로종료하지않고현재private명단/권한도복원하지않는다. 빈목록GET이나뒤에생긴성공을원명령과추정연결하지않는다.

## 10. 오류·클라이언트 처리 (신규 code는 제안)

| HTTP | code | 처리 |
|---|---|---|
| 400 | INVALID_REQUEST | body/query/header수정 |
| 401 | 기존인증/SESSION계열 | 기존session복구 |
| 403 | ROOM_MEMBERSHIP_REQUIRED / ROOM_LEADER_REQUIRED | 현재관계/권한조회 |
| 404 | ROOM_NOT_FOUND / ROOM_APPLICATION_NOT_FOUND / CHARACTER_NOT_FOUND | 공개가능범위확인·private존재누출금지 |
| 409 | REVISION_CONFLICT / POLICY_CONTEXT_CHANGED / APPLICATION_CONTEXT_CHANGED | 현재GET/context후명시새판단·새key, 실패pending보존 |
| 409 | CYCLE_CHANGED / CATALOG_VERSION_CONFLICT / RAID_INACTIVE | 주차/카탈로그재조회 |
| 409 | WEEKLY_ALREADY_COMPLETED / WEEKLY_ALREADY_PARTICIPATING | 주간과현재방관계를각각확인 |
| 409 | ROOM_MEMBER_EXISTS / ROOM_APPLICATION_EXISTS / ROOM_NOT_ACTIVE / APPLICATION_NOT_PENDING | 현재관계와옛ACK구분 |
| 409 | ROOM_FULL / ROOM_COMPOSITION_CONFLICT / SCHEDULE_CONFLICT | 현재자리/일정재판단, 자동role/party변경없음 |
| 409 | SCHEDULE_REVIEW_REQUIRED / COMBAT_REQUIREMENT_UNAVAILABLE / ROOM_FEATURE_UNSUPPORTED | 불명/미지원분기만보류 |
| 409 | ROOM_RESTRICTED / GROUP_MEMBERSHIP_LOST | 원인/정리permissions조회·완료우회금지 |
| 409 | ROOM_LEADER_TRANSFER_REQUIRED / ROOM_TRANSFER_TARGET_INVALID / ROOM_TARGET_UNAVAILABLE / ROOM_LAST_MEMBER_REQUIRED | 필요한회복순서/현재유효대상확인 |
| 409 | 기존IDEMPOTENCY_* / REQUEST_IN_PROGRESS / CURSOR_STALE | 원key/body보존·기존복구/첫페이지재조회 |
| 409/403 | 기존등록/소유/claim/lifecycle/활동/한도오류 | 해당기존원본규칙유지 |
| 503 | SERVICE_UNAVAILABLE | 결과불명은원key/body backoff, ACK후GET실패면GET만재개 |

## 11. DDL·기존 계약 연결

제안테이블은raid_rooms(현재leader/생성당시scope·group/revision/end), raid_room_rounds(room/catalog/cycle/difficulty/schedule/revision), raid_room_memberships(room/user/선택캐릭터·role/party/slot/소유수명snapshot·유효구간/revision), raid_room_applications(room/user/선택명령·서버표시·기한/상태/revision), directory/개인membership/신청head다. 실명과migration번호는실제구현시현head다음으로확정하며이번에파일을추가/적용하지않는다.

같은room활성user/slot unique, party카탈로그범위/최대8인·support/직업검사, 양의revision·상태/ended_at정합, 동일room의leader membership복합FK(지연)를설계한다. 실제User/Character FK를임의JSON/이름으로대체하지않는다. 생성scope/group·가입/탈퇴유효구간·당시표시는보존하며현재캐릭터/소유정보로과거를덮지않는다.

WeeklyState를그대로점유/완료원본으로쓰고현재membership/i는신규관계projection으로제공한다. #11 DTO/완료점유제약과기존bootstrap을임의확장하지않는다. `/v1/me/usage-limits`의raid_rooms는같은DTO안에서실제원본연결시null/unavailable→실수치/state로바뀌므로지원시점/호환시험을별도인계한다.

#19용UUID/발생시각/생성scope·group/유효구간과도메인revision은실제명령과같이보존하되통계분류/마감/집계정책을이DDL에서확정하지않는다. V2실제파티영향adapter·G3해산의active그룹방검사는별도통합검증후연결하며room테이블생성만으로보류를해제하거나0건으로치환하지않는다. 기존자료이관/삭제/과거통계backfill·자동파괴downgrade는없다.

## 12. 좁힌 검토 항목·독립 구현 순서

| 항목 | 현재/Backend 제안 | 직접 영향·다음 담당 |
|---|---|---|
| Q1 종료불명/미정일정 | unknown표현/기본시간없음, 최초는유한일정단일회차부터 | 불명일정확정분기만보류. Flutter기존소비/조작충돌확인, 새명시확인정책필요하면사용자결정으로분리 |
| Q2 역할별최소전투력 | P1은client분석표시, provider캐시와구별. 최초min=null기반/문턱있는분기보류안 | Backend/Flutter가실제대상수치·출처를기존역할계약과대조. 임의P1값을검증완료로취급하지않음 |
| Q3 group탈퇴후room | 자동삭제없이recovery_only/진행제한·본인정리·최소후보조회안 | group전용쓰기공개전잔류/조회/권한회복경계확인. public/내부원자성기반은독립진행가능 |

경로/필드/상한은Backend설계제안이며전기능재승인/실기기시험을요청하는것이아니다. 기존확정정책과충돌하는구체항목만확인한다. 위항목을전체작업무기한대기로확대하지않는다.

다음독립단위는 **F1 내부기반**: room/단일round/membership/slot/신청/head와기존한도·weekly연결의내부transaction/회복기반, migration파일·격리PostgreSQL표적시험이다. production에기본허용policy를두지않고명시policy/미지원분기를분리한다. 지원표가필요한분기/Q1~Q3는임의로활성화하지않는다. 이어서F2는확정범위HTTP/DTO/OpenAPI·회귀, F3는기존API/DB반영·실행계약검증·commit/push/원격확인→필요한Flutter인계다. **이번은명세구간이며F1구현착수/완료가아니다.**

## 13. 표적 검증 계획 (이번 미실행)

격리PostgreSQL/HTTP에서권한/그룹비공개·동명이UUID격리, 마지막자리/동일회원다원정대/동시승인·즉시참가·한도감소, 정확한도/3원인회복, 소유/활동/claim/level/P1 null·stale·위조입력/OFF, 시간인접/중복/unknown·주차최종경계, 응답유실/lease takeover/다른본문/재가입옛key, slot/weekly/usage/head/ACK전부rollback, GET SQL쓰기0/권한상실cursor·논리만료, group탈퇴와진행경쟁/정리권한을시험한다. G1/G2/G3·#11 manual·bootstrap회귀는실제변경영향에맞춰붙인다.

이번실행은문서/JSON예시·참조·요구대조/diff검사뿐이다. 서버/DB/pytest·provider/Flutter/실기기시험은실행하지않는다.
