# #13 R0 소비 계약 보완안 R2

2026-10-20 / Backend / feat/raid-recruitment / 기준1435b57. 보완 본문 커밋 e806ee4·로컬/미push.

공식 회신: [전체45번째 Backend / R0 소비 계약 보완2판](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6272271633). 다음 Flutter 재대조, 최종 계약·통합 구현 미완료.

[전체44번째 Flutter 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6272050056)에 대한 보완이다. [R1 초안](ISSUE_13_FIXED_CONTRACT_DRAFT.md)의 아래 해당 정의를 대체한다. 나머지 원자성·권한/개인정보·시간중복 경고·수06 운영/10 플레이·하위 기간 합산은 유지한다. **계약 고정 전 설계이며 구현/원본 OpenAPI/서버 반영이 아니다.** 새 경로·코드·수치 상한은 후보, G 결정은 미채택으로 구분한다.

## 1. 입력 누락과 자원 소유 보완

새 DTO는 required 필드/명시 nullable, strict 타입/UTC 시각과 R1의 원칙을 따른다. 다음 구조를 사용하며 R1의 session_drafts만으로 후보 날짜 대안을 표현하지 않는다.

### 1.1 생성·방 설정

CreateRequest 후보 필드:

- title:string(기존 후보 1..60), scope:public/group, group_id:UUID?, admission_mode:leader_only/direct_join.
- app_mode:single/mixed_bundle, items:CreateItem[], selection:CharacterSelection, selection_context:SelectionContextRef.
- experience_level:string, combat_requirement:CombatRequirement, continuation:CreateContinuationSettings, schedule_groups:ScheduleGroupInput[].
- expected_cycle_key:CycleKey, expected_catalog_version:string, expected_group_revision:Version? (group 대상일 때만 값).

CreateItem={raid_id:string,difficulty_id:string,duration_minutes:int?}. duration은 기존 10..1440/5분, null은 명시 정책표 기본값이다. CombatRequirement는 R1대로 shared/per_role 및 nullable 십진 문자열이다. experience_level은 기존 experienceLevel의 의미/선택값을 삭제하지 않고 보존하는 필드다. **현재 Backend에는 대응 enum 원천이 없으므로 임의 숙련도 단계·기본값을 만들지 않는다.** Flutter가 현재 화면의 실제 wire 값/표시 대응을 대조한 뒤 정확한 enum을 고정한다. 예시에서 해당 값은 가정하지 않는다. 미확인 값을 다른 숙련도로 자동 치환하지 않는다.

ContinuationSettings={enabled:bool,auto_open_enabled:bool,revision:Version}. 생성 입력에서는 revision을 받지 않는 CreateContinuationSettings={enabled:bool,auto_open_enabled:bool}를 사용하고 selection_context의 정책 snapshot으로 생성 문맥을 고정한다. enabled는 방의 계속하기 제공 설정이며 개인 choice와 다르다. enabled=false이면 auto_open_enabled=false만 허용한다. 자동 기본값은 G5로 남기고, 생성 화면의 실제 선택값을 명시 전송하게 해 서버가 생략을 true로 보충하지 않는다. enabled/auto_open을 나중에 바꿀 때 기존 choice를 자동 삭제하거나 미래 예약을 만들지 않는다.

방 소유 설정 조회: GET /v1/me/raid-rooms/{room_id}/settings → RoomSettings={room_id,revision,experience_level,combat_requirement,continuation,scope,group_id,admission_mode,permissions}.

수정 후보 PUT /v1/raid-rooms/{room_id}/settings body={expected_room_revision,expected_settings_revision,expected_cycle_key,experience_level,combat_requirement,admission_mode}. 공대장만 edit_settings 가능하다. 기존 참가자의 현재 캐릭터를 새 문턱으로 소급 추방하지 않고 신규 참가/명시 캐릭터 변경에 현 조건을 검사한다. 다른 효과를 원하면 별도 제품 결정으로 남긴다.

반복 설정은 별도 PUT /v1/raid-rooms/{room_id}/continuation-settings body={expected_room_revision,expected_continuation_revision,expected_cycle_key,enabled,auto_open_enabled}. 권한 edit_continuation. 설정 효력 시각과 예정 이벤트 생성/취소는 G5/G2에 따라 고정하고 이미 적용된 개시 이벤트/floor를 덮지 않는다. 모든 쓰기는 Idempotency-Key, ACK와 재조회 규칙을 따른다.

### 1.2 후보 하루와 선택일마다를 구분하는 일정 그룹

ScheduleGroupInput:
{client_group_key:string,existing_group_id:UUID?,expected_group_revision:Version?,occurrence_mode:one_of/each,planning_mode:unscheduled/manual/coordinated,required:bool,auto_confirm_additional_members:int?,alternatives:ScheduleAlternativeInput[]}.

ScheduleAlternativeInput:
{client_alternative_key:string,existing_session_id:UUID?,expected_session_revision:Version?,weekday:int1..7,starts_local:HH:mm?,leader_latest_start_local:HH:mm?,item_order:string[]}.

