# #13 통합 모집 계약 고정 초안 R1

최신 기준: [46/47번째 반영 보완3판](ISSUE_13_R0_CONTRACT_R3.md). 이 문서의 G 미정/정각 포함 추천·item 단독 탈퇴/자동 기본값·합계 기간과 충돌하는 정의는3판으로 대체한다. 최종 소비 인수·구현과는 구분한다.

후속: [Flutter44번째 대응 R0 소비 계약 보완안](ISSUE_13_R0_CONSUMER_CORRECTIONS.md)이 입력/세션 식별·버전/CAS 출처/전체 기능 지도·점수 보존의 해당 정의를 대체한다. 원래 초안의 누락 필드나 약칭을 최종 schema로 구현하지 않는다.

2026-10-20 / Backend / feat/raid-recruitment / 검토 기준 7b10616. 설계 본문 로컬 커밋 35dd5f9·미push.

공식 회신: [#13 전체43번째 Backend / R0 계약 고정 초안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507). 다음 담당은 Flutter 실제 소비 대조이며 최종 계약/구현은 미완료다.

**계약을 확정하기 위한 초안이며 최종 합의·구현·OpenAPI 반영이 아니다.** [Flutter 전체41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136), [전체42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011), [최신 정책](ISSUE_13_OCT20_POLICY_REVISION.md)을 기준으로 한다. 아래 경로·새 오류명은 후보이며 G1~G7의 미결정을 합의된 요구와 구분한다. 이 문서는 이전 31/33/40번째 설명과 충돌하는 부분을 대체한다.

## 1. 자원·시간·쓰기 원칙

- 지속 room/membership → 모집 item → 주차 round/assignment를 분리한다. room_session은 방의 공유 일정이며 item_session_segment가 해당 item의 round와 연결한다. 묶음 session을 한 round의 소유로 두지 않는다. 시간 예약은 participation/assignment와 segment에 귀속된다.
- 같은 회원의 서로 다른 방 시간 중복은 명시 신청·참가·승낙·확인·예약의 거절 사유가 아니다. 성공과 함께 경고하며 두 예약을 보존한다. 자동 추천만 기존 예약을 피한다. 동일 캐릭터/raid/cycle 참가·완료, 슬롯·한도·소유·CAS 가드는 유지한다.
- 주차/반복 운영 경계는 수요일 KST 06시다. 실제 진행 구간만 수요일 [06:00,10:00)에 겹칠 수 없다. 06시에 10시 시작 일정을 제안·동의·확인·예약할 수 있다.
- DTO 필드는 snake_case, 식별자는 UUID다. Version은 1..2147483647의 strict int, CycleKey는 기존 KST 수요일 날짜, UTCDateTime은 RFC3339 Z 또는 +00:00, DecimalValue는 기존 P1의 비음수 십진 문자열(max32)이다. 암묵적 문자열/숫자 변환·알 수 없는 필드·중복 키를 거절한다.
- 아래 DTO의 필드는 모두 required이며 ?만 nullable이다. 배열의 부재는 []로 표현한다. map의 키는 해당 자원에 허용되는 아래 명령명이다. Permission={allowed:bool,reason:string?}이며 허용 시 reason=null이다.
- GET는 일관된 읽기 전용 snapshot/no-store다. 행·lease·예약·개시 이벤트를 생성하거나 투표를 적용하지 않는다. 명시 갱신과 쓰기 ACK 후 GET를 사용하고 상시 polling을 추가하지 않는다.
- 새로운 개인표/모집 쓰기는 현재 인증 원정대 보유 회원만 가능하다. 기존 회원의 조회·확인·정리 권한은 새 신청 자격과 분리한다. 자격 상실을 자료 자동 삭제나 종료한 회차 복원의 근거로 삼지 않는다.

## 2. DTO와 읽기 계약

| DTO | required 필드 |
|---|---|
| ResourceRevision | resource:room/members/plan/item/round/session/membership/assignment/participation/proposal/choice/weekly/ownership/continuation/application, id:UUID, revision:Version |
| EditInterval | weekday:int1..7(ISO 월~일), start/end:HH:mm, end_day_offset:0/1 |
| NormalInterval | start_minute:int0..10079, end_minute:int1..10080; start<end |
| Availability | exists:bool, version:Version, timezone:Asia/Seoul, intervals:EditInterval[], normalized_intervals:NormalInterval[], updated_at:UTCDateTime? |
| Submission | membership_id:UUID, revision:Version, state:missing/ready/unavailable, source_personal_version:Version?, intervals:EditInterval[], normalized_intervals:NormalInterval[], submitted_at:UTCDateTime? |
| AssignmentView | assignment_id:UUID, revision:Version, membership_id:UUID, item_id:UUID, round_id:UUID, cycle_key:CycleKey, character_id:UUID, selected_role:dealer/support, state:active/completed/left/stopped_incomplete, ended_at:UTCDateTime? |
| SessionView | session_id:UUID, revision:Version, round_ids:UUID[], required:bool, mode:unscheduled/manual/coordinated, state:unconfirmed/confirmed/change_pending/finished/cancelled, schedule_revision:Version, starts_at/ends_at:UTCDateTime?, duration_minutes:int, duration_source:item_sum, duration_policy_version:string, earliest_start/latest_start/join_deadline:UTCDateTime?, candidate_state:ready/no_candidate/search_limited/stale/not_evaluated, permissions:map |
| ItemSegment | segment_id:UUID, item_id:UUID, round_id:UUID, starts_at/ends_at:UTCDateTime?, duration_minutes:int, duration_source:explicit/difficulty_default, policy_version:string, state:planned/released, released_reason:string? |
| MyParticipation | participation_id:UUID, revision:Version, session_id:UUID, assignment_ids:UUID[], state:active/ended, required:bool, participating:bool, confirmation_state:not_required/confirmation_pending/confirmed, confirmed_at:UTCDateTime?, confirmed_schedule_revision:Version?, reservation_state:none/active/partial/released, overlap_warning:bool, permissions:map |
| ProposalResponse | proposal_id:UUID, plan_revision:Version, membership_id:UUID, membership_generation:Version, response:pending/accept/reject/left, response_revision:Version, responded_at:UTCDateTime?, response_set:existing/newcomer |
| VoteStatus | session_id:UUID, eligible_count:int>=0, accepted_count:int>=0, required_votes:int>=1, satisfied:bool |
| ProposalView | proposal_id:UUID, revision:Version, plan_revision:Version, state:pending/applied/cancelled/obsolete, target_session_ids:UUID[], base_schedule_revisions:ResourceRevision[], proposed_segments:ItemSegment[], votes:VoteStatus[], my_response:ProposalResponse?, permissions:map |
| Ack | command_id:UUID, outcome:applied/recorded/noop, revisions:ResourceRevision[], executed_at:UTCDateTime |
| ApplicationAck | command_id:UUID, room_id:UUID, application_id:UUID, revision:Version, state:pending/accepted/rejected/withdrawn/expired/cancelled, executed_at:UTCDateTime |

참가 이력이 없으면 my_participations=[]이며 ID 없는 not_joined 객체를 만들지 않는다. confirmed_at은 해당 일정에 대한 본인 확인 시각으로 게임 참가·클리어 증거가 아니다. 현재 일정 확정과 변경안 pending은 분리한다. ItemSegment의 시작/종료는 함께 null이거나 유효한 UTC 구간이며, 확정 시 순서대로 이어진 구간 합계가 session 기간과 같다. 세션별 실제 segments 배열은 plan의 session_segments:[{session_id,segments:ItemSegment[]}]로 반환한다.

### 2.1 개인 가능표·방 제출표

후보 GET/PUT /v1/me/play-availability. PUT body={expected_version,timezone,intervals}이며 신규 미저장 version은 1이다. UUIDv4 Idempotency-Key를 사용한다. 편집 한 구간은 5분 단위·0분 초과·24시간 이하, end_day_offset은 0/1이다. 원본 편집 행과 행 순서를 보존하고 정규화 구간은 서버에서 파생한다. 수요일 23:00→03:30/+1을 수~목 일정으로 재편집할 수 있어야 한다. 겹침/인접은 정규화에서 합치고 일요일 넘김은 주기 경계에서 분할한다.

미저장은 exists=false/version1/updated_at=null/두 배열[]이다. 저장한 빈 표는 exists=true이며 항상 가능하다는 뜻이 아니다. 전체 치환이며 실제 변경만 version을 올린다. 개인표 변경으로 이미 제출한 방 표나 확정 예약을 바꾸지 않는다.

방 복사/재취득 후보 PUT /v1/me/raid-rooms/{room_id}/availability-submission body={expected_personal_version,expected_submission_revision,expected_membership_revision}. 미제출 표도 revision1의 missing 상태로 읽고 최초 쓰기에서 생성한다. 원본·정규화·source version을 한 snapshot으로 저장한다. 원본 변경 경합은 409다. GET는 복사하지 않는다. 복사는 일정 변경 동의가 아니며 현재 일정과 표가 어긋나면 경고한다. 본인의 표 밖 명시 참여를 차단하지 않는다.

### 2.2 방 계획·개인 상태

후보 GET /v1/me/raid-rooms/{room_id}/plan 반환:

- room_id, revision, members_revision, cycle_key, server_time, app_capacity.
- game_items:[{item_id,revision,raid_id,difficulty_id,catalog_version,game_party_size,round_id,round_revision,round_state}].
- sessions:SessionView[], session_segments, my_assignments:AssignmentView[], my_participations:MyParticipation[], proposals:ProposalView[].
- my_membership:{membership_id,revision,room_role,group_member}, permissions.

계획 revision은 이 DTO의 plan CAS 버전이다. 확인 권한 키는 confirm_participation, 제안 응답은 respond_proposal, 방 계획에는 edit_sessions/propose_schedule/leave/transfer_leadership/end/complete_item/close_weekly/resume_weekly/open_recruitment를 사용한다. 서버 판단이 최종이며 GET 이후의 경합도 쓰기에서 재검사한다. 초록 confirmation_pending, 신규 proposal response pending, 기존 개인 accept/reject를 각각 표시한다.

### 2.3 일괄 그래프·본인 중복 요약

후보 GET /v1/me/raid-rooms/{room_id}/schedule-context 반환:
{room_id,cycle_key,members_revision,plan_revision,evaluated_at,members:[{membership_id,display,submission:Submission,anonymous_busy:{state:ready/unavailable,revision,intervals:[{starts_at,ends_at}]}}],permissions}.

타인의 전역 user ID·개인표 원본·다른 방/레이드명·예약 ID는 반환하지 않는다. busy는 현 주차 유효 예약의 합집합이다. target_session_id query 지정 시 그 세션 자신의 예약을 제외한다. 생략 시 전체 busy임을 구분해 이중 차감하지 않는다. 실패/미확인은 unavailable이고 확인된 빈 결과만 []이다. 체크박스 부분집합 비교는 같은 snapshot에서 로컬 계산하며 투표 분모를 바꾸지 않는다.

후보 GET /v1/me/raid-schedule-overlaps 반환:
{cycle_key,revision,evaluated_at,pair_count,affected_room_count,reservation_count,items:[{pair_id,left:MyOverlapSide,right:MyOverlapSide,starts_at,ends_at}],next_cursor}.
MyOverlapSide={reservation_id,room_id,item_ids,session_id,character_id,character_display,raid_display,room_title,starts_at,ends_at}.

중복은 지금 이후 남은 구간끼리 [start,end)로 계산하고 맞닿는 끝점은 제외한다. 항목은 pair 단위로 양쪽 최소 정보를 같이 반환해 페이지 밖 상대 누락을 막는다. pair_id는 정렬한 두 예약 ID/세대의 digest다. pair/방/예약 수는 페이지 자르기 전 동일한 본인 가시 집합에서 따로 센다. 현재 접근 불가한 쪽의 상세·pair는 노출하지 않고 집계도 가시 집합에 맞춘다. 타인에게는 익명 busy/경고만 제공한다.

캐시는 환경/로그인 회원/cycle/방 권한·계획/제출/busy 세대에 묶고 변경 시 폐기한다. cursor도 같은 조회 조건과 snapshot에 묶는다. 지연 도착한 옛 응답으로 새 상태를 덮지 않는다. 상한과 탐색 budget은 G7이다.

## 3. 쓰기 명령·권한·CAS

모든 모집 명령은 expected_cycle_key와 UUIDv4 Idempotency-Key를 요구한다. 아래 path는 /v1 기준이다. actor는 세션으로 정하며 타인의 user_id를 받지 않는다. revisions 필드는 ResourceRevision[]로, 표에 적은 대상의 현재 버전을 모두 포함하고 중복/누락을 거절하는 후보다. 확인에 필요한 membership ID는 경로 대상과 서버 관계로 검사한다.

| 명령 / path 후보 | 현재 actor | 고유 입력·필수 revisions 대상 | 원자 효과 / ACK 이후 조회 |
|---|---|---|---|
| create / POST /raid-rooms | 인증 원정대 보유 회원 | 아래 CreateDraft, 본인 선택 CAS | room/item/round·creator membership/assignment, 필요한 현재 예약 / plan |
| apply / POST /raid-rooms/{room_id}/applications | 새 신청 자격 보유 회원 | selection, target_items, target_session_ids, room/members/plan·선택 CAS | pending/원 공개접수 snapshot·만료, 예약 없음 / ApplicationAck→본인 application |
| join / POST /raid-rooms/{room_id}/join | 새 참가 자격 보유 회원 | apply와 같은 입력·CAS | 자리/assignment/WeeklyState·현 유효 일정 예약, 최초 임계치 확정 효과 / plan |
| approve / POST /raid-room-applications/{application_id}/approve | 현재 공대장 | application/room/members/plan·신청 캐릭터 현 자격 CAS | 원 공개접수 예외·마감 재검사 후 join과 같은 효과 / plan/application |
| reject 또는 withdraw / POST /raid-room-applications/{application_id}/{명령} | 공대장 또는 본인 | application/room | 현 pending 종료, 예약 생성 없음 / ApplicationAck→application |
| edit_sessions / PUT /me/raid-rooms/{room_id}/sessions | 현재 공대장 | sessions:SessionDraft[], room/members/plan | 미확정 일정 편집만; 확정 일정 변경은 proposal / plan |
| propose_schedule / POST /raid-rooms/{room_id}/schedule-proposals | 현재 공대장 | targets:[{session_id,expected_schedule_revision,starts_at,item_durations}], room/members/plan | 불변 plan_revision/hash·제안자 찬성, 필요 표 검사 / plan |
| respond_proposal / POST /raid-schedule-proposals/{proposal_id}/responses | 현재 제안 대상 회원 | response:accept/reject, proposal/membership/plan | 본인 찬반 표 갱신·현재 대상 재평가, 충족 시 적용 / plan |
| confirm_participation / POST /raid-sessions/{session_id}/participation-confirmations | 해당 기존 참가 본인 | expected_schedule_revision, membership/participation/관련 round·assignment | pending 확인+본인 segment 예약+중복경고 / plan/본인 overlaps |
| leave / POST /raid-rooms/{room_id}/leave | 본인, 공대장은 선행 위임 | membership/영향 assignment·round/plan | 지속 관계와 현재 귀속 종료·본인 남은 예약 해제 / 본인 목록 |
| transfer_leadership 또는 end / POST /raid-rooms/{room_id}/{명령} | 현재 공대장 | 이전 시 target_membership_id, room/members/관련 round/plan | 현 권한 위임 또는 마지막 1인 종료 / plan/목록 |
| personal_completion / POST /raid-rounds/{round_id}/personal-completion | 해당 참가 본인 | membership/assignment/round/weekly/plan·소유 CAS | 본인 item 완료·본인 segment 해제·manual 원장, 방 관계는 G4 / plan/weekly |
| complete_item / POST /raid-rounds/{round_id}/completion | 현재 공대장 | round/members/plan·대상 assignment/weekly | 해당 item의 현재 앱 참가자만 party 완료·잔여 해당 segment 해제 / plan/weekly |
| close_weekly / POST /raid-rooms/{room_id}/weekly-incomplete-closures | 계속하기 ON 방의 현재 참가자 | round_ids, membership/대상 round·assignment/weekly/plan | 이번주 대상 활성 귀속 종료·예약 해제, 완료 생성 없음 / plan/weekly; 범위 G4 |
| resume_weekly / POST /raid-rooms/{room_id}/weekly-resume-proposals | 현재 공대장 | round_ids, members/중단 round/plan | 투표 후 현재 자격 재검사·재개, 완료 취소와 구분 / plan |
| choose_continuation / PUT /me/raid-rooms/{room_id}/continuation-choices | 현재 본인 회원 | target_cycle, choices:[{item_id,character_id,selected_role,expected_ownership_revision}], replaces:[{choice_id,revision}], membership/choice | 다음주 의도 원자 교체, 미래 활성 assignment/예약 없음 / 본인 choices |
| open_recruitment / POST /raid-rooms/{room_id}/recruitment-openings | 현재 공대장 | target_cycle, room/continuation revision | 현 주차 수06 이후 수동 개시 이벤트·round 보장, 실제 개시+30분 / plan |

CreateDraft의 필드 구조 후보:
{title,scope:public/group,group_id:UUID?,admission_mode:leader_only/direct_join,app_mode:single/mixed_bundle,items:[{raid_id,difficulty_id,catalog_version}],selection:Selection,session_drafts:CreateSessionDraft[],combat_requirement:CombatRequirement,continuation_enabled:bool}.

Selection은 기존 후보의 registration_id:UUID, character_id:UUID, selected_role:dealer/support, party_no:int1..2, expected_registration_version, expected_ownership_revision, expected_roster_revision, expected_lifecycle_revision, expected_role_summary_version, expected_weekly_revision, expected_limits_revision, expected_usage_revision을 재사용한다(모든 expected 값은 Version). 새 multi-item weekly CAS와 party_no의 혼합 앱4인 제약은 구현 전 schema 대조가 필요하다. 이 문서의 Selection 약칭 자체를 JSON 필드로 새로 정의하지 않는다. target_items는 [{item_id:UUID,round_id:UUID,expected_round_revision:Version,expected_weekly_revision:Version}]다. apply/join의 expected_policy_snapshot:string, expected_catalog_version:string도 기존 후보처럼 요구한다. SessionDraft={session_id:UUID?,expected_revision:Version?,required:bool,mode:unscheduled/manual/coordinated,starts_at:UTCDateTime?,item_durations:[{item_id,duration_minutes:int?}]}. SessionDraft의 기존 session_id/expected_revision은 둘 다 값 또는 둘 다 null이다. manual은 시작을 요구하고 unscheduled는 null이며 coordinated 후보 시각은 서버가 평가한다. 생성 시 item_id는 아직 없으므로 별도 입력 CreateSessionDraft={required:bool,mode:unscheduled/manual/coordinated,starts_at:UTCDateTime?,item_durations:[{raid_id:string,duration_minutes:int?}]}를 사용하고 item으로 변환한다. 같은 raid 중복 항목은 받지 않는다.

**이 표는 명령별 계약 고정 후보다.** Selection의 정확한 기존 필드 대응, 생성 시 session 구조, G3 구성/G7 상한까지 대조한 다음 최종 request schema와 원본 OpenAPI를 함께 확정한다. 이 초안을 이미 배포 가능한 완성 DTO라고 안내하지 않는다. 공개 목록/detail/application/choice의 전체 표시 DTO는 기존 후보와 Flutter Repository 대조에서 누락을 확인하고, 이 문서는 변경 핵심인 계획·예약·투표·원자 효과를 고정한다.

### 3.1 공통 원자성·확인과 투표 분리

현재 인증/대상 권한 → idempotency 원 ACK 회복 또는 ticket → game 쓰기 잠금·대상 행 잠금 → cycle/관계·소유/revision/catalog·현재 자격/원장/정원·슬롯/마감·점검·저장 하한 → 대상 변경/필요 표 평가/정확한 예약·원장 귀속 → 감사/버전/원 ACK → 마지막 DB 시각으로 경계 재검사 → commit 순서다. 외부 I/O는 잠금 밖이다.

같은 key/body 성공은 효과를 반복하지 않고 최소 원 ACK를 반환한다. 현재 세션·원 actor의 ACK 회복 권한을 검사하되 과거 공대장이었다는 이유로 새 명령을 허용하지 않는다. 탈퇴한 본인의 성공 leave ACK는 타인 목록 없이 회복할 수 있다. 다른 body는 409 IDEMPOTENCY_CONFLICT, 실행 중은 409 REQUEST_IN_PROGRESS/Retry-After:2다. 재시도 가능한 실패는 ticket 해제 후 같은 key로 시도한다.

원장 active_party_id만 비교하지 않고 assignment/round 세대를 대조한다. 다른 방의 새 점유를 옛 해제 명령으로 지우지 않으며 충돌이면 409로 전체 rollback한다. 회원 시간 비중복 exclusion constraint는 추가하지 않는다. GET·타이머로 완료를 만들거나 ACK만 먼저 저장하지 않는다.

제안 중 합류자는 현재 유효 일정 예약만 만들고 새 제안 응답은 pending이다. 제안 시각을 미리 예약하지 않는다. 적용 시 찬성자는 새 일정 예약, 미동의자는 해당 구일정 예약만 해제하고 초록 pending/새 예약 없음이다. 본인 confirm은 최신 schedule_revision에 대한 확인+본인 예약 생성이므로 신규 모집 마감 이후에도 가능하다. 종료한 round/assignment를 살리거나 proposal accept 표를 추가하지 않는다. 별도 key 재확인도 unique 귀속으로 이중 예약을 방지한다.

## 4. 투표 대상·명시 평가 — G1 제안

확정 동의수는 N2=2, N3=2, N4=2, N5=3, N6=3, N7=4, N8=4이며 공대장 제안 1표를 포함한다. 무응답 찬성/한 명 반대로 즉시 전체 취소는 없다. 동일 proposal/plan의 개인 표는 보존하되 현재 membership 세대로 재평가한다.

Backend 추천은 **세션별 실제 참여 대상 quorum을 모두 충족할 때 여러 세션 변경안을 한 번에 적용**하는 방식이다. 개인 응답은 제안당 한 번이며 본인이 참여하는 대상 세션에만 센다. 선택 세션 불참자/신청 pending/퇴장/그래프 체크는 분모에서 제외한다. join/approve/leave/response 명시 쓰기에서 대상 변화를 재평가한다. GET/새로고침은 적용하지 않는다.

| 예시 | 현재 표와 결과 |
|---|---|
| A/B/C에 D 합류 | A만 찬성→N4/필요2. A표 유지, D 신규 pending. B 찬성 때 적용하고 C/D는 확인 pending |
| A/B/C/D 중 D 탈퇴 | A만 찬성→N3/필요2로 재검사, 미달. B 찬성 때 적용. 탈퇴자 표는 현재 수에서 제외 |
| S1=A/B/C, S2=A/C/D | A+B만 찬성이면 S1=2/3 충족, S2=1/3 미달. D 찬성 시 둘 다 충족하여 원자 적용 |
| 위 예시를 union 방식으로 계산하는 대안 | 합집합 N4의 2표만 보면 A+B로 S2까지 변경된다. 추천 방식은 이를 피하나 아직 제품 채택 전 |
| N1 | 현재 공대장 명시 제안 1표로 자기 일정 확정을 추천. N2의 2표 규칙과 구분하며 아직 채택 전 |

N1과 세션별/union 선택은 G1이다. 계획 내용이 바뀌면 새 plan_revision으로 옛 표를 재사용하지 않는다. 명단만 바뀐 같은 안은 유효 개인 표를 보존한다. 반대와 제안 취소/폐기는 서로 다른 상태다. ProposalResponse.left는 실제 membership 탈퇴의 서버 파생 상태이며 찬반 명령으로 방을 탈퇴하지 않는다.

## 5. 권위 개시 이벤트·지연·마감 정각 — G2 제안

OpeningEvent 후보 필드:
{event_id,room_id,item_id,target_cycle,mode:scheduled_auto/manual,setting_version,authorized_effective_at,processed_at,state:scheduled/applied/blocked,cause:string?,opened_revision}.

- 자동 ON과 필요한 계속하기 설정/개인 선택이 경계 전에 서버에 저장된 경우, 예약 이벤트·설정 이력/유효기간으로 수06시를 권위 개시 시각으로 보존하는 안이다. 경계 뒤 ON 변경만으로 06시 권리를 소급 생성하지 않는다.
- worker가 09/10/11시에 늦게 처리해도 같은 이벤트의 effective=06:00/search_floor=06:30이다. 점검 구간을 제외하면 09시 처리의 최초 실제 후보는 10시다. 10시부터 다시 30분을 더하지 않는다. 11시 처리에서는 DB 현재 시각 이전인 10시를 확정하지 않는다.
- retry는 기존 event/floor를 유지한다. 최초 GET는 새 이벤트를 만들지 않는다. 예약 이벤트/이력 근거가 없으면 06시 개시를 꾸미지 않고 blocked/수동 대기한다. 현재 취소·자격·공대장 상태도 처리 시 검사하며 근거 없는 옛 자격으로 예약을 만들지 않는다.
- 11시에 실제 수동 신규 개시한 경우는 effective=11:00/floor=11:30이다. 자동 이벤트 재송과 구분한다. round 보장은 모든 지속 회원을 자동 활성 assignment/예약으로 바꾸는 뜻이 아니다. 새 주차 대상·개인 선택·현재 자격을 별도 검사한다.
- event/round 유일성과 lease/generation으로 중복 실행을 막는다. 실패는 reason 있는 blocked와 정리 권한으로 표현한다. 이벤트 생성/설정 이력 보존은 고정 전 대조할 G2이며 이번에 worker를 구현하지 않는다.

일반 신규 모집 마감의 Backend 추천은 t_db <= confirmed_start-30분이다. 마감 10:30:00.000000은 허용, 10:30:00.000001부터 거절한다. 대안은 t_db < deadline으로 정각부터 거절하는 방식이다. **정각 포함 여부는 아직 미확정**이며 채택 후 permissions와 최종 DB 시각 검사/오류에 같은 식을 적용한다. 최종 검사에서 넘으면 전체 rollback한다.

최초 임계치 합류 09:10→09:30 확정 예외와 기존 회원의 최신 일정 본인 confirm은 일반 모집 마감과 별개다. 클라이언트가 예외 flag를 보내 마감을 우회하지 않는다.

## 6. 기간·부분 완료·해제 효과

입력은 item별 duration_minutes:null 또는 10..1440의 5분 단위다. null이면 canonical 난이도 매핑으로 10/20/30분을 적용하고 명시값이 우선한다. 기존 normal/hard/nightmare뿐 아니라 stage1/2/3를 포함한 모든 실제 difficulty ID에 명시 정책표/버전을 둔다. display_order로 추정하거나 모르는 난이도를 0/10으로 대체하지 않는다. 알 수 없으면 DURATION_POLICY_UNAVAILABLE이다.

session 기간은 하위 item 유효 기간의 합계다. 별도 bundle_total 입력 UI는 필수 추가하지 않는다. 합계 24시간 상한은 합의되지 않았으므로 개별 24시간과 혼동하지 않는다(G7). 실제 구간의 점검/주차 경계는 별도 검사한다. 시작 미정이면 시작/종료는 모두 null이다.

예약은 정확히 해제할 수 있는 **item별 segment**에 귀속하고 화면/익명 busy에서만 연속 구간으로 합친다. 예: A10:00~10:10, B10:10~10:30, C10:30~11:00. B만 완료해도 A/C 원래 시각은 유지한다. C를 앞으로 당기려면 별도 일정 변경 제안이 필요하다.

| 명령/상황 | assignment·WeeklyState | 예약 효과 | 지속 관계/남는 항목 |
|---|---|---|---|
| 본인 A 완료 | 본인 A completed/manual 완료·A 활성 귀속 해제 | 본인 A 현/남은 재시도 segment만 해제 | B/C 시각 유지, 부분 완료로 방 전체 탈퇴하지 않는 안 추천 G4 |
| 공대장 B 완료 | 해당 B 현재 앱 assignment completed/party 완료·B 활성 해제 | 실제 대상 참가자의 남은 B segment 해제 | A/C 유지, 게임 외부 추가 인원의 완료 행 없음 |
| 본인 B만 참가 정리 | 본인 B left/활성 해제, 완료 없음 | 본인 B segment만 해제 | A/C·방 자리 유지; item 단독 탈퇴 허용은 G4 |
| 본인 방 전체 탈퇴 | 본인 모든 활성 assignment left/활성 해제, 완료 이력 유지 | 본인 해당 방의 남은 segment만 해제 | membership 종료, 타인/다른 방 불변. 공대장은 위임/마지막 1인 조건 |
| 마지막 남은 item 완료 | 완료 대상 원장만 갱신 | 그 대상 남은 segment 해제 | 다음주 membership 자동 삭제 없음 추천 G4; 방 종료 명령과 분리 |
| 이번주 미완료 종료 | 대상 active round 중단·활성 assignment 종료, 완료 생성 없음 | 해당 이번주 round의 남은 segment 해제 | 다음주 선택/지속 관계·기완료·과거 이력 유지; 묶음 범위 G4 |
| 변경안 적용 시 미동의자 | 관계/assignment 유지·초록 pending | 해당 구일정 본인 segment 해제, 신규 없음 | 본인 confirm 대기 |
| 최신 일정 본인 확인 | 현 membership/assignment 유지·확인 버전 갱신 | 본인 필요 segment 생성·중복경고, obsolete 귀속만 정리 | 동일 성공 ACK 재송으로 예약 재생성 없음 |

기존 개인 수동 완료의 방 탈퇴 연동과 묶음 A만 완료/B,C 유지 의미를 자동으로 같다고 해석하지 않는다. 추천은 부분 완료와 방 전체 탈퇴를 분리하는 것이며 공대장 위임/마지막 1인 조건은 유지한다. 미채택 상태에서 코드를 확장하지 않는다. 계속하기 방의 미완료 종료를 일반 비계속 방으로 확대하지 않는다. 선언자는 현재 참가자라는 기존 합의를 유지하고, 현재 item assignment가 없는 지속 회원의 자격과 묶음 전체/일부 범위만 G4로 남긴다.

다른 방의 새 원장 점유를 옛 해제로 지우지 않는다. 옛 성공 ACK는 당시 결과만 회복한다. segment 근거가 없는 기존 bundle_total 예약은 정확한 부분 해제가 불가능하므로 MIGRATION_REVIEW_REQUIRED로 해당 쓰기를 막는 안이다. 균등/비례 분배·0/가짜 시각으로 채우지 않는다. 기존 단일 round의 유한 구간은 동일 시각의 1item/segment로 대응할 수 있다.

## 7. 앱 구성·전투력·다음주 선택

### 7.1 혼합 앱4/게임8 — G3

app_capacity와 item.game_party_size를 별도 필드로 둔다. 기존 단독 8인은 2파티 규칙을 유지한다. 혼합 묶음 앱4인은 기존 4인 구성(딜러3/서포터1·기존 동일 직업 제한)을 재사용하는 안을 추천하되 새로 승인된 제품 규칙으로 표시하지 않는다. 게임8 item을 앱2파티로 잘못 변환하지 않는다. 앱4인 도달을 게임8인 충족으로 표시하거나 외부 4인 user/완료 자료를 만들지 않는다.

### 7.2 선택 역할 최근 성공 저장 점수

CombatRequirement={input_mode:shared/per_role,dealer_min:DecimalValue?,support_min:DecimalValue?}. shared는 두 값이 같고 둘 다 null이면 문턱 없음이다. per_role은 각 값이 nullable이다. 저장한 mode/값을 반환하고 저장 전 UI 초안은 Flutter가 관리한다.

선택 역할의 최근 성공 P1 저장값을 정확한 십진수로 비교한다. source=flutter_analysis/trust=client_submitted이며 게임 서버 검증값으로 표시하지 않는다. 소유/역할/summary version/관측 시각과 같은 관측의 build issues를 연결한다. 다른 역할·과거 최고점·0 채움·정수 반올림으로 대체하지 않는다.

| 문턱과 선택 역할 actual | 결과 |
|---|---|
| min=null, actual=null 또는 값 있음 | unrestricted, 이 사유로 거절하지 않음 |
| min=100.50, actual=null | missing / COMBAT_POWER_MISSING |
| min=100.50, actual=100.4999 | below / COMBAT_POWER_BELOW_MINIMUM |
| min=100.50, actual=100.50 또는 101 | meets, 다른 조건 검사 계속 |
| 유효 actual에 build 경고 있음 | 숫자로 판정하고 경고 반환, 경고 자체는 missing/거절 아님 |

OFF도 저장한 선택 역할 값을 사용하고 신청 시 강제 갱신·새 TTL 차단을 추가하지 않는다. 이 정책은 확정 사항으로 다시 A/B 선택을 요청하지 않는다. nullable P1 새 저장과 최근 성공 보존 방식/버전 결합은 기존 API 의미를 대조할 G6 기술 항목이다. 무조건 옛 높은 값을 역검색하거나 새 게임 검증 원천을 선행 필수로 삼지 않는다.

### 7.3 다음주 의도·기존 자격

현재 방 자리는 회원당 하나다. 활성 다음주 선택 유일성은 (user,character,raid,target_cycle)이며 다른 캐릭터까지 일괄 차단하지 않는다. 같은 방의 다음주 대표 선택은 하나이며 item/소유 버전을 고정한다. A→B 교체는 기존 choice ID/revision을 지정해 영향받는 묶음 item 전체를 CAS 원자 교체한다. 무관한 raid 선택/완료한 과거 snapshot은 변경하지 않는다. 미래 활성 assignment/시간 예약은 만들지 않는다.

자격 불비는 blocked reason/정리 경로로 나타내며 자동 퇴장/삭제하지 않는다. 그룹 탈퇴 후 기존 방 진행·상세 조회는 유지하고 현재 group_member 배지는 모든 상세 조회자에게 보인다. 공개 접수 원 pending의 그룹 복귀 후 외부 승인 예외는 불변 admission_scope/원 application ID로 검증하며 새 신청에 전파하지 않는다. 신청 목록은 현재 그룹/관리 권한, 본인 최소 신청 조회는 별도 본인 범위다.

## 8. 오류와 permissions

| HTTP / code 후보 | 검사/permissions.reason |
|---|---|
| 400 INVALID_REQUEST | strict 입력, 중복 ID/키/query, 5분/범위/enum 위반 |
| 401 AUTH_REQUIRED/ACCESS_INVALID/SESSION_REVOKED | 기존 인증·세션, WWW-Authenticate |
| 403 VERIFIED_ACCOUNT_REQUIRED/OWNERSHIP_REQUIRED | 신규 쓰기의 현재 인증 원정대·소유 부족, 기존 관계 회복과 분리 |
| 403 ROOM_LEADER_REQUIRED/ROOM_MEMBERSHIP_REQUIRED | 해당 현재 역할/관계 부족, 비참가 그룹원의 busy 조회 불가 |
| 404 ROOM_NOT_FOUND/ROOM_APPLICATION_NOT_FOUND/PROPOSAL_NOT_FOUND | 비가시 대상 존재 정보 보호 |
| 409 REVISION_CONFLICT/CYCLE_CHANGED/CATALOG_VERSION_CONFLICT | CAS/주차/catalog, 새 GET 후 명시 재시도 |
| 409 RECRUITMENT_CLOSED/MAINTENANCE_WINDOW/SCHEDULE_BEFORE_FLOOR | DB 시간과 동일 비교식, 최초 임계치/기존 확인 예외 분리 |
| 409 WEEKLY_ALREADY_PARTICIPATING/WEEKLY_ALREADY_COMPLETED | 동일 캐릭터 raid/cycle 원장 가드 |
| 409 ROOM_FULL/ROOM_COMPOSITION_CONFLICT/ROOM_RESTRICTED | 자리/구성/한도, 실제 증가 대상만 한도 검사 |
| 409 APPLICATION_NOT_PENDING/PROPOSAL_NOT_PENDING/PARTICIPATION_ENDED | 만료/종료/옛 안, 확인으로 종료 상태 복원 불가 |
| 409 COMBAT_POWER_MISSING/COMBAT_POWER_BELOW_MINIMUM | 선택 역할 점수만, 경고/OFF 관측 나이로 사용하지 않음 |
| 409 IDEMPOTENCY_CONFLICT/REQUEST_IN_PROGRESS | 동일 key 다른 body/실행 중, 후자 Retry-After:2 |
| 503 SERVICE_UNAVAILABLE/DURATION_POLICY_UNAVAILABLE/MIGRATION_REVIEW_REQUIRED | 원본/준비/매핑 근거 부족, 0 대체 없음 |

기존 {error:{code,message,request_id}}와 no-store를 유지하고 validation은 400으로 통일한다. 시간 중복 전용 거절 오류는 만들지 않는다. no_candidate/search_limited는 HTTP200의 계산 상태이며 다른 참가 자격을 무조건 허용한다는 뜻이 아니다. 새 코드명은 계약 고정 후 구현/OpenAPI에 함께 넣는다.

## 9. 호환·원천·이행

| 현재 자료/API | 대응과 보존 |
|---|---|
| 실행 main/API8000/DB0016 | 기존 API 유지·모집 미공개. 이번 DDL/재시작/자료 변경 없음 |
| 로컬 0017/0018·단일 Room/Round | 동일 ID를 1item/1session/같은 시간 segment로 대응. 기존 migration 이력 재작성/삭제 없음 |
| 기존 membership.round_id | 지속 membership과 주차 assignment 분리, 가입 구간·snapshot 유지. 단독8인을 앱4인으로 축소하지 않음 |
| require_no_time_overlap | 명시 경로의 거절에서 경고로 전환할 대상. 슬롯/동일 캐릭터 주차 가드 유지 |
| 기존 F2 시작/기간 후보 | startAt=clock.now()/maxPlayHours=null을 확정 일정으로 승격하지 않음. 미지정 mode로 명시 변환 후 Router/Repository 대조 |
| 기존 nullable int minCombatPower | shared 십진 값으로 대응, null=문턱 없음. 서버 값을 UI 정수에 맞춰 반올림하지 않음 |
| P1·개인 weekly manual API | 기존 역할/신뢰 재사용. 기존 manual PUT의 참가 확인 필요 가드를 임의 제거하지 않고 통합 명령에서 원자 처리 |
| /v1/me/usage-limits | 지속 방의 현재 이용과 주간 누적 통계 분리. 함께하기/계속하기 관계 포함, 주차 종료만으로 이용량 0 처리 없음 |
| /v2/me/account-bootstrap | 읽기 유지, GET에서 개인표/방/예약 생성 또는 새 거대 payload 자동 추가 없음 |
| schema/migration | 별도 활동 브랜치89a3248/dev head와 대조, 추가 migration으로 처리. 근거 불명 자료 blocked 검출, DB 초기화/강제 stamp 없음 |
| #19 주간 통계 | 실제 생성·공개 접수/참가 구간·결과/계속하기 원천을 같은 transaction에 보존하는 설계. 통계 집계/API는 별도 #19, 수동 완료를 모집 실적으로 대체하지 않음 |

기존 101/97/보존25 PASS는 당시 후보의 검증이며 이 새 통합 초안 구현·성능의 증거가 아니다.

## 10. 고정 전 결정표·구현 순서

| gate | 남은 대조/Backend 제안 |
|---|---|
| G1 투표 | N1 명시1표, 여러 세션별 quorum 후 전체 원자 적용 추천. 3/4인·겹친 세션 예시로 대조 |
| G2 시간 | 자동 예정06 effective와 실제 processed 분리/이력·floor 보존, 수동 실제+30. 마감 정각 포함 추천/제외 대안 중 고정 |
| G3 구성 | 혼합 앱4인에 기존4인 규칙 재사용 추천. 게임8/단독8과 분리, 불일치만 제품 선택 |
| G4 완료/중단 | item 부분 완료 시 방 유지·정확 segment 해제 추천. 본인 완료의 탈퇴 연동·공대장 처리, 중단 묶음 범위/현재 assignment 없는 지속 회원 선언 자격 대조 |
| G5 다음주/자격 | choice CAS/방 한 자리와 다중 캐릭터 영향, 자동 설정 기본값/변경 효력·blocked 정리 대조 |
| G6 점수 보존 | 최근 성공 선택 역할 값의 버전·관측 연결/nullable 저장 호환. 저장값 비교 정책 자체를 재질문하지 않음 |
| G7 기술 상한 | 편집/정규화 구간·세션·페이지·탐색 budget/합계 기간 상한과 근거·측정 계획. 64구간/7세션을 확정치로 사용하지 않음 |

1. R0: 이 초안 게시 → Flutter 실제 Router/DI/Repository·구자료 대응 검토 → 필요한 G 결정/정확한 request·전체 소비 DTO 보완 → 계약 확정.
2. R1: 지속/주차/세션/segment 원천 모델·추가 migration·기존 자료 변환/보존·제한 DB role 검증.
3. R2: 개인표/제출표·membership/item/round/assignment·캐릭터 선택/슬롯·WeeklyState 연결.
4. R3: segment 예약·경고/자동 후보·투표/본인 확인/그래프·다음주 이벤트/choice 연결.
5. R4: 부분 완료/이번주 중단·외부 원 신청/공개 권한·점수/한도와 모든 쓰기의 원자성 검증.
6. R5: 확정 OpenAPI/앱/DB 준비 일치 → 묶은 구현 구간 commit/push/원격 확인 → 필요한 Flutter 소비·동작 인계.

각 R은 통합 목표의 내부 순서다. 개인표만으로 전체 완료라 하지 않는다. 검증 계획은 DB clock 경계·06 운영/10 진행/지연 이벤트, 동적 투표/확인 재송, 점수 정밀도, item 해제/다른 방 새 점유/옛 ACK, 자격·공개 원 pending, 그래프 정보 보호, 앱4/단독8, 기존 API 회귀와 보존/rollback을 포함한다.

이번에는 문서·설계 예시만 검사했다. 기능 코드·DDL·원본 OpenAPI·실행 API/DB/이미지/자료를 변경하지 않았고 앱 자동시험·실제 서버·provider·Flutter·기기 테스트는 실행하지 않았다. 이 회신은 구현 테스트 요청이 아닌 계약 고정 전 소비 검토다.
