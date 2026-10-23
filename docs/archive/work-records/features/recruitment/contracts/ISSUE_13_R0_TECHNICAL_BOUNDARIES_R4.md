> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md) · [creation-and-settings](../../../../../features/recruitment/creation-and-settings/README.md) · [participation](../../../../../features/recruitment/participation/README.md) · [scheduling](../../../../../features/recruitment/scheduling/README.md) · [completion-and-records](../../../../../features/recruitment/completion-and-records/README.md) · [membership-actions](../../../../../features/recruitment/membership-actions/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# #13 R0 기술 계약 보완4판 — 필터·명령 context

2026-10-20 / Backend / feat/raid-recruitment / 기준1debffd. 설계 본문d1bdb47 로컬·미push.

공식 인계: [전체50번째 Backend / R0 기술 계약 보완4판](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283620362). 다음 Flutter 두 기술경계 재대조, 최종 API 인수/구현 미완료.

[Flutter 전체49번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283395513)에 대한 기술 답변이다. [보완3판](ISSUE_13_R0_CONTRACT_R3.md)의 필터/그룹 범위·CloseWeeklyRequest/완료 입력과 N1 미정 문구만 대체한다. 이미 확인된 정책·기본 미정/숙련도·좌석·JSON 예시의 나머지는 유지한다. 새 schema/경로는 원본 OpenAPI와 구현에 함께 고정할 계약 제안이며 **현재 구현/최종 소비 인수·서버 반영은 아니다.** 같은 제품 선택을 다시 요청하지 않는다.

## 1. N1 확정 반영

기존 일정이 있는1인 방의 공대장이 변경안을 **명시 본인 확인**하면 본인1표로 변경/예약을 한 transaction에 적용한다. R3의 미채택 표시는 폐기한다. 제안 생성만으로 확인을 대체하지 않는다. 공대장도 POST /v1/raid-schedule-proposals/{proposal_id}/responses의 response=accept를 명시 제출한다. 이 N1 확인은 제안 내용 버전에 연결되고 현재 membership/대상 session/schedule revision을 재검사한다.

확인 직전에 다른 참가자가 합류했으면 최종 잠금 안의 현재 대상과 N2~8 정족수로 재평가한다. A1표/N2면 적용하지 않고 개인 응답만 기록해 Ack.outcome=recorded를 반환한다. N1이면 applied다. 여러 세션은 모든 대상 정족수가 충족돼야 함께 적용한다. GET·시간 경과·무응답은 표가 아니다. 생성자의 수동 최초 지정은 별개이며 자동조율은 추가참가 최소1, 추가0 금지는 유지한다.

## 2. 연결 그룹과 입장 공개범위 분리

RoomCard/RoomSettings의 scope:public/group은 **현재 입장 공개범위**다. group_id:UUID?는 **방의 연결 그룹**으로 정의한다. group_name:string?도 기존 가시 요약 표시 계약에 맞춰 보존한다. group_id가 있으면 scope=public이어도 그룹 연결 방이다. 일반 모집은 group_id=null이다. scope=group이면 group_id가 반드시 있어야 한다.

그룹→공개 전환은 scope만 public으로 바꾸며 연결 group_id/이름을 지우지 않는다. 공개→그룹 복귀는 같은 연결을 사용한다. 원 공개 pending/기존 외부 참가자 보존·승인 예외는 유지한다. 공개 전환이 연결 그룹을 다른 그룹으로 바꾸거나 자동 해제하는 명령은 아니다.

새 생성도 scope=public/group_id=null인 일반 공개뿐 아니라 **scope=public/group_id=값인 그룹 연결 공개**를 허용하는 대응이다. 연결 그룹 설정은 현재 해당 그룹 자격/정책을 서버가 검사하며 expected_group_revision도 값이어야 한다. 생성 context query의 group_id는 입장 scope가 아니라 연결 대상이므로 public에도 전달할 수 있다. 잘못된 그룹을 이름만 붙여 생성하지 못한다. 그룹 연결 생성·공개변경의 기존 actor 정책은 유지한다. 연결 없는 방을 scope=group으로 바꾸는 경우는 정당한 그룹 연결/권한을 함께 검사한 명시 전환이며, group_id를 추정하거나 묵시 연결하지 않는다.

목록 분류는 새 category:general/group_linked/all로 표현한다. general은 group_id=null, group_linked는 group_id!=null이다. 기존 Flutter의 groupId 유무 분류와 대응하며 입장 공개범위 필터와 섞지 않는다. 요청에서 admission_scope:public/group/null을 별도로 지정하면 Room.scope에 적용한다. R3의 목록 query scope=group을 그룹 연결 분류로 사용하는 규칙은 철회한다. 이미 공개된 API로 주장하지 않고 새 adapter가 이 명시 구분을 사용하게 한다.

## 3. 복수 그룹 동일 회원·회원별 캐릭터 필터

### 3.1 권한 내 필터 식별자

그룹별 membership_id만으로 여러 그룹의 동일 회원을 연결할 수 없으므로 전역 user UUID 대신 **조회자·선택 그룹 집합에 한정한 member_ref**를 사용한다. 실제 GroupMembership은 서버 내부 user_id로 동일인을 판별할 수 있으나 그 값을 응답하지 않는다. 현재 조회자가 모든 선택 그룹의 회원 목록을 볼 권한이 있을 때만 그 집합 안의 회원을 합친다.

후보 GET /v1/me/raid-room-filter-context?group_ids=쉼표구분UUID목록.

FilterContext={filter_context_token:string,scope_digest:string,evaluated_at:UTC,groups:[{group_id,revision,members_revision}],members:[{member_ref:string,aliases:[{group_id,group_membership_id}],display:CharacterDisplay?}]}.

- group_ids는 중복 없는 선택 집합이며 정렬한 집합에 context를 바인딩한다. 같은 user가 G1/G2에 현재 속하면 member_ref 하나와 aliases 두 개로 합친다. 다른 사람은 display가 같아도 합치지 않는다.
- member_ref는 서버 비밀값 기반 PRF로 조회자·그룹 집합·권한 세대·내부 subject를 결합한 불투명 참조다. 전역/다른 조회자/다른 그룹 집합에서 재사용 가능한 사용자 식별자로 만들지 않는다. 토큰에는 raw user UUID/회원 매핑을 plaintext로 넣지 않는다. 서버는 현재 허용된 그룹 membership을 읽어 ref를 재구성한다.
- 기존 playerId를 group_membership_id/member_ref로 이름만 바꾸지 않는다. adapter는 해당 context의 aliases를 기준으로 회원 선택을 합친다. 그룹 집합/권한/가입세대가 바뀌면 context를 재취득하고 aliases가 현재 정확히 확인되는 선택만 대응한다. 표시명으로 선택을 복원하지 않는다. 확인 불가 선택을 다른 사람으로 자동 대체하지 않는다.
- context는 개인 원정대/전체 캐릭터 목록을 반환하지 않는다. 캐릭터 선택지는 기존 권한 내 공개 캐릭터 projection/표시 원천만 사용한다. 서버는 방 membership의 회원과 그 관계에 저장된 선택 캐릭터를 함께 비교하며 개인 roster를 추가 공개하지 않는다. 현재 캐릭터 사용 자격의 문제는 기존 needs_review 표시/쓰기 가드로 다루고, 필터가 다른 회원의 소유 캐릭터를 대신 대입하지 않는다.
- 기존 그룹 원본의 membership_id는 그룹 내 연결/버전 근거, room의 raid_membership_id는 방 관계다. member_ref가 두 범위를 연결하는 adapter 참조이며 새 권한이 아니다.

### 3.2 정확한 검색 schema

긴 회원별 조건을 평면 query로 손실시키지 않도록 **읽기 전용 POST /v1/raid-rooms/search**를 제안한다. 쓰기 명령이 아니므로 Idempotency-Key/ticket/자료 생성이 없고 인증 판정도 읽기 권한이다. GET 목록의 단순 필터는 유지할 수 있으나 이 구조를 지원하지 않는 GET에 평면 character_ids로 내보내지 않는다.

SearchRequest={category:general/group_linked/all,admission_scope:public/group/null,group_ids:UUID[],filter_context_token:string?,member_conditions:[{member_ref:string,character_ids:UUID[]}],limit:int,cursor:string?}.
SearchPage={items:RoomCard[],directory_revision:Version,filter_scope_digest:string?,next_cursor:string?,evaluated_at:UTC}.

1. 기존 방 가시권한을 먼저 적용한다. group_ids가 있으면 연결 group_id가 그 중 하나인 방만 남긴다(**그룹 OR**). category/admission_scope 조건은 별도로 AND다. group_ids=[]면 그룹 필터 없음이며 member_conditions도 []여야 한다. 회원 조건이 있으면 비어 있지 않은 group_ids와 그 집합의 유효 filter_context_token을 요구한다.
2. member_conditions의 서로 다른 회원은 **AND**다. 한 회원의 character_ids는 **OR**다. character_ids=[]는 그 회원의 어떤 캐릭터라도 포함하면 된다는 뜻이다. 같은 member_ref 중복은400이며 클라이언트가 합쳐 전송한다.
3. 각 회원 조건은 그 사람의 현재 room 관계/공개 캐릭터에서 평가한다. room에 그 회원이 있고 그 회원의 캐릭터가 선택 목록 중 하나여야 한다. 다른 회원이 선택 캐릭터를 가지고 있다는 이유로 충족시키지 않는다. 독립 membership/character EXISTS 두 개로 잘못 계산하지 않는다.
4. 현재 표시되는 지속 회원/완료 상태를 기존 목록 membership 의미대로 취급하고 과거 탈퇴 이력만으로 현재 회원 조건을 충족시키지 않는다. A완료 후 지속 관계가 남으면 A완료표시/그 회원을 보존한다. 다음주 유지 상태가 현재 구성 목록에 있는 경우도 상태를 숨기거나 레이드 불참 토글로 바꾸지 않는다.
5. 그룹 선택이 G1/G2이고 A가 둘 다 속하면 조건 A는 한 번만 평가한다. 같은 room이 join 결과에서 여러 번 나와도 room_id로 unique하게 만든 뒤 정렬/페이지를 적용한다. 방 자체의 연결 group_id는 하나이며 group_ids OR가 회원 조건을 OR로 바꾸지 않는다.
6. 반례: A:{A1},B:{B1} 선택에 A1+B2 방은 불일치다. A1+B1만 일치한다. A:{A1,A2},B:{B1}이면 A2+B1도 일치한다. B 조건을 A의 캐릭터로 대신 충족할 수 없다.

### 3.3 cursor·권한·projection

서버에서 가시권한→그룹OR/회원AND·캐릭터OR→room 중복 제거→안정 정렬(created_at DESC,room_id DESC)→페이지 순서로 처리한다. 페이지 뒤에서 추가 로컬 재필터하지 않는다. 서명 cursor는 actor/정규화한 전체 요청조건·context scope/group 권한 세대·directory_revision·마지막 정렬키에 바인딩한다. 순서만 다른 같은 집합은 같은 digest, 조건 변경/가입세대·권한·목록 세대 변경은409 CURSOR_STALE 또는 FILTER_CONTEXT_STALE로 재조회한다. 세대 고정은 과거 권한을 유지하는 허가가 아니며 매 페이지 현재 권한을 다시 검사한다. 제한/길이·유효기간은 Backend 측정으로 고정한다. 예시 숫자는 확정 상한이 아니다.

R3의 그룹별 최소 projection은 가시 카드 미리보기/기존 watchRecruitmentMembers 연결 용도로 유지한다. 그 projection에는 같은 FilterContext를 query로 연결하면 member_ref를 추가해 방 회원을 필터 선택과 매칭할 수 있다. group_membership_id는 그룹 로컬 값으로 유지하고 그룹 밖/외부 참가자의 member_ref는 null이다. 다른 그룹의 alias나 전역 user ID를 projection에 덧붙이지 않는다. 전체 결과 필터는 위 서버 검색이 담당한다.

권한 실패를 빈 정상 context/일부 그룹 성공으로 바꾸지 않는다. 허가 없는 그룹/대상은 기존404, 유효했던 문맥의 버전 변경은409, 입력 형식 오류는400이다. 공개 연결 방과 현 그룹 회원 배지·원 공개 pending 승인 예외는 별도이며 비참가자에게 참가자 전용 상세/익명busy/개인 원장 접근을 열지 않는다.

## 4. 종료·완료 입력을 권한 내 영향 context로 대체

R3 CloseWeeklyRequest의 다른 사람 assignment/weekly_states revision 배열을 제거한다. 본인 /me/raid-weekly-states를 타인 조회에 사용하지 않는다. 공대장 item 전체 완료도 같은 원칙이다.

### 4.1 읽기 context와 입력 출처

후보 GET /v1/raid-rooms/{room_id}/command-context?command=close_weekly/complete_item/personal_completion&round_id=UUID(선택).

CommandContext={room_id,command,cycle_key,context_token:string,issued_at:UTC,expires_at:UTC,actor_membership_id:UUID,actor_membership_revision:Version,room_revision:Version,members_revision:Version,plan_revision:Version,target_round_id:UUID?,effect_scope:room_current_week/item_round/personal_item,impact:{round_ids:UUID[],membership_count:int,assignment_count:int,reservation_segment_count:int,completed_preserved_count:int},continuation:{required:bool,choices_revision:Version?,current_choice:keep/release/null},leadership:{required:bool,transfer_candidates:[{membership_id:UUID,revision:Version,display:CharacterDisplay?}],can_end:bool},permission:Permission}.

close_weekly는 round_id 없이 target_round_id=null로 **방 전체 이번주**를 대상으로 한다. complete_item/personal_completion은 round_id가 필수이며 해당 item만 대상으로 한다. 무관한 round는 지정할 수 없다. impact는 해당 방에서 볼 수 있는 식별자와 필요한 최소 건수다. 타인 원장 revision/캐릭터별 원장 조합·다른 방/예약 ID는 반환하지 않는다.

- close_weekly actor: 이번주 실제 참가자인 현재 회원. 공대장 전용으로 축소하지 않는다. 다음주 자리만 유지하는 사람은 permission.allowed=false/reason=WEEKLY_PARTICIPANT_REQUIRED다. 허용되는 일반 참가자도 같은 영향 범위를 조회한다.
- complete_item actor: 현재 방 공대장. 게임 외부 인원은 영향 집합에 포함하지 않는다.
- personal_completion actor: 해당 현재 assignment 본인. 마지막 item/계속하기 선택과 위임·종료 필요 여부를 context에서 받아 확인 UI를 구성한다.

GET는 RR/READ ONLY/no-store이며 ticket/예약/이력 행을 생성하지 않는다. context_token은 AEAD로 암호화·인증한 짧은 수명의 무상태 snapshot이다. actor/room/command/cycle/대상 round와 room/member/plan/settings/choice·대상 round/assignment/segment/내부 WeeklyState의 정확한 귀속·버전/집합 digest를 담는다. **서명만으로 내부 원장 정보가 읽히는 평문 토큰을 사용하지 않는다.** 발급/만료·키 교체는 서버 시계 기준이다. 유효 시간/크기 상한은 Backend 측정 후 schema에 고정한다.

### 4.2 최종 request 정의

| 명령 | path 후보(/v1) | body(required/null 명시) |
|---|---|---|
| 방 전체 이번주 종료 | POST /raid-rooms/{room_id}/weekly-incomplete-closures | {expected_cycle_key,context_token} |
| 공대장 item 전체 완료 | POST /raid-rounds/{round_id}/completion | {expected_cycle_key,context_token} |
| 개인 item 완료 | POST /raid-rounds/{round_id}/personal-completion | {expected_cycle_key,context_token,continuation_resolution:null 또는 {action:keep/release,expected_choices_revision},leadership_resolution:null 또는 {action:transfer/end,target_membership_id:UUID?,expected_target_revision:Version?}} |

UTC/UUID/Version은 R3 정의를 따른다. 다른 path/명령/actor의 context는400 CONTEXT_TARGET_MISMATCH 또는 비가시 대상404로 거절한다. 종료 대상을 일부만 지정하는 client 배열은 없다. R3 개인 완료의 원장 CAS도 이 token에 넣고, 본인 choice/위임 확인만 context가 반환한 버전을 명시한다. transfer는 후보 ID/버전이 필수, end는 두 값이 null이며 마지막1인 조건을 재검사한다.

### 4.3 쓰기 순서와 경합

인증/최소 대상 가시권한 → idempotency reserve 또는 성공 원 ACK 회복 → token 인증/actor·대상/cycle/만료 검사 → game/room/관련 원장의 정해진 순서 잠금 → 현재 actor 권한/이번주 실제 참가 조건 → 영향 집합 재구성과 모든 내부 버전/귀속·digest 대조 → 명시 resolution의 현재 자격 → 효과 전체 갱신/감사·최소 ACK → 경계 재검사 → commit 순서다.

snapshot 이후 새 가입/다른 사람 완료/예약·원장 귀속 변경/choice 변경/공대장 변경은409 COMMAND_CONTEXT_STALE로 **전체 rollback**한다. 만료는409 COMMAND_CONTEXT_EXPIRED, 주차 변경은409 CYCLE_CHANGED, 권한 상실은403/404, 원본 불가용은503이다. 오류에 타인의 원장값/다른 방 이름은 넣지 않는다. 여전히 허용되는 context를 재취득해 다시 확인하게 한다.

같은 key/body 성공 재송은 현재 인증/원 actor의 최소 ACK 회복 권한을 검사하고 **원 ACK를 먼저 반환**한다. 이후 token이 만료되거나 대상 상태가 바뀌어도 효과를 다시 실행하지 않는다. 정리 후 탈퇴한 본인의 복구를 새 참가 권한으로 막지 않는다. 다른 body 충돌/running/재시도 가능 실패 release는 기존 규칙이다. token은 실행 완료 플래그가 아니며 다른 key로 같은 token을 보내도 현재 버전/상태 변경을 검사해 이중 효과를 방지한다.

context는 영구 권한이나 효과 예약이 아니다. GET로 원장/예약/투표를 만들지 않는다. 대상 변화가 있으면 새 방 전체에 자동 재실행하지 않고 재조회·확인으로 돌아간다.

## 5. 전체 JSON 예시

아래는 합성값이며 실제 token/개인정보가 아니다. member_ref/token은 대응 읽기에서 취득하고 client가 추정하지 않는다. 예시 제한수/유효시간은 계약 상한을 확정하는 숫자가 아니다. 허용된 일반 참가자의 방 전체 종료도 포함한다.

### 5.1 복수 그룹 필터 context — A는 두 그룹에서 하나로 합침

```json
{
  "filter_context_token": "synthetic-filter-context",
  "scope_digest": "synthetic-group-set-digest",
  "evaluated_at": "2026-10-20T03:00:00Z",
  "groups": [
    {
      "group_id": "00000000-0000-4000-8000-000000000001",
      "revision": 3,
      "members_revision": 5
    },
    {
      "group_id": "00000000-0000-4000-8000-000000000002",
      "revision": 4,
      "members_revision": 6
    }
  ],
  "members": [
    {
      "member_ref": "scope-A",
      "aliases": [
        {
          "group_id": "00000000-0000-4000-8000-000000000001",
          "group_membership_id": "00000000-0000-4000-8000-000000000011"
        },
        {
          "group_id": "00000000-0000-4000-8000-000000000002",
          "group_membership_id": "00000000-0000-4000-8000-000000000012"
        }
      ],
      "display": {
        "server_name": "sample",
        "character_name": "A1",
        "class_name": null
      }
    },
    {
      "member_ref": "scope-B",
      "aliases": [
        {
          "group_id": "00000000-0000-4000-8000-000000000002",
          "group_membership_id": "00000000-0000-4000-8000-000000000013"
        }
      ],
      "display": {
        "server_name": "sample",
        "character_name": "B1",
        "class_name": null
      }
    }
  ]
}
```

### 5.2 회원별 캐릭터 조건을 보존하는 검색 요청

```json
{
  "category": "group_linked",
  "admission_scope": null,
  "group_ids": [
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002"
  ],
  "filter_context_token": "synthetic-filter-context",
  "member_conditions": [
    {
      "member_ref": "scope-A",
      "character_ids": [
        "00000000-0000-4000-8000-000000000021"
      ]
    },
    {
      "member_ref": "scope-B",
      "character_ids": [
        "00000000-0000-4000-8000-000000000031"
      ]
    }
  ],
  "limit": 20,
  "cursor": null
}
```

### 5.3 일반 참가자의 방 전체 종료 context

```json
{
  "room_id": "00000000-0000-4000-8000-000000000040",
  "command": "close_weekly",
  "cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-close-snapshot",
  "issued_at": "2026-10-20T03:00:00Z",
  "expires_at": "2026-10-20T03:05:00Z",
  "actor_membership_id": "00000000-0000-4000-8000-000000000041",
  "actor_membership_revision": 2,
  "room_revision": 7,
  "members_revision": 5,
  "plan_revision": 12,
  "target_round_id": null,
  "effect_scope": "room_current_week",
  "impact": {
    "round_ids": [
      "00000000-0000-4000-8000-000000000051",
      "00000000-0000-4000-8000-000000000052"
    ],
    "membership_count": 3,
    "assignment_count": 6,
    "reservation_segment_count": 6,
    "completed_preserved_count": 1
  },
  "continuation": {
    "required": false,
    "choices_revision": null,
    "current_choice": null
  },
  "leadership": {
    "required": false,
    "transfer_candidates": [],
    "can_end": false
  },
  "permission": {
    "allowed": true,
    "reason": null
  }
}
```

### 5.4 일반 참가자의 방 전체 종료 요청

```json
{
  "expected_cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-close-snapshot"
}
```

### 5.5 공대장 item 전체 완료 context

```json
{
  "room_id": "00000000-0000-4000-8000-000000000040",
  "command": "complete_item",
  "cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-item-snapshot",
  "issued_at": "2026-10-20T03:00:00Z",
  "expires_at": "2026-10-20T03:05:00Z",
  "actor_membership_id": "00000000-0000-4000-8000-000000000042",
  "actor_membership_revision": 2,
  "room_revision": 7,
  "members_revision": 5,
  "plan_revision": 12,
  "target_round_id": "00000000-0000-4000-8000-000000000051",
  "effect_scope": "item_round",
  "impact": {
    "round_ids": [
      "00000000-0000-4000-8000-000000000051"
    ],
    "membership_count": 3,
    "assignment_count": 3,
    "reservation_segment_count": 3,
    "completed_preserved_count": 0
  },
  "continuation": {
    "required": false,
    "choices_revision": null,
    "current_choice": null
  },
  "leadership": {
    "required": false,
    "transfer_candidates": [],
    "can_end": false
  },
  "permission": {
    "allowed": true,
    "reason": null
  }
}
```

### 5.6 공대장 item 전체 완료 요청

```json
{
  "expected_cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-item-snapshot"
}
```

### 5.7 마지막 개인 item 완료 context — 공대장이 아닌 본인

```json
{
  "room_id": "00000000-0000-4000-8000-000000000040",
  "command": "personal_completion",
  "cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-personal-snapshot",
  "issued_at": "2026-10-20T03:00:00Z",
  "expires_at": "2026-10-20T03:05:00Z",
  "actor_membership_id": "00000000-0000-4000-8000-000000000041",
  "actor_membership_revision": 2,
  "room_revision": 7,
  "members_revision": 5,
  "plan_revision": 12,
  "target_round_id": "00000000-0000-4000-8000-000000000051",
  "effect_scope": "personal_item",
  "impact": {
    "round_ids": [
      "00000000-0000-4000-8000-000000000051"
    ],
    "membership_count": 1,
    "assignment_count": 1,
    "reservation_segment_count": 1,
    "completed_preserved_count": 1
  },
  "continuation": {
    "required": true,
    "choices_revision": 3,
    "current_choice": "keep"
  },
  "leadership": {
    "required": false,
    "transfer_candidates": [],
    "can_end": false
  },
  "permission": {
    "allowed": true,
    "reason": null
  }
}
```

### 5.8 개인 완료 요청 — 다음주 유지 의사 확인

```json
{
  "expected_cycle_key": "2026-10-14",
  "context_token": "synthetic-encrypted-personal-snapshot",
  "continuation_resolution": {
    "action": "keep",
    "expected_choices_revision": 3
  },
  "leadership_resolution": null
}
```

5.2는 A1/B1을 선택했다는 합성 예시다. A1+B2 방은 검색 결과에 없고 A1+B1만 포함된다. 결과는 기존 RoomCard의 scope/group_id 의미를2절대로 적용한 SearchPage다. 그룹 연결 공개방이면 scope=public/group_id=해당그룹을 그대로 반환하며 category=group_linked에 속한다. context/검색의 member_ref는 같은 선택 그룹 집합에서만 매칭한다.

5.3/5.4는 actor가 공대장이 아닌 현재 실제 참가자여도 허용되는 예시다. 원장/타인 assignment 버전 배열은 없다. 5.5/5.6은 공대장 권한으로 선택한 item에만 완료를 적용한다. 5.7/5.8은 본인의 마지막 개인 item과 다음주 유지 확인이며 타인 위임이 필요하지 않은 경우다. 공대장에게 위임이 필요하면 leadership.transfer_candidates의 ID/버전으로 transfer resolution을 채우고 현재 조건을 재검사한다. 모든 성공은 기존 Ack로 응답하고 plan/해당 application·본인 weekly 등 필요한 조회를 갱신한다. 읽기 context에서 승인/완료 효과가 발생하지 않는다.

## 6. 검증과 다음 단계

문서의 JSON8개/필수형태·합성참조 관계와 회원AND/회원별캐릭터OR 반례·복수그룹OR/동일인합침/방중복제거/페이지전필터, 일반참가자 종료 입력의 타인원장 부재, snapshot 변경 감지·N1 중 합류에 따른 정족수 예시를 표준 Python으로 검사한다. 이는 설계 예시 검증이며 앱/DB transaction·실제 암호화 구현의 검증이 아니다.

다음 Flutter는49번째에서 남긴 두 경계만 재대조한다. 이미 확인한 숙련도/기본상태/정책/JSON9개 전체를 다시 요청하지 않는다. Backend는 남은 기술 상한을 측정하고 이 schema를 정확한 OpenAPI/모델·이행/잠금·조회/쓰기 구현과 함께 고정한다. 현재 문서 인계이며 원본 OpenAPI·기능코드/DDL·서버/DB/이미지/자료 변경, 앱 자동시험/provider/Flutter/기기 검증은 없다. Flutter 소스는 읽지 않았다.