- client key는 해당 요청 내 참조/중복 검사 용도이며 서버 UUID로 해석하지 않는다. 생성 시 기존 ID/revision은 null, 편집 시 둘 다 값이다. item_order는 생성 시 raid_id, 생성 후에는 별도 EditAlternative DTO의 item_ids:UUID[]로 모든 대상 항목을 정확히 한 번 지정한다.
- room에 속한 schedule_group이 의도/후보 집합을 보존하고 alternative가 개별 session에 대응한다. one_of는 대안 중 하나를 채택, each는 모든 선택일을 각각 진행한다. one_of 대안을 모두 required 세션으로 합산하지 않는다. 그룹 required는 one_of의 선택된 하나 또는 each의 각 발생에 적용한다. 필수 최소1/선택 명시 참가 요구는 유지한다.
- planning_mode=manual이면 starts_local이 필수, coordinated/unscheduled이면 null이다. coordinated에서 공대장 시간 직접 지정과 자동 조율을 동시에 켜지 않는다. unscheduled도 요일 후보 의도를 보존하되 확정 예약은 없다.
- coordinated의 auto_confirm_additional_members는 공대장을 제외한 **실제 해당 타임 참가 추가 인원수**다. 앱 capacity4에서 2이면 공대장 포함3명이 최초 확정 평가 임계치다. pending 신청은 세지 않는다. 공대장도 그 타임의 실제 참여 대상일 때만 인원에 포함하고 비참가자를 자동으로1명 가산하지 않는다. 범위는 0..app_capacity-1의 후보이며 추가0의 최초 트리거/N1 의미는 G1에서 결정한다. manual/unscheduled는 null이다. 각 alternative가 속한 그룹의 임계치를 적용하고 unrelated 타임 인원을 합산하지 않는다.
- leader_latest_start_local은 저장되는 공대장 상한이며 계산 결과 latest_start와 다르다. 선택 요일의 KST 날짜에 결합하고 상한까지 실제로 가능한 후보만 남겨 earliest/latest를 구한다. 19:00/22:00 후보와 상한21:00이면 latest=19:00이지21:00이 아니다. 상한보다 늦은 manual 입력도 허용하지 않는 안이다. 확정 후 상한/선택일·순서·기간을 바꿔 실제 일정을 바꾸려면 변경안 절차를 거친다.
- 현재 주차의 요일→실제 날짜 변환은 수06시 cycle 기준이다. 해당 수요일 00~06시는 그 cycle에 포함시키지 않으며, 그날 06~10 실제 진행은 금지다. 다음주 대안을 이번주 검색에 섞지 않는다. 날짜를 만들 수 없는 항목은 명시 오류/후보 없음으로 반환하고 자동 이월하지 않는다.
- 같은 시간 적용 체크는 Flutter가 각 alternative에 동일한 starts_local/상한을 전개하는 편집 기능이다. 서버는 체크 UI를 저장할 필요 없이 전개한 행/순서·occurrence_mode를 그대로 복원한다.

읽기 ScheduleGroupView={group_id,revision,client_group_key,occurrence_mode,planning_mode,required,auto_confirm_additional_members,alternatives:[{alternative_id,session_id,weekday,starts_local,leader_latest_start_local,item_ids}],selected_session_id:UUID?,resolution:unresolved/selected/all,candidate_state,permissions}.

one_of는 미선택 selected_session_id=null, 선택 후 실제 session UUID 하나다. each는 selected_session_id=null/resolution=all이며 별도의 sessions 배열로 각 타임을 표현한다. 미선택 대안은 예정 의도일 뿐 확정 participation/예약이 아니다. 확정 후 버려진 대안으로 다른 예약을 생성하지 않는다.

예시: 화요일19시 또는 금요일20시 중 하루를 원하면 occurrence_mode=one_of, alternatives=[{weekday:2,starts_local:"19:00"},{weekday:5,starts_local:"20:00"}]라는 두 행을 유지한다(표시용 축약). 금요일이 선택되면 selected_session_id=금요일 session, 화요일 예약은0이다. occurrence_mode=each이면 두 타임을 모두 반환하고 각 타임의 참가/예약/마감을 검사한다. 조회에서 같은 두 입력 행을 돌려주므로 one_of를 each로 오해하지 않는다.

설정 편집 후보 PUT /v1/raid-rooms/{room_id}/schedule-groups body={expected_cycle_key,expected_plan_revision,expected_members_revision,groups:EditScheduleGroupInput[]}. 기존 그룹 revision을 요구하며 edit_schedule_groups 권한이다. 아직 확정되지 않은 의도만 직접 편집한다. 기존 확정 타임을 바꾸는 요청은409 SCHEDULE_PROPOSAL_REQUIRED로 유도하고 부분 저장하지 않는다. 후보 날짜 중 어느 하나를 선택하는 자동/수동 명령은 그룹 revision과 선택 session을 CAS 검사하고 하나의 원자 transaction에서만 resolution을 확정한다.

