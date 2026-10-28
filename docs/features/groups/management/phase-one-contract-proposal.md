# 그룹 관리·그룹장 레이드 제한권한 1차 계약 제안

2026-10-28 / Backend / `feat/group-management` / G-MANAGE·G-RAID 1차 설계.

**현재 제공 기능이 아닌 설계 제안이다.** 이번 사용자 승인 구간은 문서·Issue 계약 제안까지이며 HTTP 구현·DDL·실행 OpenAPI·서버/DB·배포·기기 인수는 변경하지 않는다. 조건부 해산을 지금 활성화했다는 뜻이 아니다.

## 기준·문제·기존 구현

근거는 [Issue16 전체9번째 Flutter 개발 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464117245), [전체8번째 그룹 소멸 후 방 보존 정정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6463878563), [설계39 f04f482e](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/backend-migration/39-group-flutter-integration-design.md), 같은 커밋의 [제품 §13/14](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/product/GROUP_PRODUCT_FLOW.md)·[모집37](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/backend-migration/37-raid-scheduling-and-multi-raid-planning.md)다. Backend 대조는 main/dev1b6f57b·그룹준비ea52e56이다.

관리GET·즉시 이전·일반탈퇴는 이미 제공된다. Group.ended_at/과거membership/FK, 그룹 명령 runner·game-mutations-v1 잠금·멱등 ACK를 재사용한다. 현재는 disband=false/STATE_UNAVAILABLE, 추방·대표변경·비참가 그룹장 관리 API는 없다.

실제 two-cycle 모집 원장은 존재하지만 일반 공통명령은 참가자와 공대장 자격을 함께 요구한다. 또한 cycle_lifecycle.qualify가 현재 그룹소속까지 검사해 단순탈퇴 후 기존진행 보존과 충돌할 수 있다. 기존함수의 권한검사를 제거해 전부 열지 않고 권한과 상태변경 책임을 분리한다. 표시 조회는 [G-DISPLAY 제안](../discovery/display-contract-proposal.md)을 따른다.

## 권한과 제안 API

| 동작 | 현재 그룹장 | 일반 그룹원 | 비그룹 기존 레이드 참가자 |
|---|---|---|---|
| 그룹 해산/추방/대표변경 | 아래 조건/CAS 충족 시 허용 | 불가 | 불가 |
| 그룹장 전용방 목록/context | 허용, 방 비참가도 가능 | 불가 | 불가 |
| 그룹장 권한의 공개전환/모집해산 | 대상·상태·최종조건 충족 시 허용 | 불가 | 불가 |
| 기존 레이드 상세/진행/완료/탈퇴 | 원래 레이드 역할로 별도 판정 | 같음 | 현재 레이드 관계/독립 자격으로 판정 |
| 레이드 승인/편성/캐릭터변경/일정·완료 | 그룹장 지위로 추가 허용하지 않음 | 기존 레이드 계약 | 기존 레이드 계약 |

| Method·경로(제안) | 입력/응답 |
|---|---|
| `GET /v1/groups/{group_id}/management?management_profile=group-management-1` | 기존 관리정보 + 해산 판정·추방/대표변경/방관리 permissions. 생략 시 기존 DTO 그대로 |
| `POST /v1/groups/{group_id}/disband` | 아래 GroupCAS → GroupDisbandAck |
| `POST /v1/groups/{group_id}/members/{membership_id}/remove` | GroupCAS + expected_target_membership_revision → GroupRemoveAck |
| `PUT /v1/groups/{group_id}/representative` | GroupCAS + 기존 CharacterSelection → GroupRepresentativeAck |
| `GET /v1/groups/{group_id}/raid-rooms` | limit/cursor → GroupRaidRoomPage |
| `GET /v1/groups/{group_id}/raid-rooms/{room_id}/command-context?command=make_public\|end` | 현재 actor·그룹/방·실제영향C/N의 읽기전용 context |
| `POST /v1/groups/{group_id}/raid-rooms/{room_id}/make-public` | GroupRoomCommand → GroupRoomAck |
| `POST /v1/groups/{group_id}/raid-rooms/{room_id}/end` | GroupRoomCommand → GroupRoomAck |

