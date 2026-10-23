# Issue #13 — 개인 완료후 선택T 탈퇴·양T 동일회원 추방 계약 제안1

최신 구현 기준: [개발 안내](../development/ISSUE_22_23_ATOMIC_MEMBER_ACTIONS_DEVELOPMENT.md). 아래 제안1의 source participating 한정과 표시 UUID만의 형태는 #22/#23 Backend 전체2번째 보완으로 변경됐다. 정확한 실행 wire는 openapi/two-cycle.openapi.yaml의 새 전용 DTO를 따른다.

2026-10-23 / Backend / feat/raid-recruitment / **제안1 당시 기록(현재 구현/개발 반영 완료)**.

당시 소비검토: [#22 Flutter1](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6361482436)·[#23 Flutter1](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6361482811)이 방향을 수용했다. Backend의 다음 보완은 #22 확인창 표시와 Context의 동일스냅샷 근거, #23 확정된 source review의 정리범위/권한·미확정 거절이다. 아래 제안1의 source participating 한정 등을 아직 최종 구현계약으로 간주하지 않는다. 정확한 보완/wire·예시/구현SHA/개발반영 여부 인계가 남아 있다. 마지막1인해산 유지는 확정이고 양T다인강제해산은 요청하지 않았다.

후속 계약 검토: [#22 개인 완료후 탈퇴](https://github.com/heo0328/lostparty-backend/issues/22), [#23 양T 동일회원 추방](https://github.com/heo0328/lostparty-backend/issues/23). 각 Issue 본문 전문이 소비 대조 원본이며 아직 실행계약이 아니다.

원본: [Flutter131 개인 완료후 탈퇴](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360708926), [Flutter128 양주차 함께 내보내기](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360210574), [Flutter130 기존 한T/UI 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360353809). 현재 Backend 구현/개발소비8bbcfc8·170경로/DB0030은 그대로다. 새 명령은 구 personal/단일T remove/global leave/end와 분리해 원pending·원ACK·기존 호출자를 보존한다. 마지막1인해산 유지는 확정이며 양T다인강제해산은 요청하지 않았으므로 포함하지 않는다.

## 사용자 문제·책임·선택 이유

개인 완료 뒤 실제로 그 주차 모집에서 나가고 필요한 리더 승계까지 한 번에 확정해야 한다. 카드의 같은 사람을 현재 주차만 또는 두 주차에서 내보낼 때도 두 번의 독립 쓰기를 성공 하나로 꾸미지 않아야 한다. 기존 두 명령을 앱에서 연속 호출하지 않고 새 원자적 명령을 제안한다. UI 단계/대상선택 화면을 추가하지 않으며 확인창에 실제 효과만 제공한다.

라우터는 엄격 입력/인증과 HTTP를, 업무 서비스는 대상/권한·영향/후계자 검증과 공통 내부 효과를, 기존 cycles.execute 실행 경계는 game-mutations-v1 직렬화·한 트랜잭션/원ACK·최종 주차/만료 검사를 맡는다. public 명령 함수 두 개를 호출하거나 중간 commit하지 않는다. 완료·점유/예약정리·승계·감사 공통 함수를 필요한 만큼 재사용한다. 이 문서로 기존 API/DB를 변경하지 않는다.

## 1. 개인 완료 후 해당 주차 탈퇴

### 제안 경로·대상

- GET `/v2/raid-rooms/{room_id}/personal-completion-departure-context?target_cycle_key=T&round_id=R`
- POST `/v2/raid-rooms/{room_id}/personal-completion-departures`

T는 현재C, 수요일10시 이후여야 한다. 현재 정상세션/지속회원·explicit 현재generation의 participating 본인 CycleMember, 선택round의 active 본인Assignment를 확인한다. 선택본인 캐릭터의 현재 소유/검증·활동과 ownership/lifecycle revision을 검사한다. 미래N·과거T·다른회원/round/세대·이미 완료/취소된 선택Assignment는 새 명령 대상으로 쓰지 않는다. 기존 성공의 같은Key 재송은 아래 원ACK 규칙이 우선한다. 이미 완료한 item에 새Key로 같은 완료를 덮어쓰는 동작은 추가하지 않는다.

### 한 명령의 정확한 영향

1. 선택raid의 본인 active Assignment **1개만** completed/manual source로 기록한다. 기존 party/manual 완료·완료Assignment는 덮거나 지우지 않는다.
2. 같은T/같은CycleMember의 나머지 active Assignment는 left/ended로 종료하고 해당 점유/시간예약을 해제한다. **남은raid를 완료로 만들지 않는다.** 원래 completed Assignment와 다른회원의 완료/참가는 유지한다.
3. 본인 T의 active session participation/동의·예약을 종료하고 제출/투표 등 실행 근거를 기존 취소·제안 정족수 규칙에 맞춰 정리/재평가한다. 끝난 동의/예약/제출의 증거는 감사에 보존한다. 타인의 기존 확정시간/정상 예약을 자의적으로 초기화하지 않는다.
4. 본인 CycleMember는 cancelled/ended_at으로 실제 탈퇴를 표현한다. 완료한 Assignment/주간source는 별도 사실로 보존한다. 지속Member는 종료하지 않아 다른T 관계와 기존 기록권한을 유지한다. 본인 주간summary에는 완료를 표시하지만 current 참가목록에서는 빠진다.

다중raid는 위 complete_assignment_ids(선택1)/cancel_assignment_ids(나머지active)/preserved_completed_assignment_ids를 확인창에서 구분한다. 시간예약 해제 개수·선택raid/본인 character·실제T·승계/종료 효과도 함께 제공한다. 확인창에 기술token·세대 입력을 요구하지 않는다.

### 공대장 승계·마지막1인

- 일반회원이고 남는 실제 활성/검토 관계가 있으면 다른 리더는 유지한다. 일반회원이라도 마지막 실제 참가라면 아래 마지막1인 종료 규칙이 우선한다.
- 본인이 공대장이고 다른 participating/review_required 실제 관계가 남으면, **participating이며 남은 active Assignment가 있고 현재 기존 승계자격 검사를 통과한 후보** 중 joined_order→CycleMember UUID 순 첫 사람에게 자동승계한다. 완료/stopped/cancelled/removed/review만인 사람을 실행리더로 만들지 않는다. 다른 참가관계는 남아 있는데 적격후계자가 없으면 SUCCESSOR_UNAVAILABLE로 **완료·탈퇴 모두 거절**한다. 완료만 먼저 성공시키거나 임의자격완화/두번째 명령으로 처리하지 않는다.
- 남는 실제 활성/검토 관계가 없으면 해당T만 닫는다. 모든item이 실제 완료근거를 갖추면 generation=completed, 나머지 불완료raid가 있으면 generation=cancelled로 하고 남은 active Round는 불완료 종료한다. 기존 완료Round/Assignment를 불완료로 되돌리지 않는다. T의 pending신청/제안과 빈 실행세션도 정리한다.
- 이 마지막 종료는 실행리더를 없애므로 leadership의 leader_cycle_member_id/leader_membership_id는 **둘다null**, leadership_revision은 증가한다. closed+completed도 이 nullable 형태를 허용하도록 읽기 구현을 맞춘다. 기존 완료자료의 이전 리더는 일괄 재작성하지 않고 감사에 보존한다. successor는null이다. closed+completed에 가짜현리더를 채우지 않는다.
- N이 실제 열렸으면 N의 참여/공대장/일정/동의/제출/UUID를 그대로 보존한다. 새N을 만들거나 모든주차탈퇴로 바꾸지 않는다. 공통 G1권한 규칙을 이 명령으로 재정의하지 않는다. N이 없을 때 완료보관은 기존129의 전체완료 근거 규칙을 따르며 일부완료·빈방을 전체완료로 추정하지 않는다.

### Context·POST 닫힌 형태

모든 새 객체는 additionalProperties=false, 표의 필드는 모두required이며 nullable을 명시한 필드만null이다. UUID/date/datetime/revision/Permission/Scope는 기존 two-cycle 형식과 같은 엄격 타입이다. Scope는 server_now/current_cycle_key/target_cycle_key/playable_from/phase/target_revision/policy_version/room_cycle_id/target_generation이며 대상T의 실제값을 사용한다.

Context200은 `{scope,data}`이고 data의 정확한 필드는 다음과 같다.

| 필드 | 형태 |
|---|---|
| action | literal personal_completion_departure |
| room_id | UUID |
| subject | {membership_id,cycle_member_id,cycle_member_revision,character_id,round_id,assignment_id,assignment_revision}, UUID/revision |
| leadership | 기존 {leader_cycle_member_id:UUID|null,leadership_revision:revision,leader_membership_id:UUID|null} |
| impact | {complete_assignment_ids:UUID[1],cancel_assignment_ids:UUID[0..4],preserved_completed_assignment_ids:UUID[0..5],released_reservation_count:nonnegative integer,departure_effect:leave\|automatic_successor\|close_completed\|close_incomplete,successor:Successor|null,preserves_other_cycles:true,preserves_global_membership:true} |
| permission | 기존 {allowed:boolean,reason:string|null,next_change_at:datetime|null} |
| confirmation | {context_token:string,issued_at:datetime,expires_at:datetime} 또는null |

Successor는 `{cycle_member_id:UUID,revision:revision,joined_order:정규양수10진문자열,character_id:UUID,character_name:string|null}`다. 승계후보 없음인 거절 Context는 departure_effect=automatic_successor·successor=null·permission=false/SUCCESSOR_UNAVAILABLE·confirmation=null이다. 완료/취소 대상이 이미 바뀌어 정확한 Context를 구성할 수 없으면 기존 대상/권한 오류409/403/404를 반환한다.

POST body의 정확한 필드는 `expected_cycle_key,target_cycle_key,room_cycle_id,target_generation,expected_target_revision,actor_cycle_member_id,expected_cycle_member_revision,round_id,context_token`이다. expected_cycle_key는 확인시C, 나머지는 읽은 실제T/UUID/양수revision이며 round_id는 확인한 동일round다. actor/assignment·주간revision/소유·잔여참가/정족수/후계자·리더십/plan 등 추가CAS는token의 고정근거로 현재DB와 대조한다. token과 다른 본문/대상/효과로 바꿀 수 없다.

## 2. 카드 대상의 현재만/양주차 원자적 내보내기

### 제안 경로·조회 범위

- GET `/v2/raid-rooms/{room_id}/member-removal-context?target_cycle_key=T&target_cycle_member_id=M`
- POST `/v2/raid-rooms/{room_id}/member-removals`

현재 보고 있는 실제T=C또는N과 카드의 CycleMember를 고정한다. 서버가 지속membership과 실제user_id로 반대 C/N의 **같은회원 실제관계**를 확인한다. 다른character도 같은사람이며 이름/character명으로 연결하지 않는다. 반대주차가 없거나 희망/legacy_intent/not_selected/completed/stopped/cancelled/removed일 뿐이면 함께추방의 실제대상으로 만들지 않는다. actual participating/review_required가 있으면 반대관계 존재를 알려준다. 사용자에게 raw user_id/ownership 원문을 새로 노출하지 않고 공개대상은 기존 membership_id/실제CycleMember·character와 표시명, user_id/소유근거는token 안에 결합한다.

sourceT는 explicit/open·양수generation과 현재 participating 공대장/그 자격을 확인한다. source대상은 자기자신/공대장이 아닌 participating actual이어야 한다. 반대T도 함께 처리하려면 그곳이 explicit/open·양수generation이고 **호출자가 그T의 현재 participating 공대장으로 검증**돼야 하며 대상도 participating인 비공대장이어야 한다. 반대T의 review/미확정세대·호출자가비공대장·대상이리더이면 both를 거절한다. 상대T공대장 권한을 sourceT에서 확장하지 않는다. 이 정책에서는 리더를 추방하지 않으므로 양T 추방에 자동승계를 끼워 넣지 않는다. 처리중 리더가 바뀌면 CAS로 전체거절한다.

대상회원의 소유/활동 상태가 잘못돼 정리가 필요한 관계도 현재 공대장에게 무조건 숨기지는 않는다. 그 관계의 실제 Assignment/계정 소유·활동revision 및 현재등록 근거를 확인에 고정하고 확인후 변경이면 재확인한다. 오래된 확인으로 새소유자/다른가입·재참가/다른세대의 관계를 제거하지 않는다.

### Context200과 버튼 권한

최상위는 `{scope,data}`이며 Scope는 **보고 있는 sourceT**다. data는 아래 필드만 가진다.

| 필드 | 형태 |
|---|---|
| action / room_id | literal member_removal / UUID |
| target_membership_id | 카드 대상 지속membership UUID |
| source | RemovalTarget |
| opposite_relation | OppositeRelation |
| options | {current_only:RemovalOption,both:RemovalOption} |

RemovalTarget은 `{target_cycle_key,room_cycle_id,target_generation,target_revision,actor_cycle_member_id,actor_cycle_member_revision,target_cycle_member_id,target_cycle_member_revision,character_id,character_name,leadership}`다. character_name만nullable, 나머지 UUID/revision/date와 기존Leadership이다. actor는그T의실제본인, target은실제대상이다.

OppositeRelation은 `{target_cycle_key,status:none|participating|review_required,target:RemovalTarget|null}`이다. 실제관계가 없으면 status=none/target=null. **반대의 실제review가 있지만 gen/actor 등 RemovalTarget을 확정할 수 없으면 status=review_required/target=null**을 허용하고 both를false/ROOM_REVIEW_REQUIRED로 닫는다. participating이어도 호출자가 그T의 actual actor가 없으면 target=null일 수 있으며 status는참여존재를뜻한다. 이 경우 both=false/TARGET_LEADER_REQUIRED다. null을 가짜gen/actorID로 채우지 않는다. source카드의 정확한membership/user에 결합한 최소관계만 공개한다.

RemovalOption은 `{permission:Permission,impact:RemovalImpact|null,confirmation:Confirmation|null}`이다. 허용시에만 impact/confirmation을 제공하고 거절시는둘다null이다. current_only는 sourceT 자체권한, both는 두T권한이다. 반대존재/권한이없어도 source권한이유효하면 current_only를 유지한다. 반대status=none이면 both=false/OTHER_TARGET_NOT_PARTICIPATING, review이면false/ROOM_REVIEW_REQUIRED, 상대리더권한없으면false/TARGET_LEADER_REQUIRED다. 그 외 대상이리더/본인/상태부적합은 ROOM_REMOVAL_TARGET_INVALID다. 여러거절조건이있으면 review→리더권한→대상상태 순으로 대표사유를 고른다.

RemovalImpact는 `{mode:current_only|both,affected_cycle_keys:실제date[1..2],targets:RemovalEffect[1..2],preserves_completed:true,preserves_global_membership:true}`다. RemovalEffect는 `{target_cycle_key,cycle_member_id,cancel_assignment_ids:UUID[0..5],preserved_completed_assignment_ids:UUID[0..5],released_reservation_count:nonnegative integer}`다. source첫순/반대T순으로 targets를제공하며 affected_cycle_keys도동일순서다.

UI는 반대실제관계가없으면 단일T확인, 있으면 취소/현재주차만/함께내보내기3선택을 유지한다. both불가시그선택은불가사유와비활성으로표시하고 current_only로 임의대체하지 않는다. 탭만으로 쓰지 않고 확인시에 해당option의token으로 제출한다. 대상/주차 dropdown이나 또 다른 선택단계는 추가하지 않는다.

### POST·원자성

POST body는 `expected_cycle_key,target_cycle_key,room_cycle_id,target_generation,expected_target_revision,target_membership_id,target_cycle_member_id,expected_target_cycle_member_revision,mode,context_token`이다. mode=current_only|both, 나머지는sourceT와카드의실제값이다. **option별로 별도token**을 발급해 mode/선택효과에묶는다. current_only token은source근거만재검사하고 반대T의무관변화를같은쓰기CAS로강제하지않는다. both token은 두실제T/actor·target membership/user·양쪽CM/Assignment/소유·각gen/revision/리더십/plan·현재권한/영향을 모두검사한다. 반대T body를앱에서추정/조립하거나2명령을연속호출하지않는다.

한 공통쓰기잠금·한DB트랜잭션에서 모든대상을 먼저검증하고 선택된T의대상 active Assignment/점유·예약·세션참여/제출·제안근거를정리해 CycleMember=removed로종료한다. 선택되지않은T와대상/타인의기존완료·완료Assignment/Outcome·지속Member를보존한다. secondT실패/최종경계변경이면 firstT도rollback하고 원ACK는없다. 첫T처리후두번째T검증하는부분성공은허용하지않는다.

## 3. 두 새 명령의 전용 ACK·시각/오류·재조회

UUID4 Idempotency-Key는 POST마다1개, GET은Key/pending/원장·감사를생성하지않는READ ONLY/REPEATABLE READ다. token은actor/flow/room/실제T·요청본문·확정영향/CAS를결합한opaque값, 최대4096UTF-8bytes/120초와현재C끝중이른만료, issued_at은읽기의server_now다. permission=false이면confirmation=null이며실패token구경로fallback은없다. 새GET/POST는no-store, 요청32KiB/응답전체1MiB초과413/절단없음/엄격query·중복/추가필드거절이다.

두새POST의Ack200은 `{scope,data}`이며 Scope는 **호출 당시 sourceT**이고 실제값을보존한다. data의정확한필드는다음과같다.

| 필드 | 타입/의미 |
|---|---|
| command_id | UUID4 요청Key |
| action | personal_completion_departure 또는member_removal |
| outcome / executed_at / room_id | applied / offset datetime / UUID |
| subject_membership_id | 실제본인 또는대상 지속membership UUID |
| affected_cycle_keys | sourceT첫순 실제date 배열, 개인1/current_only1/both2 |
| effects | 같은순서 ActionEffect[1..2] |

ActionEffect는 `{target_cycle_key,room_cycle_id,target_generation,target_revision,cycle_member_id,cycle_member_revision,state:cancelled|removed,leadership,completed_assignment_ids:UUID[0..1],cancelled_assignment_ids:UUID[0..5],preserved_completed_assignment_ids:UUID[0..5]}`다. 제거의 completed_assignment_ids는[]이고 개인완료는선택1개다. leadership은실행후값, 닫힌마지막T는앞서제안한null리더/증가revision이다. 모든필드는required/닫힌객체이며source와ACK의실제ID/세대·주차를대조한다. 기존room Ack DTO로강제캐스팅하거나현재T별개쓰기 결과2개를합치지않는다.

- 원ACK 복구는 기존정상인증/엄격입력/Key·본문검사후24시간내우선한다. 같은Key다른본문은 IDEMPOTENCY_CONFLICT409, 진행중REQUEST_IN_PROGRESS409/Retry-After2초, 만료IDEMPOTENCY_EXPIRED409다. 결과불명은원method/path/body/key/token을그대로재송하며리더승계/탈퇴/만료/주차변경후에도원성공ACK를복구한다. 원ACK에현재C/새revision을덮지않고원pending과비교한다.
- 새실행은 현재세션/방접근→대상/현재C·T/generation/명시CAS→token actor/flow/body/만료→선택T들최신권한/소유·영향/후계자/hiddenCAS→단일원자적효과/감사·ACK→최종C/만료·완료playable를검사한다. 타주차/actor/변조/본문불일치는 CONTEXT_INVALID400, 잘못된서로의ID관계는TARGET_SCOPE_MISMATCH400, 명시revision불일치REVISION_CONFLICT409, 숨은영향/대상변경TARGET_CONTEXT_STALE409, 만료COMMAND_CONTEXT_EXPIRED409/CYCLE_CHANGED409를구분한다. 기존인증401/소유·리더권한403/비노출404·ROOM_NOT_ACTIVE/ROOM_REVIEW_REQUIRED/ROUND_NOT_ACTIVE/PLAY_NOT_STARTED/TARGET_CYCLE_NOT_CURRENT/SUCCESSOR_UNAVAILABLE 등의현재권한사유는유지한다. 기존형식이정상인token을새flow에잘못사용해도거절한다.
- 개인성공은 본인주간summary/해당room의sourceT상세·검색/current/all목록과현재세션/예약·역할근거를무효화한다. **탈퇴한T의member-only plan을다시읽어성공조건으로삼지않는다.** 기존plan접근이막혀도ACK성공/pending해제를유지하고목록/계정완료로이동한다. 반대T실제데이터/선택은유지한다.
- 추방성공은effects의선택T들만현재호출단의room detail/plan·검색/본인목록·역할/후보/예약관련읽기를무효화한다. current_only는반대T무효화/재쓰기하지않고 both는양T를갱신한다. 다른회원기기에실시간push가새로구현됐다고가정하지않으며그회원은다음권한확인/조회에서종료를확인한다. 갱신읽기실패는성공쓰기의실패가아니다.

## 4. 감사·호환과 합의 후 검증

선택raid의개인완료는기존불변CycleOutcome(kind=personal_completion)에새action·전후효과를기록하고, 실제탈퇴/추방은해당CycleMember의취소/removed event, 승계는automatic_successor·개인탈퇴결정은declined에정확한reason/선택T증거를보존한다. 동일회원/event revision 고유제약을지키며같은revision에완료/취소event를중복삽입하지않는다. 기존완료/예약/감사원문을삭제하지않고새kind를임의로기존CHECK에넣지않는다. 현재검토는기존감사타입재사용이가능하며실제DDL필요여부는구현검증뒤인계에서확정한다. 현재migration/DB변경없음이다.

기존 personal_completion/complete_item/manual·removals·N cancel/continue·globalleave/end·완료정정/보관129·원pending/bodyhash는그대로다. 기존API에새의미/required를몰래넣지않는다. closed+completed의null리더지원은새마지막T종료의읽기영향으로검증·예시를인계하며다른주차리더십을바꾸지않는다.

합의 후 Backend는새닫힌DTO/정확한실행OpenAPI/실행예시를구현하고다음직접경계를격리검증→구간commit/push·원격확인→SHA·개발반영/DB여부인계한다. 이문서는실행API인계나시험요청이아니다.

- 개인: 일반/리더·후계자순서/후계없음/마지막1인·다중raid선택1완료/나머지취소·완료/party/타인/N보존·현재C/수10시·소유/재참가/세대/후계상태변화·selected이미완료거절
- 추방: 현재C/N반대조회·동일user/다른character·없음/review/nullgen·한쪽리더/양쪽리더/대상이반대리더·current_only의반대불변·both의2번째실패전체rollback·회원/소유/재참가/세대/리더변경
- 공통: actor/flow/본문/변조·만료/최종만료/rollover·동일Key경합/다른본문/원ACK24시간·감사실패rollback·좌석/예약/정족수/제출증거·bounded/no-store·닫힌nullable/실제ID·기존주요흐름회귀

**다음 Flutter 소비 대조 두 항목:** ① 개인완료는active선택1개+잔여T취소/실제탈퇴·자격있는자동승계/없으면전체거절·마지막T null리더·성공후member-plan미의존을위UX로소비할수있는가? ② 추방option별token·반대미참여/검토/권한없음의정확한차이·current_only유지/both불가표시·양T원자Ack를기존카드3선택에연결할수있는가? 구체차이만회신하면되며같은기존시험/정책수용을반복요청하지않는다.

두구간은 각각독립된명령/권한/완료조건을가지므로 후속Issue로분리하고 원본#13과이문서를상호연결해추적한다. 기존feat/raid-recruitment브랜치는유지하며이슈분리를새브랜치/기능완료로해석하지않는다. 전역양T강제해산·과거UI확대·시간선택UI·통계#19·pending영속복구는확장하지않고Issue OPEN·운영배포/실데이터삭제없음이다.