**기술안/제품 미결정 구분:** 위 DTO로 두 의도를 잃지 않고 보존한다. one_of 확정 후 대안 자체를 다시 여는 UX, 그룹별 서로 다른 임계치의 편집 허용 범위는 기존 요구를 넘는 경우 결정 후 활성화한다. 존재하는 요구의 삭제/자동 선택을 기본값으로 숨기지 않는다.

### 1.3 동일 의미 저장·복원 예시

아래는 manual의 일정 그룹 입력 전체 예시다. 다른 CreateRequest 필드는 포함하지 않은 유효한 ScheduleGroupInput 객체다. 한 주의 화요일/금요일 순서와 하루 선택 의미를 그대로 보존한다.

```json
{
  "client_group_key": "retry-days",
  "existing_group_id": null,
  "expected_group_revision": null,
  "occurrence_mode": "one_of",
  "planning_mode": "manual",
  "required": true,
  "auto_confirm_additional_members": null,
  "alternatives": [
    {
      "client_alternative_key": "tue",
      "existing_session_id": null,
      "expected_session_revision": null,
      "weekday": 2,
      "starts_local": "19:00",
      "leader_latest_start_local": "21:00",
      "item_order": ["sample-raid"]
    },
    {
      "client_alternative_key": "fri",
      "existing_session_id": null,
      "expected_session_revision": null,
      "weekday": 5,
      "starts_local": "20:00",
      "leader_latest_start_local": "21:00",
      "item_order": ["sample-raid"]
    }
  ]
}
```

sample-raid는 구조 설명용 식별자이며 실제 catalog 값이라는 뜻이 아니다. 서버는 group/session/item UUID를 발급한 뒤 두 alternative의 weekday/starts_local/상한/순서를 그대로 반환하고, 아직 선택 전이면 resolution=unresolved/selected_session_id=null이다. 금요일 확정 후에는 resolution=selected와 금요일 session UUID를 반환하며 화요일 예약은 만들지 않는다. 같은 입력에서 occurrence_mode만 each로 바꾸면 두 타임 모두 진행이라는 다른 의미다. coordinated 예시는 두 starts_local을 null로 바꾸고 auto_confirm_additional_members=2를 명시해 각 타임 실제 참가3명을 임계치로 평가한다. 이 값을 일정 변경 투표 필요2표와 혼동하지 않는다.

## 2. 세션·변경안·계획 버전 식별 정정

R1 ProposalView.proposed_segments를 제거하고 proposed_sessions:[{session_id,segments:ItemSegment[]}]로 바꾼다. 기존 plan.session_segments와 같은 식별 구조이며 target_session_ids와 정확히 일치해야 한다. segment는 session 안에서만 해석하며 (session_id,segment_id) 복합 소유를 검사한다. 동일 round가 재도전 S1/S2에 반복돼도 각 segment를 구분한다.

base_schedule_revisions:ResourceRevision[] 대신 base_schedules:[{session_id,expected_schedule_revision:Version}]를 쓴다. 일반 session.revision과 혼용하지 않는다. 일반 revision은 상태/참가 메타 변경에도 증가할 수 있고 schedule_revision은 적용된 시작/기간/item 순서가 바뀔 때만 증가한다. pending 제안을 만드는 것만으로 현 유효 schedule_revision을 올리지 않는다. ACK resource=session의 revision은 일반 session.revision이며 최신 계획 GET에서 schedule_revision을 별도로 받는다.

plan의 resource ID는 **room_id**다. ResourceRevision{resource:plan,id:room_id,revision:plan.revision}이고 별도 plan UUID를 만들지 않는다. members도 room_id를 ID로 쓴다. plan.revision은 현재 aggregate CAS로 그룹/일정/제안/표·확인 상태 등 계획 표시를 바꾸는 명시 쓰기에 증가한다. 투표 응답마다 plan이 바뀌어도 기존 동일 제안의 개인 표를 취소하지 않는다.

ProposalView의 기존 plan_revision은 혼동을 피하려 **proposal_plan_revision**으로 이름을 바꾼다. ProposalView={proposal_id,revision,proposal_plan_revision,created_from_plan_revision,state,target_session_ids,base_schedules,proposed_sessions,votes,my_response,permissions}다. proposal_plan_revision은 해당 제안 내용 버전이며 현재 plan.revision과 별개다. 내용 수정은 새 제안/새 내용 버전으로 옛 표를 재사용하지 않는다. 현재 명단 변화/개인 응답만으로 내용 버전을 바꾸지 않는다.

ProposalResponse의 plan_revision도 proposal_plan_revision으로 같은 이름을 사용하고 개인 응답을 (proposal_id,proposal_plan_revision,membership_id,membership_generation)에 연결한다.

