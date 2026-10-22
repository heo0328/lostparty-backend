# Issue #13 — 사전 참가 세션 표시 메타 계약 초안1

2026-10-22 / Backend / feat/raid-recruitment. [Flutter107 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6343179198)·[Backend108 확인](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6343260776)에 대응한다. **구현 전 소비 검토안**이며 현재 API168경로/DB29·0afd879 실행 계약/기본0.4.1/policy4/canonical SHA는 변경하지 않는다. 검토용 [닫힌 JSON Schema·추가 위치·합성 예시](design/issue13-prejoin-session-display.draft.json)는 실행 OpenAPI를 대체하지 않는다.

## 1. 기존 context에 명시적으로 요청하는 표시 정보

새 endpoint 대신 다음 세 GET에 optional query `include_session_display=true|false`를 추가 제안한다. 생략/default=false이며 명시null/빈값/다른문자열·중복 query는400이다.

| 기존 GET | 적용 동작 |
|---|---|
| `/v2/raid-rooms/{room_id}/admission-context` | intent=join/apply/change_character |
| `/v2/raid-rooms/{room_id}/continuation-context` | action=join/decline |
| `/v2/raid-rooms/{room_id}/opening-context` | intent=open/reopen, opening_effect별 처리 |

`true`일 때만 기존 응답 `data.session_display`를 추가한다. **생략/false 응답에는 새 필드가 없고, 명시null도 반환하지 않는다.** 기존 닫힌 DTO 소비·미결 요청/기존 token 계산을 보존하기 위한 선택이다. 기술적 opt-in이며 사용자에게 별도 설정/조회 단계를 추가하는 것은 아니다. Flutter는 새 계약/SHA 실제 인계 뒤에만 flag와 DTO를 함께 적용한다. 화면에서 표시 정보를 요청했으나 응답 필드가 없으면 계약 불일치이며 기존 C 시각/배열 순서 추정으로 대체하지 않는다.

기존 path/query의 room/실제T/character/role/action/intent 의미와 인증·방/그룹 가시권한·C 실제참가/공대장·본인소유 검사는 유지한다. private plan 권한을 완화하지 않는다. 참가 전 조회자가 이미 볼 권한이 있는 방의 선택 대상 일정만 제공하며 개인 제출표·익명 busy/다른 방·다른 회원 동의/예약 내역·이전 세대 이력을 반환하지 않는다. 한 snapshot의 READ ONLY이며 provider 호출/자료 생성/개방·동의·예약·정족수 계산 명령이 아니다.

## 2. 공통 객체 SessionDisplay

전 필드는 필수다. 정확한 wire 타입은 별도 JSON Schema를 따른다.

| 필드 | 타입·의미 |
|---|---|
| kind | existing / opening_preview / none |
| selection_mode | select_session_ids / opening_implicit_enrolment / no_session_selection |
| target_cycle_key | 기존 요청의 실제T, canonical KST 수요일 YYYY-MM-DD |
| room_cycle_id | UUID. existing/none은 실제 대상 cycle, opening_preview는 기존 opening의 prospective_room_cycle_id |
| target_generation | 양의int. existing/none은 실제 대상 generation, opening_preview는 prospective_generation |
| plan_revision | existing/none은 현재 대상 plan revision 양의int, opening_preview는null(미생성/새세대 계획에 가짜1/구세대값을 넣지 않음) |
| display_revision | 64hex 서버 표시 snapshot digest. DB 증가 revision/새 쓰기 CAS/권한 token이 아님 |
| sessions | ActualSessionDisplay[] 최대64. actual 선택 가능 session 메타 |
| previews | OpeningSchedulePreviewGroup[]. 아직 session ID가 없는 개방 일정 의도 |

### kind/selection_mode 조합

