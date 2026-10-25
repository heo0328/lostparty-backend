# 베타 모집 계약 제안1 — 일정·표시와 신청 메모

2026-10-25 / `feat/raid-recruitment` / 작업 파트: **베타 계약 대조·제안 인계**.
원요청: [Issue13 전체146 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6388828653)·[전체147 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6393242839). [수신/차이 기록](beta-contract-intake.md)을 잇는다. **사용자 제품결정 수용을 반영한 Backend 제안이며 Flutter wire 소비합의·구현/실제 반영 완료가 아니다.** 현재 실행 OpenAPI177/DB0031·source87c2a0e/이미지366e868a를 바꾸지 않는다.

공식 인계: [Issue13 전체148번째 Backend · 계약 제안1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6393622793). 다음 담당은 Flutter 소비 대조이며 새 구현/서버 반영은 미완료다.

## 1. 사용자 확정과 제안의 경계

사용자는 토의1/2/4를 채택한 뒤 지연 사례를 설명받고3도 채택했다.

1. 실제 참가 시 기본시간을 약속예약으로 점유한다. 자기방 조기탐색은 그 자기예약을 제외하고 조기확정 시 원자 교체한다. 타방 자동조율은 이를 피하되 직접제안/본인 중복수락 허용은 유지한다.
2. 자동조율 기본OFF. 미확정·마감 전 공대장만ON/OFF하며 ON의 즉시 앞당김 가능성을 확인한다. 이미확정한시각은 토글로 되돌리지 않는다.
3. 기한처리가 늦었어도 기본출발 전이면 원기본시간으로 확정한다. 기본출발까지 지난 미확정 건만 일정 확인 필요로 처리한다. 이미정상확정한 일정을 서버재시작만으로 재분류하지 않고 실제게임출발/완료를 자동 판정하지 않는다.
4. 모집번호는 전역증가·중복/재사용금지·결번허용이다. 매주1리셋이 아니며 원명령 성공 재송은 추가발급하지 않는다.

API필드명/프로필·아래 상세 데이터/오류/제한은 Backend 기술 제안이다. 추가인원4인1~3/8인1~7·기존동의분모·C/N·IF-001은 이미정한 기준을 유지한다. 저장문구/메모는147의 별도 소유/권한을 지킨다.

## 2. 호환성과 공통 규칙

- 관련 **기존 경로**에 query `contract_profile=beta-recruitment-1`을 명시할 때만 새 입력/응답 DTO를 사용한다. 생략은 기존입력/응답·reader_profile·token·digest 경로 그대로다. 알수없는 프로필/중복query/GET body/미정의키는400 INVALID_REQUEST. 현재 서버는 이 프로필을 아직 지원하지 않는다.
- 기존 `reader_profile=membership-actions-1/application-display-1` 및 include_session_display와 병용 가능하게 닫힌 새 DTO를 별도로 구성한다. 기존 closed schema에 allOf로 키를 얹거나 기본응답에 새 nullable 키를 추가하지 않는다. 공개 검색에는 참가자용 값/메모를 결합하지 않는다.
- 신규 profile을 적용한 실제 요청은 operation/path/query profile/실제T/body/Idempotency-Key를 함께 영속 복구한다. 원래 프로필 없는 pending에 앱이 새 query/필드/null을 주입하지 않는다. 신규 digest에는 profile과 필드 존재 여부/원입력을 포함하며 문자열 정규화 결과가 같아도 다른 원본문은 같은 key로 재사용하지 않는다. 기존 namespace와 기존 payload의 digest를 변경하지 않는다.
- 원성공ACK를 새CAS·시각·기한으로 재실행하지 않는다. 기존24h 원ACK·동일body/key 재송·멱등충돌/만료/진행중을 보존한다. 새 명령도 최신 인증/권한을 확인한다. 새 metadata 때문에 기존 쓰기ACK shape를 확대하지 않는다. ACK 뒤 조회실패는 원명령 재실행 사유가 아니다.
- 기존 기본 DTO·구 명령을 보존한다. 다만 beta로 생성된 대상에 낡은 클라이언트가 일정/가입 등 새 약속을 모른 채 새 쓰기를 하는 것은 원ACK 재생 후409 CLIENT_UPGRADE_REQUIRED로 차단한다. 정상 탈퇴/완료/추방·해산 등 안전한 기존명령은 새 예약 정리 helper를 재사용해 보존한다. 외부계약 합의 후 차단 operation 목록과 자동회귀를 실행 OpenAPI에 고정한다.
- 기존 방/자료를 자동 변환·삭제하지 않는다. 새profile 조회에서 기존방의 `beta_schedule=null`을 명시한다. 그 방을 새 베타 생성/조율 방식으로 조용히 추정하지 않고 새 일정 명령은409 BETA_SCHEDULE_REQUIRED. 기존조회/관리·ACK는 보존한다. 개발자료 migration을 협의의 선행조건으로 삼지 않는다.
- 모든 응답 no-store, 기존error envelope/code/request_id·401 Bearer·REQUEST_IN_PROGRESS Retry-After2를 유지한다. 시각UTC전송(KST표시/주차 의미),5분tick·점검·생성하한·진행시간/난이도기본값·주차끝 경계를 재사용한다. 새GET도DB/provider 쓰기를 하지 않는다.

