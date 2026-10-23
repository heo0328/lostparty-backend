# Issue25 계약 보완안2 — 옵션 격리·후상태/revision·복구/기록 reader

후속 구현 기준: [검색/일반 탈퇴·해산 개발 안내](../development/ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md)와 실행 OpenAPI를 따른다. 아래는 합의 당시의 설계 자료/검증 경계를 보존한 것이다. 실제 개발 API/DB 반영 상태는 개발 안내·NEXT_WORK에서 구분한다.

제품 상태 보충: [IF-001](../../../reference/INACTIVE_FEATURES.md)에 따라 close_weekly/weekly_resume 앱 진입은 비활성이다. 아래 retained/기존 content·resume 호환은 과거 자료·원 API 보존 기준이며 앱 재활성화 근거가 아니다. #25 recover_leadership 및 다음주 reopen과 구분한다.

2026-10-24 / feat/raid-recruitment / **기획·설계 범위의 닫힌 계약안, 기능 미구현**.

[Flutter 전체1번째 소비대조](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6369171307)의 네 보완에 답한다. 기존3행동 정책은 재질문하지 않는다. [설계안1](../planning/ISSUE_13_MEMBERSHIP_ACTIONS_DESIGN.md)의 모호한 wire/reader 부분은 이 안이 대체하고 기존 명령·원ACK의 효과는 유지한다. 복구 UI의 제품 승인을 뜻하지 않으며 네번째 상시버튼/탈퇴전 필수단계·GET자동승계를 추가하지 않는다.

기계가 읽을 원본은 [JSON Schema2020-12](../artifacts/issue25-membership-actions.contract.schema.json), [합성 설계벡터37개](../artifacts/issue25-membership-actions.contract.examples.json)다. 실행 OpenAPI와 구분해 docs/features/recruitment/artifacts에만 저장한다. 정의49개(기존 계약의 외부참조4개 포함)에서 모든 새 object는additionalProperties=false/모든필드required이고 nullable을명시한다. 원소상한·UUID/offset시각·revision1..2147483647을고정한다. date는canonical수요일이며명령의C/N·token UTF-8<=4096bytes·원자CAS 같은다중필드규칙은 아래의규범조건과함께검증한다. JSON Schema만으로DB권한/원자성을입증하지않는다.