새 그룹 관리 경로의 미지 query/body 필드·중복query/잘못된 enum은400이다. management_profile 생략은 기존 disband=false DTO를 유지하며 신규 기능 소비자는 프로필을 명시한다. 신규 방관리 경로는 실제 two-cycle 원장이 준비된 실행에만 제공하고 기본0023 앱에 원장없는 우회동작을 추가하지 않는다. 구현 시 두 OpenAPI를 각 프로필과 대조한다.

### 공통 DTO·오류·명령 책임

- GroupCAS: `expected_group_revision`, `expected_members_revision`, `expected_membership_id`, `expected_membership_revision`(기존 LeaveGroup와 같은 필수양의정수/UUID 계약). 대상 membership UUID는 경로에 한 번만 전달한다.
- CharacterSelection: 기존 registration_id/character_id·expected_registration_version/ownership_revision/roster_revision/lifecycle_revision. 선택 활동집합은 같은 잠금 안의 최신값으로 검사한다. 1700 추가 하한은 없다.
- 모든 쓰기는 기존 세션·UUIDv4 Idempotency-Key·동일 actor/operation/target/key/body 결합을 사용한다. 같은 key+다른본문은 기존 멱등 충돌, 진행중/lease/24h/세션철회는 기존 정책을 유지한다.
- 인증401, 현재 그룹원403 GROUP_MEMBERSHIP_REQUIRED, 리더403 GROUP_LEADER_REQUIRED, 없는/종료 그룹404 GROUP_NOT_FOUND, 타그룹/종료 대상404 GROUP_TARGET_UNAVAILABLE, stale409 REVISION_CONFLICT. 새 제품거절은 아래 안정적인 code를 제안하며 기존 envelope/request_id/no-store를 재사용한다.
- 정상 실행 권한을 재검증한 뒤 game-mutations-v1 잠금·동일 DB 트랜잭션에서 효과/사용량/revision/활동시각/ACK를 원자 확정한다. ACK 저장/최종가드 실패는 모두 rollback한다. 외부 I/O는 없다.
- 과거 성공 replay는 현재 membership/리더 재승격을 요구하지 않는다. actor·원명령·원대상·과거 membership 소유 증거를 검사하고 저장된 최소 ACK만 복구한다. 탈퇴/해산/이전/재가입 후 새 관계는 건드리지 않는다.

## 해산 판정과 동일한 그룹장 관리 목록

공통 평가 함수는 그룹에 연결된 모집 원본에서 `clear / blocked / unavailable`과 `blocking_room_count: int|null`, `evidence_revision`을 계산한다. unavailable의 count는 null이고 disband.allowed=false/reason=GROUP_RECRUITMENT_STATE_UNAVAILABLE이다. 방 원본 조회의 실제 DB오류는503이며 빈목록200으로 바꾸지 않는다.

1. 우선 RecruitmentRoom.group_id 일치와 현재 scope=group인 방 전체를 검사한다. public은 해산 차단에서 제외하되 연결과 기록을 유지한다. 검색의 필터/페이지/본인방제외 결과를 해산 근거로 쓰지 않는다.
2. ended_at 있는 방은 종료로 분류한다. ended_at이 없고 기존 completed_room_lifecycle.archived가 확정 true면 완료 보관으로 분류한다. 나머지는 차단 대상이며 스스로 새 ‘완료’ 기준을 발명하지 않는다.
3. 원장 migration_state=ready·explicit provenance와 실제 cycle/generation/round 연결을 확인한다. 세대없음/review_required/레거시 미검증·연결모순은 unavailable이다. 미확인 방도 관리 목록에서 누락하지 않고 review 항목으로 제공한다.
4. 실제 C/N row·세대와 지속 방 상태를 사용한다. 현재 페이지에 없거나 해당주차가 미개방인 것은 종료 증거가 아니다. 과거의 미완료/불명확 방도 지속 방이 종료/보관으로 입증되지 않으면 차단한다. 다른 주차를 C/N 별칭으로 변환하지 않는다.