## 3. 파트A — 기본약속·조율·기한

### 3.1 생성과 읽기

기존 `GET /v2/me/raid-room-creation-context`의 새profile query에 다음을 추가 제안한다.

| query | 규칙 |
|---|---|
| base_starts_at | 선택target의 필수UTC시각 |
| early_coordination_enabled | 필수boolean, 화면 기본false |
| early_additional_members | ON일 때 필수정수4인1~3/8인1~7; OFF이면생략 |
| next_base_starts_at / next_early_coordination_enabled / next_early_additional_members | 실제C+N동시생성일 때만N용값 필수/동일규칙. N단독생성에서는전송금지 |

context는 기존자격/선택과 두T의시각·duration·개인표revision·현재자기예약/중복근거를 함께 policy/token에 바인딩한다. 회원/기기에서 원정대 개인표를N회 미리PUT하지 않는다. 생성 POST `/v2/raid-rooms`는 해당profile에서 기존 `schedule_groups` 대신 필수 `beta_schedule_targets`를 받는다. 배열은 실제생성대상과1:1(최대2),중복/누락/불필요T거절이다. 각 항목은 `{target_cycle_key, base_starts_at, early_coordination_enabled, early_additional_members}`이며 OFF의 마지막값은null이다. 나머지 기존selection/items/continuation/CAS/원키는 유지한다. C설정을N으로 임의날짜이동해 복사하지 않는다.

최종commit시각에도 생성하한과 `now < base_starts_at−30분`을 만족해야 한다. 생성되는 각T에 안정적인session/group을1개 준비하고 묶음item_order·duration을 이어붙인 한 출발구간으로 둔다. 자정넘는 연속진행은 주차/점검 규칙 안에서 허용하며 다일별도출발은 생성하지 않는다.

새profile의 상세·개별카드·plan·schedule-context와 생성/가입/continuation/opening context에는 `data.beta_schedule`, 검색/내참가/내신청 목록에는 각item.beta_schedule을 제공한다. 없는legacy대상은null이다. field의 원본은 같은target/generation의 저장 모델이며 리스트/상세가 서로 다른 출발을 추정하지 않는다.

`BetaScheduleView`의 필수필드:

- policy_version=`beta-schedule-1`, revision,session_id,base_starts_at/base_ends_at,base_deadline_at.
- early_coordination_enabled,early_additional_members(integer|null),coordination_state,coordination_active.
- confirmed_starts_at/confirmed_ends_at(nullable),effective_starts_at/effective_ends_at,admission_deadline.
- deadline_status=`not_due|due_unprocessed|processed|obsolete`,pending_transition=`base_confirmation_due|departure_review_due|null`,review_reason=`departure_passed_unconfirmed|null`,evaluated_at.

상태는 `base_committed`(OFF)/`coordinating`(ON)/`early_confirmed`/`base_confirmed`/`proposal_confirmed`/`deadline_pending`/`needs_review`/`ended`다. **OFF라도 기본시각은 필수·약속예약도 유효하며 ‘출발미정’이 아니다.** 확정 전 두상태는기한까지ON전환이가능하다는의미다. confirmed가null이면 effective는base,있으면실제확정값이다. base는원약속이력으로보존하고명시제안으로확정시간을바꿔도몰래덮어쓰지않는다. 목록/검색은effective를사용한다.

