# Issue47 계약 보완 v2 — 전체 wire·결과 대조

보관 구분: 이 문서는 이전 v2 제안이다. 최종 채택은 [v3](batch-completion-wire-v3.md)·[현재 구현/완료 근거](batch-completion-implementation.md)이며 #47은 completed 종료됐다. 아래 미구현/합의 대기·이력 상한은 당시 제안으로 현재 계약에 적용하지 않는다.

## 최신 — Native 수용·사용자 채택 보완으로 변경할 항목

[전체4번째 Native](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6760758009)가 v2 기본 정의를 수용했다. 다음 Backend는 선택 round 외 완료/취소/보존 대상 전체의 레이드 표시와 활성 한도/누적 완료 이력 분리를 반영해 구현한다. 아래 display.rounds 선택 한정·역사 누적 시40/5개 상한/413 거절은 **그대로 구현하면 안 되는 이전 제안**이다. 과거 보존·다른 캐릭터 재가입 때문에 정상 완료를 거절하거나 이력 삭제·사용자 정리를 요구하지 않는다. 변경 wire·집계/보존 규칙·예시/구현은 아직 미완료이며 최신 실행은 [NEXT_WORK](../../../project/NEXT_WORK.md)를 따른다.

2026-11-10 / **합의 전 제안·미구현**. [Native 전체2번째 보완 요청](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6759918260)에 대한 답변이다. v1의 모호한 wire 설명은 이 문서와 [JSON Schema](examples/batch-completion-v2.schema.json)를 기준으로 교체한다. [전체 응답12개](examples/batch-completion-v2.examples.json)는 허용/거절 context, 공대 부분 완료 ACK, 개인 일반탈퇴/승계/마지막 전체·부분 완료 ACK, 권한403을 제공한다. 합성 ID·이름·token이며 서버 실행 결과가 아니다.

[전체3번째 Backend 보완 회신](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6760087700)에 schema·전체 예시 전문을 게시하고 원문 일치를 확인했다. 다음 Native 최종 수용/차이 회신 대기이며 아직 합의 전이다.

## 1. Profile 정정과 기본 규칙

최초 댓글의 `contract_profile=beta-recruitment-wire-2`는 잘못된 안내였다. 실제 query 값은 **`beta-recruitment-1`**, `beta-recruitment-wire-2`는 계약 version이다. 변경 의도는 없다. 기존 beta_profile.PROFILE·beta-contract-wire 원본과 일치시켰다. 기존 group/participation profile·단건 operation/pending/원ACK 보존은 유지한다.

새 네 API 경로·명령 필드·단일 JSON query round_ids·선택1~5개와 정렬 규칙은 v1과 같다. UUID는 JSON string, Version은 bool/float/문자열이 아닌 정수1..2147483647, CycleKey는 YYYY-MM-DD이며 서버 수요일 주차 검증을 추가한다. 시각은 timezone 포함 RFC3339 string이다. command_id는 UUID4다. query512/token4096 UTF-8 bytes·응답1MiB 상한은 JSON Schema 외 서버 검사도 필요하다.

**모든 신규 객체는 additionalProperties=false.** 아래 표의 필드는 모두 필수이며 `?`는 생략 가능이 아니라 null 허용을 뜻한다. 선택적 필드는 envelope의 기존 group_policy_version/group_policy/group_policy_effect/group_policy_effects뿐이다(기존 DTO의 생략·null 규칙 재사용). 새 contract_profile/participation_profile echo 필드는 추가하지 않는다. 기존 단건 DTO/응답을 바꾸지 않는다.

## 2. 정확한 context·ACK 필드

| 객체 | 필수 필드와 타입 |
|---|---|
| envelope | scope:Scope, data:아래 action별 ContextData 또는 AckData |
| Scope | server_now:Time, current_cycle_key:CycleKey, target_cycle_key:CycleKey, playable_from:Time, phase:current/future, target_revision:Version, policy_version:"two-cycle-contract-4", room_cycle_id:UUID, target_generation:Version |
| ContextData | action:아래 literal, room_id:UUID, actor_cycle_member_id:UUID, actor_cycle_member_revision:Version, round_ids:UUID[1..5], display:Display, impact:Impact, departure:Departure?, state:State, leadership:Leadership, expected_after:ExpectedAfter?, revisions:Revision[5..64], permission:Permission, confirmation:Confirmation? |
| AckData | action:동일 literal, command_id:UUID4, outcome:"applied", executed_at:Time, room_id:UUID, actor_cycle_member_id:UUID, round_ids:UUID[1..5], impact:Impact, departure:Departure?, state:State, leadership:Leadership, revisions:Revision[5..64] |
| Display | rounds:RoundDisplay[1..5], assignments:AssignmentDisplay 배열1..40, 개인1..5, display_revision:소문자SHA256 64자리 |
| RoundDisplay | round_id:UUID, item_id:UUID, raid_id:string, raid_name:string, difficulty_id:string, difficulty_name:string, catalog_version:string |
| AssignmentDisplay | assignment_id:UUID, round_id:UUID, membership_id:UUID, cycle_member_id:UUID, character_id:UUID, character_name:string?, effect:complete/cancel/preserve_completed/preserve_active |
| Impact | completed_assignment_ids:UUID[], cancelled_assignment_ids:UUID[], preserved_completed_assignment_ids:UUID[], preserved_active_assignment_ids:UUID[], released_reservation_count:정수>=0, preserves_other_cycles:true, preserves_global_membership:true |
| State | target_state:open/closed, generation_state:open/completed/cancelled, actor_cycle_member_state:participating/completed/cancelled |
| Leadership | leader_cycle_member_id:UUID?, leader_membership_id:UUID?, leadership_revision:Version |
| ExpectedAfter | state:State, leader_cycle_member_id:UUID?, leader_membership_id:UUID? |
| Departure | effect:leave/automatic_successor/close_completed/close_incomplete, successor:Successor? |
| Successor | cycle_member_id:UUID, revision:Version, joined_order:양의 정수를 나타내는 십진 string, character_id:UUID, character_name:string? |
| Revision | resource:아래7종 enum, id:UUID, revision:Version |
| Permission | allowed:boolean, reason:string?, next_change_at:Time? |
| Confirmation | context_token:비어 있지 않은 string, issued_at:Time, expires_at:Time |

