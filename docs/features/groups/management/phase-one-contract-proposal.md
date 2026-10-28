# 그룹 관리·레이드 생명주기 1차 계약 제안

2026-10-28 / Backend / `feat/group-management` / G-MANAGE·G-RAID 1차 설계.

게시: 설계 고정 `92c1702` push·원격일치 후 [전체10번째 Backend · 계약 제안](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464713503) 게시·실제순번 확인. 다음 Flutter 소비/정책차이대조·Backend 명세보완이며 구현/기기 인수는 미완료다.

**사용자 승인으로 관리 HTTP·후보계약을 구현했다.** DB0034에서 신규 관리프로필/해산·추방·대표변경·공통방목록을 제공한다. 실제개발서버/DB·배포·Flutter기기인수는변경/완료하지않았다. [구현/검증 기록](../implementation-2026-10-28.md)을 따른다.

## 최신 정책 정정 — 기존 제안의 같은 항목 교체

[Issue16 전체12번째 Flutter · 사용자 확정 정정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464943488)이 초기 개발 요청과 이 문서92c1702의 그룹장 제한명령 제안을 대체한다. **그룹원 누구나 기존 membership/캐릭터/한도 조건으로 그룹전용 레이드를 개설하고 해당 레이드 공대장이 관리한다.** 그룹장 지위만으로 비참가 방의 공개전환/해산 권한을 주지 않는다. 그룹장 이전은 레이드 공대장을 바꾸지 않는다.

그룹장용 command-context/make-public/end 신규 경로·GroupRoomCommand/ACK·해당 토큰/권한/시험은 개발 범위에서 제외했다. 마지막1인 대 다인강제종료 선택은 더 이상 대기 질문이 아니다. 초기 제안은 고정커밋/기존댓글에 이력으로 보존하며 현재 구현 기준으로 쓰지 않는다. 이후사용자구현승인에따라정정된범위의HTTP를구현했으며그룹장전용명령은계속제외한다.