GET에서기한이됐지만worker처리가아직없으면 persisted상태를가짜확정으로만들지않는다. 공개상태 deadline_pending + due_unprocessed/pending_transition으로 기한 처리 필요를 표시하고, coordination_active는 false이며 신규가입 권한은 닫는다. deadline_pending은 읽기 시점에 계산하는 처리 대기 상태이며 확정 효과를 실행한 상태가 아니다. 조회가확정/예약을실행하지않는다.

### 3.2 개인표·기본예약과 참가 경계

생성/직접가입/승인/기존멤버N실제참가의 명령트랜잭션에 자격→현재개인표복사→약속예약→필요조율→명령결과저장을 묶는다. 표/예약저장실패면 참가도rollback한다. 무후보 자체는기본약속의가입을실패시키지않는다. pending신청은표복사·약속예약·인원수에포함하지않는다.

개인표는 `unset`(미저장 또는 정상빈표)/`configured`(정상일부구간)로복사하고source_personal_version/copied_at을저장한다. unset은자동조율에서모든시간가능이나다른예약·점검·기간은여전히검사한다. 실패/권한불가/불량저장값을unset으로바꾸지않는다. 실패는기존503또는409자료오류이며자동빈표작성없다. 다른참가자에게는기존권한있는그래프범위에서만이상태를제공한다.

기존 `PUT /v2/me/raid-rooms/{room_id}/availability-submission`은 target/CAS/키를유지해명시최신복사에사용한다. 기본/실제약속과현재개인표다름은경고근거이며확정시간을자동이동하지않는다. 새profile의조회/graph에는기존submission필드와 `availability_copy={state,source_personal_version,copied_at}`를추가한다. 이미unset으로복사한CM과아직복사되지않은legacy누락을동일하게취급하지않는다.

기본약속예약은 기존TimeReservation/익명busy 투영을 재사용하는 내부kind=`promise`로 저장하고 일반확정은kind=`confirmed`로구분하는안이다. 기존확정동의/가입자격·주간점유를대체하거나가짜참가확인성공을만들지않는다. 양쪽이같은구간을중복점유하지않게기존활성reservation제약/자원잠금을사용한다. 자기탐색에서정확히같은T/generation/해당session의자기promise만빼고타방예약은남긴다. 조기/제안확정은관련참가자의promise해제와새예약/동의근거를한트랜잭션에반영한다.

신청에는사용자가본기본약속revision을정책snapshot으로보존하지만예약하지않는다. 승인시저장신청의동의근거와현재약속이맞는지검사한다. 신청후명시제안으로시각이바뀐경우공대장승인을신청자의새시각동의로위조하지않고기존confirmation_pending/본인참가확인경로를유지한다. 최신시각에대한동의없이는강제확정예약을만들지않는다. 직접가입자는최신context의약속을인지하고요청하는기존행동을동의근거로저장하며별도추가화면/표PUT을강제하지않는다.

### 3.3 ON/OFF·직접제안

기존 PUT `/v2/raid-rooms/{room_id}/schedule-groups`(실제router명은下の경로표참조)의 새profile은 기존 expected_cycle_key/target_cycle_key/expected_target_revision/expected_plan_revision/expected_members_revision/expected_leadership_revision을 유지하고 groups 대신 `early_coordination_enabled,early_additional_members,accept_immediate_confirmation`으로 조율설정을변경하는닫힌입력을제안한다. 공대장/미확정/기한전만허용,ON은accept_immediate_confirmation=true가필수다. OFF는false·additional=null. ON단일명령에서현재제출표/실제인원으로즉시평가하고,성공ACK후GET로상태를확인한다. 같은값ON재송/원ACK는평가를재실행하지않는다. 이미확정은409 SCHEDULE_PROPOSAL_REQUIRED,기한후는기존 RECRUITMENT_CLOSED다.

