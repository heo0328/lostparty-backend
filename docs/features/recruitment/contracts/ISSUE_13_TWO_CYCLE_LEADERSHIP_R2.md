> **현재 구현 기준(2026-10-21):** [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 잔여 충돌 없이 소비 검토를 마감했다. 계약0.4.1/policy4를 고정하며 [W1~W5 작업계획](../planning/ISSUE_13_TWO_CYCLE_WORK_PLAN.md)을 따른다. 아래 검토대기/후속질문·구판 단계표는 당시 기록이다. 실제 기능/실행API·DB 인수는 별도 미완료다.

> **최신 보완:** [계약 후보4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)이 전체80번째의 제목/전역CAS/생성checkbox/숙련도검색 수정을 반영한다. 아래3판까지의 생성후추가활성화/제목schema·global target CAS 가정은 최신계약이 아니다. 이 문서는 당시 기록으로 보존한다.

> **최신 계약 후보:** [전체 계약3판](../../../archive/recruitment/ISSUE_13_TWO_CYCLE_CONTRACT_R3.md)이 전체77/78번째의 기술 보완·L1/G1/A1 확정을 반영한다. 아래 정책 대기/부분 core 상태는 당시 기록이며 최신 전체 JSON은 별도 full 파일이다.

# Issue #13 주차별 공대장·승계 보완 2판

2026-10-21 / feat/raid-recruitment / 기준 구현 cc003e9·HEAD6490f69. **설계·계약 검토 회신이며 구현/실행 DB 이행/배포 지시가 아니다.** 문서만 로컬 미커밋·미push. 원본 OpenAPI·서버·자료는 그대로다.

입력: [전체74번째 Flutter 소비 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6296514170), [전체75번째 Flutter 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6297004407). [설계1판/전체73번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6296309772)의 전역공대장/빈N개방/승계선행취소/자동새N개방을 아래로 대체한다. 그 밖의 C/N actualcycle·승인생략·B보존·수10시완료·통계별도·원ACK 원칙은 유지한다.

## 1. 확정과 제안의 경계

**사용자 확정**: C 공대장의 명시 함께하기 활성화=같은 방 N 개방+본인 최초 실제 참가/공대장, 다른 C인원은 본인 선택. N 탈퇴는 다른 N인원/모집을 유지하며 참가 순서 자동승계, C 영향0. 직접 위임은 T에만, 위임자는 남는다. 실제 편성 기반 자리번호와 공대장 배지는 별개다.

**이번 기술안**: T별 관리권/순서원천·원자명령·revision·후보검사·자리 보존·반환형. 현재 코드의 globalleader 참조를 유지한 채 permission만 바꾸는 것으로 구현할 수 없다.

**제품 결정 대기**: 마지막 1인 뒤 재개 허용 방식/관계한도 정리, 공통자원의 최종 관리 정책, 이후 매주 자동개방과 기존auto옵션의 새 의미. 아래 추천을 사용자 확정으로 간주하거나 미정 기능을 실행하지 않는다.

## 2. 저장 구조·권한 출처

현재 integrated_models.Room.leader_membership_id, admission_service.member(leader=True), completion.transfer/drop_membership, management.settings_view, scheduling.make_session 등은 전역leader다. 모든 v2 target 명령은 별도 `cycle_leader(db,room,T,actor)`로 대체하고 v1 adapter도 동일 target 검증을 통과시킨다.

설계1판 RoomCycle에 `leader_cycle_member_id` nullable UUID, `leadership_revision` positive int, `generation` positive int, `next_join_order` bigint를 추가한다. nullable는 닫힌 회차 또는 보존자료 review에서만 허용하며 정상 모집중 회차는 실제 책임자가 있어야 한다. FK는 (room_cycle_id,leader_cycle_member_id)→동일 회차 참가관계로 묶는다.

추가 `recruitment_cycle_memberships` 제안: id, room_cycle_id, persistent_membership_id, revision, state(participating|completed|cancelled|removed|review_required), joined_order, joined_at, ended_at, eligibility_reason(nullable). (room_cycle_id,persistent_membership_id) 유일. 묶음 item별 Assignment를 하나의 실제 참가관계에 연결한다. 한 item 완료만으로 관계가 종료되지는 않고 마지막 item완료 후 completed는 관리권/당시 참가이력을 보존한다. 명시 탈퇴/추방은 ended_at을 설정한다.

이는 기존 persistent membership과 중복 역할이 아니다. persistent 관계는 방 접근/한도·보존을, cycle 관계는 해당 T의 실제 참가·공대장 권한과 참가 순서를 담당한다. 기존 weekly 원장/assignment/예약 UUID는 그대로 재사용한다. 이전3종 저장안에 이 회차 참가관계1종을 추가하며 불변 이벤트로 취소/재참가 구간을 보존한다.

`Room.leader_membership_id`는 기존자료 보존·구버전 adapter 입력으로만 남기고 N 위임으로 덮지 않는다. 과거 전역 공대장 이력을 없는 T에 소급 생성하지 않는다. 증명 가능한 기존 C 실제참가 관계에서만 최초 회차leader를 backfill하고 나머지는 review다. 06시에는 N의 같은 RoomCycle/leader_cycle_member_id/Assignment·예약이 C가 되며 새 리더 선출을 하지 않는다.

| 명령 | 권한 근거 | 다른 T 영향 |
|---|---|---|
| T 신청승인/거절·설정·편성·일정제안/조정·raid완료 | T의 현 leader_cycle_member + 기존 개별명령조건 | 없음 |
| T 직접 위임 | T 현공대장→T 실제 유효후보, leadership/members CAS | 없음 |
| T 개인탈퇴 | T 본인관계, 공대장일 경우 같은 transaction 자동승계 | 없음 |
| N 명시 최초개방+참가 | 실제 C 공대장·소스/선택자격 + N개방context | C/B 무변경 |
| T 개인완료/미완료종료 | 기존 실제참가자 범위 + T/current/수10시 guard | 없음 |
| 제목·공개범위·그룹연결·방전체해산 | 아래 공통자원 정책 별도 | 영향context에 전체범위 표시 |

C공대장 P, N공대장 Q이면 P의 N 승인/설정/일정/완료/편성 요청과 Q의 C 요청은403 `TARGET_LEADER_REQUIRED`. room UUID/전역leader 일치만으로 허용하지 않는다. 완료10시 guard는 리더권한과 별도 검사한다.

## 3. 개방+최초공대장 참가

새 read-only `GET /v2/me/raid-rooms/{room_id}/opening-context?target_cycle_key=N`은 기본 C의 현재 캐릭터/역할을 서버에서 선택한다. 대체 입력은 character_id/selected_role 두 개를 함께 제공한다. context는 소스 C 공대장·참가관계/선택·소유/한도/대상 주간원장/설정·N 존재 여부/개방세대·room공통권한 revision을120초/06시 경계로 결합한다.

`POST /v2/raid-rooms/{room_id}/recruitment-openings`는 이 context로만 실행한다. 새 N이면 RoomCycle+전체Round/스냅샷·공대장 실제 bundle 참가/점유·설정·ACK를 한 transaction에 기록한다. 최초 joined_order=1, leader 참조도 그 실제관계다. 개방만 하고 무자격 좌석을 만들거나 다른 C인원을 자동복제하지 않는다. 실패는 새 N/슬롯/선택/예약0, C/B보존이다. source/ownership/lastslot 경합과 함께 최종 DB시간을 검사한다.

기본 캐릭터가 N의 B와 충돌하면 TARGET_CHARACTER_CONFLICT와 권한내 B방 제목/상세 진입을 제공한다. 사용자가 대체 캐릭터를 선택해 새 context를 받으면 같은 원자개방 명령으로 진행한다. 자동 B탈퇴/임시좌석/자동 재시도 없음.

이미 열린 N의 같은 원키 재전송은 원ACK 복구. 새 키에서 이미 열린 상태를 발견하면 `noop`이며 기존 N공대장/참가자/설정에 손대지 않는다. 활성화한 사람이 N에서 빠졌다가 ON을 다시 눌러도 새 공대장으로 강제 복귀하지 않는다. 재참가는 별도 N admission이며 닫힌 N의 재개는 아래 미확정 정책이 필요하다.

이 개방은 **참가 확정**이다. 이미 존재하는 확정 일정 전부의 본인 확인으로 간주하지 않는다. 새 일정 생성에서 공대장이 수동 시각을 명시 확정한 기존 동작만 그 시각에 대한 확인/예약으로 처리한다. 복사한 기존 확정 일정·승계·직접위임은 동의를 만들지 않으며 참가확인 상태를 따로 돌려준다.

## 4. 자동승계·직접위임·순서와 편성

순서키는 (generation,joined_order,cycle_member_id) 오름차순이다. joined_order는 T의 next_join_order를 직렬화해 실제 bundle 참가 성공 때만 증가한다. 신청/legacychoice·실패에는 번호를 주지 않는다. 정상적으로 순번은 유일하며 UUID는 보존자료 동률의 결정적 tie-break다. 재참가는 새 joined_order/새 유효구간을 부여하므로 예전 번호를 되찾지 않는다. C/N순서는 독립이다.

자동승계 후보는 T 실제관계가 participating/completed이고 탈퇴/추방되지 않았으며 활성회원·현재 소유/캐릭터 활동·해당 대상 자격/관리권이 유효한 사람이다. 신청대기/불참/미선택/legacyintent/review는 후보가 아니다. 자기 자신 제외 후 최초 유효후보를 선택한다. 남은 사람이 모두 부적격이면 임의 외부인을 임명하거나 다른 주차를 바꾸지 않고409 `SUCCESSOR_UNAVAILABLE`/취소0으로 반환한다. 조회/자격복구·명시관리 경로를 안내한다.

취소 context에는 `mode=leave|auto_successor|close_target`, 현재 leader/leadership_revision, members_revision, 예상후보와 후보revision, 해제되는 묶음/예약 수를 담는다. 실행에서 후보가 달라졌으면409 TARGET_CONTEXT_STALE로 새 영향 확인이 필요하다. 사용자가 확인한 후보와 다른 사람을 조용히 승계하지 않는다.

탈퇴·승계·대상 전체 bundle 해제/원장/예약정리·구간이력·ACK는 한 transaction이다. T leader/members revision을 올리며 C revision/관계는 건드리지 않는다. 후보 동시탈퇴/마지막자리승인/직접위임은 기존 game-mutations 직렬화와 관련 CAS/DB제약으로 한 순서에만 성공한다. 원ACK replay는 현재leader/새주차검증보다 먼저 처리하되 동일회원·operation/T·본문에만 허용한다.

직접위임: context에 실제 후보들의 cycle_member_id/공개 캐릭터 표시/후보revision/권한, T·리더/리더revision·영향을 제공한다. 실행에서는 명시 고른 후보를 재검증하고 `leader_cycle_member_id`만 바꾼다. 위임자는 참가자로 남고 좌석/예약·C권한은 그대로다. 같은후보가 이미leader면 동일원키ACK 또는 검증된 noop, 다른후보로 같은키재사용은멱등충돌이다.

**자리 보존 추천**: 승계/위임은 기존 party_no/slot_no를 바꾸지 않는다. '공대장은항상1-1' 규칙은 실제소스에 강제되어 있지 않으며 이를 새로 요구받은 것으로 간주하지 않는다. 새 생성/개방에서 가능한 최초 자리(보통1/1)를 배정하더라도 위임 때1-1 교환을 자동실행하지 않는다. 편성변경은 별도 T 편성명령이며 역할/직업 조건을 검사한다. 따라서2-3의Q에게 위임하면 Q는2-3+공대장배지,1-1의P는그대로 참가자다. 슬롯고정 요구가 추가되면 별도 정책대조가 필요하다.

## 5. 다음 주 마지막 1인 — 제안·재개·한도

**추천안 L1, 아직 제품확정 전**: 마지막 N인원의 명시탈퇴는 해당 T 회차만 `cancelled`로 닫고 leader=null, 신규신청/참가중지, pending N신청은 cancelled, 미확정/확정N일정·예약/점유만정리한다. C의leader/참가/완료/예약·공통Room.ended_at은 그대로다. 미래주를 실제주차 미완료종료 통계로 잘못 세지 않도록 `future_empty_cancelled` 원인과시각을별도보존한다. 기존 Round 상태제약에도 cancelled 구분이필요하며 stopped_incomplete로임의대체하지않는다. 완료/수10시guard를미래예정취소에적용하지않는다.

재개추천: 새참가자의자동부활이아니라C공대장이별도개방context와최초참가를다시명시확인한다. RoomCycle UUID를보존하고 generation을증가,새Round세대/새실제참가구간을만든다. 기존취소Assignment/예약/원ACK는역사로보존한다. 이는명시재개라06시UUID승계와다르다. 이미열린N의noop은취소회차재개가아니다. 구현전 `cancelled 재개허용/당주재개불가` 중선택을요청한다.

한도는사용자요구의현재유지관계고유room10개를유지한다. C참가/관리관계가남으면N탈퇴로한도차감0이다. 다른T관계가없어도persistentmembership을자동종료했다고가정하지않는다. **추천: 모든T의실제관계/관리책임·미결신청이없을때별도명시 '방관계종료'로1개회복**,현재/과거결과와이력보존. N취소확인창에서C가있는데전역탈퇴까지실행하면안된다. 최종관계종료조건과T취소에연속확인을붙일지는제품결정대기이며검토schema에미승인자동정리를추가하지않는다.

## 6. 공통 자원 권한 — 영향과 결정안

주차별리더에서전역변경권한은자동으로도출되지않는다. 기존Room의globalleader를N위임으로덮으면C보존을위반하므로금지한다. 기존공통자료는보존하되새v2공통쓰기정책이확정되기전에는명령을공개하지않는다.

| 자원 | 권고안 G1 | 영향·대안 |
|---|---|---|
| 제목·공개범위 | 실제현재C공대장;C회차자체가없고열린N만있으면N공대장 | 권한있는변경도C/N공통. context에다른T의모집노출/그룹권한영향을표시 |
| 연결그룹 | 기존불변정책유지 | 새그룹변경기능은이번에추가하지않음 |
| 방전체해산 | 초기에는기존안전한전체마지막1인조건만유지,여러실제T참가자가있으면거절 | N마지막1인탈퇴는방전체해산아님.다중리더합의해산을임의추가하지않음 |
| 전역관계종료 | 본인관계종료,자신이책임진열린T는승계/닫기먼저 | 다른회원/C관계까지암묵삭제금지 |

G1은C우선관리+N자리독립을단순하게유지하는**제안**이다. C가존재하지만공대장review/회차종료인경우N에권한이자동확장되지않고관리복구/명시위임이필요하다는한계가있다. 대안G2는C/N공대장전원명시동의로공통변경(동의/만료·충돌계약추가),G3는기존전역공통관리자를분리보존(별도관리권승계·고아관계정책추가). 최종G1/G2/G3선택없이양쪽공대장에게임의권한을부여하지않는다.

## 7. ON/OFF·이후 자동 개방 — 확정/미정 표

| 상황 | 확정된효과 | 미정/보류 |
|---|---|---|
| C공대장명시N활성화 | N개방+본인실제참가/공대장원자확정,외부/기존인원기존자격검사 | 없음(새정확한wire소비대조필요) |
| 열린N공대장본인탈퇴 | N자동승계/다른인원·모집유지,C무변경 | 마지막1인후재개·관계종료세부는L1검토 |
| 옵션OFF | 공대장탈퇴나열린N일괄삭제/철회수단이아님 | 이미열린N의탭/검색은유지추천,기존C특례도이미열린T에유지추천;최종범위소비/제품확인 |
| ON상태로06시전환 | 이미있는N이같은T/UUID/리더/예약으로C가됨 | 그직후새N을매주자동개방할지는별도미정 |
| 기존auto_open_enabled | 과거값/이력보존,구worker의지연일괄admit를새정책으로재사용금지 | 의미/기본값/이행일을별도확정;값true만으로새동의추정금지 |

추천A1은초기에는명시개방만제공하고자동매주개방은미정기능으로노출하지않는안이다. 새N자동개방을채택할경우단순worker추가로끝나지않는다. 그주책임자실제참가를누가어떤사전동의로보장할지,캐릭터/한도·자격실패시미개방·blocked처리,승계후예약동의범위,실행효력시각/중복개방을추가확정해야한다. 빈N을만들거나현재인원을일괄자동가입시키는것으로대체하지않는다. 정책확정전에는기존설정의뜻을조용히변경해배포하지않는다.

## 8. 전체74번째 보완 — 소스·충돌·예약·자리DTO

| 소스C상태 | N기존인원특례 | 유지조건/진입차이 |
|---|---|---|
| 실제참가중 | 가능 | 현재소유·T자리/자격·persistent관계/소스CAS |
| C개인완료/전체완료 | 가능 | 완료구간+방/회차관계보존,전역탈퇴/추방없음 |
| C이번주미완료종료 | 가능 | 실제C참가이력+관계보존,취소/추방과명확히구분 |
| 명시C좌석취소/탈퇴/추방 | 불가 | 예전assignment나choice만으로우회불가 |
| C신청중/legacy의사만있음 | 불가 | 일반신청/직접참가사용 |
|06시이후예전C로미선택 | 예전소스특례불가 | 같은actualtarget는새C,일반admission과현재권한으로입장.원ACK먼저복구 |

마지막개인완료는단독으로persistent관계를자동삭제하지않고실제N관계도유지한다. 남길관계가없을때의명시전체정리는L1별도안이다. 소스 자격와권한은서버가매번현재유효구간으로판정하고UIboolean을권한으로사용하지않는다.

Conflict schema에 **required nullable room_title** 추가. 본인B의해당target상세조회권한이있을때만값제공,없으면room_title=null/can_view_detail=false·식별자도기존보호규칙적용. 실제B에대한새detail전수조회가없어도최소충돌안내가능하다.

참가/확인은별개: 기존확정수동일정에새참가/대체캐릭터참가시confirmation_pending,명시확인후그본인/해당session/schedule_revision예약. 공대장승계/직접위임은기존참가확인/예약을새로생성·타인으로이전하지않는다. 개방과동시에본인이새수동일정을명시작성한경우에만그확정행위의예약을검사해생성한다. 실패시개방전체rollback. '즉시참가성공=모든세션확인'이아니다.

전체detail/plan DTO에 `target_leadership {cycle_member_id,leadership_revision}`, `my_target_role(leader|member|none)`, T별actual cycle_member/참가순서·permission, `formation_slots[]`를추가한다. 각slot은target_cycle_key/round_id/party_no(1..2)/slot_no(1..4)/assignment_id(nullable)/status(empty|participating|completed|review_required),leader표시를가진다. slot row의실제Round/Assignment제약으로보장하고문자열명단순서로추정하지않는다. 4인party_no=1만,8인1..2. 자리근거없는review assignment는slot row를만들지않고unplaced배열로보낸다. 완료행은이력projection에서actual자리보존,현재빈자리와두번점유시키지않는다. 같은room내item별편성이다르면round별로별도반환한다. 배지와slot은독립.

## 9. 검토용 wire·준비상태

`docs/features/recruitment/artifacts/issue13-two-cycle.openapi.json`은2판core로보완한다. 원본openapi/openapi.yaml은불변이고전체모집API고정완료가아니다.

- 기존scope와명령의actualtarget/expected현재C를유지한다. 새 `Leadership`는T leader_cycle_member_id nullable와leadership_revision. leader필수조건은상태/권한표로서버검사한다.
- 개방context와위임context/POST를추가. 개방expected_target_revision은미존재일때명시null,새context는후보RoomCycleID/round/리더참가계획을서명해같은body로실행한다. 위임은expected_leadership_revision/candidate_cycle_member_id/expected_candidate_revision/context_token필수.
- 취소context에Leadership/후보/impact/mode 추가,취소POST에expected_leadership_revision을추가한다. 후보교체·임의전역종료를body boolean으로선택하게하지않고명시토큰에확인영향을결합한다.
- 오류:403 TARGET_LEADER_REQUIRED,409 SUCCESSOR_UNAVAILABLE/TARGET_CONTEXT_STALE/TARGET_CYCLE_CLOSED,닫힌T재개미승인시409 TARGET_REOPEN_NOT_AVAILABLE. 기존원ACK재생이새권한/CYCLE_CHANGED보다우선이다.
- 후보목록최대8,opening/transfer/cancel context120초/4096bytes,Idempotency-Key필수,알수없는필드/null정책엄격. source/대상/권한없으면permission=false이고민감후보명단을반환하지않는다.

검증계획(미실행): C/N상이한리더교차명령403,개방+본인bundle원자성/충돌대체·재전송noop/열린N리더보존,참가순서동률/재참가뒤순서·후보동시탈퇴/직접위임경합,승계+취소C보존/선택후보변경409,마지막N취소의C·마감통계불변,슬롯변경0/완료review자리혼입0,현재/미래반복소스·06시원ACK/UUID승계,수동확인과예약분리,공통권한위조·v1글로벌우회거절.

다음Flutter는74번째질문의해소여부와주차별권한/취소·위임·자리DTO소비를대조하고,사용자결정이필요한 **L1(마지막1인재개/관계한도정리),G1~G3(공통권한),A1(명시개방우선/자동개방미정유지),OFF뒤열린N특례범위**를구분해회신하면된다.확정75번째정책을재질문하지않는다. Backend는대조결과반영→전체DTO/원본OpenAPI·이행고정→W1~W5구현이며이번은실회원시험요청이아니다.

검토 명세 검증: 11개 경로/39개 schema JSON 파싱·내부참조·JSON Schema2020-12 메타검증·operation ID 중복0 확인. 정식 OpenAPI validator·실행계약 비교/기능·DB·성능시험은 미실행이다. 이번 확장에는 미정 L1을 채택 전 실행하지 않는 TARGET_POLICY_NOT_READY permission guard를 명시했다.
