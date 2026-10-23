# 선택 주차 탈퇴·모두 탈퇴·공대장 주차 해산 기획/설계안1

2026-10-24 / Backend / feat/raid-recruitment / **설계 제안·미구현/미배포**.

정책 원본은 [#13 전체136번째 Flutter 사용자확정 전달](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6367266418)이다. 135번째의 사전위임·마지막1인해산/다인제외는 새행동에 적용하지 않는다. 아래 권한복구/기록 접근·wire는 그 정책을 실현하기 위한 **Backend 설계안**이며 아직 상대 측 소비검토나 실행 계약 확정으로 표시하지 않는다.

## 1. 사용자가 보는 행동과 완료 조건

| 행동 | 대상 | 지속회원/반대T | 성공 후 |
|---|---|---|---|
| 이번주/다음주 탈퇴 | 현재 보는 실제T의 본인 participating/review 관계 | 반대T 보존. 방이 유지되면 본인 지속회원 유지 | 선택T 상세 이탈·그 실제T 내참가/계정으로 복귀 |
| 모두 탈퇴 | 본인의 C/N 실제참가·본인 미결신청·지속회원 | 각T에서 본인이리더면 독립승계/빈T종료 | 상세 이탈·내참가/계정 갱신 |
| 모집 해산 | **본인이 현재리더인 모든 C/N 유효주차**의 전원참가·미결모집 | 비공대장T의 본인/타인/리더/예약/완료 보존 | 대상T에서만 이탈·원ACK 성공 유지 |

선택탈퇴와 모두탈퇴는 사전위임·인원수·공대장 여부·캐릭터의 신규참가자격을 거절조건으로 삼지 않는다. C는 수10시 이전에도 취소 가능하며 게임 완료/미완료 선언과 구분한다. 모두탈퇴는 실제참가0개·본인지속관계만 남아도 가능하다. 해산은4/8인도 지원하고 전체마지막지속회원1인 제한을 제거한다.

해산 대상은 탭으로 고르지 않고 서버의 각T 리더권한으로 계산한다. C리더/N일반이면C만, C일반/N리더면N만, 양리더면C/N 모두. 숨은 반대T 권한을 현재탭 역할로 추정하지 않는다. C/N 둘다리더가 아니면 해산 visible=false/permission=false다. 이미닫힌 completed/stopped/cancelled 세대는 새 해산 대상으로 열거나 다시종료하지 않는다.

참가상세의 두 탈퇴버튼은 인원수·승계가능 여부로 숨기지 않는다. 해산은 관리할 리더T가 있으면 표시하고 기존 빨강/흰글씨·아이콘·위치를 유지한다. 확인창에는 실제 날짜/주차, 해산 인원·예약/참가 영향과 **“해산 대상 주차의 모든 파티원이 탈퇴 처리됩니다.”**, 비대상 주차 보존을 표시한다. 취소는쓰기0이며 영향T 집합/권한/의미변경은 POST 없이 다시확인한다.

실제 선택C/N·목록/상태 갱신은 ACK효과를 따르고 성공 뒤 member-only plan403/404나 refresh 실패를 쓰기실패/재전송 사유로 쓰지 않는다. 무조건현재C로돌아가거나 비대상T를 다시쓰지 않는다.

## 2. 현 구현과 변경 경계

| 현재 소스/행동 | 현재 사실 | 새행동 설계 |
|---|---|---|
| cycle_leadership.prepare_cancel | next_only=True, 적격후계없음이면거절 | 구동작보존·새action으로C/N 자기탈퇴, 승계불가도탈퇴성공 |
| cycle_common leave/end | 리더사전위임/전체마지막지속회원1인·G1공통권한 | 구동작보존·각T권한/원자다중효과의새명령 |
| atomic_members / D22 / #22 | 선택1완료+잔여취소·후계없음전체거절 | 기존완료명령/원pending효과는보존. 이번 새3행동과혼합하지않음 |
| cycle_commands.leadership / card batch | review+null리더는오류 | 새복구상태에만 null두ID·증가revision 읽기 지원, 실행권한 부여 금지 |
| cycle_member_reads·base.member | 주로활성지속회원만조회, cancelled CM plan제한 | 종료관계의증명된자기기록읽기와 새쓰기권한을 분리 |
| room_count / MemberHead·UsageHead | 활성지속Member+미종료Room 기준 | 모든탈퇴/최종Room종료 때 지속회원/한도head 원자갱신 |
| cycle_worker | open대상만처리 | 리더복구review의 주차만료도빠지지않게정확히확장 |

대상 Room/CM/지속Member의 user/room/cycle/gen·Assignment·점유가 실제로 연결되는지는 검증한다. **탈퇴를막지않는 후계자격**과 **다른회원/세대의자원을해제하지않기위한대상증명**을 구분한다. 증명할 수 없는 source/nullgen·깨진lease는 ROOM_REVIEW_REQUIRED/안전한거절·복구안내이며 가짜ID/정상참가를 만들지 않는다. 버튼은숨기지않고 기술적불가사유를안내한다. 적법하게증명된본인review 관계의자기정리에 현재캐릭터소유/활동자격을 요구하지않는다.

## 3. 실제참가 순서와 후계 부적격 — 탈퇴성공/권한보류

후계대상은 같은현generation의 지속회원활성·actual participating/review 중 **남은 active Assignment/증명된 실제점유가 있는 사람**이다. completed/stopped/cancelled/removed·단순지속회원/미결신청은 승계하지 않는다. actual review로 점유가 불확정이면 없다고 단정해빈T를닫지않고 검토필요 잔여관계로 보존한다.

1. 순서는 서버의 현재 joined_order 오름차순→CM UUID다. 재참가는 기존 cycles.allocate_join_order에서 부여한 새순서를 사용하고 기존 joined_order/가입일을 재사용하지 않는다. 앱에서후계자를추정하지않는다.
2. 그순서에서 **증명가능하고 기존자격을통과한 첫 remaining participating**에게 자동승계한다. 현재소유/활동·회원활성/그룹/한도·raid/lease 자격은 life.qualify의필수근거를재사용한다. 완료/퇴역/비소유자에게 신규관리권한을주지않는다. 앞선부적격자를건너뛴사유/검사순서는감사에고정한다.
3. 남은실제/검토관계는있지만 적격자가없거나순서를증명할수없으면 **본인탈퇴는성공**한다. row/gen=review_required, 두leader ID=null, leadership_revision증가, 별도leadership recovery 근거를저장한다. 남은사람을임의participating/공대장으로바꾸거나순서를만들지않는다. SUCCESSOR_UNAVAILABLE로탈퇴를rollback하지않는다.
4. 이때 남은참가/완료/점유·정상예약은보존하고 신규참가·일정확정/승인/편성 등 관리쓰기는보류한다. 본인자기탈퇴는가능하다. active검색에서는review가제외되고 내참가에는 실제review/관리복구상태로남는다. 명확한리더없는T는해산권한대상으로추정하지않는다.
5. 남은실제/검토관계가없으면 T를cancelled/closed·null리더로종료한다. 취소/해산으로새completed/주간완료를기록하지않고 기존완료Round/Assignment/source를보존한다. active Round는불완료종료되지만 빈모집취소·해산사유는별도감사로구분한다. 이미완료한항목을stopped로덮지않는다.

### 복구 경로 제안

추가관리자의임의지정 없이 `recover_leadership`을 아래새명령의 보조action으로제안한다. 화면은 복구상태/자격정리안내와 명시적인복구진입을소비한다. 일반3버튼의필수 추가선택단계는아니다. **이복구UI/DTO는Flutter소비차이검토대상**이며이미합의된기능으로표시하지않는다.

같은T의 남은 actual회원만 GET할 수 있고, GET은 후보를재계산해보여줄뿐관리자를배정하지않는다. 명시POST에서같은쓰기잠금/CAS/최신자격을재검사하고 같은순서의최초적격자에게만 배정한다. 호출자자신을지명/전달하는필드는없다. 회복후기존검토사유가남으면대상row는review로유지하고 해당사유를안내하며, 모든실행근거가검증된때만open으로복구한다. 소유권/활동·시간동의/예약을새로만들거나기존동의를재작성하지않는다.

복구처리의 pending/resolved 근거와 다른review사유를구분해 저장한다. 권한이복구됐어도다른검토사유가남은경우에는 기존리더의정리권한만기존규칙에따라사용하며 임의전체open은금지한다. 복구가더필요한경우같은보조action으로현재리더/자격/검토근거를다시증명한다. 적격자없음은복구option만 permission=false/LEADERSHIP_RECOVERY_NOT_READY, 본인탈퇴option에는영향을주지않는다. 과거T가되면복구승계를하지않고worker가증명된미완료참가를종료/기록으로이관한다. 매조회복구·시간경과만으로권한배정은없다.

## 4. 주차·방·지속관계 수명

선택탈퇴는 본인T의 active Assignment/점유·예약·session participation/동의·제출을정리하고 CM=cancelled/end/revision증가. 타인참가/완료는보존하며 본인T 미결신청만종료한다. 본인투표·제출·기존동의이력은감사로보존/현재eligibility에서제외하고 관련제안의정족수를기존규칙으로재평가한다. 타인일정을자기탈퇴의편의로초기화하지않는다.

모두탈퇴는본인의C/N대상을먼저모두검증후각T에서위효과/승계/빈T종료를적용하고 본인 room내미결신청과 지속Member를종료한다. 중간실패하면양T·지속관계·감사모두rollback한다. 비대상과거의미해결active근거가본인지속관계종료에충돌하면 안전한검토오류로반환하며 과거lease를추정삭제하지않는다.

해산은각대상T의 actual참가/review CM을종료하고 active Assignment/점유·예약/participation·제출/미결신청/일정을정리한다. CM은removed(외부기존cancelled표현과대조), generation=cancelled/null리더, 완성된과거자료는보존한다. 타T와연결된제안이있으면대상부분을멋대로절단하지않고증명된전체제안의현재eligibility/obsolete처리규칙으로닫는다. 타T자원수정이필요하면그원인을별도검토하며이번명령권한을확대하지않는다.

**방 전체종료:** 대상처리뒤 같은snapshot에서 모든 live/review 주차/실제active·미확정근거를확인한다. 비대상T가유효하거나과거/기타미해결actual근거가있으면 Room은유지한다. 모든유효T가없고 안전한종료근거가있을때만 Room.ended_at/revision을설정하고 남은활성지속Member를종료·모든영향회원의 MemberHead/UsageHead를한번씩갱신한다. 현재T두개가끝났다는이유만으로미확정다른근거를무시하지않는다. 방역사소유필드Room.leader_membership_id(현재non-null)는감사참조로유지하며 실행리더로쓰지않는다.

Room유지중인해산에서는다른유효T와그관계를보존하기위해대상자의지속Member를일괄종료하지않는다. 한도는현규칙대로 방당활성지속관계1개이며 선택T종료만으로별도주차한도해제를꾸미지않는다. 본인모두탈퇴는Room유지중에도본인한도를해제한다. Room전체종료시는모든관련활성지속관계한도를해제한다. 이차이를확인창요약에담는다.

### 기록 접근의 직접 연계

현재base.member/보관detail·plan은활성지속회원을전제로하는부분이있다. 따라서Member종료만구현하고기록을남겼다고선언할수없다. 새쓰기회원권한과**증명된옛본인기록읽기**를분리한다.

- 입구 read_target/base.room의 group 가시성 검사부터 증명된 본인 기록 경로를 분리한다. 탈퇴 뒤 현재 그룹회원이 아니어도 자기 기록 증명이 있으면 해당 기록만 읽으며 일반 그룹검색/새쓰기 가시성을 열지 않는다.
- 같은room/실제T의 본인 ended Member→CM/Assignment·감사근거로기록권한을증명한다. 이메일/이름/그룹가시성만으로옛회원권을만들지않는다. 재가입으로다른membership이생겨도user+membership이력을혼합해새쓰기권한을승격하지않는다.
- 기존내기록/회원detail·plan의read-only분기에서이근거를허용하고모든쓰기permission을false로한다. 공개card검색권한이나타인의과거회원정보를확대하지않는다. 같은형태를재사용할수있는필드부터보존하며 null리더/이미탈퇴CM은위조하지않고새표시형식이필요하면고정wire에서명시한다.
- active방에서자기선택T만나간경우기존plan403/404를억지로성공요건으로바꾸지않는다. 일반관리plan을열어주지않고확정ACK뒤이탈한다. 종료기록은검증된기록진입에서만읽는다.
- 내기록 목록은 cancelled/removed/종료관계로남고current에서는빠진다. 서버수명판정을앱이모든raid완료/빈방으로다시추정하지않는다.

## 5. 새 wire 제안 — 옛 body를 새효과로 해석하지 않음

기존 `/participation-cancellations`, `/leave`, `/end`, common/cancellation Context, D22/E23의요청·DTO·operation namespace/원ACK는보존한다. 새로 다음2경로를제안한다. **실행OpenAPI에는아직추가하지않는다.**

- GET `/v2/raid-rooms/{room_id}/membership-action-context?target_cycle_key=T`
- POST `/v2/raid-rooms/{room_id}/membership-actions`

같은room의3행동과복구보조를한번의읽기로제공하고 선택직전에다시읽는다. 카드마다읽는API가아니며기존마지막1인해산사전조회를대체한다. 1개option의의미비교/확정에무관한option/token을섞지않는다. 실제화면의1회조회/기존Router통합방법은Flutter가선택하고데이터를읽는것만으로pending/감사/권한변경을하지않는다.

**닫힌필드 제안:** 아래모든필드는required, 객체마다additionalProperties=false. nullable명시외null금지. UUID/date(수요일canonical)/offsetdatetime·양수revision<=2147483647·joined_order양수10진문자열은기존엄격형식. Impact/ACK의T배열은 **실제날짜오름차순C→N**이며새전용DTO로읽는다. 기존ActionResult의source첫순과구분하고강제cast하지않는다.

| 객체 | 정확한필드/형태 |
|---|---|
| Scope | server_now, current_cycle_key, view_cycle_key, policy_version literal `membership-actions-1` |
| Context | scope:Scope, data:MenuData |
| MenuData | room_id:UUID, room_revision:revision, actor:Actor, options:Options |
| Actor | membership_id:UUID, membership_revision:revision |
| Options | leave_target:Option, leave_all:Option, dissolve_led_targets:Option, recover_leadership:Option |
| Option | visible:boolean, permission:기존Permission, impact:Impact 또는 null, confirmation:기존{context_token,issued_at,expires_at} 또는 null |
| Impact | action:Action, affected_cycle_keys:date[0..2], targets:TargetPlan[0..2], room_effect:RoomEffect, existing_completion_preserved:true, display_revision:sha256문자열 |
| Action | leave_target 또는 leave_all 또는 dissolve_led_targets 또는 recover_leadership |
| TargetPlan | target_cycle_key, room_cycle_id:UUID, target_generation:revision, target_revision:revision, leadership_before:기존nullableLeadership, transition:leave 또는 automatic_successor 또는 leadership_pending 또는 close_empty 또는 dissolve 또는 recover, affected_members:MemberEffect[0..8], successor:Successor 또는 null, leadership_after:PlannedLeadership, cleanup:Cleanup |
| MemberEffect | membership_id:UUID, cycle_member_id:UUID, cycle_member_revision:revision, character_id:UUID 또는 null, character_name:string 또는 null, joined_order:양수문자열 또는 null, cancelled_assignment_ids:UUID[0..5], preserved_completed_assignment_ids:UUID[0..5] |
| Successor | membership_id:UUID, cycle_member_id:UUID, cycle_member_revision:revision, character_id:UUID, character_name:string 또는 null, joined_order:양수문자열 |
| PlannedLeadership | leader_cycle_member_id:UUID 또는 null, leader_membership_id:UUID 또는 null, status:active 또는 pending_review 또는 closed, recovery_reason:string 또는 null |
| Cleanup | released_reservation_count:nonnegative, ended_participation_count:nonnegative, cancelled_application_count:nonnegative, cancelled_session_count:nonnegative |
| RoomEffect | kind:preserve 또는 preserve_review 또는 end, actor_membership_will_end:boolean, ended_persistent_membership_count:nonnegative, preserves_unaffected_cycles:true |

정확한영향을안전하게만들수없으면 permission=false/impact=null/confirmation=null로한다. visible은정책에따라유지한다. source actual ID/양수gen가불확정인관계는부정확한TargetPlan에넣지않고reason=ROOM_REVIEW_REQUIRED로닫는다. 그경우에위조대상을반환하거나실행가능해보이게만들지않는다. TargetPlan.affected_members는해당명령의실제참가대상이며완료/stopped역사전원을대상자로늘리지않는다. 활성자리상한을벗어난모순CM집합은검토오류로안내하며큰집합을조용히절단하지않는다. 지속관계종료대상전체의원시회원목록은공개하지않고RoomEffect의count·본인효과와서버내감사에기록한다.

**POST정확한본문6필드:** `expected_cycle_key,view_cycle_key,actor_membership_id,expected_actor_membership_revision,action,context_token`. 별도후계자/영향T/지명회원/새권한입력을받지않는다. path room과고정actor·action·당시C/viewT·본문6필드에token을결합한다. 각option마다다른token을발급하고확인영향의실제T/CM/세대/순서/권한/리더십·대상/주간lease·표시/CAS는서버opaque근거로고정한다. 앱은원Impact와요청을함께보관해ACK를검증한다.

**전용ACK `MembershipActionResult`:** `{scope:Scope,data:ResultData}`.

| 객체 | 정확한필드/형태 |
|---|---|
| ResultData | command_id:UUID4, action:Action, outcome:applied, executed_at:datetime, room_id:UUID, room_revision:revision, actor_membership_id:UUID, actor_membership_revision:revision, actor_membership_ended:boolean, affected_cycle_keys:date[0..2], effects:TargetResult[0..2], room_ended:boolean, ended_persistent_membership_count:nonnegative |
| TargetResult | target_cycle_key, room_cycle_id, target_generation, target_revision, target_state:open 또는 review_required 또는 closed, generation_state:open 또는 review_required 또는 cancelled, leadership:기존nullableLeadership, leadership_status:active 또는 pending_review 또는 closed, recovery_reason:string 또는 null, members:MemberResult[0..8] |
| MemberResult | membership_id, cycle_member_id, cycle_member_revision, state:participating 또는 review_required 또는 cancelled 또는 removed, cancelled_assignment_ids:UUID[0..5], preserved_completed_assignment_ids:UUID[0..5] |

단순지속관계만모두탈퇴는effects/affected_cycle_keys=[]이면서actor_membership_ended=true일수있다. 이형태를실패/가짜T로읽지않는다. 복구는회원의자기참가취소가없어members=[] 또는검토상태가실제로복구된CM만포함하고그효과를Context에고정한다. 새흐름으로과거completed/stopped를변경하지않으므로새ACK에그것을실행결과로만들지않는다.

### 의미 비교·CAS·오류

선택option의impact/permission/visible·actor와의관계를비교하고confirmation시각/token만변경된것과구분한다. 표시용캐릭터·이름/실제날짜·후계자/영향대상·집합/RoomEffect도동일snapshot·token에묶는다. display_revision은그표시와영향의서버digest이고기술ID입력을사용자에게요구하지않는다.

leave_target은선택T근거와RoomEffect를결정하는다른live주차의존재/수명만묶고반대T의무관한표시·일정/CMrevision을강제하지않는다. leave_all은모든본인T·지속관계와각T의후계효과를묶는다. dissolve는**리더인T집합을만든양T권한관측**을묶으므로확인뒤반대T리더가되거나그만둬도재확인하며새집합으로자동실행하지않는다. recover는원복구사유/revision·후계순서/자격·남은검토사유를묶는다.

새실행오류는 정상인증401/비노출404·본인회원아님403, 잘못된field/query/선택T·scope/token본문불일치400, explicit회원revision409/REVISION_CONFLICT, 숨은영향·권한집합변경409/TARGET_CONTEXT_STALE, 주차변경409/CYCLE_CHANGED, 만료409/COMMAND_CONTEXT_EXPIRED, 미증명관계409/ROOM_REVIEW_REQUIRED, 무리더관리T의해산403/TARGET_LEADER_REQUIRED, 복구준비미충족409/LEADERSHIP_RECOVERY_NOT_READY로제안한다. 인원수/후계자격을사유로주차/모두탈퇴를거절하는코드는새행동에사용하지않는다. 실제서버의공통오류코드/HTTPstatus와최종wire에서대조한다.

정상인증·엄격입력/UUID4Key·원bodyhash검사뒤**원ACK24시간복구가새권한·Membership종료·만료/주차검사보다우선**한다. 기존같은Key다른body/진행중·만료 규칙을재사용한다. 새operation `membership-action`의action은bodyhash에포함하고구namespace와충돌시키지않는다. 결과불명은원method/path/body/key/token재송,확정성공뒤새명령을만들어반복하지않는다.

## 6. 저장·트랜잭션·권한 차단

라우터는본문/중복·알수없는query/헤더·인증·no-store와전용DTO를연결한다. pure snapshot planner가GET과쓰기중최신영향/권한검증을공유한다. cycles.execute의 game-mutations-v1 공통잠금/한DB트랜잭션에서 모든T를먼저검증하고 정리→승계/보류/주차종료→필요지속관계·Room종료→head/감사·ACK를적용한다. 같은CM/대상은명령당한번만revision/ParticipationEvent를만들며각T는독립된효과를보존한다. 중간commit/구public명령연속호출/두명령결과합성없음. 마지막에C와120초/C끝중이른만료를재검사하고실패시전체rollback한다. 동시탈퇴둘은직렬화되므로뒤명령의낡은근거는재확인한후새순서로처리한다.

GET은READ ONLY/REPEATABLE READ·쓰기/Key/pending없음,Token<=4096 UTF-8bytes·<=120초/C끝,요청32KiB/응답1MiB·초과413/절단없음이다. rawuser/토큰·인증/소유응답은새로노출하지않는다. 새1MiB상한을위해원시옛회원전체목록을응답에펼치지않는다.

저장은 기존CM cancelled/removed, row/gen review_required/cancelled, nullablegen리더·기존FK/Assignment/주간점유해제를재사용한다. 하지만현재 CycleDecision kind CHECK와ParticipationEvent만으로새다중행동/복구·Room종료감사전체를무리하게인코딩하지않는다. **추가migration 제안**은 (1)명령당immutable membership_action_audits(room/actor/Key/action·원영향/자격/정리/Room효과·시각), (2)cycle/gen별 leadership_recovery 상태/revision/원인·참조감사다. 번호·DDL상세는소비검토뒤고정한다. 기존업무행의일괄상태변경/삭제·구테이블kind재해석은하지않는다.

새review/null리더 reader는특정복구증거에따라정확한null/복구reason을지원하고정상관리권한을허위부여하지않는다. 기존G1공통권한은현재C우선/미확정fallback금지를유지한다. 새T별해산권한만별도판정하고기존전역설정변경권한을승계예외로열지않는다. actor리더의소유/활동문제는자기탈퇴를막지않으며해산은현재actual리더본인+정확한대상정리증명으로허용하되타인의권한을추정하지않는다.

migration구현시 readiness·cycle_worker/outcomes·schedule/times·completion_correction·weekly_summary·v1_compat의0030허용목록과이미지/worker혼용차단을대조한다. 구DB/새앱이준비됐다고오인하지않고추가migration/감사권한/trigger/index를격리DB에서검증한다. 개발반영전새기준선으로기존행/열/설정·키mount 지문을보존하고기존데이터재작성·운영변경은하지않는다. 이번설계로DB/컨테이너를기동/변경하지않는다.

## 7. 구현 구간·검증·소비 검토

1. Flutter 소비대조: 메뉴한번읽기·새전용Context/ACK/6필드원본문·C→N순서, 리더복구보류/명시복구안내, ended회원의기록읽기와쓰기분리의구체차이만확인. 이미확정된3행동정책을재수용하도록묻지않는다. 스키마표는설계안이며구현전closed OpenAPI/합성대표예시로고정한다.
2. Backend 내부구간: 원자scope/영향planner·선택T탈퇴/후계복구·감사기반 → 모두탈퇴/각T해산·Room/Member/한도·기록/worker reader직접연계. 하나의독립완료조건후속안에서추적하며독립검색은별도로한다. 설계단계에기능코드/실행OpenAPI를수정하지않는다.
3. 표적검증: C/N·C만/N만/양리더·각비리더/1인/8인·소유부적격/review후계/순서미확정·재참가/동시탈퇴·리더집합변경·한T실패/감사/최종C·만료rollback·완료/반대T/동의·예약보존·원ACK/구pending24h·지속관계/한도/재가입기록혼합방어·null리더review읽기/worker만료/명시복구·서버결정과 앱 성공 뒤 GET실패를검증한다. 합성시간/DB검증과정상실회원/기기는구분한다.
4. 검증된구현을commit/push·원격확인한뒤정확한소비SHA/closed OpenAPI/허용·거절/승계·보류·1인·8인·역할혼합대표예시/실행개발·DB상태를후속Issue에인계한다. Flutter연결/사용자기기전체인수·dev/main/운영은별도다. 검색·탈퇴후목록은영향T만갱신하고다른기기에즉시push전달을새로보장하지않는다.


협업 추적: [이 설계 Issue #25](https://github.com/heo0328/lostparty-backend/issues/25) / [관련 후속 #24](https://github.com/heo0328/lostparty-backend/issues/24) / [원본 #13](https://github.com/heo0328/lostparty-backend/issues/13). 검색/탈퇴·해산의 완료조건을 분리한 것이며 원본 요구의 폐기/완료나 별도 기능 브랜치 생성이 아니다.