찬반 요청은 {expected_cycle_key,expected_proposal_revision,expected_proposal_plan_revision,expected_membership_revision,response:accept/reject}. 최신 aggregate plan revision을 필수로 요구해 무관한 다른 참가자의 표 때문에 무한 재충돌시키지 않는다. 서버는 잠금 안에서 현재 명단/각 base_schedule/종료 상태를 검사하고 적용한다. 제안 생성·일정 편집 같은 전체 구조 변경에는 expected_plan_revision을 요구한다.

예: 현재 plan=12, session 일반revision=7/schedule_revision=3에서 제안 P 내용버전1 생성→plan13. 응답 저장→plan14여도 P내용1 표는 유지한다. 적용 시 session 일반revision 증가/schedule_revision4, plan도 증가한다. 최초 base_schedule3을 가진 다른 옛 제안은 새 일정에 덮어쓸 수 없다.

## 3. CAS 입력의 조회 출처·최소 문맥

R1의 오래된 단일 Selection 전체를 다중 item 요청에 중복 복사하지 않는다. **통합 요청은 새 CharacterSelection**:
{registration_id:UUID,character_id:UUID,selected_role:dealer/support,expected_registration_version,expected_ownership_revision,expected_roster_revision,expected_lifecycle_revision,expected_role_summary_version,expected_limits_revision,expected_usage_revision}.

모든 expected는 Version이다. party_no는 방 전체 선택에서 빼고 target_items별로 둔다. 통합 CharacterSelection에는 expected_weekly_revision이 없다. 기존 후보 Selection은 내부 호환 모델로 남기되 단일 item adapter가 target의 weekly/party를 주입한다. 아직 공개하지 않은 기존 후보 request와 새 request를 같은 schema로 조용히 섞지 않는다.

SelectionContextRef={context_token:string}. CreateRequest.selection_context도 이 구조다. GET는 문맥행을 만들지 않고 조회 scope/조건·주차·버전에 바인딩한 서버 서명 토큰을 반환한다. 별도 context UUID/버전은 요구하지 않는다. 토큰은 DB 권위 버전/현재 자격 재검사를 대체하지 않으며 no-store다. 서명/토큰 길이·조회 상한은 G7에서 고정한다.

TargetItemSelection={item_id:UUID,round_id:UUID,party_no:int1..2,expected_round_revision:Version,expected_weekly_revision:Version}. 혼합 앱4의 party_no는 채택된 G3 구성에 따라1만 허용한다. 생성 전 대상은 별도 CreateTarget={raid_id,difficulty_id,expected_weekly_revision,party_no}로 selection context에 반환하고 CreateItem에 같은 필드를 추가해 요청한다. 동일 캐릭터여도 raid별 원장 버전을 각각 요구한다.

| 입력 값 | 현재/후보 조회 출처 | 쓰기 의미 |
|---|---|---|
| registration/ownership/roster/lifecycle | 기존 본인 회원 API에 관련 값이 있으나 모집의 최소 원천은 아래 create/admission context가 같은 snapshot으로 반환 | 본인 관계·실제 현재 값 재검사. 다른 주체의 API 조회 금지 |
| selected role summary version | 기존 GET /v2/me/game-accounts/{registration_id}/characters의 역할 요약, 모집 context의 selected_role_summary_version | 현재 저장 head 버전 CAS. 비교 성공값의 버전과 구분 |
| limits/usage | 기존 GET /v1/me/usage-limits, 모집 context의 limits_revision/usage_revision | 같은 한도 원천·현재 이용 증가 검사, unavailable이면0으로 채우지 않음 |
| item별 weekly | 기존 GET /v1/me/raid-weekly-states 또는 모집 context.targets[].weekly_revision | (본인,character,raid,cycle)별 버전. 아직 행 없음도 서버가 반환한 초기1, 클라이언트 추정 금지 |
| room/members/plan/round | plan 또는 admission context의 room_revision/members_revision/plan_revision/targets[].round_revision | id와 버전 묶음. 같은 item/주차 소유 확인 |
| policy/catalog | create/admission context의 policy_snapshot/catalog_version | 서명/불변 정책 snapshot과 현재 조건 대조. 임의 문자열 만들지 않음 |
| choice/settings/group | choices/settings GET·현재 그룹권한을 반영한 context | 기존 choice/settings 원천 CAS. 그룹의 개인정보 상세를 추가 조회하지 않음 |

새 읽기 전용 GET /v1/me/raid-room-creation-context 후보 query={character_id,selected_role,items:JSON 문자열,group_id?} (items는 [{raid_id,difficulty_id}]의 중복 없는 목록). 응답 CreationContext={expected_cycle_key,server_time,catalog_version,policy_snapshot,context_token,selection:CharacterSelection,targets:[CreateTarget],group_revision:Version?,settings_defaults:{auto_open_default:bool?,experience_levels:[{value,label}]},comparison:PowerComparison,permissions}. 미합의 기본값은 null로 표시하고 생성 시 선택값을 요구한다. raid/difficulty 선택 유효성은 생성에서 재검사한다. 실제 enum 원천 확정 전 experience_levels를 가짜 목록으로 채우지 않는다.