직접제안/응답은 기존schedule-proposals 경로와기존대상참가자분모·투표/revision·예약원자교체를재사용한다. beta의base_committed/coordinating도기본약속을제안의비교기준으로삼아명시제안할수있도록별도guard를확장한다(기존confirmed전용API의무조건완화가아니다). 일정밖/타예약중복은기존경고·명시수락으로허용하고표자체를수정하지않는다. 합의된새시각은proposal_confirmed이며원기한은obsolete가된다.

### 3.4 조기·기한·지연의 서버 책임

- 자동조율은현재실제참가자전원·추가인원조건을사용한다. 시작범위는ceil5분(max(now,기존생성floor,선택T점검끝)) 이상, base_starts_at **미만**이다. 진행끝이주차밖이면제외한다. 같은주차의이전날짜도탐색하며기본요일에만묶지않는다. 후보전체구간이부분표에포함되고타예약과겹치지않아야한다.
- 최초임계인원합류명령은이전열림권한으로원자합류·즉시확정될수있다. 그명령만기존최초임계예외를보존하며새실제시각의마감이열린것으로확대하지않는다. 다음신규증가는실제확정출발−30분에막는다. pending승인에도같은최종검사를적용하고실패pending은유지한다.
- 기본기한에미확정이면개인표공통후보/인원미달로기본약속을취소하지않고현재실제참가자로base_confirmed한다. 리더1명도동일하다. 약속예약을확정예약으로바꾸며이미확정은재이동하지않는다.
- 기존worker의영속target처리·자원잠금과재시도수명을재사용하고대상별기한index/버전fence로중복확정·중복예약을막는다. 새외부scheduler/Redis는필요하지않다. 타이머발화와무관하게관련새명령의DB시각guard로정각이후가입/승인을막는다.
- due 정합처리는독립적인서버시계효과다. 사용자명령실패트랜잭션에섞어확정까지rollback시키거나실패한가입이성공한것처럼기록하지않는다. worker또는인증된쓰기진입에서동일정합helper를별도트랜잭션으로처리한후사용자명령을최신상태로검사한다. 각사용자명령은기한직전경합시finalstamp도재검사한다. GET은대신실행하지않는다.
- 기준토18:00/기한17:30:17:30정각처리는base확정,17:40지연복구도18:00유지.18:00이후까지미확정이면needs_review/고정사유로전환하며actual시각은null이다. 모집은원기한에닫히고원약속·참가·기록은보존한다. 이미early/base/proposal확정인건은서버재시작으로needs_review가되지않는다.
- needs_review의기존리더는현재참가/주차·권한을검사한기존일정제안경로로미래시각을제안할수있게beta전용복구guard를제안한다. 기존동의분모·현재참가자수락·과거시각/점검검증을유지하며종료/해산/주차종료는복구하지않는다. 새가입은복구된실제시각의기한을따르며기존회원/원ACK를새로만들지않는다. 이경로는IF-001 weekly_resume/미완료종료재개가아니다.

### 3.5 필터와 모집번호

기존 `/v2/raid-rooms/search` POST와GET adapter의새profile에 `departure_windows`(최대16개의UTC {starts_at,ends_at})와 `schedule_states`(최대9개,위8상태와legacy)를선택적으로추가한다. UI의KST날짜/시간대는날짜를명시한UTC구간으로변환한다. 구간은시작포함/끝제외·5분정렬·양수/24h이내,선택주차경계안이다. 자정범위는예를들어토22시~일02시처럼날짜가있는구간으로보내고요일만으로추정하지않는다. 빈배열/null/불량구간/중복state는400,생략만필터없음이다. 구간중첩은정렬/병합해cursor정규화한다. 시간구간끼리OR,상태끼리OR,서로와기존필터는AND다.

SQL에서effective출발·상태를필터한뒤기존정렬·자기참가제외·limit/cursor를적용한다. legacy의명시확정시각이있으면그시각의OR를사용하고미정자료에서기본시간을조작하지않는다. 상태필터legacy로명시선택가능하며생략은기존자료를숨기지않는다. 새profile만으로사용자자료를삭제/이관하지않는다. cursor는profile/정규화조건·카탈로그/디렉터리·기존권한scope에바인딩하고기존400 INVALID_REQUEST/409 CURSOR_STALE를유지한다.

