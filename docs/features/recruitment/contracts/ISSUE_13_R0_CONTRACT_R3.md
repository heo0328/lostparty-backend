# #13 R0 계약 보완3판 — 46/47번째 반영

최신 기술 정정: [49번째 대응 보완4판](ISSUE_13_R0_TECHNICAL_BOUNDARIES_R4.md)이 필터/그룹연결·입장범위, 종료/완료 입력과 N1의 충돌 정의를 대체한다. 나머지 확인된 계약은 유지한다.

2026-10-20 / Backend / feat/raid-recruitment / 기준8639e7b. 설계 본문7e9c2f2 로컬·미push.

공식 인계: [전체48번째 Backend / R0 계약 보완3판](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283178369). 다음 Flutter 소비 재대조, 최종 인수/구현은 미완료.

[Flutter46번째 소비 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6282880292)·[47번째 사용자 결정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283062852)을 반영한다. [보완2판](../development/ISSUE_13_R0_CONSUMER_CORRECTIONS.md)의 충돌 정의는 이 문서로 대체하며 원자성·ACK/보안·명시 중복경고·P1 최근 성공 보존 기술안과 전체 기능 지도는 유지한다. **확정 정책의 계약 반영이며 구현/최종 소비 인수/원본 OpenAPI·실행 서버 반영은 아니다.** 새 경로/오류명은 계약 후보로 구분한다.

## 1. 확정 정책과 수명·효과

| 대상 | 계약에 반영할 동작 |
|---|---|
| 방 참가 전제 | 방 구성원은 모든 모집 item의 레이드 참가자다. raid별/이번주 불참 ON/OFF를 새로 만들지 않는다. item 단독 탈퇴 API/권한은 제외한다. 필수/선택 재도전 타임별 참가와 레이드 자체 참가를 구분한다 |
| 여러 세션 변경 | 각 세션의 현재 참가 집합에 N2=2/N3·4=2/N5·6=3/N7·8=4 적용, 전 대상 충족 시 한 transaction으로 전부 적용. 제안/내용이 같으면 현재 유효한 개인 표 보존 |
| 신규 증가 마감 | 최종 DB now < confirmed_start-30분만 허용. 정각부터 신청/즉시참가/최종승인 거절. 최초 임계치 합류 예외/기존 참가자 confirm은 별도 유지 |
| 혼합 앱4 | 딜러3/서포터1·기존 동일 직업 제한. game_party_size=4/8 유지. 단독8은 앱8/2파티, 혼합 게임8의 나머지는 인게임 모집이며 외부 완료 행을 만들지 않음 |
| A 개인 완료 | 본인의 A assignment=completed/원장 manual 완료·정확한 A 활성 귀속 해제/남은 A segment 해제. B/C assignment·예약·시각 불변. 완료를 탈퇴로 기록하지 않음 |
| 전체 탈퇴 | 본인의 묶음 모든 활성 assignment=left·각 정확한 원장 귀속/남은 예약 해제, 완료 이력 보존. 방 membership 종료. 공대장 위임/마지막1인 종료 조건 유지 |
| 마지막 개인 item 완료 | 함께하기ON이면 본인 다음주 choice/유지 의사에 따라 지속 관계 보존, OFF는 기존 개인 완료·탈퇴 절차. 공대장 위임/종료 확인 필요. 개인 완료와 공대장 전체 완료는 다른 명령 |
| 이번주 미완료 종료 | 함께하기ON 방 전체의 이번주 미완료 round/item·남은 타임을 중단. 이번주 실제 참가 이력이 있는 현재 참가자 누구나 선언, 다음주 자리만 유지하는 회원은 제외. 완료/다음주 선택·과거 이력 보존 |
| 자동 개시 | 기본OFF. 수06 경계 전 ON은 해당 새주, 경계 뒤ON은 다음주부터. 이번주 즉시 개시는 별도 수동. OFF 변경만으로 이미 개시한 모집/예약 종료 없음 |
| 기간 | 각 item 명시값 우선, 없으면 canonical 난이도 대체값. 한 타임 segment 합계<=1440분. 재시도 타임은 각각 검사하며 주간 총합을1440으로 제한하지 않음 |

### 1.1 완료·대기·차주 유지의 표시

AssignmentView에 기존 state와 별도로 raid_participation_state:active/completed/left/stopped_incomplete, completion_source:manual/party/null, completed_at:UTCDateTime?를 반환한다. completed는 A item 아래 그 회원의 '이번 주 레이드 완료' 표시 근거다. completed assignment를 활성 명단에서 지우고 아무 일 없었던 것처럼 처리하지 않는다. 세션 참여/예약 release와 지속 membership은 별도 상태다. 실적 표시의 원천은 assignment/원장 귀속이며 예약 해제만으로 완료를 추론하지 않는다.