기존 후보 GET /v1/raid-rooms/{room_id}/admission-context를 통합형으로 보완: query={character_id,selected_role,intent:apply/join/change_character}. 응답 AdmissionContext={room_id,room_revision,members_revision,plan_revision,expected_cycle_key,server_time,catalog_version,policy_snapshot,context_token,selection:CharacterSelection,targets:TargetItemSelection[],session_choices:[{session_id,required,join_deadline,permission}],comparison,permissions}. party_no는 context가 가능한 슬롯을 반환하고 최종 선택은 target_items로 전송한다.

Apply/JoinRequest={expected_cycle_key,expected_room_revision,expected_members_revision,expected_plan_revision,expected_policy_snapshot,expected_catalog_version,selection_context:{context_token},selection:CharacterSelection,target_items:TargetItemSelection[],target_session_ids:UUID[]}. R1과 달리 이를 하나의 명시 DTO로 사용한다. 표 밖 선택/중복/잘못된 round/주차는 거절한다. GET 후 경합 시409와 최신 context 재조회로 대응하고 client 자동 채움/replay는 하지 않는다.

### 3.1 공대장 승인과 신청자의 개인정보 분리

공대장 approve의 ‘신청 캐릭터 현 자격 CAS’ 입력 요구를 **삭제**한다. 신청자는 신청 시 자신의 context/선택 CAS를 보낸다. 서버가 검증한 공개 접수 원본·선택 역할/빌드 snapshot을 application에 보존한다. 공대장은 권한 내 검토 응답만 보고 신청자 개인 API/개인 원장 버전을 조회하지 않는다.

GET /v1/raid-room-applications/{application_id}의 관리 응답 ApplicationReview={application:ApplicationView,room_revision,members_revision,plan_revision,server_time,eligibility:{evaluated_at,state:eligible/blocked/unavailable,reasons:string[],comparison:PowerComparison},permissions:{approve,reject}}. eligibility는 읽은 시점 설명이고 예약/승인 보장이 아니다. 외부 신청자가 공개 접수 후 그룹 복귀해도 admission_origin.scope=public로 예외를 검증한다.

ApproveRequest={expected_cycle_key,expected_application_revision,expected_room_revision,expected_members_revision,expected_plan_revision}. 서버가 승인 transaction 안에서 신청 캐릭터 현재 소유·역할값/조건·원장·한도/슬롯·일정/마감과 원신청 예외를 재검사한다. 신청 snapshot은 당시 표시 이력이며 승인 당시 최신 자격의 대용이 아니다. 실패는 현재 사유로 전체 rollback하고 새로 조회한다. 성공한 원 ACK 재송에는 최신 점수로 효과를 다시 실행하지 않는다. 관리 검토에 raw ownership/개인 원장/다른 방 정보는 노출하지 않는다.

## 4. 전체 조회·명령 대응 지도

Flutter44번째 보고 기준 실제 BackendApp 목록 주입은 PendingBackendPartyReadRepository이고 생성/상세/그룹 route도 pending이다. 기존 Domain 인터페이스 존재는 Backend adapter 완성이 아니다. 아래는 **필요 연결의 계약 후보 지도**로, 모두 서버 공개/Flutter 적용 미완료다. 기존 F2 후보 경로는 재사용하되 새 DTO로 고정할 때 명시 교체한다.

공통 Page<T>={items:T[],next_cursor:string?}. 공개/본인/관리 DTO를 섞지 않으며 cursor는 actor/권한/필터·snapshot에 바인딩한다. 최대 페이지 수는 G7에서 정한다.

