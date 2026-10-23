# Issue #3 내 계정 복원 계약 검토안

상태: **합의 기반 로컬 구현·원본 OpenAPI 반영, 실인수 후속** (2026-10-14). 원본 요구는 [Issue #3](https://github.com/heo0328/lostparty-backend/issues/3), 인증은 기존 계약 `519c609495966a3d785c6671c09bf513b28875a6`을 재사용한다. 이 문서는 합의·제안 이력이며 현재 REST 원본은 [OpenAPI](../../../openapi/openapi.yaml), 실제 구현/검증 범위는 [내 계정 API 안내](ISSUE_3_DEVELOPMENT.md)이다. 아래 회신대기·미구현 설명은 설계 당시 이력이다.

## 확정 요구와 독립 구현

로그인만으로 원정대 인증/등록/활동을 만들지 않는다. Firebase 이관·연결·삭제 없음. 서버 fresh 응답만 장비 증거로 사용한다. baseline 6부위의 Type/Name/Grade만 비교하고 Tooltip은 제외한다. 난수로 1~3개 부위를 선택하고 전부 사라졌을 때 나머지 baseline과 일치해야 한다. null·중복·잘못된 응답은 성공으로 취급하지 않는다. 이 순수 판정과 bounded provider transport는 계약 합의와 독립적으로 개발하며 아직 HTTP/DB에 연결하지 않는다.

## API·식별자·쓰기 제안

Issue 본문의 12개 경로를 유지한다. 자체 Bearer principal, strict allowlist, UTC Z, 기존 error 객체를 사용한다. UUID는 registration/game_account/character/challenge를 구분한다. preview에는 canonical ID나 소유권 증명이 없다. unrelated registration/challenge는 404, 본인 등록이지만 소유 상실 시 쓰기는 403 OWNERSHIP_REQUIRED. 버전 불일치는 409 REVISION_CONFLICT. 장비 mismatch는 200 pending 및 result_code로 구분한다.

- 등록/캐릭터 목록: cursor pagination, 기본 50/최대100, 등록은 created_at+id, 캐릭터는 server_name+character_name+id 순. cursor는 scope·정렬에 바인딩하고 변경 중 snapshot 일관성은 보장하지 않는다.
- 모든 변경 요청은 Idempotency-Key UUIDv4를 사용한다. actor+operation+key 유일성, normalized payload hash 비교, 다른 payload는 409 IDEMPOTENCY_CONFLICT. 확정 결과24시간 보관, 그 이후409 IDEMPOTENCY_EXPIRED tombstone을 추가24시간 보관하는 제안. 보장 종료 뒤에는 먼저 GET 재조회하며 자동 blind retry를 하지 않는다. 실패/진행중 의미와 각 응답을 OpenAPI에 상세화한다.
- PATCH/DELETE는 expected_version, 설정 PUT는 expected_settings_version와 expected_ownership_revision. DELETE는 body 없이 query expected_version을 사용한다.
- 등록 label1~40자, 캐릭터명1~64자, 회원 등록 최대20·계정 캐릭터 최대200·1MiB upstream body 상한 제안. 초과 응답은 부분 반영 없이 거절한다.
- 같은 회원에서 검증된 siblings 중첩은 중복 등록으로409 REGISTRATION_EXISTS. canonical 두 계정과 중첩 시409 IDENTITY_CONFLICT. 미인증 preview와 등록은 canonical 생성/소유권 변경 없음.
- 직접입력 인증 성공은 같은 transaction에서 미인증 등록을 재사용하거나 기본 label의 부계정을 만든다. 기존 본계정이 없어도 자동 본계정 지정은 하지 않는 제안.

## 데이터·원자성 제안

물리 구조 후보: game_account_registrations, game_accounts, game_characters, character_settings, activity_characters, game_account_verifications, ownership_audits, game_account_requests. 기존 users FK 사용. active 본계정 partial unique, 관찰키(server_name,character_name) unique, 활동 membership unique/FK. 삭제한 등록은24시간 tombstone 후 관계 정리; canonical/audit는 별도 유지한다. 기존 DB 초기화 없이 additive migration을 준비한다.

네트워크 호출 전 권한·revision을 읽고 DB lock 없이 외부 호출 후, 회원/세션→canonical 계정→등록→설정 순으로 최신 상태를 잠금·재검증한다. 생성 후보 경합은 관찰키 unique/advisory lock을 이용해 재판정한다. 소유권 이전은 revision 증가, 이전 등록 ownership_lost, 이전 활동 자격 종료, 새 owner unconfigured, audit/dedup 결과를 한 transaction으로 처리한다. 소유권 유지 재인증은 이전 처리와 구분하고 유효 설정을 보존한다.

- 본계정 제거 후 자동 승격하지 않는다. 마지막 등록 제거는 그 회원의 활동/대표를 종료하지만 소유권 포기와 혼합하지 않는다. 재등록 시 unconfigured로 시작하는 제안.
- configuration_state: unconfigured/configured/needs_reconfiguration. configured는 활동>=1, 대표가 선택 집합에 포함, confirmed/current owner. 누락 ID/과거 선택은 이력으로 보존하되 앱 사용 가능 여부는 별도 false. 대표 또는 선택 캐릭터 누락 시 needs_reconfiguration.
- 대표 최초 저장은 next_change_at=null. 실제 대표 변경만5분 cooldown 시작, 같은 대표/멱등 재전송은 시각 유지. 누락 대표 복구도 cooldown을 우회하지 않는다(아래 Flutter 회신 반영).

## provider·보존·상한 제안 및 한계

공식 [usage guide](https://developer-lostark.game.onstove.com/usage-guide)에서 Bearer 인증·429·rate-limit 응답 헤더를 확인했다. 문서의100/min은 예시이며 실제 key quota로 단정하지 않는다. [changelog](https://developer-lostark.game.onstove.com/changelog)에서 siblings가 계정 전체 profile을 반환한다는 설명 및 profile CombatPower 추가를 확인했다. 영속 계정/캐릭터 ID와 roster 전체성/스냅샷 원자성은 이 두 자료로 확인되지 않았다. 실제 schema·sanitized 응답 확인 후 parser/전체성 정책을 확정한다.

서버 private LOSTARK_API_TOKEN 제안. 현재 .env에 LOSTARK_API_TOKEN/LOSTARK_API_KEY 항목이 없고 별도 key 준비는 미확인. secret 값은 Issue로 받지 않는다. 전체 Armory 종합 상세는 인증 때만, 일반 목록은 siblings 요약. combat_power 미제공은 null이며 최근 정상값 유지+stale 표시를 설계한다.

- transport: HTTPS 고정 origin, redirect 금지, timeout connect3/read5초,1MiB body 상한, 동시2개, 자동 retry 없음. 사용자 입력은 path segment percent-encode. timeout/429/401/HTML/invalid JSON은 정상 빈 roster와 구분한다.
- summary cache30분·manual refresh10초·actor start3회/분·confirm challenge당5초·actor12회/분, 전체 provider 요청80회/분을 시작 후보로 제안. 실제 quota가 더 낮으면 축소한다. 요청 합치기는 동일 관찰키·조회 종류 단위이고 proof는 캐시로 성공시키지 않는다.
- challenge10분, now>=expires_at 만료. baseline은 종료 후24시간 내 제거. preview cache는 TTL 종료 후1시간 내 제거. dedup은 위48시간 후 청소. audit은90일 제안이며 운영 보존 정책은 별도 결정. raw JSON은 저장하지 않는다.
- siblings 비정상/빈/null/입력 캐릭터 누락/중복/상한 초과는 reconciliation 금지. schema-valid 응답의 조용한 일부 누락을 감지할 수 있다는 보장은 없다. 안전안: 최초 누락을 suspect로 보류하고 독립 fresh 재조회에서도 누락될 때 missing으로 전환하며, 인증 roster identity와 별도로 처리한다. 그래도 완전성을 증명하지 못하는 한계와 UI 상태를 합의해야 한다.

## Flutter가 회신할 항목

1. 12개 경로·식별자·cursor·Idempotency-Key/조건부 버전·위 제안 상한을 소비할 수 있는지, 변경 필요한 DTO/화면 조건.
2. 본계정 제거 시 자동 승격 없음, 직접입력 인증 성공 시 부계정 등록, 마지막 등록 제거 후 설정 초기화, 최초 대표 cooldown 없음과 누락 대표 복구 예외에 대한 동의/수정.
3. 실제 provider siblings/Armory의 개인정보 제거 schema 예시(필드명·타입·null/장비 해제 표현), 영속 ID/전체성 근거와 기존 검증 슬롯 Type 정확한 문자열. 캐릭터명 등 실사용 자료나 token/key는 첨부하지 않는다.
4. 서버 전용 API client/key 준비 담당과 개발 테스트 가능 여부만 회신. key 값은 안전한 로컬 설정으로 별도 준비. 테스트 캐릭터/실제 장비 조작은 합의 후 수동 공동 인수.

최신 수용 회신을 반영해 [구현 설계·작업 계획](ISSUE_3_IMPLEMENTATION_PLAN.md)을 작성했다. 신규 REST/DDL은 구현 전이며 합의된 영역부터 구현·검증한다. 합의 후 등록/provider/migration → 인증/identity/이전 → 활동·대표 → PostgreSQL 경쟁/권한 검증 → OpenAPI/SHA 인계 순으로 진행한다. commit/push/통합·운영 배포는 이번 지시의 승인 범위로 확대하지 않는다.

## 2026-10-14 Flutter 회신 반영과 잔여 정의

근거: [Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159759288). 경로/UUID/dedup/버전/상한은 소비 가능. 등록 정책은 호환 가능하며 동일 owner 단순 재인증의 유효 설정 보존을 확인했다. **누락 대표 cooldown 우회는 도입하지 않는다.** 파서 근거: siblings ServerName/CharacterName/CharacterClassName string, CharacterLevel int, ItemAvgLevel nullable string, CombatPower는 ArmoryProfile nullable string. 6부위 Type은 현재 구현과 일치하지만 기존 Flutter 코드 파서 정보이며 실 provider 보장/해제 표현/영속 ID/전체성 증거는 아니다. 서버 key 준비 담당/가능 시점 미확인.

다음 정의는 후속 제안이며 앞선 충돌하는 설명을 대체한다. Flutter 소비 회신과 provider 보류 정책이 필요하다.

- 캐릭터 GET는 paginated characters와 **페이지 독립 전체 settings**를 분리한다. settings는 전체 선택ID(최대200), 대표, configuration_state, settings_version/ownership_revision, next_change_at, selection_complete=true 및 ineligible_character_ids를 포함한다. 미인증/ownership_lost는 자신의 자격 없는 상태·선택[]/대표null이며 타인 설정을 노출하지 않는다.
- roster_revision에 cursor를 바인딩하고 변경 시409 CURSOR_STALE. Flutter는 같은 revision 모든 페이지+전체settings를 읽은 뒤 draft/save. PUT에 expected_roster_revision 추가 제안. 일부 페이지를 전체 선택으로 교체하는 실수를 서버가 추론할 수 없다는 한계를 명시한다.
- dedup scope actor+operation, hash에 method/대상path/query/body 의미를 포함. 같은 key 다른 대상/내용409 IDEMPOTENCY_CONFLICT, 처리중409 REQUEST_IN_PROGRESS+Retry-After2. replay 전 session/resource 권한 재검증. 과거 성공 result와 현재 소유/설정을 분리하며 GET이 현재 상태 기준. lease crash 복구/rollback/upstream 장애 처리 후 재시도를 설계·검증한다. 24시간 결과+24시간 tombstone,48시간후 기억 보장 없음. 입력/권한 오류는 성공 dedup으로 저장하지 않는다.
- 응답 유실: register/patch/delete/settings는 동일 key 및 GET, start 동일 key로challenge ID 복구, confirm/cancel은 challenge GET와 내 계정 GET. TTL 뒤 자동confirm/재시작 없음.
- confirmed/suspect/missing, summary_fetched_at/last_confirmed_at/requires_refresh를 분리. suspect/missing은 새 활동 저장/사용 부적격이며 기존ID/선택 이력 유지, 영향 있으면 needs_reconfiguration. 두 번 누락은 삭제/전체성 증거가 아님. 실제 전체성 판단 근거 확인 전 live roster 감소의 자동missing/소유권 이전 확정은 보류한다. 같은 관찰키 복귀는 기존ID 재사용, 이름변경 자동병합 없음.
- preview TTL30분+청소유예1시간, challenge10분/종료baseline24시간, 최종challenge 상태/result24시간, dedup24+24시간, audit90일. 청소 지연은 권한 연장 아님. 현재 동시2는 프로세스 단위, 전체80/min/actor 제한은 PostgreSQL 공통 bucket 구현안이며 실제quota에 맞춰 축소. rate-limit Retry-After는 실제 남은 대기초.
- Backend가 안전한 key 준비 후 sanitized 실provider 근거를 확보한다. Flutter가 이미 없다고 밝힌 실제 fixture/전체성 근거를 확보한 것으로 가정하지 않는다. 수동 장비 조작은 사용자 공동 인수.

최신 기준: [A/B·경계 보완 수용 회신](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616). 아래 후속 제안의 소비 가능 회신은 확보했다. 페이지 간 세 version/revision 비교, DELETE 성공 replay, lease/crash 재시도 조건을 구현 설계에 반영한다. configuration_state와 ownership_lost는 별도 상태로 분리한다. provider 실증 대기는 합의된 API/DB 자동 검증을 막지 않는다.