MyRoomMembership에는 current_week_state:participating/completed/stopped/next_week_only와 continuation_choice_state:selected/not_selected/blocked를 구분해 반환한다. next_week_only는 이미 합의된 주차 종료/다음주 유지 결과이고 사용자가 레이드 참가를 임의 OFF하는 모드가 아니다. 타임 선택/초록 confirm pending도 레이드 불참·자동탈퇴가 아니다.

A완료 시 다른 회원 A 상태는 불변이다. 마지막 개인 item 완료에서 함께하기ON인데 유지 의사가 정해지지 않았다면 본인 선택 확인 후 같은 명령을 제출한다. 후보 PersonalCompletionRequest는 expected_cycle_key, round/assignment/weekly/membership/plan CAS와 continuation_resolution:null 또는 {action:keep/release,expected_choices_revision:Version}, leadership_resolution:null 또는 {action:transfer/end,target_membership_id:UUID?,expected_target_revision:Version?}를 받는다. 필요한 선택/위임이 빠지면 CONTINUATION_DECISION_REQUIRED 또는 LEADERSHIP_RESOLUTION_REQUIRED로 아무 효과 없이 응답한다. 이미 저장된 유효 choice를 재사용할 때도 버전을 확인한다. 부분 A완료에서 강제로 방 전체 탈퇴/위임을 요구하지 않는다. 완료/정리/위임·필요 종료는 한 transaction으로 적용한다. 정확한 확인 UI/이 필드 매핑은 Flutter 재대조 대상이며 확정 정책을 바꾸는 분기는 아니다.

### 1.2 이번주 전체 종료와 재개

CloseWeeklyRequest={expected_cycle_key,expected_room_revision,expected_members_revision,expected_plan_revision,expected_membership_revision,rounds:[{round_id,expected_revision}],assignments:[{assignment_id,expected_revision}],weekly_states:[{character_id,raid_id,expected_revision}]} 후보다. 서버가 잠금 내 방 전체 현재 미완료 영향 집합을 다시 만들고 누락/변경이 있으면409로 전부 rollback한다. 클라이언트가 round 일부만 보내 효과를 축소할 수 없다. 완료한 round/assignment는 유지한다. next_week_only만인 사람의 선언은403 WEEKLY_PARTICIPANT_REQUIRED다. 재개는 기존 공대장 제안/현재 대상 합의·자격/예약 재검사 절차이며 완료 취소가 아니다.

### 1.3 자동 개시 효력과 시각

설정 읽기에 enabled,auto_open_enabled,auto_open_effective_cycle,revision을 반환한다. 생성 입력에서 auto_open_enabled 기본은 false다. 수06 직전 설정 ON은 그 경계의 새 cycle부터, 경계 정각 또는 이후 ON은 그 다음 경계부터 자동 효력이 생기는 안으로 정밀 경계식을 고정한다. ON 저장 성공 commit 시각과 서버 cycle 경계로 결정하고 client 시각으로 소급하지 않는다. 경계 이벤트와 설정 변경은 같은 game/room 잠금 순서로 직렬화한다.

예약된 권위 이벤트06:00의 stored floor06:30과 worker processed_at을 분리한다. 점검 때문에 실제 최소10:00이며10시부터 다시30분을 더하지 않는다. 실제 수동11시 개시는11:30 하한이다. ON/OFF 변경/retry/GET는 이미 저장한 floor를 이동하지 않는다. OFF는 아직 적용하지 않은 미래 자동 이벤트만 취소하고 현재 개시를 끝내지 않는다. 현재 주차 자동 적용은 미래 설정 효력과 별개로 현 자격/실제 선택을 재검사한다.

## 2. nullable 숙련도와 기존 역할 조회 출처

ExperienceLevel = null | tryLevel | clearExp | multiClearExp | semiExperienced | experienced.

모든 CreateRequest/RoomSettings/RoomCard/설정수정은 experience_level 키를 required로 두되 null을 허용한다. null=제한 없음이고 다른 단계로 대체하지 않는다. creation-context에는 experience_levels:[{value:"tryLevel",label:"트라이"},{value:"clearExp",label:"클경"},{value:"multiClearExp",label:"다클경"},{value:"semiExperienced",label:"반숙"},{value:"experienced",label:"숙련"}],experience_unrestricted_value:null을 반환한다. unknown 값은400, fallback 없음이다. 기존 metadata.experienceLevel?.name과 일대일 대응한다.