`action`은 공대 `batch_completion`, 개인 `batch_personal_completion_departure`다. 공대 departure는 반드시 null이며 개인은 객체다. 공대 cancelled는 빈 배열, 개인 preserved_active는 빈 배열이다. 선택은 현재 활성 대상만 받으며 이미 완료된 round는 선택 불가다.

Impact의 완료/취소/기존완료보존/활성보존 ID는 각각 서로소·중복없음·정렬이며 display.assignments를 effect별로 분할한 집합과 정확히 같다. 공대 completed 1..40, cancelled 0, preserved_completed 0..40, preserved_active 0..40; **네 집합 합계/display 최대40**. 개인 completed1..5, cancelled0..4, preserved_completed0..5, preserved_active0; **합계/display 최대5**. rounds는 선택 집합만 표시하며 assignments에는 미선택 취소/보존 round도 포함된다. 같은 이름/raid가 아닌 정확한 assignment ID로 대조한다. 표시 digest는 display_revision을 제외한 Display의 UTF-8/키 정렬/공백 없는 JSON SHA256다.

이 수치는 새 명령의 응답/영향 자료 상한이지 과거 자료 삭제나 truncation 기준이 아니다. 과거 완료 누적 등으로 완전한 영향 집합이 이 상한을 넘으면 **413/RESPONSE_TOO_LARGE로 전체 거절**하며 토큰·부분 성공을 만들지 않는다. 실제 구현에서 상한을 넓혀야 할 근거가 나오면 계약 차이를 먼저 협의한다. 8인×5개는 활성 참가 최대 검증 조건이며 누적 역사량까지 항상40개 이하라고 가정하지 않는다.

## 3. 허용·권한 거절

- Context는 읽기 권한과 대상 귀속을 먼저 검증한다. 비참가자/타인·비공개 자료 노출은 기존403/404 오류 envelope로 거절하며 display를 반환하지 않는다.
- 읽을 수 있는 유효한 context에서 실행 권한·시각·후계자 조건만 불충족이면 HTTP200, permission.allowed=false/reason=기존 code, confirmation=null, expected_after=null이다. impact/departure는 검토용 예상 영향이며 명령 근거가 아니다. 후계자 부재는 departure.effect=automatic_successor/successor=null이다.
- 허용이면 permission={allowed:true,reason:null,next_change_at:null}, confirmation과 expected_after 모두 non-null이다. confirmation.expires_at 이후에는 새 context를 받아야 하지만 기존 pending의 원요청/ACK 복구를 바꾸지 않는다.
- POST에서 현재 권한·CAS·token을 다시 검증한다. 실패는 기존 오류 envelope이며 ACK/data/scope를 합성하지 않는다. 403 예시는 error={code,message,request_id,details:null}; details와429 retry 필드의 전체 타입·생략 조건은 기존 Error DTO를 유지한다. 새 오류 code를 추가하지 않는다.

## 4. Revision 의미와 상태 전이

Context의 revisions는 해당 명령 ACK가 제공할 revision 키들의 **실행 전 기준**이다. ACK는 같은 resource/id 집합의 최종값이다. 목록은 resource 문자열→UUID 오름차순, (resource,id) 중복 금지다. 이 목록은 모든 하위 일정/예약 행의 변경 로그가 아니라 Native의 재조회/무효화를 위한 제한된 authoritative summary다. 일정 하위 변경은 plan으로 대표한다.