| 기능 | 후보 경로(/v1)·응답/쓰기 | permissions·미완료 범위 |
|---|---|---|
| 공개/그룹 목록 | GET /raid-rooms → Page<RoomCard> | view_summary, 그룹목록은 현 그룹 권한. 실제 Backend adapter pending |
| 공개 요약 | GET /raid-rooms/{room_id} → RoomCard | view_summary, 현재 비가시 방은404 |
| 참가자 상세 | GET /me/raid-rooms/{room_id} → RoomDetail | view_detail, 그룹 탈퇴한 기존 참가자 접근 유지 |
| 본인 참가 | GET /me/raid-room-memberships → Page<MyRoomMembership> | 본인 scope, 현재/종료 필터와 지속 관계/주차 상태 분리 |
| 본인 신청 | GET /me/raid-room-applications → Page<ApplicationView> | 본인 최소 자료, 그룹 전체 신청 목록과 분리 |
| 신청 목록/검토 | GET /raid-rooms/{room_id}/applications → Page<ApplicationReview>; GET /raid-room-applications/{id} | view_applications는 현재 그룹+기존 관리 권한. 본인 단건은 최소 ApplicationView만 반환하는 구분 schema |
| 방 생성/신청/가입·승인/거절/철회 | R1 경로 + 이 문서 Create/Apply/Join/ApproveRequest | create/apply/join/approve/reject/withdraw, 두 승인방식만 |
| 계획/그룹·제안/확인 | R1 plan/context + 이 문서 schedule-groups/proposed_sessions | edit_schedule_groups/propose_schedule/respond_proposal/confirm_participation. 투표와 신규 신청 승인은 별개 |
| 캐릭터 변경 | POST /raid-rooms/{room_id}/character-changes | change_character:본인 현 관계. Apply/Join과 같은 새 선택 context + membership/영향 assignment·choice/plan CAS. 변경 대상 item/다음주 선택을 명시해 전체 원자 교체 |
| 추방 | POST /raid-rooms/{room_id}/removals | remove_member:현재 공대장, body target_membership_id/현재 대상 revision+관련 round/plan CAS. 완료 생성 없이 해당 대상 남은 예약/활성 귀속만 해제. 자기 추방/공대장 추방을 위임 우회로 허용하지 않음 |
| 배치 | PUT /raid-rooms/{room_id}/formation | edit_formation:현재 공대장, body expected_members/plan + placements:[{membership_id,expected_revision,item_id,party_no,slot_no}]. 현재 캐릭터/역할·게임/앱 구성을 재검사. 시간 변경 동의는 이 명령으로 우회하지 않음 |
| 공개↔그룹 | PUT /raid-rooms/{room_id}/visibility | change_visibility:현 공대장/대상 그룹 자격. body expected_room/members/settings/group revisions,scope,group_id. 원 공개 신청/기존 외부 회원 때문에 그룹복귀를 거절하지 않음 |
| 반복 설정·다음주 조회/선택 | settings/continuation-settings 및 GET/PUT /me/raid-rooms/{room_id}/continuation-choices | edit_continuation/choose_continuation, 본인 choice 조회는 본인 한정 |
| 탈퇴/위임/종료·item 완료/이번주 중단/재개 | R1 경로·효과표 | leave/transfer_leadership/end/complete_item/close_weekly/resume_weekly. G4 제품 미결정은 아래 분리 |

### 4.1 최소 읽기 DTO의 필드

- RoomCard={room_id,revision,title,scope,group_id:UUID?,admission_mode,experience_level,app_capacity,app_member_count,state,items:[{item_id,raid_id,difficulty_id,game_party_size}],schedule_summary:{mode,occurrence_mode,confirmed_starts_at:UTCDateTime[],earliest_start:UTCDateTime?,latest_start:UTCDateTime?},combat_requirement,continuation_enabled,permissions}. 비로그인/비가시 대상의 식별·member 상세는 넣지 않는다.
- RoomDetail={room:RoomCard,settings:RoomSettings,members_revision,members:RoomMember[],my_membership:MyRoomMembership?,plan_revision,permissions}. 큰 그래프/타인 개인표는 detail에 자동 끼워넣지 않고 별도 일괄 context로 조회한다.
- RoomMember={membership_id,revision,room_role:leader/member,group_member:bool,joined_at,character:{character_id,display,selected_role},assignments:[{assignment_id,item_id,round_id,state,party_no,slot_no}],comparison:PowerComparison}. display는 기존 공개 캐릭터 표시 계약만 재사용한다. group_member는 공대장뿐 아니라 모든 상세 조회 권한자에게 제공한다. 단, 비그룹 신청 승인 예외와는 다른 값이다.
- MyRoomMembership={membership_id,revision,room_id,state:current/ended,room_role,joined_at,ended_at:UTCDateTime?,assignments:AssignmentView[],permissions}. 주차 종료만으로 state=ended로 바꾸지 않는다.
- ApplicationView={application_id,revision,room_id,state,created_at,expires_at:UTCDateTime?,admission_origin:{scope:public/group,group_id:UUID?,room_revision},submitted_selection:{character_id,selected_role,display},submitted_items:[{item_id,round_id,party_no}],submitted_build_snapshot,permissions}. submitted_build_snapshot은 신청 시 선택 역할의 표시용 점수/관측/경고·버전이며 현 개인정보 원본 전체가 아니다. 본인/관리 허용 scope만 반환한다.
- ChoicesView={room_id,target_cycle,membership_revision,revision,items:[{choice_id,revision,item_id,raid_id,character_id,selected_role,state:selected/blocked,blocked_reason:string?}],permissions}. 미선택은 []이며 충돌을0/자동이전으로 바꾸지 않는다. 본인 선택 조회와 방 전체 설정을 분리한다.

기존 후보의 표시/복구 필드는 새 최소 DTO 때문에 삭제하지 않는다. RoomCard에는 leader_display/created_at/cycle_key/phase/restricted를 기존 의미로 유지하고 game_items로 단일 raid/difficulty를 확장한다. RoomDetail에는 access:{state,policy_snapshot,evaluated_at,issues}와 본인 관계의 recovery_only/history_only를 유지한다. RoomMember는 is_me/status/status_reason와 role별 build 표시를 유지하며 build의 현재 head와 비교 성공 snapshot을 구분한다. ApplicationView는 ended_at과 당시 snapshot을 유지한다. Page는 조회 종류별 directory_revision/membership_head/applications_revision을 해당 head 값으로 추가 반환해 갱신·cursor 기준을 보존한다. 초기 최소 표는 이 기존 필드를 폐기하라는 뜻이 아니다.