역할 버전 기존 GET 출처를 **/v2/me/characters/{character_id}/personal-profile**의 dealer.version/support.version으로 정정한다. Backend profile_router.py/PersonalProfileOut도 이 경로/구조를 확인했다. lifecycle characters 응답에는 역할 요약을 추가하지 않는다. 새 모집 context가 CharacterSelection의 관련 버전을 한 snapshot으로 제공하는 방향은 유지한다. 최근 성공 출처 버전과 현재 role head CAS 버전은 서로 다르다.

## 3. 통합 입력 타입 — 이 정의가 앞선 중복 정의를 대체

이 문서에서 Version=1..2147483647 strict int, UUID는 canonical UUID 문자열, UTC는 RFC3339 Z/+00:00, DecimalValue는 기존 P1 비음수 십진 문자열이다. 모든 필드 required, ?만 nullable, 모르는 필드/중복 ID/키 거절. UUIDv4 Idempotency-Key는 쓰기 header다. 아래 기존 CharacterSelection expected 필드는 모두 Version이다.

| 타입 | 필드 |
|---|---|
| CharacterSelection | registration_id:UUID,character_id:UUID,selected_role:dealer/support,expected_registration_version,expected_ownership_revision,expected_roster_revision,expected_lifecycle_revision,expected_role_summary_version,expected_limits_revision,expected_usage_revision |
| CreateItem | raid_id:string,difficulty_id:string,duration_minutes:int?,expected_weekly_revision:Version,party_no:int |
| TargetItemSelection | item_id:UUID,round_id:UUID,party_no:int,expected_round_revision:Version,expected_weekly_revision:Version |
| CombatRequirement | input_mode:shared/per_role,dealer_min:DecimalValue?,support_min:DecimalValue? |
| CreateContinuation | enabled:bool,auto_open_enabled:bool |
| CreateRequest | title:string,scope:public/group,group_id:UUID?,admission_mode:leader_only/direct_join,app_mode:single/mixed_bundle,items:CreateItem[],selection:CharacterSelection,selection_context:{context_token:string},experience_level:ExperienceLevel,combat_requirement:CombatRequirement,continuation:CreateContinuation,schedule_groups:ScheduleGroupInput[],expected_cycle_key:CycleKey,expected_catalog_version:string,expected_group_revision:Version? |
| AdmissionRequest(apply/join 공통) | expected_cycle_key,expected_room_revision,expected_members_revision,expected_plan_revision,expected_policy_snapshot:string,expected_catalog_version:string,selection_context:{context_token:string},selection:CharacterSelection,target_items:TargetItemSelection[],target_session_ids:UUID[] |
| ApproveRequest | expected_cycle_key,expected_application_revision,expected_room_revision,expected_members_revision,expected_plan_revision |

expected_*revision은 모두 Version이다. CreateItem에 뒤 절에서 필드를 더하는 식으로 해석하지 않는다. 생성 전 item은 raid_id로 식별하고 생성 후는 item_id다. party_no는 선택 요청이며 slot_no는 서버가 구성 조건을 검사해 배정한다. 배치 수정 명령만 slot_no를 명시한다. group_id/expected_group_revision은 group 범위에서 값, public이면 null이다. context_token은 서버가 반환한 서명 문맥이며 예시의 문자열을 실제로 쓸 수 없다.

### 3.1 일정 없음·요일만·전체 주차 조율

ScheduleGroupInput={client_group_key:string,existing_group_id:UUID?,expected_group_revision:Version?,occurrence_mode:one_of/each,planning_mode:unscheduled/manual/coordinated,required:bool,auto_confirm_additional_members:int?,day_scope:any_current_cycle/selected_weekdays,alternatives:ScheduleAlternativeInput[]}.

ScheduleAlternativeInput={client_alternative_key:string,existing_session_id:UUID?,expected_session_revision:Version?,weekday:int1..7,starts_local:HH:mm?,leader_latest_start_local:HH:mm?,item_order:string[]}.