방 목록은 위 차단/미확인 대상 방을 room_id당 한 번 제공한다. 실제T별 상태는 nested targets이며 `room_cycle_id/target_cycle_key/generation/target_revision/state`를 포함한다. 과거 미확인은 해당 실제키와 검토 사유로만 표시하며 현재 명령대상으로 승격하지 않는다. 루트는 `group_id/group_revision/members_revision/evaluated_at/evidence_revision/state/blocking_room_count/items/next_cursor`다. item은 `room_id/title/scope/group_id/room_revision/state/reason/targets/permissions`이고 참가자 상세·신청명단/시간표는 공개하지 않는다.

목록은 created_at DESC·room_id DESC, limit기본20/최대50, 전체평가 후 페이지를 자른다. cursor는 actor/session·현재 그룹장 membership/revision·그룹 revision·전체 방/세대/evidence·limit에 결합한다. 권한변경은403, 자료변경은409 CURSOR_STALE이다. 목록 count와 해산 검사는 같은 스냅샷에서 같은 집합을 계산하며 모든 변경 명령은 잠금 뒤 다시 계산한다.

## 그룹 명령 상태 전이·원자성

### 조건부 해산

현재그룹장 → CAS → 활성membership 정확히 본인1명 → `relation_state`가 pending인 관계0 → 위 평가clear 순서로 확인한다. expired·발신자탈퇴로 실효cancelled인 관계는 유효pending에 포함하지 않는다. readonly 관리GET은 이를 정리하는 쓰기를 하지 않는다.

거절: GROUP_DISBAND_SOLE_MEMBER_REQUIRED / GROUP_PENDING_RELATIONS_EXIST / GROUP_ACTIVE_RECRUITMENT_EXISTS / GROUP_RECRUITMENT_STATE_UNAVAILABLE. 과거 활동·정원초과·대표needs_update를 관계정리의 추가 차단조건으로 쓰지 않는다.

성공 시 Group.ended_at, 본인membership.ended_at/revision, group.revision/members_revision·directory, 본인가입사용량 revision·활동시각, 모든 활성 코드 revoked_at/revision을 함께 갱신한다. 남아 있는 실효만료/취소 관계는 원사유·원만료시각에 맞게 종료한다. 과거 행·원ACK·코드재발급 이력은 보존하고 캐릭터/레이드/주간점유는 삭제/수정하지 않는다. Group.leader_membership_id는 종료된 과거 membership을 계속 참조한다.

GroupDisbandAck: `group_id/membership_id/membership_revision/group_revision/members_revision/ended_at`. 이미 종료된 그룹의 새key 명령은404이며 원key replay는 과거ACK만 반환한다.

### 그룹원 추방

현재그룹장 → GroupCAS → 경로 대상이 같은 그룹의 활성membership인지 → 대상revision 일치 → 자기/현재그룹장 대상 아님을 검사한다. 자기대상409 GROUP_REMOVAL_TARGET_INVALID. 대상 회원의 소유/활동/1700·현재 세션 유무로 기존 관계 정리를 막지 않는다.

성공 시 대상membership 종료, 그 membership이 보낸 pending invitation 실효상태별 종료·관련subject revision, 대상가입사용량·group/members/directory·활동시각·ACK를 갱신한다. subject 차단/신청횟수 초기화·다른그룹 관계/레이드 membership 변경은 하지 않는다. 재가입은 새UUID다.

GroupRemoveAck: `group_id/membership_id/membership_revision/group_revision/members_revision/ended_at`. target display/개인정보는 최소ACK에 넣지 않는다. 발신초대 정리 helper를 일반탈퇴와 공유한다.

### 그룹 대표 변경

현재그룹장 → GroupCAS → 기존 selected_character의 소유·현재registration/claim/lifecycle·활동/버전 검사 → group의 representative_character_id/user_id/display 갱신. 대표는 그룹장 본인의 선택만 받는다. user 대표·활동목록·멤버의 표시캐릭터·이름·리더는 자동 변경하지 않는다. 같은 대표와 동일 snapshot은 noop이며 revision/활동시각은 올리지 않는다.