모집번호는전역bigint증가/유일제약으로각새실제T에1회발급하고번호/랜덤숫자5자리문자열을target에저장한다. 롤백·실패번호는재사용하지않고결번허용,동일성공키재송은새발급없음. N→C는같은T행이므로번호도같다. 공대장/시각변경으로재발급하지않는다. 새주차개방은새T이므로새값이다.

새profile의 **해당T 개별상세/본인plan에만** `recruitment_identity={number,password}`를추가하고공개/비참가자/pending/반대T만참가/탈퇴·내보내기후에는null이다. 두키를각각공개하지않고전체객체null로통일한다. 현재T의실제participating CM·현재membership/접근권한을검사하며완료이력/일반참가카드·검색/로그/원ACK에는패스워드를추가하지않는다. 다른T의참가권한이나예전원ACK로현재조회권한을만들지않는다. number는JSON정수이고Flutter가정밀하게표시할수있도록안전정수상한9,007,199,254,740,991을계약상한으로제안한다.5자문자열은00000~99999/중복허용이다.

## 4. 파트B — 메모·계정 저장문구

### 4.1 신청 메모

`POST /v2/raid-rooms/{room_id}/applications?contract_profile=beta-recruitment-1`의기존본문에 `application_memo`(선택string|null)를제안한다. 즉시가입/생성/캐릭터변경에는허용하지않는다. 생략/null/정규화후빈문자열은메모없음으로저장한다. 기존무메모요청에는키를추가하지않고현재계약도그대로지원한다.

메모/프리셋문자열은동일 규칙: **NFC 정규화 → 금지문자/한줄 검증 → Unicode White_Space 앞뒤 trim → extended grapheme cluster 20개 이하**. CR/LF/NEL/U+2028/U+2029·TAB/기타C0/C1·양방향표시제어는거절한다. emoji ZWJ/ZWNJ/variation selector/combining mark는일괄삭제하지않는다. UAX29 Unicode17.0.0 Rev47 기준과공통벡터를제안하며Flutter사용분할버전차이는소비대조에서닫는다. 한문자열UTF-8 4096byte상한/전체요청32768byte상한은별도413 REQUEST_TOO_LARGE다. 입력초과를잘라서신청하지않는다. 길이초과는400 APPLICATION_MEMO_TOO_LONG,금지문자/형식은400 INVALID_REQUEST다.

신청트랜잭션에서정규화된문자열snapshot을Application에저장하고원요청동일성은정규화전원본문기준으로검사한다. 프리셋ID는입력으로받지않으며옛신청을프리셋현재값으로조회하지않는다. 승인/거절/철회가메모를수정하지않고제출후수정API도추가하지않는다. 다시결정/재신청은기존새명령정책이다.

새profile의신청목록(application-display-1병용가능)/단건review/본인신청/본인상세my_application에 `application_memo:string|null`을항상제공한다. legacy신청은null이다. 현재권한있는대상리더와신청자본인에게만제공하고다른참가자/공개검색/상세일반멤버에는메모key를추가하지않는다. ACK는기존최소shape,전체프리셋목록/메모본문은로그에남기지않는다.

### 4.2 저장문구 자원

재사용검토결과기존 `/v1/me/settings`는nice_group의closed전체PUT/버전이므로그자원을확대하지않고새본인자원 **GET/PUT `/v2/me/application-message-presets`**를제안한다. 별도POST/PATCH/DELETE를늘리지않고최대5개의작은목록전체PUT으로추가/수정/삭제/순서를원자처리한다. 프로필query없이도이전부터있던API처럼호출하는것이아니라향후구현후사용할신규경로다.

GET200: `{version:1,items:[],saved_at:null}`이기본값이며읽기로row를생성하지않는다. item은 `{id:UUIDv4,text:string}`이고순서가선택목록표시순서다. text는위정규화후비어있을수없다. 최대5/중복id금지;동일text자체는허용해기존문구를앱이조용히병합하지않는다. UUID는본인목록내식별자이며타회원조회경로가없다.