- **완전 미정 생성은 schedule_groups=[]가 canonical**이다. 기본 임의 session/요일/예약을 생성하지 않는다. Plan.schedule_state=unscheduled, groups/sessions/segments/participations는[]다. 방 회원/각 item 이번주 assignment·WeeklyState 귀속은 정상 생성하며 일정 없음이 레이드 불참이라는 뜻은 아니다.
- 필수 최소1은 실제 일정을 설정·예약 확정할 계획의 유효성 조건이다. 일정 자체가 없는 기본 생성에 임의 필수 session을 만들기 위한 조건이 아니다. 최초 유효 계획을 저장할 때 최소 필수1을 검사하며 각 required 타임 전원/선택 타임 명시 참가 규칙을 적용한다.
- 요일만 고름: planning_mode=unscheduled,day_scope=selected_weekdays,alternatives에 선택 요일과 starts_local=null을 저장한다. 조회도 같은 의도를 반환한다. 실제 시각/예약은 없고 one_of 대안을 모두 필수로 바꾸지 않는다.
- 요일 제한 없는 자동 조율: planning_mode=coordinated,day_scope=any_current_cycle,occurrence_mode=one_of,alternatives=[]다. 서버가 현 주차 전체에 방 제출표 교집합/다른 활성예약 회피·점검/개시floor/상한·기간을 적용한다. 7개의 필수 타임을 생성하지 않는다. 후보 선택 후 실제 session 하나를 만든다.
- 선택일의 자동 조율: coordinated/selected_weekdays에 weekday별 starts_local=null 대안을 둔다. each이면 각 타임, one_of이면 대안 중 하나다. manual은 selected_weekdays+명시 starts_local만 허용한다.
- 자동조율 추가인원은 **1..app_capacity-1**, manual/unscheduled는 null이다. 추가0은 허용하지 않는다. 공대장도 해당 타임 관계에 따라 세되 방의 레이드 자체 불참 모드는 만들지 않는다.
- 현재 시간/주차만 검색하며 후보 GET는 예약/세션 생성이 없다. 확정 쓰기에서 group/session/assignment·원장 버전을 재검사하고 필요한 계획/예약을 함께 만든다.

ScheduleGroupView는2판의 필드에 day_scope를 추가하고 alternatives[].session_id를 nullable로 정정한다. 시각 없는 대안은 alternative_id만 가지며 실제 session이 만들어진 후에만 session_id를 반환한다. group/alternative와 session은 같은 자원이 아니다.

Plan에는 schedule_state:unscheduled/unconfirmed/confirmed/change_pending, schedule_groups:ScheduleGroupView[], sessions:SessionView[], session_segments:[{session_id,segments}]를 반환한다. any_current_cycle의 미확정 그룹은 alternatives=[]/selected_session_id=null, 확정 뒤는 선택한 날짜·UTC session을 별도로 반환하되 원래 any_current_cycle 의도를 보존한다. 그룹 자체를7요일로 재작성하지 않는다. 기본/미정 상태와 필요한 주간 전체 탐색을 구분한다.

### 3.2 좌석 번호와 adapter

| 구성 | party_no | slot_no | 기존 Flutter 대응 |
|---|---|---|---|
| 단독4 | 1 | 1..4 | partyIndex=0,slotIndex=0..3 |
| 단독8 | 1..2 | 각 party 1..4 | partyIndex=0..1,slotIndex=0..3 |
| 혼합 앱4(게임4/8 무관) | 1 | 1..4 | partyIndex=0,slotIndex=0..3 |

전송은 party_no=partyIndex+1/slot_no=slotIndex+1, 복원은 각각-1이다. 0/null/범위초과를 서버가 보정하지 않는다. 같은 party 내 slot은 unique이며 역할/직업 조건을 같이 검사한다. item별 game_party_size8을 근거로 혼합 앱의 party_no2를 만들지 않는다. 단독8의 두 party를 하나로 합치지 않는다. 실제 슬롯별 역할 위치의 기존 규칙을 재사용하고 UI 인덱스만 바꾼다고 슬롯 자격이 달라지지 않는다.

### 3.3 표 밖의 정확한 의미

context가 제공하지 않은 item/round/slot 소유조합·틀린 주차/캐릭터를 거절한다는 뜻이다. **개인 가능표 밖 명시 신청/승낙·다른 방 시간 중복은 허용+경고**다. 자동 후보만 기존 예약을 피한다. 시간 경고를 신규403/409로 바꾸지 않는다. 점검 구간/개시 하한·일반 마감/주차·동일 캐릭터 원장·한도/역할은 별도로 검사한다.

## 4. 참가 전 그룹권한 필터·최소 projection

기존 그룹 회원 선택 필터에 **기존 그룹 membership_id**를 사용한다. raid membership_id는 방마다 다르므로 회원 필터 ID로 이름만 바꾸지 않는다. group_membership_id는 기존 그룹 회원 목록의 ID이며 그 그룹 범위에서 여러 방의 현재 같은 회원을 연결한다. 전역 user UUID나 새 전역 식별자는 공개하지 않는다.