기존 permissions.move_slot→edit_formation, repeat→edit_continuation/choose_continuation, change_scope→change_visibility, complete→complete_item의 명시 adapter 대응을 작성한다. 의미가 다른 두 동작을 같은 bool로 합치지 않는다. 캐릭터 표시 구조와 외부원 배지는 기존 CharacterDisplay에 group_member를 별도 연결하며 타인의 전역 UUID를 추가하지 않는다.

### 4.2 기존 인터페이스의 연결과 제품 분기

캐릭터 변경은 현 활성 item/다음주 choice를 선택 범위로 함께 CAS 검사하고 완료한 과거 snapshot은 불변이다. item 단독 탈퇴/마지막 item 완료 후 지속 관계를 변경/추방 API가 임의 결정하지 않는다(G4). 배치는 G3의 단독4/단독8/혼합앱4 슬롯 정책 확정 뒤 같은 경로에 구현한다. 공개범위는 그룹 복귀 시 기존 외부회원·원 공개 pending 보존/승인 가능을 유지하며 nonGroupParticipants/pendingNonGroupApplications 같은 옛 거절 규칙을 재사용하지 않는다. 새 외부 신청은 현재 공개범위로 검사한다.

## 5. 최근 성공 저장값의 서버 보존 — G6 기술안

### 현재 코드로 확인한 한계

app/game_accounts/models.py의 CharacterRoleSummary는 (user_id,character_id,ownership_revision,role) PK에 현재 summary/version/saved_at만 둔다. profiles.put은 요청 summary가 다르면 해당 JSON을 덮어쓴다. profile_schemas.RoleSummary는 점수/관측 시각의 nullable 쌍을 지원한다. **현재 구현에 별도 최근 성공 수치 보존은 없다.** nullable 불가능이 아니라 null 저장 뒤 옛 성공 관측을 증명할 별도 원천이 없는 상태다.

### 제안할 보존 모델/쓰기 규칙

현재 head와 별도로 RolePowerSuccess={user_id,character_id,ownership_revision,role,power_revision,combat_power:DecimalValue,observed_at,source_summary_version,source_saved_at,analysis_rules_version,observed_lifecycle_revision,integrity_status,issues}를 보존한다. 값·관측 시각·그 버전의 경고를 한 snapshot으로 묶고 같은 P1 저장 transaction에서 갱신한다. 성공은 **서버가 P1 저장을 수락한 유효 수치/관측 쌍**이라는 뜻이며 게임 서버 검증 성공을 뜻하지 않는다. build error/warning 존재만으로 숫자를 버리지 않는다.

| 입력/사건 | 현재 head | 최근 성공 snapshot·비교 |
|---|---|---|
| 유효 수치/관측 쌍 새 저장 | 기존 규칙으로 version 증가 | 더 최근 observed_at이면 교체. 값이 낮아져도 최신 성공 사용 |
| 같은 observed_at의 명시 재분석 | 기존 규칙으로 version 증가 | 더 높은 수락 summary version의 snapshot으로 교체, 최고점 비교 없음 |
| 관측이 더 오래된 지연 도착 | 기존 P1 head 저장 의미 유지 | 최신 성공 관측은 역행시키지 않음. API head와 비교 snapshot의 출처를 각각 반환 |
| 점수/관측 둘 다 null 저장 | 현재 head에 null/현재 issues 저장 | 최근 성공 snapshot 유지. 현재 경고와 성공 당시 경고/시각을 구분 |
| HTTP/분석 실패로 저장 없음 | head 불변 | snapshot 불변. 클라이언트 실패를 서버 성공으로 기록하지 않음 |
| dealer→support 선택 | 각 role head 독립 | support 성공만 사용, 없으면 missing. dealer 값 복사 없음 |
| 소유 이전 | 새 ownership_revision의 head/snapshot 별도 | 과거 소유자 snapshot 사용 금지 |
| lifecycle 변경 | 현재 자격/동일 캐릭터 계보 별도 검사 | 옛 관측의 lifecycle 버전은 보존해 표시. 단순 관측 나이에 따른 TTL 추가 금지, 현재 사용할 수 없는 캐릭터는 기존 자격 가드로 제한 |
| 같은 key/body 재송 | 원 ACK 회복 | head/snapshot 중복 갱신 없음 |

후보 PowerComparison={selected_role,requirement:DecimalValue?,actual:DecimalValue?,state:unrestricted/missing/below/meets,source:flutter_analysis,trust:client_submitted,current_summary_version:Version,success_summary_version:Version?,power_revision:Version,observed_at:UTCDateTime?,success_saved_at:UTCDateTime?,success_issues:AnalysisIssue[],current_issues:AnalysisIssue[]}.