기존content의참조 URI `urn:lostparty:two-cycle-0eed67c`는 [기존소비OpenAPI](https://github.com/heo0328/lostparty-backend/blob/0eed67c453040b332653fd2071e6cd2e1eeed503/openapi/two-cycle.openapi.yaml) 전체를그대로가리킨다. 신규schema를이URI로등록한원본과함께검증한다. 정상plan의 content는기존 `ResumePlanContext`, detail은기존 `OutputContract3GetV2RaidRoomsRoomIdDetail`, 목록항목content는기존 `BMembership`다. 원본의현재등록이름을사용하며마운트되지않은BPlan이라는이름을가정하지않는다.

## 1. 메뉴 전체 접근과 옵션별 권한

GET `/v2/raid-rooms/{room_id}/membership-action-context?target_cycle_key=T`의입구는 정상세션+해당room의현재활성지속Member/현재접근근거다. **선택T actual회원·공대장을메뉴입구조건으로쓰지않는다.** 현재T일반/미참가·반대T리더도메뉴를읽는다. 선택T는C/N이고없는T를열거나CM을만들지않는다. 메뉴에대한본인활성지속Member없음은접근오류403(비노출room은404)이며개별옵션의부족조건을그오류로승격하지않는다.

| option | visible / permission |
|---|---|
| leave_target | 선택T 본인실제participating/review면표시. 인원수·리더·후계부적격으로숨기지않음. 미참가면visible=false/allowed=false/WEEKLY_PARTICIPANT_REQUIRED. 실제source/lease미증명은표시유지/allowed=false/ROOM_REVIEW_REQUIRED |
| leave_all | 지속Member활성이면표시. 실제T0개여도본인지속관계종료가능. 본인대상중증명안되는관계만그option을ROOM_REVIEW_REQUIRED로차단하며타T미참가/리더/후계부적격은차단조건아님 |
| dissolve_led_targets | 현재본인이actual리더인유효C/N집합이있으면표시. 선택T역할과독립. 집합내하나의정리증명실패면option전체불가/집합을자동축소하지않음. 리더T0개면visible=false/allowed=false/TARGET_LEADER_REQUIRED |
| recover_leadership | 선택T actual회원+명시복구근거가있을때만안내영역의진입후보. 미참가/해당없음은이option만visible=false/false/LEADERSHIP_RECOVERY_NOT_REQUIRED. 준비안됨은visible=true/false/LEADERSHIP_RECOVERY_NOT_READY |

모든허용option은visible=true/permission.allowed=true/impact와confirmation이둘다비null, 모든거절option은allowed=false/impact=null/confirmation=null이다. visible은독립정책이다. 다른option의token·기술오류를선택option의서명으로확대하지않는다. recover의같은T회원조건으로메뉴전체를403으로만들지않는다.

벡터 `view_C_not_participating_N_leader_menu`가 leave_target=false/leave_all=true/해산=N만/recover=false를, `view_C_member_N_leader_menu`가현재C자기탈퇴도가능한혼합역할을보인다. 해산N만성공이면C화면·본인C참가를유지한다. 새GET은기존detail의현재역할·마지막1인end조회로대체할수없는실제메뉴근거다.

## 2. Impact와 ACK의 상태·revision 대조

POST본문6필드는설계안1그대로고정한다. `{expected_cycle_key,view_cycle_key,actor_membership_id,expected_actor_membership_revision,action,context_token}`이며원method/path/key/body/token과원Impact를보관한다. 각option token은선택action·원actor/pathroom/실제C/viewT·실제영향/후상태/리비전규칙을묶는다.

### 추가/변경된 정확한 필드

- TargetPlan에 현재 `members_revision,plan_revision,target_state,generation_state`와 **planned_target_state/planned_generation_state**, `revision_rules:{target,members,plan,leadership}`를추가한다.
- 각rule은 닫힌 `{before:revision,comparison:equal|increase,exact_after:revision|null}`다. equal이면exact_after=before이고ACK가정확히같아야한다. increase이면ACK>before이고exact_after가비null이면추가로정확히그값이어야한다. null은0/unknown권한이아니라**고정된엄격증가규칙**이다.
- MemberEffect는 현재state와 planned_state/revision_rule을갖는다. PlannedLeadership에는실제 leadership_revision을추가한다. TargetResult에는실행후 members_revision/plan_revision을추가한다. gen번호는고정(재개/새주차생성아님), gen상태는기존open/review_required/cancelled/completed/stopped를정확히표현한다.
- RoomEffect는 room_revision_rule/actor_membership_revision_rule을갖는다. 앱은result의room/member/CM/target/leadership을각규칙과실제ID·후상태로검증하며모든값을임의+1로만들지않는다.

| 자원 | 유지/증가 규칙 |
|---|---|
| Room.revision | 이명령이Room.ended_at를실제로바꿀때1회+1,그외유지. 지속Member/다른T의내부변경만으로Roomrevision을증가시키지않음 |
| 지속Member.revision | ended_at또는현재지속관계가실제종료되면1회+1. 원래유지되는선택T탈퇴/복구는동일. Room최종종료의모든대상Member도각1회 |
| CM.revision | 상태/ended_at변경·명시복구의review→participating같은실제변경시명령당1회+1. 후계pointer변경만이면CMrevision유지. Context affected_members는CM상태/근거가실제로변하는대상과그후값을명시 |
| leadership_revision | leader두ID또는active→pending_review/closed등리더십해결상태가바뀌면1회+1. 이미정한리더를유지한채다른review만정리해open으로복구하면유지 |
| target.revision / plan_revision | 효과가있는T는엄격증가,내부제안/정족수·일정재평가의추가증가가능. 따라서exact_after=null의increase로고정. 원ACK의최종실제값을보존하며클라이언트는>before를검사 |
| members_revision | CM실제상태/참가집합변경이있으면1회+1. 단순리더pointer·다른검토사유복구만이면유지. 내부helper가중복증가하지않도록새명령에서집계 |

동시변경때더큰revision이면그냥허용하는규칙이아니다. 서버는원token의**모든before/권한/대상CAS를먼저일치검증**한다. 그뒤한명령내부집계의최종값을ACK에낸다. 새generation/다른회원의더큰revision으로낡은명령을재해석하지않는다. overflow는명령전체를거절한다. 내부helper가직접revision을중복소유하는부분은구명령효과를바꾸지않는작은내부효과단위로분리할구현구간에포함한다.

후상태는정확히일치한다. 후계없음탈퇴는target/gen=review_required·두리더null·pending_review. 복구가능하면open/open·검증된후계ID, 다른검토잔존이면review_required/review_required·검증된리더ID·recovery_reason=OTHER_REVIEW_REMAINS다. 기존닫힌completed/stopped의투표자격정리등직접연계가필요하면그상태는그대로유지하며새완료로덮지않는다.

벡터 `recover_open`, `recover_review_remaining`, `recover_existing_leader_revision_unchanged` 및 `no_eligible_successor_still_leaves`가이를구분한다. `empty_effects_membership_end`는effects=[]/affected_cycle_keys=[]/actor_membership_ended=true이고room_revision은유지·actorMember만증가한다. 가짜T를추가하지않고Flutter는관계종료event로C/N내목록·한도를별도무효화한다. `eight_members_two_led_targets`는양T각8인의해산과Room/지속관계종료,실제C→N순서를표현한다.

ACK scope.server_now는원실행시각이고원ACK복구때새C/새revision으로덮지않는다. 소비자는현재시각이아니라저장된명령/Impact·당시C/viewT에대조한다.

## 3. reader 호환 — 명시 opt-in 프로필

새메뉴만으로기존detail/plan/목록의엄격한파서를확장했다고간주하지않는다. **기존GET의 기본응답은그대로 유지**하고다음명시프로필을제안한다. 옛reader에알수없는필드/상태를조용히넣지않는다. 새reader/recordroute연결의기술차이검토용이며추가화면단계나카드별조회요구가아니다.

- GET `/v2/raid-rooms/{room_id}/detail?target_cycle_key=T&reader_profile=membership-actions-1`
- GET `/v2/me/raid-rooms/{room_id}/plan?target_cycle_key=T&reader_profile=membership-actions-1`
- GET `/v2/me/raid-room-memberships?target_cycle_key=T&state=current|ended|all&reader_profile=membership-actions-1`

명시profile이없는기존DTO/조회/원parser는유지한다. 향후 이3GET의query/200 union은명시적으로확장되지만기존default분기의component/JSON은보존한다. 새상태를구DTO로안전하게표현할수없는기본읽기는기존검토오류로닫고가짜값을내지않는다. profile오타/미지원값은400이며기본응답으로fallback하지않는다. profile/list state/filter는cursor/cache scope에결합한다. plan의기존include_resume_display는legacy content가있는현재참가조회에서만그대로허용하고record모드에서true를요구하면400이다. 그외기존query중복/추가필드·no-store·상한을유지한다.

세응답의Scope는 `{server_now,current_cycle_key,target_cycle_key,policy_version:'membership-actions-1',reader_kind:'detail'|'plan'|'memberships'}`. detail/plan의닫힌data는 **target,viewer,access,recovery,permissions,content,record** 7필드다. 각각의모든하위필드/enum/null은동봉schema가원본이다.

- `target`: 실제room/선택T/UUID·generation/revision/상태와nullableleadership. gen미확정이면target_generation/gen상태/leadership은null이며실제row의revision이나CMID를지우거나양수gen를만들지않는다.
- `viewer`: membership_id/revision/state(active|ended), 실제CM ID/revision/state·joined_order/role/mode/record_locator. mode는participant/retained/recovery/record/relation_only로구분한다. cancelled/removed는새schema에서만실제값을표현하며구members.target_state로위장하지않는다.
- `recovery`: state=none/leadership_pending/review_remaining/unverified, reason/revision/remaining_review_reasons/menu_access/can_request_recovery를명시한다. **단순null리더로복구를추정하지않는다.** explicit복구근거없는legacy미확정은unverified이고자동승계진입으로읽지않는다.
- `content`: 정확히기존detail/plan의**전체200 envelope** 또는null이다. 정상참가·기존형태로안전하게표현되는경우기존content를재사용한다. profile의viewer/recovery가새표시·권한판정기준이며내부content파서가없다고가짜my_membership/공대장/formation을채우지않는다. source불확정detail은안전한요약만return하고content=null,그plan은view_plan=false/403이다.
- `record`: 증명된자기기록의RecordSnapshot 또는null. mode=record이면content=null/record비null이며옛parser에cancelled/removed나가짜현회원정보를주입하지않는다. 정상참가모드는기존content·구일정/계획을재사용하므로기존운영기능을새간이record형식으로축소하지않는다.

| 조회 관계 | role/mode/읽기·메뉴 |
|---|---|
| 양수현gen·본인실제참가/review·복구pending/null리더 | role=member/mode=participant. 자신의실제CM을유지,명시recovery로표시. 본인detail/증명가능한plan 허용,일반관리권한보류·본인메뉴진입은허용 |
| 같은gen에리더배정됐지만다른검토잔존 | 실제role leader 또는member/recovery=review_remaining. 기존리더로서별도검증된정리option외일반관리를추정허용하지않음 |
| 실제review CM/row 있으나gen미확정 | role=none/mode=recovery,목록에서버리지않고기존복구안내. content=null/plan=false,복구leadership으로추정하지않음 |
| 정상activeRoom의현재 completed/stopped CM·활성Member | mode=retained,실제기존role·source권한을유지. 기존stopped재개허용을recordread-only로일괄차단하지않음 |
| ended Member/Room종료 또는자기cancelled/removed·옛gen기록 | role=none/mode=record,진짜옛CM·기록Locator 유지. detail/plan읽기허용/쓰기·메뉴false |
| 지속관계만/선택T 미선택 | mode=relation_only·CMnull/not_selected. 가짜T기록link/plan을만들지않고선택T미참가가메뉴전체차단으로이어지지않음 |

목록page의data는items/membership_head/next_cursor/evaluated_at이며items각항목은target/viewer/recovery/permissions/content(기존BMembership 또는 null)다. current/ended/all SQL선별의기존의미는유지한다. current의정상실제review는role=none이라는이유로지우지않고mode/recovery로구분한다. ended에복구미확정항목을사실없이이동시키지않는다. Member가ended지만선택T실제CM없음이면relation_only/record_locator=null로표현하고상세recordlink를만들지않는다.

## 4. 종료 회원의 자기 기록·재가입/그룹탈퇴

record진입은위detail/plan profile에 **membership_id와cycle_member_id를둘다**추가하고목록의record_locator를그대로사용한다. 반쪽anchor는400, 다른회원/room/T/CM·gen가일치하지않거나확인할수없는record는404/ROOM_NOT_FOUND다. 현재Member가없는데anchor도없으면보이는room은403/ROOM_MEMBERSHIP_REQUIRED·비노출room은404이고임의최근이력을선택하지않는다. group탈퇴한자기기록은일반그룹검색가시성이아닌증명된로그인user→옛Member→CM/Assignment의권한으로입구부터확인한다.

같은user의새활성Member가있어도명시옛anchor조회는**항상그옛record**다. mode=record·role=none/access.read_only=true·모든새쓰기/메뉴permission=false이고새Member로바꿔권한을재활성화하지않는다. menu/POST는별도의현재활성Member근거로만진입하며옛record를writeContext로사용할수없다. 탈퇴/재가입이력의Member ID·CM·generation을한화면자료로섞지않는다.

RecordSnapshot의정확한필드는locator/rounds/assignments/schedule_segments다. 기록세대/자기CM에연결된실제item/round/캐릭터/난이도·Assignment상태/완료출처/완료·종료시각과본인관련일정segment만돌려준다. display이름은그기록snapshot이며현재owner의새정보로재연결하지않는다. 기존완료/감사를보존하고기록읽기로게임완료해제·참가/자리/예약복구를하지않는다. 다른과거회원의명단/개인제출/투표·rawuser/소유응답을자기기록근거로새로노출하지않는다.

record의read-only는오류가아니므로access.state=allowed/basis=historical_membership(ended Member) 또는target_record(자기취소된T·지속관계유지)다. view_detail/view_plan=true,manage_target/resume_weekly/read_action_menu=false. active방에서선택T탈퇴뒤일반plan403/404는그대로성공후이탈사유이며위record경로가명령성공조건이아니다.

벡터 ended_cancelled/removed/completed의detail/plan 및ended_records_page, rejoined_group_departed_old_record에명시했고foreign_record_hidden은404기존Error형태를사용한다. 구record DTO의값을늘리거나권한을확대했다고가정하지않는다. 정상readonlylegacy보관과새ended회원기록은명시profile로구분해최소변경으로연결한다.

## 5. 정적 검증·구현 구간

이번37개벡터는**직접작성한합성설계값**이고서버캡처나실동작시험이아니다. JSON Schema/format검증과9개의Impact→ACK ID/상태/리비전·actor/Room종료대조,기존legacy ref2개해석,추가필드/거절option의비null영향·리더ID불일치/리비전변조의4거절probe를검증했다. 처음합성detail/plan이같은객체를공유해생긴예시content종류혼합과정적검사누락을수정후통과했다. 실제DB/트랜잭션/동시성·서버인증/한도/worker/화면동작을입증한수치로보고하지않는다.

구현구간은 (1)고정wire/권한planner·option격리/자기T탈퇴·revision수집·audit/recovery, (2)모두탈퇴/리더T집합해산·Room/Member/한도, (3)opt-in reader·기록권한/worker만료 직접연계, (4)표적PostgreSQL/HTTP·기존원명령보존/DB준비·개발반영 인계다. 모든관련구간이검증/게시되기전네이티브에기능시험을요청하지않는다. 현재사용자지시는기획/설계범위이며그구현/DB반영을이번문서로실행하지않는다.

다음Flutter는네보완의새구체wire/기록profile에남은소비차이가있을때만이Issue에제시한다. 기존원자성/제품정책/시험을반복재수용하도록요구하지않는다. 복구UI는기존안내영역의제안상태를유지한다. 다음Backend는소비차이/구현지시에맞춰구현구간을진행하며실행계약·SHA/개발/DB결과는그때별도인계한다.