후보 GET /v1/groups/{group_id}/raid-room-member-projections?room_ids=쉼표UUID목록 → {group_id,members_revision,evaluated_at,rooms:[{room_id,members:[{raid_membership_id,group_membership_id:UUID?,character_id,display,group_member:bool}]}]}.

현재 해당 그룹 회원으로 해당 방 요약을 볼 권한이 있어야 한다. 그룹에 속한 가시 방만 허용하고 조회 대상 외 그룹/비가시 방은 최소404로 처리한다. room_ids의 수/길이는 성능 측정으로 고정할 기술상한이다. 원본 개인표/role summary/예약/전역 user ID/다른 방 데이터는 없다. 외부 참가자는 group_membership_id=null/group_member=false이며 해당 방 공개 캐릭터만 반환한다. 그룹을 떠났다가 재가입해 새 그룹 membership 세대가 생기면 현재 목록의 새 ID로 대조하고 캐시를 폐기한다.

그룹 목록의 전체 결과 필터는 후보 GET /v1/raid-rooms?scope=group&group_id=...&group_membership_ids=...&character_ids=...&member_match=any/all로 **서버에서 페이지 자르기 전에** 처리한다. group_membership_ids/character_ids는 중복 없는 쉼표구분 UUID 목록이다. member_match는 회원 목록 중 any=하나 이상/all=모두 포함이며 생략 시any, 빈 회원 목록은 회원 조건 없음이다. character_ids는 하나 이상 캐릭터 포함 조건이고 회원 조건과는 AND다. 지정한 그룹 회원 ID는 현재 해당 그룹의 기존 목록 ID인지 검사하고 그룹 밖 ID/비권한 식별자의 상세를 노출하지 않는다. 캐릭터 조건도 조회 가능한 가시 방의 공개 projection 범위를 넘는 원본 조회 권한을 주지 않는다. cursor는 이 필터 전체에 바인딩한다. projection은 페이지의 카드/회원 미리보기·기존 watchRecruitmentMembers adapter를 위한 최소 읽기이고 전체 결과 필터의 대체가 아니다. 이 대응으로 필터를 켠 뒤 현재 받은 페이지만 검색해 결과를 누락시키지 않는다.

참가 후 RoomDetail의 group_member 배지는 기존처럼 모든 상세 조회 권한자에게 제공한다. 비참가자의 projection 권한과 참가자 전용 상세/익명busy 권한은 분리한다. 공개 접수 원 pending의 승인 가능 여부는 admission_origin과 승인 시 현재 조건으로 검사하며 현재 group_member=false만으로 거절하지 않는다.

## 5. 잔여 기술 대조와 인계 범위

- 생성자의 수동 최초 시각 지정은 기존 허용이다. 자동 조율은 추가인원 최소1이다. N1 변경 제안의 별도 표 규칙은 아직 사용자 채택이 아니다. 추천은 기존 일정이 있는1인 방의 명시 변경을 자기 확인으로 끝내는 안이지만, 이를 확정 정책이나 추가0 자동 조율로 구현하지 않는다. 정확히 이 사례만 Flutter와 대조하고 N2~8/세션별 quorum 전체를 다시 질문하지 않는다.
- 그룹 목록은 서버 필터로 전체 결과 의미를 보존하고 projection은 가시 카드의 최소 읽기다. 개인 시간표/세팅/전역 user ID를 노출하는 대안은 쓰지 않는다.
- 구간/타임/페이지/토큰·조합 탐색 상한은 Backend가 대표 복수구간·재시도·묶음·8인·경합 자료로 비용/응답량을 측정해 제시한다. 단순 입력을 임의64구간/7타임으로 막거나 기술 숫자를 사용자에게 결정하게 하지 않는다. 타임 합계1440분은 이미 제품 확정이다.
- RolePowerSuccess와 기존 source/head 버전 구분은46번째에서 요구 부합 확인을 받았으나 구현/이행·동시성 검증은 별도다. Nullable 숙련도/기본 미정 생성/좌석 인덱스·기존 DTO 호환까지 소비 대조한 뒤 정확한 OpenAPI와 구현을 함께 진행한다.

다음 Flutter: 이 보완본과 아래 전체 JSON 예시를 재대조하고 남은 타입/조회 권한·필터 대응/N1의 정확한 사례에 한해 차이를 회신한다. Backend는 고정된 범위의 모델/이행·원자 쓰기·조회/계약·시험을 내부 R1~R5 순서로 진행한다. 현재 기존 모집 adapter/route는 pending이며 새 서버 테스트·배포 요청은 아니다.