| resource | id가 가리키는 대상 | 전이/대조 |
|---|---|---|
| target | scope.room_cycle_id | RoomCycle.revision. ACK가 context보다 커야 하며 scope.target_revision과 같음 |
| members | 같은 room_cycle_id | RoomCycle.members_revision. 멤버/참가 영향 후 증가 |
| plan | 같은 room_cycle_id | RoomCycle.plan_revision. 점유/일정 정리 후 증가 |
| leadership | 같은 room_cycle_id | 해당 target_generation의 CycleGeneration.leadership_revision. leadership 응답과 같음. 리더 보존은 동일, 승계/개인 마지막 종료는 기존 규칙으로1 증가 |
| cycle_membership | CycleMember.id | actor(항상 포함)와 실제 변경된 해당T 멤버. actor 기준은 ContextData.actor_cycle_member_revision과 같음. 변경된 멤버는 증가, 공대 명령에서 actor 자체 미변경이면 동일 허용 |
| round | RecruitmentRound.id | 명령으로 상태/revision을 바꿀 round만. 공대 선택 round, 개인 마지막 종료에서 종료 처리할 활성 round를 포함. 기존 완료 round 제외 |
| assignment | RecruitmentAssignment.id | completed/cancelled 집합만 포함하며 모두 증가. preserved 집합은 포함하지 않음 |

고정4종 target/members/plan/leadership와 actor는 항상 존재한다. 별도 generation revision/resource는 **없다**. 세대는 scope.room_cycle_id+target_generation으로 식별한다. 전역 room/membership revision을 이 값으로 혼동하지 않는다. target/plan 등의 내부 도우미가 여러 번 bump할 수 있으므로 일반 revision에 정확히+1을 가정하지 않고 최종값 증가와 키/대상 일치를 검증한다. round/assignment도 최종 증가값을 쓰며 수정하지 않은 보존 자료를 올리지 않는다.

Context state/leadership은 현재 상태다. expected_after는 실행 가능 context가 결합한 예상 업무 상태/리더 ID이며 revision 예측값은 넣지 않는다. ACK state는 expected_after.state와, ACK 리더 ID 둘은 expected_after의 ID들과 정확히 일치해야 한다. 상대가 바뀌었다면 기존 토큰은 stale로 거절하고 다른 결과를 같은 명령의 성공으로 반환하지 않는다.

| 개인 departure.effect | ACK actor 상태 | ACK target/세대 상태 | ACK leadership·successor 대조 |
|---|---|---|---|
| leave | cancelled | open/open | context 리더ID·leadership_revision 보존, successor=null |
| automatic_successor | cancelled | open/open | context successor.cycle_member_id가 최종 leader ID, 최종 membership ID는 expected_after 값. leadership_revision+1, successor 객체는 context 그대로 |
| close_completed | cancelled | closed/completed | leader 두ID null, leadership_revision+1, successor=null |
| close_incomplete | cancelled | closed/cancelled | leader 두ID null, leadership_revision+1, successor=null |

개인 회원 state는 마지막1인 전체 완료라도 completed가 아닌 **cancelled**다. generation.completed는 전체 완료 증거, generation.cancelled는 미완료 포함 종료를 나타낸다. 마지막 종료는 두 경우 모두 해당 주차의 leadership만 null로 만들며 다음T/지속 소속을 끝내지 않는다. successor.revision은 **선정 당시 후보 revision**이고 ACK에서도 그대로이므로 후계자의 실행 후 revision이라고 해석하지 않는다. 기존 주차 승계는 포인터 변경만으로 후보 CycleMember revision을 자동 증가시키지 않는다.

공대 완료는 actor/선택 영향을 받은 멤버의 남은 활성 참가 유무에 따라 participating/completed를 판정한다. 남은 활성 round/참가가 없으면 기존 공대 완료처럼 closed/completed다. 이때도 기존 공대 완료의 리더 보존 규칙을 따른다(개인 마지막 탈퇴의 null 규칙을 적용하지 않는다). expected_after가 정확한 결과를 제공한다.

원ACK 재생 시에는 저장 당시 scope/시각/state/leadership/revisions 전체가 그대로다. 현재 주차·GET·권한과 맞추기 위해 ACK를 다시 생성하지 않는다. Native는 최초 저장한 명령/context의 의미와 대조한다.

## 5. 검증과 다음 담당

Schema는 추가 필드·필수/nullable·기본 타입·상한을 표현하며 별도 의미 검사는 집합 분할/정렬·선택과 display/ACK 일치·state/리더 쌍·revision 귀속/전이·날짜/시각 및 byte 상한을 확인한다. 전체 예시는 생성 schema/format과 의미 정합성을 검증한 **계약 예시**이며 기능 구현/격리 DB/실제 HTTP 검증이 아니다.

다음 Native는 v2 전체 wire와 예시, revision·개인 탈퇴 결과 대조 기준을 확인하고 최종 수용/차이를 같은 Issue에 회신한다. Backend는 합의 후 구현·격리 PostgreSQL/HTTP·두 전체 OpenAPI 검증으로 넘어간다. 이번 보완은 미커밋·미push이고 실행 OpenAPI/서버/DB·키/환경·Native 코드·운영/APK·Issue 종료는 변경하지 않는다.