| context 결과 | kind / selection_mode | 데이터 |
|---|---|---|
| admission join/apply/change_character | existing / select_session_ids | 현재 실제T의 `session_choices`와 정확히 동일 ID집합의 sessions, previews=[] |
| continuation action=join | existing / select_session_ids | 현재 열린N의 실제 choices ID집합 sessions, previews=[] |
| continuation action=decline | none / no_session_selection | sessions=[]/previews=[], 실제 대상 scope/revision만 제공 |
| opening_effect=create_and_join/reopen_and_join | opening_preview / opening_implicit_enrolment | sessions=[], 아래 source 기반 previews |
| opening_effect=already_open | none / no_session_selection | 기존 noop이며 sessions=[]/previews=[], 해당N의 실제 scope/revision |

continuation의 기존 `target_session_ids=[]`는 유지한다. 이는 모든 선택지를 담은 목록이 아니며, 새 sessions는 선택 메타이지 자동 체크/전송할 목록이 아니다. 명시 선택은 기존 required/permission·클라이언트 확인 흐름을 따르고 POST target_session_ids 규칙은 바꾸지 않는다. 새 메타로 권한false를true로 해석하지 않는다.

source/room 접근 검사 후 context가 실행 permission=false로 반환되는 경우에도 같은 가시권한 내 표시만 제공한다. permission=false가 조회 권한을 새로 주는 것은 아니며, 접근 권한 자체가 없으면 기존404/403 등으로 전체 거절한다. none/빈배열을 권한 실패의 정상 응답으로 사용하지 않는다.

## 3. ActualSessionDisplay — 기존 세션을 ID로 직접 연결

`{session_id,revision,schedule_revision,state,required,starts_at,ends_at,join_deadline,permission}`.

- session_id UUID와 revision/schedule_revision 양의int는 실제 target CycleSession·현재 generation의 RecruitmentSession에서 읽는다. state는 기존 선택지의 unconfirmed/confirmed만 제공한다. active ScheduleHead에 연결된 해당T/세대의 세션만 포함한다. finished/cancelled/legacy_review_required·비활성 그룹·이전generation은 제외한다.
- starts_at/ends_at은 UTC RFC3339/null. 현재 저장 제약대로 **둘 다null 또는 둘 다시각이고 starts_at<ends_at**이다. confirmed는 둘 다필수, unconfirmed는 미정/null 또는 저장된 구간을 표시하되 확정 동의로 취급하지 않는다. 끝만 추정하거나 기존DB가 허용하지 않는 실제 start-only 상태를 만들지 않는다.
- required/join_deadline/permission(allowed/reason/next_change_at)은 동일 snapshot의 기존 SessionChoice와 일치해야 한다. join_deadline은 기존 confirmed 시작30분전 규칙이며 클라이언트가 날짜로 새로 계산하지 않는다. state가 미정이어도 required/참가마감의 기존 판정은 서버 원본이다.
- sessions는 session_id 정규UUID ASC. 표시시각 순서를 ID와의 대응으로 쓰지 않는다. 중복ID/누락/다른 실제T·세대/기존choices와 불일치는 소비 불일치로 처리한다. 원문 시각은 UTC로 유지하고 화면에서 KST/실제 날짜로 표시한다. C의시각으로N ID를 만들거나 주차를 추정하지 않는다.

## 4. OpeningSchedulePreviewGroup — 미생성 session을 가짜 ID로 표시하지 않음

개방 준비는 `cycle_opening.schedule_inputs`의 실제 source C 일정 의도를 선택N/새generation으로 복사하지만, **읽기에서는 대상 session을 생성하지 않는다.** 기존 install이 실제session UUID를 쓰기 중에 발급하므로 사전에 가짜 session ID/예약 revision을 만들지 않는다.

각 group은 `{preview_group_ref,source_group_revision,planning_mode,occurrence_mode,day_scope,required,alternatives}`다. refs는 서버가 prospective cycle/generation·source그룹/alternative 근거에 결합한64hex 불투명 표시키로 만들며 UI 조각 연결에만 사용한다. 원천group/alternative UUID·개인표를 새로 공개하지 않는다. source_group_revision은 source C의 실제그룹 revision이지 새N의 revision이 아니다. groups/alternatives는 각 preview_ref ASC로 반환한다.