그룹 revision/directory/활동시각·ACK만 갱신한다. members_revision과 기존 membership revision은 바꾸지 않는다. GroupRepresentativeAck: `group_id/group_revision/character_id/representative{display,status}/changed_at/outcome(applied|noop)`. noop changed_at은 null이다. 새로운 GET에서 현재 needs_update를 다시 판정하며 과거ACK valid를 현재자격으로 쓰지 않는다.

## 그룹장 레이드 제한 명령

그룹장 권한 검사와 모집 상태변경을 분리한다. 기존 cycle_common의 참가 actor/authority를 새 그룹장에게 가짜로 생성하지 않는다. 그룹전용 원본 방·그룹장·허용 동작을 먼저 검사하고, 기존 effect 계산/예약·점유·신청·ACK 원자성은 재사용한다.

### context와 CAS

context 응답: `group_id/group_revision/members_revision/actor_membership_id/actor_membership_revision/room_id/room_revision/command/expected_cycle_key/impact_cycles/permissions/evidence_revision/context_token/issued_at/expires_at`.

impact_cycles에는 현재 실제 C/N의 cycle_id/key/generation·target/members/plan/leadership revisions 및 영향 assignment/reservation/pending 개수, 방 종료 시 대상 persistent membership ID/revision을 포함한다. 미개방이면 영향대상에 가짜row를 만들지 않는다. C/N 밖 활성효과나 검토상태가 있으면 실행불가 사유로 제공한다.

토큰은 기존 opaque 서명을 재사용하되 새 operation namespace를 사용한다. actor/session·현재그룹장membership/역할·그룹/CAS·scope/group link·방/CN원본·유효한도·정확한명령/영향을 결합한다. 만료는120초와 주차경계 중 이른시각이며 response에 명시한다. GET이 DB에 명령/세대/default를 만들지 않는다.

GroupRoomCommand 필수: GroupCAS + `expected_cycle_key/expected_room_revision/context_token`. 대상과 operation은 경로에서 결정되며 임의 target_user_id·title·scope·group_id 변경필드는 받지 않는다. stale409 TARGET_CONTEXT_STALE/REVISION_CONFLICT, 만료409 COMMAND_CONTEXT_EXPIRED, 주차변경409 CYCLE_CHANGED. 최종 ACK 저장 직전 만료/주차·업무기한을 다시 검사한다.

### 공개 전환

현재 그룹전용 방만 `scope=public`으로 바꾼다. 연결 group_id·제목·신청·참가/역할·일정·C/N 설정은 보존한다. 완료보관/종료방은409 ROOM_NOT_ACTIVE. 기존 소유/한도·검토상태 제한은 필요한 현재 동작별 정책을 적용하며 신규 대표 캐릭터 선택은 요구하지 않는다.

현재 그룹장이 비참가자여도 허용하지만 일반 공대장 권한을 얻지는 않는다. 공개된 방은 관리 차단목록에서 빠지며 재차 group장 권한의 새key 호출은409 GROUP_ROOM_NOT_GROUP_ONLY. 동일key 원ACK는 복구한다. 공개→그룹전용 왕복은 기존 공대장 경로/그룹불변 정책을 유지한다.

### 모집 해산

**기존 ‘마지막 참가자 방 해산’의 인원 제한을 유지한다.** 전체 지속 membership이1명이고 C/N에 다른 실제참가/활성배정이 없어야 한다. 2명 이상이면409 ROOM_LAST_MEMBER_REQUIRED이며 그룹장이 다수 참가자를 일괄 제거하는 새 기능을 만들지 않는다.

비참가 그룹장은 명령 actor일 뿐이며 기존 유일 참가자를 사칭하지 않는다. 효과 계산은 유일 지속membership을 별도 대상으로 명시하고 C/N 실제배정·예약/주간점유·pending·방종료를 기존 해산 방식대로 처리한다. 완료 기록은 보존한다. 대상/원장 불명확·기존 해산의 상태/기한/독립자격 거절은 그대로 유지한다. 0명/일관성 불명확은 ROOM_REVIEW_REQUIRED로 보류하며 자동수정하지 않는다.

