# Issue #3 내 계정 탭 복원 구현 설계·작업 계획

작성: 2026-10-14. 상태: **계획 기반 로컬 구현·자동 검증 완료, 실provider/Flutter 후속 검증**. 작업 브랜치 `feat/3-account-restoration`, 기준 dev `e6c72e4`. 이 문서는 구현 전 설계 이력이며 최신 실행결과/한계는 [실행 안내](ISSUE_3_DEVELOPMENT.md)와 DEV_LOG가 기준이다. 원격 게시·실인수 완료를 의미하지 않는다.

근거: [Issue 요청](https://github.com/heo0328/lostparty-backend/issues/3), [첫 Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159759288), [A/B·멱등/보존 수용과 경계 보완](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616). 계약 의미는 [계약 검토안](ISSUE_3_ACCOUNT_CONTRACT_DRAFT.md), 진행 경계는 [협업 작업 단계](API_COLLABORATION_WORKFLOW.md), 다음 실행은 [NEXT_WORK](project/NEXT_WORK.md)를 따른다. 내부 구현 선택은 Backend가 검증하며 기존 합의의 재승인을 기다리지 않는다.

## 1. 목표·보존 범위와 완료 단계

Google 로그인 이후 빈 내 등록 조회 → siblings 미리보기·등록 → 서버 장비 challenge → 소유권 확정 → 전체 캐릭터/활동/대표 조회·저장 → 재조회로 설정 유지의 Backend 기반을 만든다. 등록, 소유 인증, 현재 사용 자격을 각각 표현한다.

기존 /health와 #2 인증6개 API·세션 정책을 유지한다. Flutter 로컬 캐릭터·빌드·표시순서·displayLimit을 서버에 이관/삭제하지 않는다. Firebase/guest 연결, 파티·그룹·WS·빌드 JSON 동기화·운영 배포·개발 DB 초기화는 제외한다.

| 단계 | 완료 기준 |
|---|---|
| Backend 구현 | 합의된12개 route·DTO·모델·migration·service·OpenAPI 및 보류/실패 상태 구현 |
| Backend 자동 검증 | 격리 PostgreSQL 권한·경쟁·원자성·멱등·시간 경계와 API/계약 비교 통과 |
| 계약 인계 | 사용할 버전/게시 SHA·예제·실행 조건·오류·테스트 결과와 실검증 대기 명시 |
| Flutter 적용·테스트 | Flutter 소비 버전·전체페이지/저장/재시작/유실/로컬보존 등 결과 확인 |
| 실provider 인수 | 서버 key 준비 후 schema·해제 표현·지연·quota·허용 관찰 기준 및 실제 장비 흐름 확인 |

Backend 구현/자동 검증은 실provider 자료 대기와 독립적으로 완료한다. 실provider 미확인 판정은 fail closed로 응답하며 테스트용 증거를 공개 API에서 받지 않는다.

## 2. 모듈과 기존 코드 연결

`app/game_accounts`에 기능을 모으고 현재 인증 모듈의 SQLAlchemy Base·DB session·DB clock·Bearer 검증을 재사용한다.

| 파일 후보 | 책임 |
|---|---|
| models.py / schemas.py / router.py | DB 구조·strict DTO·12개경로와 auth dependency |
| registrations.py / queries.py | 등록 CRUD·본계정 전환·pagination/전체settings 조회 |
| verifications.py / ownership.py | challenge 상태·equipment 판정·canonical identity·소유권/audit transaction |
| character_settings.py / roster.py | atomic 선택/대표·summary reconciliation·suspect/복귀 |
| idempotency.py / rate_limit.py / cleanup.py | lease/fencing·성공결과/tombstone·공통 quota·TTL 정리 |
| provider.py / equipment.py | 현재 transport/판정 확장, typed parser·증거 품질 분리 |

`app/main.py`는 새 router만 연결한다. 기존 auth principal이 응답 DTO를 반환하므로 쓰기 service는 그 id로 User/Session을 다시 읽어 잠금·상태 검사한다. 요청 시작 dependency만으로 commit 권한을 보장하지 않는다. 오류 응답은 기존 `{error:{code,message,request_id}}` 구조/no-store를 재사용하고 status별 Retry-After를 지정할 수 있도록 확장한다. #2의 기존 오류/헤더 의미는 유지한다. Alembic metadata에 새 모델을 등록하되 migration은 runtime model import 없이 고정 DDL로 작성한다.

## 3. 데이터 모델·제약·수명

UUID PK, 모든 시각 timestamptz, revision/version은1부터 시작하고 증가만 한다. 관찰키는 provider가 반환한 server_name+character_name의 정확한 문자열이다. 임의 lower-case/이름변경 추론을 하지 않는다. nullable 수치를0으로 바꾸지 않는다.

| 테이블 후보 | 주요 필드·DB 제약 |
|---|---|
| game_account_registrations | id, user_id FK, game_account_id nullable FK, lookup_character_name, label, is_main, registration_status, version, created_at/updated_at/deleted_at. live 회원+canonical partial UNIQUE, live 본계정 회원 partial UNIQUE. label1~40. 회원20개 상한은 user lock 아래 검사 |
| registration_characters | registration_id FK, server_name, character_name, class_name, character_level, item_level nullable numeric, summary_fetched_at. 관찰키 composite PK. 미인증 summary 저장이며 canonical ID/소유 증명 없음 |
| game_accounts | id, status, active_owner_user_id nullable FK, ownership_revision, roster_revision, verified_at, updated_at. owner는 단일 칼럼, revision>=1. active status의 의미와 owner 정합성을 CHECK |
| game_characters | id, game_account_id FK, server_name, character_name, class_name, character_level, item_level nullable numeric, combat_power nullable numeric, power_fetched_at nullable, roster_status confirmed/suspect/missing, summary_fetched_at, last_confirmed_at, version. 관찰키 UNIQUE, (game_account_id,id) UNIQUE |
| character_settings | id, user_id FK, game_account_id FK, ownership_revision_at_configuration, configuration_state, representative_character_id nullable, version, representative_changed_at/next_change_at nullable, ended_at nullable. live user+account UNIQUE. account+대표 composite FK로 교차계정 참조 차단 |
| activity_characters | settings_id FK, game_account_id, character_id. (settings_id,character_id) PK, settings/account 및 character/account composite FK. 최소1명·대표 포함·confirmed/current owner는 service transaction 검증 |
| game_account_verifications | id, actor_user_id FK, registration_id nullable FK, source, lookup_character_name/server_name, candidate_account_id nullable, ownership_revision_at_start nullable, status pending/verified/expired/cancelled, baseline JSONB nullable, required_slots JSONB, roster_observation JSONB nullable, created_at/expires_at, attempt_count/last_checked_at, verified_at, result_reference nullable, terminal_at nullable. actor/time·expiry index |
| ownership_audits | id(result reference), account_id FK, previous_owner nullable, new_owner, before/after revision, challenge_id UNIQUE, created_at. 최소 감사정보만 저장. OAuth subject/email/token·raw JSON 저장 없음 |
| game_account_requests | actor_user_id, operation, key(UUIDv4), request_hash, target_id nullable, state running/retryable/completed/expired, lease_generation, lease_expires_at, result_status/result_body nullable, completed_at/result_expires_at/tombstone_expires_at. UNIQUE(actor,operation,key). result에 credential/baseline 없음 |
| game_account_cache / game_account_limits | preview/summary 최소 요약·관찰시각/TTL, bucket scope/key/window/count. cache는 ownership 증명이 아님. quota key에 secret 저장 없음 |

물리 구조는 구현 시 불필요한 중복을 줄이되 계약 의미를 유지한다. 설정의 이전 owner 이력은 ended_at으로 종료하고 새 owner에게 복사하지 않는다. 삭제 등록은24시간 tombstone 뒤 private preview 관계를 정리한다. dedup 대상 참조는 등록 삭제에 cascade하지 않으며 challenge/audit의 최소 대상 UUID는 보존한다.

migration `0002_game_accounts`는 additive로 작성한다. 기존 인증 행/테이블을 수정·import하지 않는다. 격리 DB에서0001→0002 적용과 기존 행 보존을 검증한다. 앱 rollback 시 추가 테이블을 보존하며 데이터가 있는 downgrade는 자동 실행하지 않는다. 기존 테스트fixture에 새 모델 격리와 rate state 초기화를 추가한다.

## 4. API·응답 설계

모든 API는 자신의 유효Bearer session이 필요하다. mutation은 Idempotency-Key UUIDv4와 strict allowlist를 적용한다. GET마다 provider 상세를 암묵적으로 호출하지 않는다. 등록20/캐릭터200, page default50/max100이며200초과는 잘라서 누락으로 처리하지 않는다.

| API | 입력 | 성공·동작 |
|---|---|---|
| POST /v1/game-accounts/preview | character_name | 200 preview·server_fetched_at·expires_at, 소유/등록/활동 생성 없음 |
| GET /v1/me/game-accounts | limit,cursor | 200 등록page, label/main/version, nullable canonical ID, 인증/소유 상태·revision·대표 요약 |
| POST /v1/me/game-accounts | lookup_character_name,label,is_main | 201 fresh siblings 검증 후 미인증 등록, 같은 회원 관찰overlap 중복 거절 |
| PATCH /v1/me/game-accounts/{registration_id} | label/is_main,expected_version | 200 등록, user lock 내 본계정 전환·기존 main version 증가 |
| DELETE 위 등록 경로 | query expected_version | 204 자신의 등록·활동 관계 종료, canonical/다른 회원/로컬 자료 보존 |
| GET 위 등록 경로/characters | limit,cursor | 200 캐릭터page+페이지 독립 전체settings+각revision/시각 |
| POST 위 등록 경로/refresh | 빈object | 200 summary·관찰 결과·추가/suspect 수·requires_refresh와 재조회 위치, 실패 시 기존 자료 보존 |
| POST /v1/me/game-account-verifications | source, registration_id 또는character_name | 201 안내, 배타적 입력 검증·6부위 완전baseline·fresh roster·10분challenge |
| GET 위 인증 경로/{challenge_id} | 없음 | 200 현재status/required_slots/expires_at/result_reference, private baseline 없음 |
| POST 위 인증 경로/{challenge_id}/confirm | 빈object | 200 pending+result_code 또는verified+result_reference/등록ID, commit 전 재검증 |
| DELETE 위 인증 경로/{challenge_id} | 없음 | 204 pending취소, terminal결과 보존·성공 되돌림 없음 |
| PUT 위 등록 경로/character-settings | activity_character_ids,representative_character_id,세expected값 | 200 확정 전체settings, 한transaction에서 교체 |

세expected값은 expected_settings_version/expected_ownership_revision/expected_roster_revision이다. refresh는 서버가 호출 전 읽은revision으로 commit 전 재검증하므로 공개expected_version을 추가하지 않는다. 실구현 시 새로 외부에 영향을 주는 입력/enum/오류는 Issue에 차이를 제시하며 미합의 필수 조건을 조용히 추가하지 않는다.

characters GET는 REPEATABLE READ read transaction 또는 단일query로 page/settings를 같은snapshot에서 읽는다. cursor는 scope·정렬·roster_revision을 담은 서명된 opaque값이다. 설정version은 cursor에 고정하지 않아도 응답에 제공한다. Flutter는 모든page의 세version/revision 일치와 로딩완료를 확인해 draft를 만들고 PUT는 세값을 DB에서 원자 검사한다.

configuration_state는 unconfigured/configured/needs_reconfiguration. ownership_lost는 별도 소유 상태이며 이 enum에 혼합하지 않는다. 미인증/비owner settings projection은 빈선택/대표null. needs_reconfiguration은 자신의 기존 선택·대표를 보존하고 부적격ID/사유·현재 사용가능 여부를 별도 응답한다.

오류는 기존error 객체/no-store를 유지한다. 400 INVALID_REQUEST/EMPTY_ACTIVITY_SELECTION/REPRESENTATIVE_REQUIRED/EQUIPMENT_INCOMPLETE,403 OWNERSHIP_REQUIRED,404 REGISTRATION_NOT_FOUND/CHARACTER_NOT_FOUND/VERIFICATION_NOT_FOUND,409 REVISION_CONFLICT/CURSOR_STALE/IDENTITY_CONFLICT/REGISTRATION_EXISTS/REPRESENTATIVE_COOLDOWN/IDEMPOTENCY_CONFLICT/REQUEST_IN_PROGRESS/IDEMPOTENCY_EXPIRED,429 RATE_LIMITED,503 UPSTREAM_UNAVAILABLE를 정의한다. 기존401/ACCOUNT_DISABLED 유지. live증거 보류 result_code는 계약 차이로 명시하고 message는 UI분기 기준으로 사용하지 않는다.

## 5. mutation·lease·commit 권한

strict DTO/인증 → dedup예약 → 필요한 외부 호출 → 짧은DB transaction에서 권한/lease/revision 재검사 → 업무 변경+dedup결과 동시commit → 응답 순서다.

- scope actor+operation, hash는method/대상path/query/기본값 적용body를 포함한다. 선택ID는 중복을 거절한 뒤 순서에 의미가 없을 때만 sort한다. expected조건도 hash에 포함한다.
- lease는 DBclock30초, 재취득 시generation 증가. 처리중409/Retry-After2. 새worker가 재취득한 뒤 구worker의generation은 commit할 수 없다. provider transport에 전체deadline을 추가하고 필요하면generation 조건으로 lease갱신한다.
- upstream장애/commit전crash는 retryable 또는lease만료 후 같은key 재취득. commit후crash는 같은transaction의 completed결과를 replay한다. 입력/권한 오류를 성공결과로 저장하지 않되 기존key/hash 결합을 해제해 다른payload에 전용하지 않는다.
- replay도 principal/actor/operation/대상/hash 검증. DELETE성공은 live row가 없어도 동일actor 저장결과204를 복구하고 다른actor에게 노출하지 않는다. 등록 청소가 dedup권한 근거를 제거하지 않는다.
- start replay는 원challenge ID/결과, 현재status는GET기준·TTL연장 없음. confirm pending replay는 같은관찰 결과를 반환하고 다음 사용자 명시 확인만 새key로 fresh조회한다. verified challenge는 새key confirm에도 같은결과를 반환하고 추가 이전을 만들지 않는다.
- 성공result24시간 후 body제거·expired, 추가24시간 tombstone. TTL은 요청에서도 평가하고 청소 지연으로 연장하지 않는다.48시간후 blind retry 보장 없음.

lock순서: user UUID순→session→account UUID순→registration→settings→challenge. canonical후보 생성은 정렬한 관찰key의 transaction advisory lock 후 overlap재검색, UNIQUE가 최종 기준이다. dedup최종화는 업무lock후generation 조건update하며 예약worker가 업무row를 역순으로 잡지 않는다. 외부 대기 중 DB transaction/lock을 유지하지 않는다. 소유권 이전에서 이전 owner를 함께 잠가야 하면 후보 조회에서 관련 user ID를 수집해 정렬하고, account lock 이후 owner가 달라졌다면 역순 lock을 추가하지 않고 transaction을 재시작한다.

## 6. identity·인증·소유권

preview/미인증등록의 관찰key를 canonical권한ID로 응답하지 않는다. 요청의owner/verified/장비는 신뢰하지 않는다. 동일회원 등록경쟁은 fresh조회 후user lock내에서 관찰overlap를 재검사한다.

start는 fresh roster/ArmoryProfile의 입력server/name일치·6부위 장착을 확인한다. 서버난수1~3슬롯과 private baseline을DB저장,client에는 안내만 반환한다.10분 now>=expires_at 만료. 취소/만료/타actor는 confirm거절하며 expired변경을 오류rollback으로 지우지 않는다.

confirm은 fresh장비 비교·roster 입력존재·snapshot품질·identity overlap를 평가한다. commit전 등록live/actor/session/candidate ownership_revision을 재검사한다. canonical overlap0이면 신규account/character,1이면 같은ID,여러개면409 IDENTITY_CONFLICT. 확인 중 소유revision변경은409,삭제등록확정은 거절한다.

이전은 owner변경+revision증가,canonical소속유지,이전등록ownership_lost·이전settings종료·활동자격종료,새owner등록 연결+unconfigured,audit+challenge verified/result+dedup을 한commit으로 처리한다. 회원삭제/설정복사 없음. 동일owner재인증은 유효설정/ownership_revision을 불필요하게 바꾸지 않고 audit종류로 구분한다. 부분 실패는 전부rollback한다.

live보류는 adapter품질평가로 수행한다. schema-valid라도 기존roster감소/입력결락/다중canonical overlap를 완전proof로 인정하지 않는다. 실장비schema 검증 전 live ownership확정은 보류하되 정상transaction경로는 pytest의fixture injection으로 검증한다. 공개request/env의 임의bool로 mock proof를 받을 경로는 만들지 않는다. 실증 후 품질조건을 보완해 보류범위를 좁히며 미합의 live감소→missing/이전은 열지 않는다.

## 7. roster·활동·대표

typed observation만 summary에 반영한다. invalid/null/빈값/중복/입력부재/상한초과는 기존자료 유지·refresh실패다. 신규관찰key는 새ID/비활동,기존key는ID/선택보존. 최초누락은suspect와시각/재조회필요를 표시한다. live missing자동확정은 보류하고 상태전이 코드는 품질fixture로 검증한다. 같은key복귀는 기존ID/confirmed,rename추론/계정병합 없음. power null은 이전정상값 유지+stale/개별조회시각이다.

PUT는 current owner/account소속/confirmed/세expected/중복없음/최소1명/대표선택포함을 검사한다. 다른계정설정을 건드리지 않는다. suspect/missing 기존선택은 보존하고 영향 시needs_reconfiguration·자격중지. 명시save성공만 전체선택/대표 교체·settings version증가. 완전히같은내용의 새key저장은 불필요한version/cooldown변경을 피한다.

최초seed next_change_at=null. 이후 실제대표변경만 changed_at·현재+5분,같은대표 활동변경/replay는 시각유지. missing대표복구도 우회없음. 실패시활동도 보존. 본계정삭제후 자동승격없음,canonical owner유지·당해관계종료·재등록unconfigured·타계정활동보존.

## 8. provider·quota·보관

typed adapter는 roster요약,Armory profile/equipment,fetched_at,품질/보류사유를 반환한다. 기존Flutter파서근거로 parser를 구현하고 미실증값은 안전거절한다. item_level/power는decimal변환,null과불량format 구분. baseline외raw JSON/Tooltip 저장없음.

preview30분+청소유예1시간,terminal baseline/관찰snapshot24시간내제거,상태/result reference24시간,dedup24+24시간,audit90일. expiry index·batch·skip locked로 청소하며HTTP TTL은 DBclock으로 판단한다. 보관중dedup의 challenge가 청소되면 과거result와현재404의 의미를 인계한다.

manual10초,start actor3/min,confirm challenge5초+actor12/min,provider전체80/min DB제한. 고정window경계burst 방지를 위해 직전60초event를 집계·lock내예약한다. worker/instance공통,Retry-After는 실제허용까지 ceil초. 실quota/다른consumer영향에 맞춰 축소한다. transport동시2는 process단위,summary동일조회는 DBlease합류,proof는cache로 성공판정하지 않는다. 키없음은503이며 로컬성공으로 위장하지 않는다.

## 9. 구현 단위와 검증 순서

| 단위 | 구현 대상 | 완료 검증·다음에 가능한 일 |
|---|---|---|
| 1. 모델/공통 기반/등록 | 0002, auth 재검사, typed adapter, dedup/lease, preview/등록 CRUD | migration 기존 행 보존, guest/타인/필드 위조, 본계정 동시 전환, 중복 등록/상한, DELETE replay, lease takeover/구 worker rollback. 빈 등록/CRUD/오류를 Flutter에 인계 가능 |
| 2. 조회/refresh | 전체 settings/query, cursor/revision, summary/roster, quota/cache | 200 초과 무부분 반영, 세 version 반환, cursor stale/변조, cache TTL, null/부분 실패 보존, 신규/의심/복귀, 다중 worker quota. 목록·draft 준비 검증 가능 |
| 3. challenge/identity/owner | start/get/confirm/cancel, canonical/audit/이전 transaction | 10분 경계, 취소 경쟁, 동시 identity/confirm, 다른 owner/낡은 revision, 불량 snapshot/지연/429, rollback, 성공 replay/live 보류. 실provider 미검증 정상 경로는 fixture 검증 |
| 4. 활동/대표 | atomic PUT·소유권 상실/reconfiguration | 최소1/대표 포함/최초seed/5분 경계/같은 대표, 교차소속/suspect/stale, 이전과 늦은 save, 다른 계정 선택 보존, 등록 삭제/재등록. 관리 화면 계약 완성 |
| 5. 통합/인계 | 청소/보존, sanitized 예제/오류 표/실행 안내, 계약 비교·회귀 | 기존46 포함 필요한 pytest, 최신 image 전체 OpenAPI 비교, 의존성/차분/비밀 혼입 확인. 실제 실행 결과·미확인 구분해 Issue 인계 |
| 6. Flutter/실provider 후속 | key 안전 준비, 실응답 관찰, 화면 연결/장비 조작 | 실제 schema·지연·quota, 페이지/409/유실/재시작·로컬 보존, live 보류 해제 근거. 발견된 실패 수정·대상 회귀·재확인 |

각 단위의 code/tests/문서를 맞춘다. 단위 완료 후 다음 단위로 진행하고 실provider 준비를 기다리며 멈추지 않는다. 현재83개 통과는 기반 코드의 과거 결과이며 새로운 API/DB 검증에 전용하지 않는다. 개발 DB migration은 대상/영향을 명시해 필요 시 적용하고 먼저 격리 DB에서 검증한다.

## 10. 인계·후속 입력

Issue 보고에는 새로 테스트 가능한 API/흐름, 원본 OpenAPI, migration, 실제 테스트 결과, 호환 영향, 계약/구현 SHA(미commit이면 미발행), 로컬 실행/비밀 설정 준비, Flutter 테스트 항목, 실provider 미확인 항목을 포함한다. 미push 코드를 원격에서 가져올 수 있는 것으로 취급하지 않는다.

| 후속 항목 | 직접 보류할 동작 | 계속할 작업·담당·해제 조건 |
|---|---|---|
| server key 미준비 | live provider 호출/실장비 인수 | API/DB 전체·fixture 검증 계속. 사용자/Backend가 안전한 로컬 설정을 준비한 뒤 Backend 관찰 |
| 해제 표현/실schema 미검증 | 미실증 snapshot의 live ownership 확정 | parser/장비 비교/소유 transaction·rollback 구현. Backend 실응답+사용자 수동 장비 검증 |
| 부분roster 전체성/관찰 기준 | live 감소의 자동missing·그 roster를 이용한 소유권 이전 | suspect/보존/복귀·revision/부적격 처리 구현. Backend가 근거 제시하고 필요한 관찰 기준만 합의 |
| Flutter 미연결 | UI/재시작/전체page/로컬보존 인수 완료 | API·계약 인계 계속. Flutter가 소비 버전·안전한 재현 결과를 Issue로 보고, Backend가 수정 |

commit/push/통합·운영 배포 및 기존 데이터 파괴에 별도 승인이 필요한 범위는 기존 규칙을 따른다. 이번 설계 작성은 구현 완료나 배포 승인을 의미하지 않는다.

## 구현 반영 차이

초기 개발의 경쟁 안전성을 위해 개별 계정 lock 대신 짧은 game mutation 전역 advisory lock을 사용한다. 네트워크 대기에는 유지하지 않고 auth 쓰기는 영향을 받지 않는다. 미인증 preview는 registration JSONB로 최소 요약을 저장해 별도 registration_characters 테이블을 생략했다. summary fetch lease 테이블을 포함해 신규11개 테이블이며 모델·고정DDL을 함께 검증했다. 활동은 composite FK 관계 테이블이고 소유상실은 별도 ownership_status다. refresh에 새로운 expected_version 입력을 추가하지 않고 서버가 읽은 등록version을 재검사한다. 실provider 성공판정만 보류하며 transaction/상태 코드는 구현·자동검증했다.