## 6. 전체 요청/응답 예시

아래 UUID/카탈로그/token은 구조 설명용 합성값이다. 실제 서버 유효값이 아니며 client가 초기 revision/token을 임의 생성해도 된다는 뜻이 아니다. 실제 값은 해당 create/admission/review GET에서 받는다. 예시의 모든 요청 헤더는 Authorization과 Idempotency-Key를 사용하며 헤더 값은 게시하지 않는다.

### 6.1 완전 미정 생성 — POST /v1/raid-rooms

```json
{
  "title": "합성 모집 예시",
  "scope": "public",
  "group_id": null,
  "admission_mode": "leader_only",
  "app_mode": "single",
  "items": [
    {
      "raid_id": "sample-raid",
      "difficulty_id": "normal",
      "duration_minutes": null,
      "expected_weekly_revision": 1,
      "party_no": 1
    }
  ],
  "selection": {
    "registration_id": "00000000-0000-4000-8000-000000000001",
    "character_id": "00000000-0000-4000-8000-000000000002",
    "selected_role": "dealer",
    "expected_registration_version": 2,
    "expected_ownership_revision": 3,
    "expected_roster_revision": 4,
    "expected_lifecycle_revision": 5,
    "expected_role_summary_version": 6,
    "expected_limits_revision": 1,
    "expected_usage_revision": 2
  },
  "selection_context": {
    "context_token": "synthetic-context-not-valid"
  },
  "experience_level": null,
  "combat_requirement": {
    "input_mode": "shared",
    "dealer_min": null,
    "support_min": null
  },
  "continuation": {
    "enabled": false,
    "auto_open_enabled": false
  },
  "schedule_groups": [],
  "expected_cycle_key": "2026-10-14",
  "expected_catalog_version": "synthetic-catalog",
  "expected_group_revision": null
}
```

### 6.2 생성 ACK

```json
{
  "command_id": "00000000-0000-4000-8000-000000000003",
  "outcome": "applied",
  "revisions": [
    {
      "resource": "room",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 1
    },
    {
      "resource": "plan",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 1
    },
    {
      "resource": "members",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 1
    },
    {
      "resource": "item",
      "id": "00000000-0000-4000-8000-000000000011",
      "revision": 1
    },
    {
      "resource": "round",
      "id": "00000000-0000-4000-8000-000000000012",
      "revision": 1
    },
    {
      "resource": "membership",
      "id": "00000000-0000-4000-8000-000000000013",
      "revision": 1
    },
    {
      "resource": "assignment",
      "id": "00000000-0000-4000-8000-000000000014",
      "revision": 1
    }
  ],
  "executed_at": "2026-10-20T03:00:00Z"
}
```

### 6.3 ACK 후 GET /v1/me/raid-rooms/{room_id}/plan — 완전 미정 복원

```json
{
  "room_id": "00000000-0000-4000-8000-000000000010",
  "revision": 1,
  "members_revision": 1,
  "cycle_key": "2026-10-14",
  "server_time": "2026-10-20T03:00:00Z",
  "app_capacity": 4,
  "game_items": [
    {
      "item_id": "00000000-0000-4000-8000-000000000011",
      "revision": 1,
      "raid_id": "sample-raid",
      "difficulty_id": "normal",
      "catalog_version": "synthetic-catalog",
      "game_party_size": 4,
      "round_id": "00000000-0000-4000-8000-000000000012",
      "round_revision": 1,
      "round_state": "active"
    }
  ],
  "schedule_state": "unscheduled",
  "schedule_groups": [],
  "sessions": [],
  "session_segments": [],
  "my_membership": {
    "membership_id": "00000000-0000-4000-8000-000000000013",
    "revision": 1,
    "room_role": "leader",
    "group_member": false
  },
  "my_assignments": [
    {
      "assignment_id": "00000000-0000-4000-8000-000000000014",
      "revision": 1,
      "membership_id": "00000000-0000-4000-8000-000000000013",
      "item_id": "00000000-0000-4000-8000-000000000011",
      "round_id": "00000000-0000-4000-8000-000000000012",
      "cycle_key": "2026-10-14",
      "character_id": "00000000-0000-4000-8000-000000000002",
      "selected_role": "dealer",
      "state": "active",
      "ended_at": null,
      "raid_participation_state": "active",
      "completion_source": null,
      "completed_at": null
    }
  ],
  "my_participations": [],
  "proposals": [],
  "permissions": {
    "edit_schedule_groups": {
      "allowed": true,
      "reason": null
    },
    "leave": {
      "allowed": false,
      "reason": "LEADERSHIP_RESOLUTION_REQUIRED"
    },
    "transfer_leadership": {
      "allowed": false,
      "reason": "TRANSFER_TARGET_REQUIRED"
    },
    "end": {
      "allowed": true,
      "reason": null
    }
  }
}
```