PUT입력 `{expected_version,items:[{id,text},...]}` + UUIDv4 Idempotency-Key. 항목추가는새UUID,수정은ID유지,삭제는목록에서제외,전체삭제는[]다. auth/current-user만DBrow를결정한다. 입력member_id·character/registration/room_id는거절한다. 최대6개는400 APPLICATION_PRESET_LIMIT_EXCEEDED. no-op은version/saved_at그대로,변경은version+1/DB저장시각,stale expected는no-op이어도409 REVISION_CONFLICT. 기기 간 공유는 동일 회원이 다른 기기에서 GET할 때 같은 저장 자료를 읽는다는 뜻이며, 실시간 push/새 polling을 추가하지 않는다. 별도 고유 operation namespace `application-message-presets-put`와기존reserve/commit/tombstone/lease를재사용한다. PUT200은GET와같은snapshot,원키/원본문은24h당시원응답을재생하고최신목록은GET한다.

기기A/B가같은version을읽고동시수정하면한쪽만성공한다. 실패측은현재입력을보존하고최신목록을조회해사용자가결정한새명령/key로저장한다. 자동덮어쓰기/자동병합은없다. 프리셋조회/저장실패는신청입력값/무메모지원을차단하거나자동재신청시키지않는다. 최대5개/20자라는제품상한은재질문하지않는다.

## 5. 경로·권한·오류와 자료 계약

실제 재사용 경로는 현행 cycle_router 기준으로 대조한다. 주요 경로:

- 생성context/POST raid-rooms,admission-context/POST join/applications/approve,continuation-context/continuation-participations,opening-context/recruitment-openings:profile과새약속/개인표/예약을결합.
- GET raid-rooms/{room_id}/detail,GET me/raid-rooms/{room_id}/plan,GET me/raid-rooms/{room_id}/schedule-context,GET/PUT me/raid-rooms/{room_id}/availability-submission,GET/POST search·내목록:위읽기/수동복사계약을적용.
- 일정설정/제안/응답:현행 schedule-groups·schedule-proposals·responses operation과 CAS/원ACK를재사용하며`POST /v2/raid-rooms/{room_id}/schedule-proposals`와 `POST /v2/raid-schedule-proposals/{proposal_id}/responses`를 사용한다.
- 메모는신청POST와신청조회만,프리셋은새본인GET/PUT만이다. 구API를합치거나삭제하지않는다.

기존오류는실행계약을유지:400 INVALID_REQUEST,401 ACCESS_INVALID,403대상권한오류,404해당자원없음,409 REVISION_CONFLICT/TARGET_CONTEXT_STALE/SELECTION_CONTEXT_CHANGED/CYCLE_CHANGED/RECRUITMENT_CLOSED/SCHEDULE_PROPOSAL_REQUIRED/멱등계열,413 REQUEST_TOO_LARGE,503 SERVICE_UNAVAILABLE. 새프로필별세부입력/토큰검증은기존오류를먼저재사용한다.

추가제안코드는409 BETA_SCHEDULE_REQUIRED(기존방새방식쓰기불가),409 SCHEDULE_REVIEW_REQUIRED(지연미확정의일반일정명령불가/복구제안사용),400 APPLICATION_MEMO_TOO_LONG,400 APPLICATION_PRESET_LIMIT_EXCEEDED다. 승인자격실패는기존reason/pending유지를보존한다. 메모문자수·프리셋version을전역모집revision과섞지않는다.

닫힌신규component와대표예시는 [schema](proposals/beta-recruitment-v1.schema.json)·[예시/기대사례](proposals/beta-recruitment-v1.examples.json)를따른다. 이는**제안의신규component**이며기존전체쓰기/읽기DTO의실행OpenAPI가아니다. 전체합성원본문예시는기존필수selection/CAS/ACKshape에각operation별새profile의명시차이만합성한다. 새optional/null이원pending에주입되지않는검증을반드시포함한다.


새 profile의 기존 명령별 입력 차이는 다음과 같다. 표에 없는 기존 필수 입력은 현재 실행 계약에서 그대로 상속한다.