정정 게시: `cb9b6b9` push·원격확인 후 [#16 전체13번째 Backend · 정정결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6465101118)에 회신했다. 당시상태는설계정정/구현전이었으며이후구현승인에따라진행한현상태는구현기록을따른다.

## 기준·문제·기존 구현

근거는 [Issue16 전체9번째 Flutter 개발 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464117245), [전체8번째 그룹 소멸 후 방 보존 정정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6463878563), [설계39 f04f482e](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/backend-migration/39-group-flutter-integration-design.md), 같은 커밋의 [제품 §13/14](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/product/GROUP_PRODUCT_FLOW.md)·[모집37](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/backend-migration/37-raid-scheduling-and-multi-raid-planning.md)다. Backend 대조는 main/dev1b6f57b·그룹준비ea52e56이다.

관리GET·즉시 이전·일반탈퇴는 이미 제공된다. Group.ended_at/과거membership/FK, 그룹 명령 runner·game-mutations-v1 잠금·멱등 ACK를 재사용한다. 기본management 응답은기존 disband=false/STATE_UNAVAILABLE를유지하며 새profile에서실제판정과추방/대표변경을제공한다. 비참가 그룹장 전용 레이드 명령은 최신정책상 개발하지 않는다.

실제 two-cycle 모집 원장은 존재하지만 일반 공통명령은 참가자와 공대장 자격을 함께 요구한다. 또한 cycle_lifecycle.qualify가 현재 그룹소속까지 검사해 단순탈퇴 후 기존진행 보존과 충돌할 수 있다. 기존함수의 권한검사를 제거해 전부 열지 않고 신규 그룹 접근과 기존 레이드 관계의 권한을 구분한다. 표시 조회는 [G-DISPLAY 제안](../discovery/display-contract-proposal.md)을 따른다.

## 권한과 제안 API

| 동작 | 현재 그룹장 | 일반 그룹원 | 비그룹 기존 레이드 참가자 |
|---|---|---|---|
| 그룹 해산/추방/대표변경 | 아래 조건/CAS 충족 시 허용 | 불가 | 불가 |
| 현재 그룹전용 방 목록·기존 상세 진입 | 현재 그룹원 범위 | 같은 현재 그룹원 범위 | 기존 레이드관계의 상세 접근만 |
| 그룹전용 레이드 개설 | 기존 membership/캐릭터/한도 조건 | 같은 조건 | 현재 그룹원 아니면 불가 |
| 공개전환/모집해산 | 해당 레이드 공대장/실제T 권한일 때만 | 같은 레이드 권한 | 기존 레이드 역할/실제T 정책 |
| 기존 레이드 상세/진행/완료/탈퇴 | 원래 레이드 역할로 별도 판정 | 같음 | 현재 레이드 관계/독립 자격으로 판정 |
| 레이드 승인/편성/캐릭터변경/일정·완료 | 그룹장 지위로 추가 허용하지 않음 | 기존 레이드 계약 | 기존 레이드 계약 |

| Method·경로(제안) | 입력/응답 |
|---|---|
| `GET /v1/groups/{group_id}/management?management_profile=group-management-1` | 기존 관리정보 + 해산 판정·추방/대표변경 permissions. 생략 시 기존 DTO 그대로 |
| `POST /v1/groups/{group_id}/disband` | 아래 GroupCAS → GroupDisbandAck |
| `POST /v1/groups/{group_id}/members/{membership_id}/remove` | GroupCAS + expected_target_membership_revision → GroupRemoveAck |
| `PUT /v1/groups/{group_id}/representative` | GroupCAS + 기존 CharacterSelection → GroupRepresentativeAck |
| `GET /v1/groups/{group_id}/raid-rooms` | limit/cursor → GroupRaidRoomPage(현재 그룹원 공통 목록) |

그룹 방 목록은 현재 그룹원 공통 열람이며 신규 그룹장용 관리명령을 제공하지 않는다. 새 그룹 관리 경로의 미지 query/body 필드·중복query/잘못된 enum은400이다. management_profile 생략은 기존 disband=false DTO를 유지하며 신규 기능 소비자는 프로필을 명시한다. 신규 방 목록은 실제 two-cycle 원장이 준비된 실행에만 제공하고 기본0023 앱에 원장없는 우회동작을 추가하지 않는다. 구현 시 두 OpenAPI를 각 프로필과 대조한다.

### 공통 DTO·오류·명령 책임

- GroupCAS: `expected_group_revision`, `expected_members_revision`, `expected_membership_id`, `expected_membership_revision`(기존 LeaveGroup와 같은 필수양의정수/UUID 계약). 대상 membership UUID는 경로에 한 번만 전달한다.
- CharacterSelection: 기존 registration_id/character_id·expected_registration_version/ownership_revision/roster_revision/lifecycle_revision. 선택 활동집합은 같은 잠금 안의 최신값으로 검사한다. 1700 추가 하한은 없다.
- 모든 쓰기는 기존 세션·UUIDv4 Idempotency-Key·동일 actor/operation/target/key/body 결합을 사용한다. 같은 key+다른본문은 기존 멱등 충돌, 진행중/lease/24h/세션철회는 기존 정책을 유지한다.
- 인증401, 현재 그룹원403 GROUP_MEMBERSHIP_REQUIRED, 리더403 GROUP_LEADER_REQUIRED, 없는/종료 그룹404 GROUP_NOT_FOUND, 타그룹/종료 대상404 GROUP_TARGET_UNAVAILABLE, stale409 REVISION_CONFLICT. 새 제품거절은 아래 안정적인 code를 제안하며 기존 envelope/request_id/no-store를 재사용한다.
- 정상 실행 권한을 재검증한 뒤 game-mutations-v1 잠금·동일 DB 트랜잭션에서 효과/사용량/revision/활동시각/ACK를 원자 확정한다. ACK 저장/최종가드 실패는 모두 rollback한다. 외부 I/O는 없다.
- 과거 성공 replay는 현재 membership/리더 재승격을 요구하지 않는다. actor·원명령·원대상·과거 membership 소유 증거를 검사하고 저장된 최소 ACK만 복구한다. 탈퇴/해산/이전/재가입 후 새 관계는 건드리지 않는다.

## 해산 판정과 동일한 그룹원 공통 방 목록

공통 평가 함수는 그룹에 연결된 모집 원본에서 `clear / blocked / unavailable`과 `blocking_room_count: int|null`, `evidence_revision`을 계산한다. unavailable의 count는 null이고 disband.allowed=false/reason=GROUP_RECRUITMENT_STATE_UNAVAILABLE이다. 방 원본 조회의 실제 DB오류는503이며 빈목록200으로 바꾸지 않는다.

1. 우선 RecruitmentRoom.group_id 일치와 현재 scope=group인 방 전체를 검사한다. public은 해산 차단에서 제외하되 연결과 기록을 유지한다. 검색의 필터/페이지/본인방제외 결과를 해산 근거로 쓰지 않는다.
2. ended_at 있는 방은 종료로 분류한다. ended_at이 없고 기존 completed_room_lifecycle.archived가 확정 true면 완료 보관으로 분류한다. 나머지는 차단 대상이며 스스로 새 ‘완료’ 기준을 발명하지 않는다.
3. 원장 migration_state=ready·explicit provenance와 실제 cycle/generation/round 연결을 확인한다. 세대없음/review_required/레거시 미검증·연결모순은 unavailable이다. 미확인 방도 관리 목록에서 누락하지 않고 review 항목으로 제공한다.
4. 실제 C/N row·세대와 지속 방 상태를 사용한다. 현재 페이지에 없거나 해당주차가 미개방인 것은 종료 증거가 아니다. 과거의 미완료/불명확 방도 지속 방이 종료/보관으로 입증되지 않으면 차단한다. 다른 주차를 C/N 별칭으로 변환하지 않는다.

방 목록은 위 차단/미확인 대상 방을 room_id당 한 번 제공한다. 실제T별 상태는 nested targets이며 `room_cycle_id/target_cycle_key/generation/target_revision/state`를 포함한다. 과거 미확인은 해당 실제키와 검토 사유로만 표시하며 현재 명령대상으로 승격하지 않는다. 루트는 `group_id/group_revision/members_revision/evaluated_at/evidence_revision/state/blocking_room_count/items/next_cursor`다. item은 `room_id/title/scope/group_id/room_revision/state/reason/targets`이다. 각 실제T target에 기존 공개용 `leader_display`(이름/서버/직업 또는 null)와 현재T 상세 진입 가능 여부를 제공한다. 그룹해산 안내에서 그룹장이 타 공대장에게 정리를 요청할 수 있도록 안내하되 전역 user_id·신청명단/개인시간표는 공개하지 않는다. 상세 진입은 기존 접근권한을 그대로 재검사한다.

목록은 created_at DESC·room_id DESC, limit기본20/최대50, 전체평가 후 페이지를 자른다. cursor는 actor/session·현재 조회자 membership/revision·그룹 revision·전체 방/세대/evidence·limit에 결합한다. 권한변경은403, 자료변경은409 CURSOR_STALE이다. 목록 count와 해산 검사는 같은 스냅샷에서 같은 집합을 계산하며 모든 변경 명령은 잠금 뒤 다시 계산한다.

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

## 그룹원 개설·기존 레이드 공대장 관리 재사용

- 현재 그룹원은 그룹장/일반멤버 구분 없이 기존 생성 context/POST로 개설한다. 최신 membership·현재선택/소유/생명주기·유효한도 검사는 그대로다. 그룹 가입만으로 레이드 참가를 생성하지 않는다.
- 공개범위·신청 승인·편성·완료·해산은 기존 실제T/세대의 공대장 및 해당 동작 권한을 그대로 사용한다. 다른 레이드의 공대장이라는 이유로 해당T 권한을 얻지 않는다.
- 그룹장 이전은 group의 역할만 바꾸며 기존 C/N 레이드 공대장·원ACK·참가관계를 변경하지 않는다. 그룹장 명목의 새 역할·토큰·명령 namespace를 추가하지 않는다.
- 활성 전용방 때문에 그룹해산이 막히면 공통 방 목록과 실제T의 공대장 표시를 안내한다. 정리는 각 레이드 공대장이 기존 상세의 공개전환/해산 명령으로 수행하고 그룹장은 최신 그룹해산 판정을 다시 조회한다.
- 일반 공대장의 기존 마지막1인·실제참가·상태/기한·CAS/원ACK 조건은 유지한다. 다인방강제종료·그룹장에 의한 다른참가자 명령대행·자동공개전환은 추가하지 않는다.
- 한 방이 public으로 전환되면 그룹해산 차단집합에서 빠지지만 그룹연결·참가·기록은 보존한다. 다시group으로 전환되는 경쟁은 기존 명령과 그룹해산을 같은 잠금/최신그룹상태로 검증한다. 종료그룹으로 새group전환은 거절한다.

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

이 질문은 G-DISPLAY·조건부해산/추방/대표변경·공통방안내의 독립 구현을 막지 않는다.

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

관리GET의 disband 판정은 `{allowed,reason}`다. 활성방이 있으면 그룹해산은 blocked다. 일반멤버도 공통 목록에서 방과 실제T 공대장을 볼 수 있으나 그룹장 지위의 make_public/end 권한은 없다. 미확인 원장은 blocking_room_count=null/state=unavailable이며 clear와 구분한다.

## 구현·검증·인계 순서

1. 이 명세와 표시명세를 각 #16/#12에 제안 게시. 제품차이/복구질문만 분리하고 UI시안/동일기초시험 회신을 전체구현 선행조건으로 추가하지 않는다.
2. 활동시각/표시근거는0034_group_features의확장테이블을사용한다. migration은격리검증에서만적용하고개발DB에는적용하지않았다. 기존행·FK·과거ACK·sequence/자료는 보존한다.
3. 그룹 원자명령·기존 레이드 권한보존·동일활성방판정·표시profile·원장접근/배지 소비를 함께 구현한다. 원본 OpenAPI는 구현과 함께 합의범위만 반영한다.
4. 아래 직접경계 시험과 두실행프로필 계약을 검증→의미있는 작업구간 commit/push→원격확인→같은Issue 고정SHA/검증/미확인 인계. 개발서버 반영·Flutter연결·실기기·운영은 구분한다.

구현시 검증할 항목(이번 설계에서 실행하지 않음):

- 현재그룹장/일반멤버의동등개설·공통목록·타그룹/위조membership 거절, 비참가그룹장은공대장명령거절·그룹장이전후레이드리더불변.
- 마지막1인/pending실효만료/코드폐기·동시가입/이전/해산/추방/방생성/공개왕복/정원한도변경·group/members/CN CAS.
- 활성C만/N만/양T·완료보관/미완료/다음세대/review/원장없음/DB오류·부분페이지·본인참가검색제외에도 동일해산판정.
- ACK실패/최종만료/주차전환 rollback·응답유실 원key·다른본문·이전/재가입 뒤과거ACK·no-op 활동시각/사용량보존.
- 그룹탈퇴/추방/실제소멸후 기존상세·공대장진행·일정·완료·탈퇴/기록 유지, 다른T신규참가/검색/신청은차단·public origin 예외/공개방정책·전체참가자배지.
- 그룹장 전용명령경로미제공·공대장기존해산조건유지·공개왕복/그룹해산경쟁·원ACK/완료기록 보존·독립회원/소유/한도제한 유지.

설계당시에는문서검증만수행했으며이후사용자승인으로구현·격리PostgreSQL검증과두후보계약전체비교를완료했다. 결과는구현기록을따른다. 실제개발서버/DB반영·실회원·배포/자료삭제·Flutter기기인수는미실행이다.