### 6.4 요일만 선택한 전체 생성 요청

```json
{
  "title": "합성 모집 예시",
  "scope": "public",
  "group_id": null,
  "admission_mode": "leader_only",
  "app_mode": "single",
  "items": [
    {
      "raid_id": "sample-raid",
      "difficulty_id": "normal",
      "duration_minutes": null,
      "expected_weekly_revision": 1,
      "party_no": 1
    }
  ],
  "selection": {
    "registration_id": "00000000-0000-4000-8000-000000000001",
    "character_id": "00000000-0000-4000-8000-000000000002",
    "selected_role": "dealer",
    "expected_registration_version": 2,
    "expected_ownership_revision": 3,
    "expected_roster_revision": 4,
    "expected_lifecycle_revision": 5,
    "expected_role_summary_version": 6,
    "expected_limits_revision": 1,
    "expected_usage_revision": 2
  },
  "selection_context": {
    "context_token": "synthetic-context-not-valid"
  },
  "experience_level": null,
  "combat_requirement": {
    "input_mode": "shared",
    "dealer_min": null,
    "support_min": null
  },
  "continuation": {
    "enabled": false,
    "auto_open_enabled": false
  },
  "schedule_groups": [
    {
      "client_group_key": "weekdays-only",
      "existing_group_id": null,
      "expected_group_revision": null,
      "occurrence_mode": "one_of",
      "planning_mode": "unscheduled",
      "required": true,
      "auto_confirm_additional_members": null,
      "day_scope": "selected_weekdays",
      "alternatives": [
        {
          "client_alternative_key": "tue",
          "existing_session_id": null,
          "expected_session_revision": null,
          "weekday": 2,
          "starts_local": null,
          "leader_latest_start_local": null,
          "item_order": [
            "sample-raid"
          ]
        }
      ]
    }
  ],
  "expected_cycle_key": "2026-10-14",
  "expected_catalog_version": "synthetic-catalog",
  "expected_group_revision": null
}
```

### 6.5 요일 제한 없는 조율의 전체 생성 요청

```json
{
  "title": "합성 모집 예시",
  "scope": "public",
  "group_id": null,
  "admission_mode": "leader_only",
  "app_mode": "single",
  "items": [
    {
      "raid_id": "sample-raid",
      "difficulty_id": "normal",
      "duration_minutes": null,
      "expected_weekly_revision": 1,
      "party_no": 1
    }
  ],
  "selection": {
    "registration_id": "00000000-0000-4000-8000-000000000001",
    "character_id": "00000000-0000-4000-8000-000000000002",
    "selected_role": "dealer",
    "expected_registration_version": 2,
    "expected_ownership_revision": 3,
    "expected_roster_revision": 4,
    "expected_lifecycle_revision": 5,
    "expected_role_summary_version": 6,
    "expected_limits_revision": 1,
    "expected_usage_revision": 2
  },
  "selection_context": {
    "context_token": "synthetic-context-not-valid"
  },
  "experience_level": null,
  "combat_requirement": {
    "input_mode": "shared",
    "dealer_min": null,
    "support_min": null
  },
  "continuation": {
    "enabled": false,
    "auto_open_enabled": false
  },
  "schedule_groups": [
    {
      "client_group_key": "whole-current-cycle",
      "existing_group_id": null,
      "expected_group_revision": null,
      "occurrence_mode": "one_of",
      "planning_mode": "coordinated",
      "required": true,
      "auto_confirm_additional_members": 2,
      "day_scope": "any_current_cycle",
      "alternatives": []
    }
  ],
  "expected_cycle_key": "2026-10-14",
  "expected_catalog_version": "synthetic-catalog",
  "expected_group_revision": null
}
```

### 6.6 신청 — POST /v1/raid-rooms/{room_id}/applications