각 alternative는 `{preview_ref,session_id,state,weekday,starts_at,ends_at,time_state,materialization}`이다.

- session_id는**항상null**, state는preview. weekday는기존1..7. 시간은UTC RFC3339/null이며 target N의 실제날짜를 사용한다. source C의 실제시작/종료를 복사하지 않고 `local_start(target_cycle_key,weekday,starts_local)` 및 새 대상 settings의 전체 item duration 합계로 계산한다. C에서 완료된 item을 다음N 전체묶음에 복구하는 현재 schedule_inputs 순서/설정도 함께 반영한다.
- time_state=bounded는 시작/끝모두존재·start<end, undetermined는둘다null, start_only는수동시각의도는있지만현재duration근거가없어끝을계산할수없을때다. start_only는**미생성 미리보기**에만 허용하며 실제session 상태로오인하지 않는다. 실행가능/입장/예약 보증이 아니고 최종현재기간·시작floor·duration/권한검사는 기존쓰기에서수행한다. duration을클라이언트가임의추가하지않는다.
- materialization=on_open: manual이면서each 또는one_of/alternative1개인 현재 생성조건. after_group_selection: manual/one_of/복수후보라서개방만으로session을생성하지않음. after_coordination: coordinated(후보/명시선택·기존조건충족후의생성). not_scheduled: unscheduled. coordinated/unscheduled는시간을임의확정하지않고undetermined/null로표시한다.
- day_scope=any_current_cycle인coordinated는alternatives=[]가정상이다. UI는그룹의주차전체·조율대기상태를표시하며가상요일/session을추가하지않는다. source에일정그룹자체가없으면previews=[]다. 빈미리보기와조회실패를혼동하지않는다.

**기존 opening 쓰기 효과를 그대로 표시한다.** target_session_ids는[]로유지하고preview_ref/session_id=null을본문에전송하지않는다. install 시 실제 생성되는session에는개방자본인의참가관계가연결되지만, copied=True이므로시간확정동의/예약을자동생성하지않는다. 아직생성되지않는manual복수후보/coordinated/unscheduled를이미참가할실제session으로체크하지않는다. 실제개방원ACK뒤현재T plan을읽을권한이생기면새실제ID를조회한다. preview_ref와실제ID를이름/정렬순서로동일시하지않는다.

## 5. 표시 snapshot과 기존 token·쓰기/원ACK

display_revision은 표시허용scope·kind/selection_mode·실제T/대상cycle/generation·plan_revision·세션ID/revision/schedule_revision/상태/시각/required/마감·preview source근거/설정·권한근거를정규화해만든digest다. evaluated_at/server_now·issued_at/expires_at 자체를넣어매조회마다인위적으로변경하지않는다. 현재실행자/flow·그룹권한/room/target CAS와함께**context token을발급하기전에**표시객체를binding에포함한다. 표시metadata와token을다른snapshot에서만들지않는다.