| operation | 새 profile의 입력 차이 |
|---|---|
| POST `/v2/raid-rooms` | schedule_groups 제거, beta_schedule_targets 필수. 실제 생성 C/N과 1:1 |
| GET opening-context | 새 T를 여는 intent에서 base_starts_at/early_coordination_enabled/(ON 시)early_additional_members를 query에 추가 |
| POST recruitment-openings | 새 T 개방에서 beta_schedule(config) 필수. 기존 context_token/selection/target_items/target_session_ids/intent·CAS 유지. 이미 열린 T의 확인/관리에는 새 생성 config를 주입하지 않음 |
| POST join/continuation-participations | 기존 body 필드 유지. profile context에 보인 현재 약속·개인표 revision을 바인딩하고 실제 참가/복사/예약 원자 처리 |
| POST applications | application_memo 선택 추가. 기본약속 revision은 기존 selection_context 토큰에 바인딩. 표/예약 생성 없음 |
| POST approve | 기존 body/CAS 유지. 저장 신청과 현재 약속·신청자 동의/참가확인 경계를 검증하고 표복사는 서버에서 처리 |
| PUT schedule-groups | 기존 CAS 유지, groups 제거, 조율 ON/OFF·추가인원·즉시효과 수락3필드 필수 |
| POST schedule-proposals/responses | 기존 body와 동의분모 유지. profile token/revision 및 beta 미확정/needs_review 전용 guard를 적용 |
| PUT availability-submission | 기존 body/CAS 유지. unset 복사도 정상상태로 처리하고 새 read metadata 제공 |

현재 가입자가 복사하게 될 개인표 revision은 새 context 정책 snapshot에 포함한다. context 뒤 개인표가 바뀌었다면 기존 SELECTION_CONTEXT_CHANGED/REVISION_CONFLICT로 최신 context를 다시 받으며 과거 개인표를 복사하지 않는다. 승인 시에는 신청 당시 표가 아닌 승인 명령이 읽은 신청자의 최신 저장 표를 원자 복사한다. 신청자가 표를 바꾼 것을 승인자의 오래된 권한/CAS로 덮어쓰지 않는다.

## 6. 정적 대조와 앞으로의 검증

작성한 신규 component/상속 요청은47종이며 JSON/상태시각 정적48사례(정상21·거절27)를 확인했다. grapheme 벡터6개와 HTTP 기대사례9개는 앞으로 구현에서 실행할 명세이며 이번 정적 통과 수에 넣지 않는다.

현재실행한것은제안문/경로·닫힌schema/작성JSON예시와상태시각/숫자경계의정적검증뿐이다. 아래는구현후격리PostgreSQL/FastAPI로확인할완료조건이며지금통과한기능시험이아니다.

1. 목생성/토18기본/추가2명/금20공통→금20확정. 후보없음기본유지.리더단독/인원미달토17:30→토18확정.이미금확정이면토기한이동없음.
2. 자기promise만제외·타방promise/busy회피,부분표/전체unset/조회실패구별.실제가입/표복사/약속예약한쪽실패모두rollback, pending부작용0.표갱신으로확정시각이동0.
3. 기한정각/최종commit경합·중복worker·기존원ACK,첫임계합류예외·뒤신규증가차단,동시승인/탈퇴·리더변경·C/N/종료/해산/주차경계격리.조회가due효과를실행하지않음.
4. 17:40복구토18확정/18:20미확정복구needs_review,이미확정서버재시작상태보존·새시각자동생성/게임완료0·기존미래제안권한/동의후복구.
5. 번호동시발급·성공재송불변·결번/재사용금지·C/N/N→C·5자리선행0. public/pending/반대T/퇴장후/로그/ACK누출0.
6. 날짜·자정·상태필터/정렬후페이지관계·cursor위조/조건변경/stale, legacy표시와기존검색제외보존.
7. 무메모/20자/21자·가족emoji/조합한글/trim/줄바꿈·제어문자/ZWJ·byte상한,0~5/6개/id중복/타회원·공개누출·기기간CAS·프리셋바뀐뒤옛신청/원본문불변·ACK후GET실패로재신청없음.

다음Flutter는profile합성/원pending·권한별표시/조율OFF의기본약속·ON즉시효과/지연review복구표시·문자분할공통 버전/예시·전체목록PUT에구체소비차이가있는지회신한다. 기존정상시험반복/인원·동의기준재수용은요청하지않는다. 회신을반영해실행wire를닫은후구현한다. 이번제안은서버교체·DBmigration/초기화·자료삭제·실회원/기기시험·AWS배포승인이아니다.