```json
{
  "expected_cycle_key": "2026-10-14",
  "expected_room_revision": 1,
  "expected_members_revision": 1,
  "expected_plan_revision": 1,
  "expected_policy_snapshot": "synthetic-policy",
  "expected_catalog_version": "synthetic-catalog",
  "selection_context": {
    "context_token": "synthetic-applicant-context"
  },
  "selection": {
    "registration_id": "00000000-0000-4000-8000-000000000021",
    "character_id": "00000000-0000-4000-8000-000000000022",
    "selected_role": "dealer",
    "expected_registration_version": 2,
    "expected_ownership_revision": 3,
    "expected_roster_revision": 4,
    "expected_lifecycle_revision": 5,
    "expected_role_summary_version": 6,
    "expected_limits_revision": 1,
    "expected_usage_revision": 2
  },
  "target_items": [
    {
      "item_id": "00000000-0000-4000-8000-000000000011",
      "round_id": "00000000-0000-4000-8000-000000000012",
      "party_no": 1,
      "expected_round_revision": 1,
      "expected_weekly_revision": 1
    }
  ],
  "target_session_ids": []
}
```

### 6.7 신청 ACK

```json
{
  "command_id": "00000000-0000-4000-8000-000000000023",
  "room_id": "00000000-0000-4000-8000-000000000010",
  "application_id": "00000000-0000-4000-8000-000000000024",
  "revision": 1,
  "state": "pending",
  "executed_at": "2026-10-20T03:01:00Z"
}
```

### 6.8 승인 — POST /v1/raid-room-applications/{application_id}/approve

```json
{
  "expected_cycle_key": "2026-10-14",
  "expected_application_revision": 1,
  "expected_room_revision": 1,
  "expected_members_revision": 1,
  "expected_plan_revision": 1
}
```

### 6.9 승인 ACK

```json
{
  "command_id": "00000000-0000-4000-8000-000000000025",
  "outcome": "applied",
  "revisions": [
    {
      "resource": "room",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 2
    },
    {
      "resource": "members",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 2
    },
    {
      "resource": "plan",
      "id": "00000000-0000-4000-8000-000000000010",
      "revision": 2
    },
    {
      "resource": "application",
      "id": "00000000-0000-4000-8000-000000000024",
      "revision": 2
    },
    {
      "resource": "membership",
      "id": "00000000-0000-4000-8000-000000000026",
      "revision": 1
    },
    {
      "resource": "assignment",
      "id": "00000000-0000-4000-8000-000000000027",
      "revision": 1
    }
  ],
  "executed_at": "2026-10-20T03:02:00Z"
}
```

6.4의 조회는 schedule_state=unscheduled이며 같은 one_of/weekday2/starts_local=null 의도를 반환한다. 저장된 group/alternative UUID·revision과 서버 item_ids를 붙이며 시각 없는 대안은 확정 session/예약으로 만들지 않는다. 6.5는 현 주차 전체 탐색 의도를 보존하고 임계치 도달 전에는 candidate_state=not_evaluated/선택 session 없음이다. 실제 후보가 없으면 no_candidate, 제한에 도달하면 search_limited로 구분한다. 입력의 []를7개의 필수 타임으로 바꾸지 않는다.

6.6의 신청자 선택값/원장 버전은 신청자 자신의 context에서 받은 합성 예시다. 일정 미정이라 target_session_ids=[]이며 향후 유효한 필수 일정이 설정되면 방 구성원으로 그 일정의 참여/변경 확인 절차에 들어간다. 지금 미정이라는 이유로 레이드 자체 불참자로 만들지 않는다. 6.8의 공대장 승인에는 신청자의 개인 역할/소유/원장 버전 입력이 없다. 서버가 신청 snapshot과 현재 자격·원장·한도·자리/시간조건을 재검사하고 같은 transaction으로 반영한다. ACK 뒤 plan/application을 재조회하며 승인 결과는 새 회원/assignment가 추가된 상태다. direct_join 모드의 즉시참가는 6.6과 같은 AdmissionRequest를 /join에 보내고 Ack를 받는 별도 명령이다.

## 7. 검증·미실행

문서의 전체 JSON 요청/ACK와 기본 미정 plan 예시를 구문/필수키·형태로 확인하고, 좌석0↔1 왕복·마감 정각 거절/직전 허용·item 합계1440/초과와 재시도별 분리·A만 완료/B,C 불변·자동ON 경계 효력 사례를 표준 Python으로 검사했다. 실제 앱/API 동작 검증이 아니라 설계 예시 검사다. Backend 기능코드/DDL/원본 OpenAPI/서버·DB/이미지/자료 변경 및 앱/실DB/provider/Flutter/기기 시험은 없다. Flutter 소스는 접근하지 않았고 공식46/47번째 보고를 근거로 삼았다.
