# Issue #8 — V2 기술계약 보완안

현재 상태(2026-10-18): 아래는 합의 당시 설계 근거다. Backend 구현·격리 검증과 DB0015 반영은 [개발 안내](ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md)를 따르고, 실제 REST 계약은 `openapi/openapi.yaml`을 기준으로 한다. Flutter 적용·실기기 인수는 별도다. 제안된 자동 삭제는 미추가이며 공통 날짜 기록은 [DB 기준](DATABASE_RECORD_TIMESTAMPS.md)을 따른다.

2026-10-18. [140번째 Flutter 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237226314)에 대한 답변 원문. **142번째 Flutter 소비검토 수용·구현 준비 기준 / 미구현**, 기준구현 feat/raid-services/69d9a40. 이 문서가 [기존 설계](ISSUE_8_OWNERSHIP_DISPUTE_DESIGN.md)의 proof 복원·HTTP/DTO·방어 대상·동시 분쟁 관련 충돌 설명을 대체한다. 실행 OpenAPI는 변경하지 않는다.

공유 원문: [#8 전체141번째 Backend 계약 보완](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237543030). 설계본문과기계판독JSON을같은댓글에공유했으며새기능원격코드SHA는없다.

## 사용자 추가 확정

- 원정대당 진행 분쟁 최대 **3건**. 분쟁은 매번 시도자의 새 장비 확인 성공 후에만 성립한다.
- 기존 소유자가 새 장비 인증으로 방어에 성공하면 **같은 원정대·같은 현재 소유권을 대상으로 진행 중인 분쟁 모두** 방어 완료한다.
- 방어가 없으면 **장비 확인 성공으로 먼저 성립한 분쟁부터** 만기 처리한다. 이전이 확정되면 이전 owner를 대상으로 한 나머지는 종료한다. 그 시도자는 새 owner를 대상으로 새 장비 확인부터 다시 시작할 수 있다.
- 방어성공 후 영구금지·별도 재도전대기 없음. 앱내안내 우선·푸시 후속. 과거 수동 제재를 가져오지 않는다.

## 1. 공통 타입·현재성과 명령 응답

모든 경로는 App Bearer/no-store. 입력·출력은 아래 필드를 필수로 가지며 `?` 표기는 **필수 필드이면서 값으로 null 허용**이라는 뜻이다. 입력의 생략 허용은 별도로 명시한다. unknown field/query/중복scalar/잘못된 UUID·strict int·null은400 INVALID_REQUEST. UUID는 UUID문자열, Version은boolean/실수거부 integer>=1, Time은UTC RFC3339 Z, Name은trim후1..64자다.

V1 PreviewOut/VerificationOut/enum/confirm{}·멱등본문은 변경하지 않는다. V2 별도 DTO/명령/VM으로 소비한다. V2는 소유 성공·장비 성공·분쟁 개시를 구분하며 기존 verified 콜백으로 뭉치지 않는다.

**settle는 200 DisputeOut 한 형식으로 고정**한다. POST는 만기 확인과 작업 예약까지만 수행하고 외부조회/소유이전을 기다리지 않는다. 202/다른 queue body를 쓰지 않는다. `state=defending, phase=settlement_due|retrying_settlement`는 처리대기이며 이전완료가 아니다. 실제결과는worker와GET으로확인한다. 자동 due worker는 별도로 실행되어야 하며 버튼/GET을 해야만 자동이전하는 설계가 아니다.

변경 POST는 UUIDv4 Idempotency-Key. actor+operation+대상+정규화본문 hash, lease/generation fencing, 성공ACK24h+만료tombstone24h를재사용한다. 같은key/본문은원ACK, 다른본문409 IDEMPOTENCY_CONFLICT, 처리중409 REQUEST_IN_PROGRESS/Retry-After2. 원ACK의server_now/상태/등록참조는그당시값이며 현재권한증거가아니다. 재전송후현재GET으로동기화한다. ACK보장기간뒤같은key blind retry/새start 금지,먼저목록조회한다. 세션현재성은매요청검사하되proof를시작한기기의session ID에고정하지않고같은앱회원의정상새세션에서도복구한다.

## 2. 경로·입력·성공 응답 확정안 (11동작)

| Method/path | 입력 | 정상 status/body |
|---|---|---|
| POST `/v2/game-accounts/preview` | `{character_name:Name}`; 멱등키불필요 | 200 PreviewV2 |
| POST `/v2/me/game-account-verifications` | ClaimStartIn | 201 VerificationV2 |
| GET `/v2/me/game-account-verifications` | purpose=all/claim/defense, view=active/all, limit/cursor | 200 VerificationPage |
| GET `/v2/me/game-account-verifications/{id}` | 없음 | 200 VerificationV2 |
| POST `/v2/me/game-account-verifications/{id}/confirm` | `{expected_version:Version}` | 200 VerificationV2 |
| POST `/v2/me/game-account-verifications/{id}/cancel` | `{expected_version:Version}` | 200 VerificationV2 |
| GET `/v2/me/ownership-disputes` | role=all/challenger/owner, view=active/all, limit/cursor | 200 DisputePage |
| GET `/v2/me/ownership-disputes/{id}` | 없음 | 200 DisputeOut |
| POST `/v2/me/ownership-disputes/{id}/cancel` | `{expected_version:Version}` | 200 DisputeOut |
| POST `/v2/me/ownership-disputes/{id}/defenses` | DefenseStartIn | 201 VerificationV2 |
| POST `/v2/me/ownership-disputes/{id}/settle` | `{expected_version:Version}` | 200 DisputeOut(예약 ACK) |

ClaimStartIn은 아래 두 형태만 허용한다. V1의 생략/null 호환을 V2에 암묵적으로 가져오지 않는다:

```json
{"source":"direct_input","character_name":"ExampleHero"}
```
```json
{"source":"registration","registration_id":"00000000-0000-4000-8000-000000000001","expected_registration_version":1,"target_character":{"server_name":"예시서버","character_name":"ExampleHero"}}
```

등록 source는 필수 target/version을 저장된 현재 등록 전체목록·현재소유/claim에 exact 대조한다. direct_input에는 다른형태의필드/explicit null을넣지않는다. 서버가 API 원문 이름을 유일하게 해석하며 cache/digest의 원입력은보존한다.

DefenseStartIn (모든 필드 필수):
```json
{"expected_dispute_version":1,"selection":{"registration_id":"00000000-0000-4000-8000-000000000001","character_id":"00000000-0000-4000-8000-000000000002","expected_registration_version":1,"expected_ownership_revision":1,"expected_roster_revision":1,"expected_lifecycle_revision":1}}
```

defense의 parent dispute_id는 path이고 일반 시작 body로 purpose/타인 actor/account를 지정할수없다. `{expected_version}`은 proof 확인/취소 또는 분쟁취소/settle 각각의 version이다. 방어 시작만 expected_dispute_version과선택version들을구분한다.

## 3. DTO 전체 필드

### PreviewV2

`{preview:PreviewOut, ownership_context:OwnershipContext, server_now:Time}`. preview는 기존3필드 characters/server_fetched_at/expires_at이며 characters는기존Summary 6필드(server_name,character_name,class_name,character_level,item_level?,combat_power?)를따른다. character_level은strict integer,두수치는nullable십진문자열이다. 소유미인증 preview combat_power는항상null이다. UUID/활동/설정/다른회원정보없음.

OwnershipContext: `{relation:self|other|unverified|unresolved, notice_code:OTHER_OWNER_VERIFIED?, observed_at:Time, can_start_claim:bool, blocked_reason:ContextBlock?}`.

ContextBlock = ALREADY_VERIFIED / IDENTITY_UNRESOLVED / DISPUTE_ALREADY_ACTIVE / DISPUTE_CAPACITY_REACHED. can_start_claim=true면blocked_reason=null, false면위이유중1개. self는ALREADY_VERIFIED, unresolved는IDENTITY_UNRESOLVED, other의정상사용은notice_code=OTHER_OWNER_VERIFIED다. 다른relation의notice_code=null. can_start_claim은현재관계/분쟁자리기준의안내이며키/quota/최종권한을보장하지않는다. 캐시된preview관찰시각과현재DB소유판정시각을혼동하지않고시작/성공때다시검사한다.

### VerificationV2

| 필드 | 타입/의미 |
|---|---|
| verification_id / version | UUID / Version |
| purpose / source | claim 또는 defense / direct_input 또는 registration 또는 dispute_defense |
| source_registration_id | UUID?; 본인입력등록참조. direct에서는null |
| equipment_status | pending / passed / expired / cancelled / invalidated |
| ownership_outcome | none / verified / dispute_opened / defended / blocked |
| ownership_context | OwnershipContext; 현재안내용, 저장성공ACK는당시값 |
| target | `{server_name:Name,character_name:Name}`; 이proof의API원문대상 |
| required_slots | 무기/투구/어깨/상의/하의/장갑중서로다른1..3개 |
| created_at / equipment_expires_at / server_now | Time; 방어proof만끝시각이공통방어가능기한으로단축될수있음 |
| ended_at | Time?; pending만null |
| result_code | ProofResult?; 아래표 |
| dispute_id | UUID?; 방어는parent ID, claim은dispute_opened때만생성ID |
| registration_id | UUID?; 본인source/result의이력참조,삭제후404일수있으며현재권한증거아님 |
| allowed_actions | 중복없는배열: confirm / cancel / view_dispute / open_registration |

purpose=defense이면source=dispute_defense이고source_registration_id/registration_id/dispute_id가non-null. claim direct는source_registration_id=null; claim registration은non-null이다. 다른회원의등록ID나target canonical UUID는노출하지않는다. required_slots/target/기준snapshot은proof마다고정하며진행중다른캐릭터로변경하지않는다.

| equipment_status / ownership_outcome | result_code / 연결값 |
|---|---|
| pending / none | 처음null,비교불일치 REQUIRED_EQUIPMENT_PRESENT 또는 NON_REQUIRED_EQUIPMENT_CHANGED,근거불충분 PROVIDER_EVIDENCE_PENDING 또는 ROSTER_EVIDENCE_PENDING |
| passed / verified | VERIFIED; registration_id non-null,dispute_id=null (신규미점유원정대소유성공) |
| passed / dispute_opened | DISPUTE_OPENED; dispute_id non-null,등록참조는아래8절 |
| passed / defended | OWNER_DEFENDED; parent dispute_id non-null,시도자소유성공콜백실행0 |
| passed / blocked | DISPUTE_CAPACITY_REACHED 또는 DISPUTE_ALREADY_ACTIVE; 새dispute_id=null,소유변경0 |
| invalidated / blocked | REVISION_CONFLICT / IDENTITY_CONFLICT / LOSTARK_KEY_CHANGED / PARENT_DISPUTE_ENDED / DEFENSE_WINDOW_CLOSED; 분쟁개시0 |
| expired / none | VERIFICATION_EXPIRED |
| cancelled / none | VERIFICATION_CANCELLED |

ProofResult는이표의문자열만사용하는폐쇄enum으로제안한다. provider통신/키오류는아래HTTP오류로반환하고거짓passed/소멸을저장하지않는다. 기한지난pending의GET은expired/none/VERIFICATION_EXPIRED·ended_at=equipment_expires_at으로논리투영한다. GET은저장/버전증가/외부호출0,confirm은기한확정시원자적으로종료하고버전증가한다.

pending이고현재scope/키version/기한이유효하면confirm,cancel; 키/대상변화로성공불가면cancel만. expired/cancelled/invalidated는해당두명령불가. dispute_id가본인참여분쟁이면view_dispute,verified이고등록이현재본인소유/활성이면open_registration을추가한다. 다른경우빈배열가능. passed는10분이지나도expired로강등하지않고참조분쟁의현재결과를따로조회한다. 성공반영/종료마다version증가,GET시각/쿼터단순소비는version변경없음.

### DisputeOut

| 필드 | 타입/의미 |
|---|---|
| dispute_id / version | UUID / Version |
| viewer_role | challenger / owner; 시작당사자기준이며현재owner권한과별개 |
| state | defending / defended / transferred / cancelled / invalidated / review_required |
| phase | awaiting_defense / settlement_due / retrying_settlement / finished / review_required |
| target | `{server_name:Name,character_name:Name}`; 시작당시시도자표시용,방어대상필수조건아님 |
| started_at / defense_deadline / server_now | Time;각분쟁장비성공시각/그뒤24h/현재서버시각 |
| defense_available_until | Time?;같은owner/revision의열린분쟁중가장빠른기한,원정대기준방어불가/종료면null(viewer_role과별개) |
| resolved_at / reason_code / next_retry_at | Time? / DisputeReason? / Time? |
| my_registration_id | UUID?;현재viewer본인의살아있는등록만,없거나삭제됐으면null |
| my_active_verification_ids | UUID배열;본인pending/기한유효proof만,없으면[] |
| allowed_actions | 중복없는배열: cancel_dispute / start_defense / view_my_verifications / request_settlement / open_registration |

DisputeReason = OWNER_DEFENDED / OWNERSHIP_TRANSFERRED / CHALLENGER_CANCELLED / OWNER_CHANGED / TARGET_CHANGED / PARTY_IMPACT_REVIEW_REQUIRED / REGISTRATION_REMOVED / REGISTRATION_CONFLICT / REGISTRATION_LIMIT / UPSTREAM_UNAVAILABLE / LOSTARK_KEY_NOT_CONFIGURED / LOSTARK_KEY_REJECTED / WAITING_FOR_EARLIER_DISPUTE / MEMBER_UNAVAILABLE.

- state=defending은resolved_at=null. now<자신의deadline이면awaiting_defense, 기한후마지막장애와next_retry_at이있으면retrying_settlement, 나머지는settlement_due다. review_required는같은이름phase/resolved_at=null/이유필수/자동worker대상제외다. 나머지4상태는finished/resolved_at·이유필수/next_retry_at=null이다.
- 정상 defending 이유는null. 만기후provider/키/등록한도등회복가능실패는위이유·next_retry_at을반환한다. owner교체는invalidated/OWNER_CHANGED,다른분쟁승자로이전돼도동일하다. target/등록참조충돌·현재파티영향은review_required와해당이유로보류하며근거없는이전을하지않는다.
- challenger는defending의자기deadline전또는review_required에서cancel_dispute. owner는현재owner/base revision이유지되고공통방어가능기한전이면start_defense. 적격등록이없는경우기존동일회원재등록흐름으로복구후선택할수있으며권한없이방어시작하지않는다.
- view_my_verifications는my_active_verification_ids가있을때만. owner조회는같은account/owner revision의진행방어proof들을발견할수있고, challenger조회는해당분쟁의자기proof만보며다른도전자의proof를보지못한다.
- 양측모두defending/자기deadline이후면request_settlement 가능. 먼저성립한분쟁이있으면그순서를유지하는작업만예약하고현재분쟁에는WAITING_FOR_EARLIER_DISPUTE를표시한다. terminal은요청불가지만동일key의원명령ACK는복구한다.
- open_registration은my_registration_id가있고현재viewer의소유사용권이유효할때만. 이전owner의ownership_lost등록ID를조회할수있어도새사용권으로바꾸지않는다. 모든행동배열은현재안내이며최종명령재검사필수다.

### 목록 envelope

VerificationPage / DisputePage 모두 `{items:[각 DTO], next_cursor:string?, feed_revision:Version, server_now:Time}`. 다른최상위필드없음. 기본purpose/role=all,view=active,limit20/최대100,cursor생략가능/길이<=2048,명시빈cursor/unknown query/중복입력400이다. proof는created_at DESC,id DESC,분쟁은started_at DESC,id DESC. items=[]/next_cursor=null은정상빈결과다.

proof active는논리pending/기한유효행이며passed분쟁의진행은DisputePage로복구한다. proof all은terminal도포함한다. dispute active는defending/review_required, all은종료도포함한다. actor별별도proof/dispute feed_revision을생성·종료·외부상태변경시증가시키고workerlease/GET만으로증가시키지않는다. cursor는actor/필터/limit/feed revision/정렬에HMAC서명한다. 분당시간경과로active구성이바뀌는경계는cursor내논리valid_until로검사해409 CURSOR_STALE를반환한다. feed_revision만같다고기한경계를넘어목록이불변이라고보장하지않는다.

proof metadata는종료후90일제안,진행분쟁이참조하는metadata는분쟁종료후90일까지최소유지한다. baseline/수집장비는기존종료후24시간정리경계를유지하고분쟁감사에는최소digest/시각/권한근거만남긴다. 만료/GC로404이면새소유성공/증거로추측하지않는다. 세부운영보관은별도다.

## 4. 응답 예시

다음값은실사용데이터가아닌고정예시다.

```json
{"preview":{"characters":[{"server_name":"예시서버","character_name":"ExampleHero","class_name":"예시직업","character_level":60,"item_level":"1700.00","combat_power":null}],"server_fetched_at":"2026-10-18T01:00:00Z","expires_at":"2026-10-18T01:30:00Z"},"ownership_context":{"relation":"other","notice_code":"OTHER_OWNER_VERIFIED","observed_at":"2026-10-18T01:00:00Z","can_start_claim":true,"blocked_reason":null},"server_now":"2026-10-18T01:00:00Z"}
```
```json
{"verification_id":"00000000-0000-4000-8000-000000000010","version":2,"purpose":"claim","source":"direct_input","source_registration_id":null,"equipment_status":"passed","ownership_outcome":"dispute_opened","ownership_context":{"relation":"other","notice_code":"OTHER_OWNER_VERIFIED","observed_at":"2026-10-18T01:02:00Z","can_start_claim":false,"blocked_reason":"DISPUTE_ALREADY_ACTIVE"},"target":{"server_name":"예시서버","character_name":"ExampleHero"},"required_slots":["장갑"],"created_at":"2026-10-18T01:00:00Z","equipment_expires_at":"2026-10-18T01:10:00Z","server_now":"2026-10-18T01:02:00Z","ended_at":"2026-10-18T01:02:00Z","result_code":"DISPUTE_OPENED","dispute_id":"00000000-0000-4000-8000-000000000020","registration_id":null,"allowed_actions":["view_dispute"]}
```
```json
{"dispute_id":"00000000-0000-4000-8000-000000000020","version":1,"viewer_role":"challenger","state":"defending","phase":"awaiting_defense","target":{"server_name":"예시서버","character_name":"ExampleHero"},"started_at":"2026-10-18T01:02:00Z","defense_deadline":"2026-10-19T01:02:00Z","server_now":"2026-10-18T01:02:00Z","defense_available_until":"2026-10-19T01:02:00Z","resolved_at":null,"reason_code":null,"next_retry_at":null,"my_registration_id":null,"my_active_verification_ids":[],"allowed_actions":["cancel_dispute"]}
```
```json
{"items":[],"next_cursor":null,"feed_revision":1,"server_now":"2026-10-18T01:00:00Z"}
```

## 5. proof ID가 없는 새 기기·응답 유실 복구

- 로그인/앱복귀때회원별proof active목록과분쟁active목록을서로독립조회한다. 장비상세/자동갱신완료를기다릴필요없다. 현재로그인회원/환경세대가바뀌면그결과를폐기한다.
- start응답이유실됐고기기journal에원key/body가있으면같은명령으로201원ACK복구. proof ID만없거나원key를모르는새기기는GET proof목록으로발견해기존ID로확인/취소한다. 목록을가져오기전에새start를자동생성하지않는다.
- 같은원key 재전송은새proof가아니다. 다른key start는별도새proof이며기존쿼터/중복검사를받는다. 복수행이있으면purpose/target/시각으로명시선택하며‘최근한개가반드시이기기명령’이라고추측하지않는다. 시작transaction진행중목록이비었다고즉시새명령을발급하지않고원key재전송또는목록재조회한다.
- 방어는DisputeOut.my_active_verification_ids또는purpose=defense목록에서복원한다. 타기기에서도같은회원의유효한현재세션이면가능하다. 키version교체/대상revision변화로옛proof가불가해졌다면현재GET/확인결과를따르고기한전새방어proof를시작한다.
- proofpassed/dispute_opened원ACK는최종이전결과가아니다. 분쟁GET/feed변화뒤roster/settings/lifecycle/profile/weekly/group대표를다시읽어ownershiprevision으로늦은작업을격리한다. 자동이전은기존장비verified콜백없이도발견해야한다.
- 앱내안내/로그인·복귀GET은범위에포함한다. 30초상시polling은후보기술안일뿐이계약회신으로실행을확정하지않는다. 가시화면의갱신주기는Flutter UI구현구간에서결정한다.

## 6. 방어 캐릭터 선택 수정

**고정target만방어가능하던135번째제한은철회한다.** 기존소유자가해당원정대의다른유효한본인캐릭터를명시선택할수있도록한다. 기존본인canonical캐릭터목록/등록GET을재사용해선택하고DefenseStartIn으로ID와현재revision을전달한다. 활동선택/대표/1700/표시대상조건은추가하지않는다.

서버는parent분쟁당사자/current owner/base ownership revision·selection등록의현재소유/동일account·캐릭터active/confirmed/현재claim·선택기대한4revision을검사한다. 같은원정대가아니거나타인/퇴역/불명확하면거절한다. 삭제등록을되살리지않고현재동일회원재등록경로로새등록을복구한뒤선택한다.

그뒤fresh siblings/Armory가선택된UUID의현재exact서버/원문이름과claim/같은account anchor에맞는지검사하고선택캐릭터기준새6부위baseline/무작위해제/10분proof를발급한다. 방어proof는그선택대상과자체roster digest를고정한다. 분쟁을시작한시도자의대상/roster와방어자의대상/roster가문자열로같아야할이유는없다. 두proof는같은canonical account/owner revision에귀속되어야한다.

소멸한원래캐릭터때문에owner인증을자동해제하지않고, 다른이름에기존UUID를자동승계하지도않는다. 다른유효캐릭터방어가성공하면원래시도대상의누락을시도자승리로바꾸지않는다. 방어할수없고원래target의최종동일성도불명확하면review_required이며무조건이전하지않는다.

## 7. 최대3건·일괄 방어·만기 순서의 원자 처리

- account당defending/review_required진행분쟁최대3건. 같은앱회원이같은account/current owner revision에동일도전을중복적재하지않는검사를별도로둔다. 장비시작은자리예약아님. 성공시account락아래현재slot/본인중복·owner/revision을재검사해최대3건을보장한다. 기존account당active unique1개제안은폐기한다. proof당분쟁unique는유지한다.
- 정원이이미찬경우start는409 DISPUTE_CAPACITY_REACHED. 외부조회중다른분쟁이차서네번째장비확인이성공하면200 VerificationV2/passed+blocked/DISPUTE_CAPACITY_REACHED(새분쟁없음)로정직하게구분한다. 자리가비었다고지난성공proof로뒤늦게새24시간을열지않고새장비확인부터시작한다. 같은회원기존분쟁도DISPUTE_ALREADY_ACTIVE로중복생성0이다.
- 각분쟁은자기장비성공후24h기한을갖는다. 순서는DB성공시각+서버확정sequence로고정하며우연한worker실행순서/UUID난수순서로승자를바꾸지않는다. 동일account의앞선진행분쟁이있으면뒤분쟁worker는이를뛰어넘어이전하지않는다. 앞분쟁취소/invalidated뒤다음분쟁은자기의24h가끝난후에만처리한다. 앞분쟁의일시실패/review_required는보존하며뒤분쟁으로우회하지않는다.
- 기존owner의방어성공은같은account/base owner+revision의진행분쟁모두를하나의transaction에서defended로종료하고각version/feed/event를증가시킨다. 진행중다른방어proof는종료분쟁의stale proof로더이상권한을쓰지못한다. 유효장비결과를내지못한옛시도자proof는분쟁성립이아니므로일괄승인/방어기록으로바꾸지않는다. 별도방어generation을올려방어이전에시작한claim/defense proof의최종snapshot을무효화한다. 새시도는대기시간없이새baseline부터가능하며,방어전옛proof의늦은성공으로즉시새24시간을열지않는다. 이generation은평소소유revision을가짜로변경하거나다른진행분쟁추가때마다올리는값이아니다.
- 일괄방어가늦게시작된분쟁을통해앞분쟁의24h를연장하지않도록공통방어가능기한은같은cohort중가장빠른deadline이다. defense_available_until에표시하고새proof만료는min(시작+10분,공통기한)이다. 앞분쟁이취소돼기한이뒤로바뀌어도이미발급한proof의기한을자동연장하지않고필요시새proof로시작한다. 마감전전송이어도최종commit이공통기한이상이면방어로확정하지않는다.
- 첫이전성공은owner/revision/새등록/새unconfigured설정/이전설정종료/감사와그승자분쟁을transferred로동시commit한다. 같은옛owner/revision의나머지진행분쟁은invalidated/OWNER_CHANGED로종료한다. 남은시도자의장비성공/24h/자리/개인자료를새owner분쟁으로승계하지않는다.
- 동시에방어/취소/slot확보/worker이전/등록변경이경합해도account락과현재revision/최종DB시각검사로한순서만commit한다. GET은상태를쓰지않는다. 향후운영자고정은별도policyrevision guard로연결하되이번에고정DDL/도구를추가하지않는다.

## 8. 등록참조·한도·재조회

VerificationV2.registration_id는본인등록source/신규소유성공결과참조이며대상회원의등록은절대반환하지않는다. direct_input으로분쟁을열때는등록을자동생성하지않으므로null이다. 등록source는입력ID다. 분쟁개시는소유변경/등록한도증가가아니다.

DisputeOut.my_registration_id는조회시viewer의살아있는관련등록1개만반환한다. 미등록direct시도자는null,source등록이있으면그ID,기존owner는자기연결등록ID(없으면null),이전성공새owner는생성/연결한ID다. 이후등록삭제시현재GET은null로바뀐다. ownership_lost인옛owner의살아있는등록은ID가있어도open_registration권한을뜻하지않는다.

최종이전은다음과같다:

- 등록source: 원본등록이살아있고같은관찰원정대/소유후보라면재사용. 24h중명시삭제됐거나다른대상으로바뀌면자동부활/새등록대체없이review_required/REGISTRATION_REMOVED 또는 REGISTRATION_CONFLICT. 본인철회후새정상경로가능.
- directsource: 현재본인에게유일한같은후보account연결등록또는검증된관찰에대응하는미인증등록이있으면재사용. 여러충돌이면REGISTRATION_CONFLICT로보류하고임의등록을고르지않는다. 없으면한도20내에서새부계정등록을만들며본계정자동승격0이다.
- 신규생성이필요하지만한도20이면owner/설정/감사를부분commit하지않는다. 기존소유유지+defending/retrying_settlement/REGISTRATION_LIMIT/next_retry_at로남긴다. 사용자등록정리뒤worker또는settle로재검사하며새장비재인증/새24시간기산을강제하지않는다. 부분자료삭제나한도우회는없다.
- 성공한원ACK의등록ID는그때의본인참조다. 재전송후현재dispute/등록/roster/settings를GET하고현재owner/revision으로사용권한을확인한다. 새owner의활동없음/unconfigured를인증실패로표시하지않는다. 과거개인/주간/그룹/파티권한을새owner에게상속하지않는다.

## 9. POST 상태·오류 정리

- preview200,신규start/defense201,confirm/cancel/분쟁cancel/settle200. 이11경로에204/202/성공빈본문없음. provider/권한/잘못된입력은기존error envelope로반환한다.
- confirm의장비미해제/비지정부위변경은200 pending,기한만료는200 expired,최종scope변화는200 invalidated/blocked. 인증/현재권한을네트워크전에거부한경우는아래HTTP오류다. 동일key의성공ACK를과거결과라는이유로새상태로덮지않는다.
- proof cancel은pending만취소가능;이미expired면200 expired확정. passed/invalidated등을새cancel명령으로바꾸려하면409 VERIFICATION_TERMINAL. 같은key재전송은원ACK다. 분쟁cancel은challenger·defending자기기한전또는review_required만가능,terminal은새명령409 DISPUTE_TERMINAL. owner는전체취소대신방어를사용한다.
- 일반start/confirm현재본인소유차단409 ALREADY_VERIFIED유지. defense전용route는현재owner/분쟁당사자·선택snapshot을통과할때만예외다.
- HTTP 공통:400 INVALID_REQUEST;401 ACCESS_INVALID등기존인증코드/Bearer;403 DISPUTE_ACTION_FORBIDDEN/OWNERSHIP_REQUIRED;404 VERIFICATION_NOT_FOUND/DISPUTE_NOT_FOUND/CHARACTER_NOT_FOUND/REGISTRATION_NOT_FOUND(무관회원자원은404);409 REVISION_CONFLICT/IDENTITY_CONFLICT/IDEMPOTENCY_CONFLICT/IDEMPOTENCY_EXPIRED/REQUEST_IN_PROGRESS/CURSOR_STALE/ALREADY_VERIFIED/DISPUTE_CAPACITY_REACHED/DISPUTE_ALREADY_ACTIVE/DISPUTE_NOT_DUE/DEFENSE_WINDOW_CLOSED/VERIFICATION_TERMINAL/DISPUTE_TERMINAL;400 EQUIPMENT_INCOMPLETE;429 RATE_LIMITED;409 LOSTARK_KEY_NOT_CONFIGURED/LOSTARK_KEY_CHANGED/LOSTARK_KEY_REJECTED,503 UPSTREAM_UNAVAILABLE/UPSTREAM_RATE_LIMITED/LOSTARK_KEY_UNAVAILABLE/SERVICE_UNAVAILABLE.
- error는 `{error:{code:string,message:string,request_id:UUID}}`가기본이며생략가능하고nullable인retry_after_seconds(integer>=1)/retry_at(UTC시각)과Retry-After는기존계약을따른다. 새resource ID/상대회원ID를error에추가하지않는다.

## 10. 검토 산출물과 완료 경계

[기계판독용 V2 OpenAPI 초안](contracts/ownership-dispute-v2.openapi.draft.json)에필드/필수null/enum·11동작/status/body를별도정리한다. 초안이며기존실행OpenAPI에포함하지않는다. 이문서의상태간불변조건/권한/시간/동시성검사도구현해야하며구조스키마통과만으로증거를인정하지않는다.

[#8 전체142번째 Flutter 최종소비검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)에서세공백해소가능/기술차단없음을확인했다. 같은계약검토를다시선행조건으로두지않는다. 다음Backend구현·검증뒤실제계약SHA/실행반영범위를인계하고Flutter가최소UI설계/연결한다. 지금UI구현/실기기시험을선행요청하지않는다. Backend는확정계약과사용자추가정책에따라구현단위를준비할수있으나이번산출물은설계회신이다. 기존로컬DB0014/자료/키/flag·코드/실행OpenAPI/API/worker변경·새환경접속/초기화·운영배포없음. 설계문서/초안은미커밋·미push이며Issue본문으로계약원문을공유한다.

## 11. 142번째 검토 수용·Backend 구현 준비

[#8 전체142번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)에서V2별도DTO·proof발견/복원·동일200 settle·다른본인캐릭터방어가소비가능함을확인했다. 실행API/worker/Flutter구현완료와구분한다. 추가페이지상단방어안내는기존role=owner/view=active·state/phase/defense_available_until/allowed_actions로대응하며별도배너API없음. 확인은방어진입/복수분쟁선택이고즉시장비스타트/방어성공이아니다. 기한뒤처리중/검토필요·조회실패/열람과종료구분·회원scope복원을보존한다. 구체배치/닫기/배지·상시polling은Flutter후속UI설계,외부push는후속이다.

Backend구현순서는다음과같다.

1. additive모델/DDL·분쟁head/방어generation·event/회원feed·최대3slot/본인중복·멱등기반. 기존DB0014/자료보존·격리DB검증.
2. 기존collector/장비증거·claim/owner/lifecycle재사용한V2 preview/proof/분쟁개시·양측발견/복원/조회/취소·등록참조. V1strictDTO/멱등/ALREADY차단보존.
3. 선택캐릭터방어·공통기한/일괄종료·옛proof generation검사·legacy타소유즉시이전우회차단.
4. 선성립우선worker due/lease·재시작복구·예약ACK·소유/등록/설정/감사/feed/나머지종료원자화·그룹대표/개인자료/주간/파티guard.
5. 격리PG/모의HTTP·동시3자리/4번째거절·일괄방어/만기/rollback/worker재시작/새기기복원/권한회귀·실행OpenAPI전체검증→인계구간commit/push/원격확인→같은Issue결과회신. 실제API/worker/DB반영과Flutter/실게임미확인을구분한다.

이번은준비정리이며코드/DDL/API/worker실행·DB변경없음. 기본로그인/키/사용자게임시험을반복선행조건으로두지않는다. 운영자고정/Discord·새환경/초기화·외부push는범위밖이다.