이는 참가인원 제한을 늘리는 제안이 아니라 #16이 요청한 비참가그룹장 권한을 기존1인해산 효과에 연결하는 제안이다. 네이티브가 요청한 ‘모집해산’이 다인 방 강제종료까지 뜻한다면 정책변경으로 별도 질문하며 그 범위는 구현하지 않는다.

GroupRoomAck: `command_id/group_id/room_id/command/outcome/executed_at/room_revision/room_ended/affected_cycle_keys/revisions`. 현재 권한·명단은 넣지 않는다. 이전후 과거그룹장 key의 과거성공복구는 가능하되 새context/새명령은 거절한다. 그룹 activity/directory·실제영향 cycle directory·사용량/주간원장 head를 효과에 맞게 함께 갱신한다.

## 그룹 소멸·탈퇴 후 기존 레이드 보존

| 구분 | 그룹이 활성 | 그룹이 ended/소멸 |
|---|---|---|
| 그룹 자체 목록/상세·관리 신규열람 | 현재 그룹membership/역할로 판정 | GROUP_NOT_FOUND/신규권한 없음 |
| 그룹전용 신규 검색/신청/참가 | 현재 그룹소속·최종자격 검사 | 차단. 기존공개origin pending도 소멸그룹 신규참가 우회불가 |
| 기존 레이드 참가자의 상세·진행·완료·탈퇴 | 레이드관계로 보장 | 같은관계/독립제한으로 유지 |
| 전체공개 방 신규 모집 | 기존공개정책 | 기존공개정책, 연결표시가 자격을 만들지 않음 |
| 소속배지 | 현재활성그룹+현재membership 기준 | false/비그룹인원 |

구현에서 `_group`의 신규소속검사와 기존참가 검사를 분리한다. 기존참가를 증명하는 persistent membership 및 **해당 실제T/generation**의 CycleMember/assignment가 있어야 보존경로를 쓴다. 다른T 신규가입·새방/재가입을 기존참가로 위장하지 못한다. 소유·claim/lifecycle·캐릭터활동·게임입장/한도 등 독립정책은 기존 동작의 계약대로 유지한다.

cycle_lifecycle.qualify·공통설정 linked_group·검색/상세 접근·출력/배지의 소비지점을 함께 대조한다. 그룹을 떠난 기존 공대장에게 그룹소속 검사를 되씌워 정상 레이드 진행을 막지 않는다. 공개범위의 **그룹전용 전환**은 현재 활성그룹과 현재 그룹membership 검사를 유지한다. 소멸그룹 방은 자동공개전환하지 않으며 기존 접근/진행을 보존하는 것과 공개범위 전환 권한을 구분한다.

표시 확장 시 기존 레이드 reader profile/엄격 DTO를 보존하고 새 opt-in `include_group_state=true`에서만 `group_state{group_id,name,state(active|ended|unavailable)}`를 추가한다. 기본응답은 그대로다. name은 보존된 그룹행, ended_at 종료상태를 사용한다. 실제행이 없으면 이름null/unavailable이며 다른 그룹과 재연결하지 않는다. FK를 끊는 물리삭제는 이번API에 없다. 그룹이름/배지 확장 요청은 detail뿐 아니라 기존상세권한자의 참가카드 조회에도 같은 opt-in으로 적용한다.

## 자격상실 정리·복구승계의 미결정

현재 User.status는 active/disabled를 구분한다. 대표 needs_update·장기미접속·단순 그룹탈퇴·조회실패는 disabled가 아니며 그룹 자격상실로 추정하지 않는다.

2026-10-28 사용자 선택: **모든 원정대의 인증소유권 상실을 그룹 자격상실로 볼지는 미정으로 분리한다.** 이 설계는 정리/승계 실행API를 추가하지 않는다. 요구를 폐기하거나 G3 전체 완료로 표시하지 않으며 G-RECOVERY로 추적한다.

네이티브 대조 질문은 다음 범위만 남긴다.