- flag=true의token에내부버전표지 `session_display_version=1`을seal한다. 이표지는서버내부값이며클라이언트가작성하거나POST필드로추가하지않는다. 기존token포맷/opaque처리그대로다. 쓰기는unseal한표지를기준으로동일표시근거를재계산한다. 일반admission의policy_snapshot에도결합하고character/continuation/opening의기존life.sign binding에도결합한다. 표지없음은기존계산경로로유지해flag=false/기존미결요청을불필요하게무효화하지않는다.
- 새명령은같은actor/room/실제T·generation/권한·context·CAS를재검사한다. 실제session시각/끝·상태/revision·required·선택가능목록/그룹활성·previewsource설정/기간이바뀌면기존SELECTION_CONTEXT_CHANGED/POLICY_CONTEXT_CHANGED/TARGET_CONTEXT_STALE/REVISION_CONFLICT등경로별판정으로거절한다. 삭제/세대교체/권한상실도기존판정우선순위를따르고표시만정상빈배열로숨기지않는다. 표시digest확인이날짜/마감final guard를대체하지않는다.
- 기존POST/PUT body·expected revision 출처·멱등키/원문불변·원ACK복구를바꾸지않는다. **성공원ACK재생은현재표시가변했어도기존우선순서로복구**한다. 결과불명은새표시/새token으로본문을덮어재전송하지않는다. 확정거절후에만새context/표시를취득하고변경내용을사용자에게보인뒤명시새시도한다. 새로운표시전용쓰기/outbox/동의명령은없다.
- opening_preview는metadata.room_cycle_id/target_generation이**prospective 필드**와일치해야한다. cancelled 세대의재개에서는기존scope가구generation/기존target_revision을가리킬수있으므로새preview세대를scope의구세대로덮어쓰지않는다. 실제body의expected_target_revision은기존현재값/null규칙이며preview예정값을새CAS로전송하지않는다. source C나계획이바뀌어새미리보기가필요하면기존opening token근거가변해거절되며클라이언트가새N UUID를추정하지않는다.

## 6. 계약·크기·소비 전환과 검증

신규경로/DDL/저장자료변경은제안하지않는다. 세GET에optional query와응답data의optional/non-null session_display를추가하는별도보완이다. 기본0.4.1/policy4/canonical SHA·현재168경로의원본을미합의상태에서수정하지않는다. 합의후실행OpenAPI에서세GET의query/응답schema변경과추가schema를명시한다. flag생략/false의실제응답·기존token/body/원ACK는유지한다.

응답은부분일정/첫64개만조용히잘라동의창을만들지않고, 전체선택목록·미리보기를제공한다. actual은기존64session 상한, preview는기존그룹/alternative를누락없이제공하며임의새총개수제한을정하지않는다. flag=true 전체JSON UTF-8응답은1MiB 상한을**제안**하고초과는413 RESPONSE_TOO_LARGE다. 실패시flag를빼서표시검증을우회하거나시각을추정하지않는다. 구현때큰그룹/복수일정의batch/SQL/bytes·토큰4096자/기존body제한과response상한을측정한다. 현재wire검사로DB/성능을검증했다고표시하지않는다.

| 향후 검증 사례 | 확인할 결과 |
|---|---|
| 일반join/apply·캐릭터변경/N특례의복수session | 실제ID와시작/끝·상태/revision/required/permission일치·다른T/이전세대누락 |
| 미정/기간변경·session삭제/그룹비활성·권한상실 | null/상태구분·stale/권한거절·기존원ACK우선 |
| N없음/취소후새generation/이미열린N | preview는prospective와binding·UUID실제발급없음/none noop |
| manual each/단일/복수 one_of·coordinated/unscheduled/주차전체 | 생성예정/추후선택/미정구분·가짜sessionID/자동시각동의/예약0 |
| KST수요일00~05:55·06/10시·최소미래시각 | 실제target주차귀속과기존쓰기final guard보존 |
| flag생략/false·새flag/토큰·결과불명 | 기존응답/토큰경로보존·새표시변경감지/원키불변 |
| 크기·읽기 | batch/완전목록/413구분·GET DB불변·양프로필실행계약대조 |

**다음 Flutter 소비 대조:** opt-in query/닫힌DTO·existing와opening_preview/none의구분·미생성session ID와동의/예약처리·prospective세대비교·크기제안을확인한다. 충돌이없으면Backend구현/격리검증·commit/push·개발반영/실행계약·소비SHA인계로진행한다. 기존F1~F4/후보·F5독립일정의동일시험/정책채택을반복요청하지않는다. 현재완료는보완계약작성/합성wire검사·게시이며실제API/표시동작·실회원/기기/F5전체/F6완료가아니다.
