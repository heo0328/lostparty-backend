> **현재 구현 기준(2026-10-21):** [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 잔여 충돌 없이 소비 검토를 마감했다. 계약0.4.1/policy4를 고정하며 [W1~W5 작업계획](ISSUE_13_TWO_CYCLE_WORK_PLAN.md)을 따른다. 아래 검토대기/후속질문·구판 단계표는 당시 기록이다. 실제 기능/실행API·DB 인수는 별도 미완료다.

> **최신 보완:** [계약 후보4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)이 전체80번째의 제목/전역CAS/생성checkbox/숙련도검색 수정을 반영한다. 아래3판까지의 생성후추가활성화/제목schema·global target CAS 가정은 최신계약이 아니다. 이 문서는 당시 기록으로 보존한다.

# Issue #13 두 주차 전체 계약 3판

2026-10-21 / Backend / feat/raid-recruitment / 기준 구현 cc003e9, 문서 시작 HEAD6490f69.

**확정 정책을 반영한 전체 계약 후보**다. 제품정책은 확정됐지만 새 DTO에 대한 Flutter 최종 소비 대조·기능 구현·실행 계약 대조/DB 이행·실서버 준비는 각각 별도다. 문서·명세·명세 생성 도구만 미커밋/미push이며 기존 사용자 변경을 보존한다. `openapi/openapi.yaml`은 현재 실행 구현의 원본으로 그대로 유지한다. 미구현 v2를 실행 API처럼 원본에 올려 자동 계약 검증을 무너뜨리지 않는다. 소비 대조 후 구현 단계에서 이 후보의 해당 부분을 원본에 반영하고 FastAPI 전체 대조한다.

기준: Flutter [전체77번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6307642641), [전체78번째 정책확정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6307975683). 1/2판에서 정책미정으로 표시한 L1핵심/G1/A1·OFF 범위를 아래로 대체한다. 이미 확정한 정책을 재질문하지 않는다.

## 1. 반영 완료 정책·제외 범위

- L1핵심: 마지막 N 참가자 탈퇴는 N만 cancelled. pending 신청·해당 세대 일정/제안/점유/예약만 정리한다. C 공대장/참가/완료/예약과 Room.ended_at은 보존한다. `future_empty_cancelled` 원인은 실제주간 미완료종료와 다르다.
- 재개는 C 공대장이 별도 intent=reopen context에서 본인 참가까지 명시한다. RoomCycle UUID는 그대로, generation+1/새 Round 세대·새 실제참가 구간. 예전 인원/예약/동의 자동복원0. 조회·일반신청·ON재전송은 재개가 아니다.
- G1: 제목/공개범위는 실제 C 공대장. C 회차 자체가 없고 열린 N만 있으면 N 공대장. C가 있지만 리더 review/탈퇴 등 관리불가이면 N 자동승격 없음. 연결그룹 불변·그룹 자격 유지. 전역해산은 기존 안전한 전체마지막1인 조건과 다른T실제참가자 없음 모두 필요.
- A1: 명시 개방만.06시 기존 N→C는 같은UUID/리더/assignment/예약으로 승계하며 새N 자동생성/가입 없음. old auto_open_enabled=true를 동의로 쓰지 않는다. OFF로 열린N 철회/기존C 참가특례차단하는 추가명령 없음.
- N좌석취소는 persistent 관계를 자동삭제/한도회복하지 않는다. 새 '방관계종료' 진입점·연속확인 UX는 추가하지 않는다. 기존 전역 leave/end의 명시 영향/안전조건은 아래대로 분리한다. #19 사전취소 통계정책은 여전히 별도다.

## 2. 전체 명세·재현·준비 상태

- 전체 파일: `docs/design/issue13-two-cycle.full.openapi.json` — **53경로/56operation/196schema**, 독립적으로 내부 참조를 해석할 수 있는 OpenAPI3.1 문서다. 모집 전체/수동완료 v2 계약 후보이며 앱 인증/계정 bootstrap/개인표 등 불변 API를 중복 정의하지 않는다.
- `docs/design/issue13-two-cycle.openapi.json`은 전체73·76번째의 core2 입력 스냅샷(11경로39schema)으로 보존한다. 더는 최신 전체 계약으로 취급하지 않는다.
- `docs/design/build_issue13_two_cycle_contract.py`는 cc003e9 원본과 core2를 읽어 전체 파일을 결정적으로 생성한다. 입력 canonical SHA-256을 검사하고 실행 코드/DB/원본 OpenAPI를 수정하지 않는다. 로컬 full 명세가 원격 파일로 공개된 상태는 아니므로 Issue에는 본문과 **재현 도구 전문**을 제공한다. 두 입력은 원격 cc003e9의 원본과 전체73 core+76 delta 병합본이다.
- 이 생성기는 기존 계약의 상세형을 재사용하면서 target/권한/역할/입출력 타입을 명시적으로 바꾼 설계 도구다. v2 런타임 adapter 구현이 아니며 prefix만 바꿔 기존 서버에 호출하면 동작한다는 뜻이 아니다.
- 전체 후보에서 `B_`는 재사용한 기존 DTO 이름공간이고 wire의 접두사가 아니다. 보존된 client 분석 build 등 기존 opaque payload는 신규 서버 권한/시간/정렬 데이터로 해석하지 않는다.

## 3. 전체 wrapper·필드명·revision 출처 고정

단일 target 응답은 **`{scope,data}`**. scope는 `server_now,current_cycle_key,target_cycle_key,playable_from,phase,target_revision,room_cycle_id,target_generation,policy_version="two-cycle-contract-3"` 모두 필수다. 단일 방의 미개시 context와 방에 귀속되지 않는 수동완료, 여러 방을 합친 페이지/겹침 조회에서는 target_revision/room_cycle_id/target_generation을 명시null로 반환한다. 단일 방의 이미 존재하는 T 조회·쓰기에서는 실제 저장값이다. 페이지의 개별 Card/Projection에는 room_cycle_id/target_generation/target_revision을 각 행에 제공하며, 본인목록에서 회차가 없는 persistent 관계만 남은 행은 명시null이다. 오류는 별도 `{error:{code,message,request_id,details,...}}`이며 성공 wrapper를 씌우지 않는다.

복수 주차 예외는 GET /v2/raid-cycles와 POST /v2/me/raid-weekly-summary이며 각 실제 cycle 키를 직접 포함한다. 그룹 필터 context는 target과 무관한 권한 snapshot을 그대로 재사용한다.

**공대장 필드는 항상 `data.leadership`**: `leader_cycle_member_id,leader_membership_id,leadership_revision`. detail/plan/settings/card/입장 context/위임·취소·개방 context 모두 같은 schema다. `target_leadership` 별칭과 v1 global room_role은 v2에서 사용하지 않는다. 표시용 `my_target_role=leader|member|none`, 회원행의 `target_role`은 그 T에서 계산한다.

| revision/ID | 권위·사용 |
|---|---|
| room_revision | 공통 Room 제목/공개범위/전역 상태; N전용변경으로 C보존용 CAS를 무의미하게 증가시키지 않음 |
| scope.target_revision / expected_target_revision | RoomCycle 해당T의 모든 원자명령 epoch. 다른T만 변경되면 그대로 |
| settings/members/plan revision | 해당 RoomCycle의 설정/실제참가·자리/계획. 전역 persistent 멤버 수 아님 |
| leadership.leadership_revision | 해당T 책임자/CAS. 위임/승계 시 증가 |
| membership_id/revision | 기존 방 persistent 관계. 조회/한도·전역leave용이며 target권한과 구별 |
| cycle_member_id/cycle_member_revision | 해당T 실제참가관계/명령권한. expected_cycle_member_revision으로 전송 |
| assignment/round/session/proposal/weekly revisions | 해당실제자원의 기존 CAS. path ID→T/room/generation 일치 검증 |

편성 placement는 `cycle_member_id,expected_cycle_member_revision,item_id,party_no,slot_no`. target 추방은 `target_cycle_member_id,expected_removed_cycle_member_revision`이고 C/N 전체관계를 삭제하지 않는다. 같은 이름 expected_target_revision에 '삭제 대상 회원revision'과 'RoomCycle revision'을 섞지 않는다. v1의 expected_membership_revision을 v2 target 명령에 그대로 보내지 않는다.

## 4. 참가 순번 — JSON 정밀도 고정

DB next_join_order/joined_order는 signed bigint, wire는 **양의 십진 문자열**이다. 범위 **"1".."9223372036854775807"**, 선행0/부호/소수/지수/JSON number/null 금지. schema에는 상한까지 제한하는 pattern을 넣었다. Dart/web에서 문자열 원문을 보존하고 정렬이 필요하면 BigInt로 비교한다. 문자열 사전순/JS Number 변환 금지. 예: `"9007199254740993"`은 정확히 유지한다.

순서=(generation,joined_order,cycle_member_id). 실제 전체bundle 참가성공만 번호를 받으며 재참가는 새순번. 순번이 슬롯번호가 아니다. DB상한 도달은409 JOIN_ORDER_EXHAUSTED로 원자 무변경,0으로 순환/기존번호 재사용 금지. source C 순번을 N에 복사하지 않는다.

## 5. opening prospective ID/revision — 클라이언트 추정 금지

GET opening-context에는 필수 **intent=open|reopen**. 서버는 read-only 조회 중 후보 UUID를 만들어 AEAD token에 actor/C리더·source cycle member·선택·N현재존재/세대/revision·catalog/그룹/한도·주간원장 snapshot과 결합한다. GET은 자원 생성·예약·자리 선점이 아니다. 같은context의원키/본문을결과불명시에그대로쓴다. 새context는다른후보UUID일수있으며기존성공을변경하지않는다.

| 값 | 처음개방(open, N미존재) | 재개(reopen, cancelled N r/g) |
|---|---|---|
| scope.room_cycle_id/target_revision/target_generation | null/null/null | 기존K/r/g |
| data.prospective_room_cycle_id | 서버발급K | 같은K |
| prospective_generation | 1 | g+1 |
| prospective_target_revision | 1(최초 commit epoch) | r+1(이 명령의 commit epoch) |
| targets[].round_id | 서버가발급·token결합한새UUID | 취소Round와다른새UUID |
| targets[].expected_round_revision | 초기새Round=1,서버명시 | 새세대Round=1,서버명시 |
| targets[].expected_weekly_revision | 선택회원/캐릭터·raid·**N**의 실제원장revision,미존재시1 | 재개시새snapshot의실제revision(취소후보통증가),고정1아님 |
| POST expected_target_revision | scope값 **null** | scope값 **r**(prospective r+1아님) |

POST에는 서버응답의 selection/targets→target_items/target_session_ids를 그대로 복사하고 intent와 원token을 전달한다. prospective_room_cycle_id/generation/prospective_target_revision은 표시/대조용이며 새 client입력으로 중복 제출하지 않는다. 의미를 추정해 round revision을 +1 하거나 미존재 원장을 미리 만들지 않는다.

**성공 예시(합성)**: C=2026-10-21,N=2026-10-28, N미존재. context가후보K/새R,round1/weekly7,scope.expected=null을발급하면POST는expected_target_revision=null과R/1/7을전송한다. 성공201이아닌opening200 ACK의target revision1과실제R/assignment를조회한다. 생성자first order="1"이다. HTTP201은새room 생성에만사용한다.

**거절 예시**: 다른개방이N을먼저만들었거나weekly7→8/C리더/소유/그룹권한이바뀌면409 TARGET_CONTEXT_STALE/REVISION_CONFLICT·새N쓰기는0. client가round revision2로바꾸거나T/후보ID를위조하면400 TARGET_SCOPE_MISMATCH 또는409 context불일치. 다른B의N점유는409 TARGET_CHARACTER_CONFLICT, B불변/A생성0. 이미열린N에서새open context를받으면already_open/noop이며기존N리더를덮지않는다.

**재개 예시**: 취소N의K/g1/r4에서reopen context는같은K/g2/예정r5·새R2/round1/현재weekly9를반환한다.POSTexpected_target_revision=4,R2/1/9.성공후K/g2/r5,옛R1·취소구간·예약이력보존,옛참가자복원0.다른재개가선행하면stale/무변경.일반open으로cancelled N을재개하면409 TARGET_REOPEN_REQUIRED.06시를넘으면새명령은CYCLE_CHANGED/재확인,원성공ACK는먼저복구한다.

개방POST는RoomCycle revision을해당명령당정확히한번전진시킨다. 내부헬퍼가각각increment해서prospective숫자와달라지게하지않는다. 새Round초기1과target epoch는별개다. token생존은120초와C종료경계중짧은값,최대4096bytes이며압축/배치상한은구현시검증한다.

## 6. 전체 경로·기존 API 이행

전체 JSON이필수/nullable/default/배열·scalar constraint와정확한schema를정의하고,아래는경로변경·권한의설명이다. GET target query는필수이고검색/쓰기의actualtarget는body필수다. 서버 actual C 기대인expected_cycle_key는그대로. path의application/round/session/group/proposal가실제T를소유하는지검증한다.

- /v2/raid-cycles, /v2/me/raid-weekly-summary: C/N메타·50캐릭터×2target×현재카탈로그5raid=최대500entry. 본인캐릭터만,권한없는항목이섞이면전체403. 최소주간원장/실제참가i/완료/permission만제공하며Armory/bootstrap재전수조회없음.
- 생성context/POST raid-rooms: T명시,C/N일반신규방생성·본인최초참가. v2생성의`continuation.enabled`는false만허용한다. **C방생성ACK이후명시N활성화**는opening-context→openingPOST로구분한다. 기존v1생성checkbox의자동미래효과를그대로v2에가정하지않는다. 이화면흐름/입력차이는Flutter소비대조대상이며N개방+본인참가의원자성은유지한다. N신규방생성으로C+14를암묵생성하지않는다.
- 검색/목록·카드/summary·detail/plan·그룹projection: T의유효세대/실제인원·캐릭터/자리/조건만. target SQL→가시권한/필터→remaining_slot_counts→member_count및기존동률정렬→page. defaultdescending·정확한자리OR를유지한다. v2 app_member_count는active assignment lease를보유한고유cycle member(review점유포함),완료·legacychoice·persistent만남은사람은자리로세지않는다.
- 본인membership/application/관리신청목록·입장context·join/apply/approve/reject/withdraw: actualT/generation원자CAS. pending은좌석아님. application상태accepted를사용하며잘못된approved별칭은v2에없다. 승인/관리자는T리더만.
- 개인표원본은v1그대로,방제출표는T별명시복사. GETsubmission도cycle_member_id/revision을함께제공하여현재sourceCAS를추정하지않게한다. 개인표저장이C/N방제출표를자동변경하지않는다.
- schedule-context/groups/candidates/selections/proposals/responses·session confirmations·현재주resume·완료context/개인/공대장완료/미완료종료·수동완료: T의ID/세대/계획·권한·120초context와최종DB시각을검증한다. 투표분모/N1·명시확인/중복경고는기존규칙을유지하며N재개와현재주미완료resume는다른명령이다.
- 명시 opening/continuation-participations/declines/cancellation·leadership-transfers: 전체76정책을정확한schema로유지하되L1개방·재개조건을활성화했다. **v2 continuation-settings PUT, choices PUT, OFF차단/철회, global transfer-leadership는없다.** legacy choices는읽기만. T위임은새leadership-transfers,전역권한은G1로구분한다.
- T settings/formation/character-changes/removals: T만. character-change의구futurechoices동시수정입력을제거한다. target추방으로다른T를종료하지않는다. 공통title/visibility는G1 common-context+common-settings로대체하며group_id변경은허용하지않는다.
- 기존 leave/end 진입점을v2에보존하되common-context에모든C/N영향을결합한다. N탭탈퇴에는participation-cancellations를사용하고전역leave로우회하지않는다. 별도'방관계종료'신규API/연속확인UI는이번에추가하지않는다.

### v2 전역 leave/end의 최소조건

leave는명시전체persistent관계정리다. 어떤열린T에서든본인이책임자면그T위임/대상탈퇴를먼저해결해야하고,보통참가자이면context가명시한전체T assignment/예약을정리한다. 이미N취소뒤T관계가모두없고책임도없으면기존leave로persistent관계를종료해1room한도를회복할수있다. 자동실행/과거자료삭제없음. 다른T가있을때N취소와전역leave를연속으로자동호출하지않는다.

end는G1권한+기존전체persistent관계마지막1인+다른T실제참가자없음 모두필요하다. N한주만마지막1인인상황에서C의다른실제참가자가있으면전역end거절이다. 허용된전역end도과거완료를지우지않고미래정리원인은future cancel로구분한다. G1관리자없음/보존자료review면조회·복구만제공하고N공대장으로무단확장하지않는다.

## 7. 상태·명령 권한·편성

| 상태/명령 | actor/조건 | 효과·거절 |
|---|---|---|
| N미개방→open / cancelled→reopen | 실제C리더/소스·전체bundle자격 | 명시본인참가·N리더;실패원자무변경 |
| N기존인원참가/대체캐릭터 | 유효C실참가구간/탈퇴추방없음 | 승인생략+전체 조건검사,B보존 |
| N취소·자동승계 | T본인관계,리더면최초유효후보재확인 | T만해제,후보변경409,마지막이면Ncancelled |
| 직접T위임 | T현재리더/명시실제후보·CAS | actor남음,자리/예약/C무변경 |
| T 설정/승인/편성/일정관리 | T리더·open·기존자격/마감 | C리더로N명령403및역방향도거절 |
| 완료/수동체크·정정·취소/이번주미완료종료 | T=C AND now≥수10시+기존개별권한 | 미래/06~10거절,다른T보존 |
| 본인마지막완료 | 실제대상본인/동일10시조건 | 완료원천만,자동N가입/전역탈퇴없음 |
| C완료/미완료종료후관계보존 | 실제참가구간,회원/소유·권한유효 | N소스특례유지;명시C취소/추방/전역탈퇴는불가 |
| completed관리권 | T관계completed·미탈퇴/미추방·현자격유효 | 읽기/해당T위임·G1조건부공통권한유지,끝난raid를추가완료/입장시키지는못함 |
| review관리권 | 소유/회원/한도등사유노출 | permissionfalse,조회·자격복구/명시취소가능범위제시,임의외부승계없음 |

cycle_member상태는participating/completed/stopped/cancelled/removed/review_required로구분한다. 주간미완료종료의stopped는명시취소가아니므로유효소스이력과persistent관계를보존한다. 승계후보는참가중/완료/주간stopped실제관계중현재자격이유효하고탈퇴추방되지않은사람만,review/신청/의사선택제외다. 후보상태·원장/소유근거는실행시재검사하며완료·stopped관리범위는실제명령시험에포함한다.

formation_slots는현재세대각Round의자리(4인party1/slot1..4,8인party1..2/slot1..4). joined_order/회원응답순서를자리로쓰지않는다. 개인완료로풀린자리는empty이고완료의원래자리는formation_history에기록한다. 동일Round/party/slot현재점유중복0. review지만증명된실점유는자리를유지,근거없는행은unplaced_assignments에만보낸다. 공대장배지는leadership과assignment소유자로판정하고위임때슬롯교환0이다.

참가성공/승계/위임은기존모든확정세션의본인일정동의가아니다. 기존수동확정일정에나중참가하면confirmation_pending,명시session확인후그schedule_revision의본인예약만생성. 본인이개방과함께새시각을명시작성한경우의기존확정행위만그시각예약을생성한다. 재개는이전동의/예약을복원하지않는다.

## 8. 오류·캐시·재시도

400 INVALID_REQUEST/TARGET_CYCLE_OUT_OF_RANGE/TARGET_SCOPE_MISMATCH,401/403기존인증·권한,403 TARGET_LEADER_REQUIRED/SOURCE_PARTICIPATION_REQUIRED,404존재숨김,409 TARGET_CHARACTER_CONFLICT/TARGET_CONTEXT_STALE/REVISION_CONFLICT/CYCLE_CHANGED/COMMAND_CONTEXT_EXPIRED/SUCCESSOR_UNAVAILABLE/TARGET_REOPEN_REQUIRED/TARGET_CYCLE_CLOSED/JOIN_ORDER_EXHAUSTED,완료409 TARGET_CYCLE_NOT_CURRENT/PLAY_NOT_STARTED,커서409 CURSOR_STALE/FILTER_CONTEXT_STALE를사용한다. 자리·구성/소유·그룹·한도/카탈로그등기존오류도유지한다.

details는conflicts최대bundle수및available_at(nullable)로정의한다. Conflict.room_title은권한있을때만값,없으면null/식별자도보호.그룹필터context/캐시는권한범위동일하면공유하며search cursor는회원session+actualT+generation+정규화조건/target목록revision·그룹권한세대를결합한다.06시라벨이바뀌어도actualT는안바뀌지만oldcursor는명시stale로처리한다.

모든성공/오류no-store. 원키·원본문결과불명재전송은동일회원/operationversion/T의원ACK먼저복구,새주차자격으로성공명령을다시실행하지않는다.원ACK는새현재회원/소유자의자료를조회해재구성하지않고원래필요최소결과만반환한다.다른T/본문같은키는409 IDEMPOTENCY_CONFLICT.409 REQUEST_IN_PROGRESS는Retry-After2초,429/503은retry정보에따른동일명령재시도만.확정충돌은자동새키·B탈퇴·target+7보정없음.

기존v1은현재주읽기adapter·안전한쓰기만유지하고,N관계에잘못된전역효과를내는구keep/release/globalleader명령은409 CLIENT_UPGRADE_REQUIRED. 원성공ACK는예외적으로먼저복구한다. v1수동완료에도확정10시guard를동일적용해야하며인계시소비차이를명시한다.

## 9. 저장 이행·검증·구현 준비

이행DDL의핵심: RoomCycle유일(room,T)·generation/리더복합FK,cycle_member유일(cycle,persistent)·순번/generation/유효구간,CAS·readiness,Round현재활성세대partialunique·cancelled구분,Application.target/generation과pending유일(room,user,T),T별제출표,Proposal/Session의명시T·generation,assignment/주간점유/예약의일치FK,참가/취소/재참가이벤트원천.

**개방원천제약도수정필요**: 기존OpeningEvent유일(room,item,T,mode)/applied partialunique는한T재개를막는다. 기존행/시각을보존하면서generation을추가해유일(room,item,T,generation,mode)와applied유일 제약(room,item,T,generation)로전환한다. old manual/scheduled_auto자료는증명된세대로만backfill,새명시open/reopen은generation별저장한다. oldauto원천을새동의로전용하지않는다.

N마지막취소때RoomCycle/해당세대Round·이벤트cancelled,weekly lease/예약/제안·신청만T로범위제한.재개는같은RoomCycle/새generation·Round/새 참가구간,이전 assignment재활성화로세대이력을덮지않는다.같은 세대취소후일반재참가는기존Assignment유일제약을유지하면서재활성화/새joined_order·이벤트를기록한다.완료assignment는재참가로부활불가.

기존자료증명없는설정/소스/세대는review+provenanceunknown,과거0건가정/임의현재키·미래복제없음. shadow/backfill검증뒤제약강화·v1safeadapter/새 worker동시전환,autoenrolment이전 경로 중지.06시cleanup은target/generation기준,created_at이이전 C라는이유로N제안을폐기하지않는다.

기능·DB·성능검증은미실행. 구현시기존계획대로W1저장/원장/10시guard→W2메타summary/생성·target조회/일반입장→W3개방/특례/취소/위임→W4일정·완료·전역/06시→W5보존/성능/전체실행계약·게시.독립된구현준비는가능하지만미완성multi-cycle경로를실서버에공개하지않는다. SQL수/rows/bytes/p50·p95/EXPLAIN은동일합성데이터로구버전과측정하고예상ms/비용0을보장하지않는다.

이번문서검증은JSON/ref/메타·경로/쿼리/타입/예시·재현동일성이다.실제FastAPI전체대조/자동HTTP·DB경합/실회원·기기시험과구분한다. 다음Flutter는정책채택여부가아니라전체DTO(생성활성화분리/순번string/개방예정값/리더필드/권한)의소비차이를검토하고Backend는충돌보완후구현계약을고정한다.

검색의 directory_revision은 T별 목록 head에서 제공한다. 기존 전역 DirectoryHead는 v1/공통 변경용으로 보존하고 새 cycle_directory_heads(T,revision)를 추가하는 이행안이다. T 가입/취소는 해당 head만, 제목·공개범위 등 공통 변경은 영향받는 C/N head를 갱신한다. 그룹 권한세대는 필터 context에서 별도 결합한다. 읽기에서 head 행을 생성하지 않고 미존재 초기값1을 사용한다. 새 저장안은 이 target 목록 head를 포함해 구체 DDL 단계에서 기존 인덱스/원천과 대조한다.

plan의 permissions는 edit_schedule_groups/cancel_target_participation/transfer_leadership/open_next_cycle/reopen_next_cycle/view_common_context/leave_global/end_global로 고정했다. N탈퇴를 옛 leave permission으로 전역 탈퇴시키지 않도록 명령 이름을 분리한다. 입장 context의 permissions에는 요청 intent(join/apply/change_character) 한 키만 반환한다.

private plan/제출표/schedule-context와 투표·확인 명령은 해당T 실제관계/권한을 검사한다. 방 persistent 관계나 C리더라는 이유만으로 미참가 N의 개인 제출표/익명 busy·투표권을 얻지 않는다. 일반 detail은 기존 방 가시권한·안전한 멤버 projection 범위로 제공하고 미참가자는 my_target_role=none·view_plan=false다. source C 회원의 N참가 준비는 전용 context가 제공하며 광범위한 private plan 권한으로 대체하지 않는다.

실행한 설계 검증: 196schema 메타/전체ref 해석, 56operation의 path·query·멱등헤더/ID검사, 합성schema사례16개 통과. 원격73+76본문에서 core2를 재구성해 로컬입력과 paths/schema가 동일함을 확인했다. 전체후보 canonical SHA-256(JSON sort_keys/ensure_ascii=False/compact UTF-8)은 `a8c9d2c8e1fbe816113ec9d61bdd39dc99210e83de4401abb28ebfefa1f27020`다. 정식 OpenAPI validator는 환경에 없어 미실행이며 FastAPI/DB/기능/성능 인수 통과로 해석하지 않는다.