1. 실제 disabled회원과 모든인증소유권상실·일부상실을 각각 어떤 그룹 필수자격으로 볼지. 서버가 관측한 lifecycle 보류와 영구자격상실을 어떻게 구분할지.
2. 제품의 ‘유효한 다음 가입멤버’가 요구하는 회원/소유/한도조건·동일joined_at tie-break·기존정원 수용불가 시 처리. 대표/활동문제만으로 후임을 제외할지 임의 결정하지 않는다.
3. 유효후임없음은 자동삭제/운영자승격 없이 복구필요 유지. 누가 어떤 복구를 요청할지 후속제품결정이 필요하다.

이 질문은 G-DISPLAY·조건부해산/추방/대표변경·제한방관리의 독립 구현을 막지 않는다.

## 대표 예시

아래는 합성UUID/시각을 쓴 그룹해산 요청·성공ACK다. 실행 API 또는 실제 인수자료가 아니다.

```json
{
  "expected_group_revision": 8,
  "expected_members_revision": 4,
  "expected_membership_id": "00000000-0000-4000-8000-000000000001",
  "expected_membership_revision": 3
}
```

```json
{
  "group_id": "00000000-0000-4000-8000-000000000002",
  "membership_id": "00000000-0000-4000-8000-000000000001",
  "membership_revision": 4,
  "group_revision": 9,
  "members_revision": 5,
  "ended_at": "2026-10-28T09:00:00Z"
}
```

그룹장 방 context에서 permissions는 `make_public/end` 각각 `{allowed,reason}`다. 다인방은 make_public.allowed=true일 수 있어도 end.allowed=false/ROOM_LAST_MEMBER_REQUIRED이며 그룹 해산 자체는 blocked다. 미확인 원장은 blocking_room_count=null/state=unavailable이며 clear와 구분한다.

## 구현·검증·인계 순서

1. 이 명세와 표시명세를 각 #16/#12에 제안 게시. 제품차이/복구질문만 분리하고 UI시안/동일기초시험 회신을 전체구현 선행조건으로 추가하지 않는다.
2. nullable 활동시각/표시근거 등 필요한 최소 후속 migration은 실제 구현시 최신head에서 정한다(현재0033). 이번에0034를 선점하거나 적용하지 않는다. 기존행·FK·과거ACK·sequence/자료는 보존한다.
3. 그룹 원자명령·모집 공통효과/권한분리·동일활성방판정·표시profile·원장접근/배지 소비를 함께 구현한다. 원본 OpenAPI는 구현과 함께 합의범위만 반영한다.
4. 아래 직접경계 시험과 두실행프로필 계약을 검증→의미있는 작업구간 commit/push→원격확인→같은Issue 고정SHA/검증/미확인 인계. 개발서버 반영·Flutter연결·실기기·운영은 구분한다.

구현시 검증할 항목(이번 설계에서 실행하지 않음):

- 현재그룹장/일반멤버/비참가그룹장/탈퇴그룹장·타그룹/위조membership·다른operation token·과다권한 없음.
- 마지막1인/pending실효만료/코드폐기·동시가입/이전/해산/추방/방생성/공개왕복/정원한도변경·group/members/CN CAS.
- 활성C만/N만/양T·완료보관/미완료/다음세대/review/원장없음/DB오류·부분페이지·본인참가검색제외에도 동일해산판정.
- ACK실패/최종만료/주차전환 rollback·응답유실 원key·다른본문·이전/재가입 뒤과거ACK·no-op 활동시각/사용량보존.
- 그룹탈퇴/추방/실제소멸후 기존상세·공대장진행·일정·완료·탈퇴/기록 유지, 다른T신규참가/검색/신청은차단·public origin 예외/공개방정책·전체참가자배지.
- 2명이상 방강제종료 거절·1인C/N종료 효과·예약/점유/신청 원자성·완료기록 보존·독립회원/소유/한도제한 유지.

이번 실제 검증은 소스/고정원문 대조·문서경로/JSON예시·git diff 검사다. 서버/DB/새합성기능시험·회원명령·배포·자료삭제/복원·Flutter기기시험은 미실행이다.