unrestricted는 min=null이면 actual 존재와 무관하다. 문턱이 있고 해당 role 성공 쌍이 없을 때만 missing이다. 비교는 Decimal로 하며 int/double/표시 반올림을 경유하지 않는다. 경고=missing이 아니고 OFF의 강제갱신/새 TTL도 없다. context의 expected_role_summary_version은 현재 head CAS, 실제 판정값의 출처는 success_summary_version/power_revision이다. power_revision은 모집 context 생성 시 서명 snapshot에 포함한다. 초기 성공 없음은 power_revision=1/성공 관련 nullable 필드 null/배열[]로 반환한다. 승인 쓰기는 두 head를 잠금 내 재검사하고 클라이언트가 선택한 옛 높은 값을 쓰지 않는다.

기존 자료 이행: 현재 head에 유효 수치/관측 쌍이 있으면 그 version/saved_at/같은 경고로만 snapshot 초기화한다. 현재 null이고 과거 성공 이력이 없으면 복원할 근거가 없으므로 성공값을 만들지 않는다. 현 원본 데이터가 없는 과거를 '보존 완료'라고 보고하지 않는다. 다음 수락된 유효 역할값부터 원천을 남기며 문턱 없음은 계속 허용한다. 이 메타데이터를 기존 P1 응답에 무단 추가하지 않고 모집 context의 comparison에 먼저 제공하는 설계이며 P1 저장 transaction 확장/추가 migration은 계약 합의 뒤 구현한다.

## 6. 남은 제품 결정과 예시 — 임의 채택 없음

| gate | 보완 사례·Backend 추천 | 미확정 범위 |
|---|---|---|
| G1 대상/표 | 공대장 A가 S1에 불참하고 B/C/D만 참여하면 N3/필요2. A의 제안 행위는 S1 표0, B+C 찬성 시 충족 추천. A가 참가하는 S2에서는 A표1 | 비대상 공대장 표0·N1/추가0·세션별 quorum vs union. 대상0이면 자동 충족 처리하지 않고 대기/새 참가 후 명시 평가하는 안. 제안 권한과 투표 자격 분리 |
| G2 정각/개시 | 10:30 정각 허용 추천, 1마이크로초 뒤 거절. 예정 이벤트06 floor06:30→점검 후10, 실제 수동11→11:30 | 정각 비교 선택/예정 이벤트·이력 보존 구현안. 운영06/플레이10 자체는 확정 |
| G3 구성 | 혼합 앱4는 기존4인 슬롯 추천, 단독8은2파티 유지. 게임8 인원4는 앱 일행만 충족 | 혼합 동일 직업/역할 슬롯 등 구성 채택 |
| G4 부분 완료/중단 | A완료 시 B/C 시각·관계 유지 추천. 마지막item 종료 후 다음주 membership 유지 추천 | 본인완료 탈퇴연동/item단독 탈퇴/중단 묶음범위·현재 assignment 없는 지속회원 선언 자격. 방 전체 선언 요구를 조용히 item만으로 축소하지 않음 |
| G5 반복/choice | 생성 시 auto_open을 명시 선택, 다음주 choice는 미래 예약 아님. 경계 뒤ON은06 소급 없음 추천 | 자동 기본값/설정 효력 시점·blocked 정리. 기존 개인 choice 자동 삭제 없음 |
| G6 점수 보존 | 위 성공 snapshot/역할·관측·버전 규칙으로 보존 추천 | 보존 기술안 대조. 저장값 비교/문턱 없음·missing 정책을 재질문하지 않음 |
| G7 상한 | 임의64구간/7세션 고정 대신 실제 복수구간·대안/재시도·조합을 측정해 상한/budget 결정 | 페이지/구간/세션/합계기간/탐색·토큰 크기 등 기술 수치. 측정 전 성능 보장 없음 |

각 결정은 Flutter 실제 소비 대조에서 불일치/사용자 선택이 필요한 것만 질문한다. 현재 Domain 구현이나 예시가 있다는 이유로 최종 채택으로 바꾸지 않는다.

## 7. 다음 단계와 검증 구분

Backend 보완본 게시 → Flutter request/조회 DTO·버전 출처/기능 지도 재대조 및 실제 experienceLevel 값 대응 → 필요한 G 제품 결정/기술 상한 고정 → 정확한 OpenAPI와 구현을 함께 진행한다. R1~R5 내부 구현 순서는 유지하며 개인표만으로 통합 목표 완료로 축소하지 않는다. 새 서버 테스트/배포 요청이 아니다.

문서/모델·P1 저장 코드 대조와 예시 계산만 수행했다. 기존/신규 서버 코드·migration·원본 OpenAPI·실제 API/DB/이미지/자료는 변경하지 않았다. 앱 자동시험·실서버·provider·Flutter·기기 검증은 실행하지 않았다. Flutter 소스는 읽지 않았고44번째의 실제 소비 조사 보고를 근거로 삼았다.
