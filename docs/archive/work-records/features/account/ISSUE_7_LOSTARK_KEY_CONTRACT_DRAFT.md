> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [api-keys](../../../../features/login-account/api-keys/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 회원별 Lost Ark API 키 계약 제안

2026-10-15. [Issue #7](https://github.com/heo0328/lostparty-backend/issues/7)의 확정 요구에 대한 Backend 최소 계약 **제안**이다. [Flutter 수용·구현 요청](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172158382)을 확인했으며 이 문서의 제안을 구현 기준으로 합의했다. 원본 OpenAPI·기능·additive migration에 반영했다. 현재 `feat/member-settings`에서 구현하고 #6의 미커밋 인수 기록을 보존한다.

## API

경로는 `/v1/me/lostark-api-key`. 모든 요청은 앱 Bearer로 본인 회원/세션을 검증하며 성공/오류 모두 no-store. body에 user_id를 받지 않는다. 앱 인증 JWT는 Authorization, Lost Ark JWT는 PUT body로 분리한다.

| Method | 입력 | 성공 |
|---|---|---|
| GET | body/query 없음 | 200 metadata |
| PUT | UUIDv4 Idempotency-Key, `{token:string,expected_version:integer>=1}` | 200 metadata |
| DELETE | UUIDv4 Idempotency-Key, `?expected_version=integer>=1`, body 없음 | 200 metadata |

metadata는 필수 3필드만 반환한다: `{configured:boolean,version:integer>=1,updated_at:UTC string|null}`. 초기 상태는 false/1/null이며 GET은 행 생성·복호화·외부 호출을 하지 않는다. updated_at은 마지막 등록/교체/삭제 시각이며 외부 검증 시각이 아니다. 원문·마스킹된 일부 토큰·fingerprint·암호화 key_id·외부 claims는 응답하지 않는다. 기존 회원/설정/캐릭터 DTO를 변경하지 않는다.

PUT token은 엄격 string, ASCII compact JWT의 비어 있지 않은 base64url 3구간, 최대 16KiB, 공백/개행/`Bearer ` 접두사 불가. expected_version은 bool/string 아닌 엄격 정수. 추가 필드·null·알 수 없는/중복 query를 거절한다. 입력을 자동 trim하거나 변형하지 않는다. 이 형식 검사로 서명·발급처·유효성을 보증하지 않는다.

**등록 시 Lost Ark 호출 및 JWT claims/exp 해석은 하지 않는다.** 캐릭터 입력 없이 임의 테스트 캐릭터를 조회하지 않으며 공식 키 검증 전용 API가 확인되지 않은 상태에서 검증 API를 가정하지 않는다. 200/configured=true는 암호화 저장 완료일 뿐 유효한 키라는 뜻이 아니다. 폐기되거나 사용할 수 없는 키도 형식이 맞으면 저장될 수 있고 실제 외부 요청의 401/403을 LOSTARK_KEY_REJECTED로 안내한다. 앱은 “유효성 검증 완료”라고 표시하지 않는다. 이후 별도 검증 UX/API가 필요하면 독립 합의한다. [공식 안내](https://developer-lostark.game.onstove.com/getting-started)는 발급 키가 보안상 폐기 또는 client 삭제 전까지 무기한 유효하다고 설명하므로 앱 JWT처럼 주기적 만료/refresh를 가정하지 않는다. 임의 exp claim 해석을 공급자 서명 검증으로 취급하지 않는다.

첫 PUT은 version2, 모든 새 PUT 명령은 같은 token이라도 명시 교체로 version+1 및 updated_at 갱신한다. DELETE는 현재 등록 상태를 false로 바꾸고 version+1/updated_at 갱신, ciphertext/nonce/key_id/fingerprint를 제거한다. 미등록 DELETE는 no-op으로 version/updated_at 유지한다. stale expected_version은 같은 값/미등록 삭제에도 409 REVISION_CONFLICT. 삭제 후 metadata/version 행을 남겨 재등록 시 버전이 초기화되지 않게 한다. 로그아웃·새 세션·새 기기 로그인은 키를 삭제하지 않는다. 키 삭제는 캐릭터/원정대/회원 삭제가 아니다.

## 오류와 멱등

기존 `{error:{code,message,request_id}}` 형식과 앱 인증 400/401/403/409/429/503 규칙을 재사용한다. 검증 오류의 input/body/원문을 반환하지 않는다.

| 상태 | code | 의미·Flutter 처리 |
|---|---|---|
| 400 | INVALID_REQUEST | 키 형식·DTO·query 오류, 원문 미반환 |
| 409 | LOSTARK_KEY_NOT_CONFIGURED | 외부 조회가 필요한 명령의 회원 키 없음, 명시 등록 안내 |
| 409 | LOSTARK_KEY_REJECTED | Lost Ark 401/403, 만료/폐기/잘못된 키를 구분 확정하지 않음. 교체 안내, 앱 로그아웃 금지 |
| 409 | LOSTARK_KEY_CHANGED | 요청 중 키 등록/교체/삭제, 결과 미반영. 현재 키 상태 GET 후 새 명령/new key |
| 503 | LOSTARK_KEY_UNAVAILABLE | 암호화 설정 누락/키 식별 불가/복호화 또는 무결성 실패, 공용 fallback 없음 |
| 429 | RATE_LIMITED | 서버의 키별 호출 예산, Retry-After 유지 |
| 503 | UPSTREAM_RATE_LIMITED | 외부 429, 재시도 가능한 외부 제한. 자동 즉시 재시도 없음 |
| 503 | UPSTREAM_UNAVAILABLE | 외부 네트워크/5xx 등, 기존 세부 허용 reason 유지 |

Lost Ark 401/403을 앱 HTTP401로 전환하지 않는다. 앱 Bearer/세션 오류에만 HTTP401을 사용한다. 키 오류가 있어도 저장자료 GET은 계속 가능하다. metadata GET은 configured=true를 외부 유효 상태로 확장하지 않는다.

PUT/DELETE는 기존 UUIDv4 멱등 lease30초·완료 응답24시간·tombstone24시간·generation fencing을 재사용한다. 같은 명령/key는 원래 성공 metadata replay, 현재 값 확인은 GET. 과거 PUT replay는 삭제/새 교체를 다시 적용하지 않는다. replay에도 현재 앱 회원/세션 검증. 진행중 REQUEST_IN_PROGRESS/Retry-After2, 다른 body 같은 key IDEMPOTENCY_CONFLICT, 보관기한 후 IDEMPOTENCY_EXPIRED. version 충돌은 GET→사용자 새 결정→새 key이며 자동 덮어쓰기하지 않는다.

PUT 멱등 digest는 원문을 일반 reserve payload에 넣는 대신 전용 HMAC-SHA256으로 만든 token fingerprint와 expected_version·target의 정규화 metadata만 사용한다. DB RequestResult에는 원문/암호문이 아닌 digest와 원문 없는 성공 metadata만 보관한다. fingerprint는 외부 비공개. HMAC에 `credential-fingerprint-v1` 용도 구분을 넣고 동일 토큰 비교에 쓰며 인증 암호화 키와 별도 비밀을 사용한다. 교체마다 무작위 ciphertext가 달라도 동일 key/body 비교가 안정적이어야 한다.

## 암호화 저장·서버 설정

기존 `cryptography==50.0.2`의 AESGCM을 사용한다. AES-256-GCM, 매 암호화마다 새 CSPRNG 12-byte nonce, AAD는 정규화한 format version/user_id/credential version/key_id. 다른 회원 행이나 버전으로 암호문을 옮기면 복호화가 실패한다. DB는 회원 PK/FK, nullable ciphertext/nonce/key_id/fingerprint, 단조증가 credential version, updated_at을 가진 최소 1테이블을 추가한다. 미등록 행은 비밀 필드 모두 null. 키 material을 DB나 일반 회원 JSON에 두지 않는다.

기존 `/run/secrets` 파일 방식에 별도 `lostark-credential.key`(32-byte)와 `lostark-fingerprint.key`(독립 32-byte), 비밀이 아닌 `LOSTARK_CREDENTIAL_KEY_ID`를 추가하는 안이다. 앱 signing/recovery key와 재사용하지 않는다. 구 암호화 key_id는 제한된 식별자로만 과거 키 파일을 선택하며 외부 임의 경로를 허용하지 않는다. 암호화 키 교체 시 구키 보존과 기존 행 재암호화가 필요하고 HMAC 키 교체는 quota/멱등 fingerprint에 영향을 주므로 별도 계획 없이 자동 회전하지 않는다. 서버 재시작 때 키를 새로 만들지 않는다. 키 파일은 DB와 별도로 복구 가능하게 관리한다.

문서에는 파일 생성/권한/마운트·존재/길이 검사 절차를 제공하되 실제 비밀을 요구하거나 출력하지 않는다. 이번 설계에서는 파일/환경값을 만들거나 변경하지 않는다. SQL parameter·HTTP body/header·예외 repr·provider 원본·진단에 token을 기록하지 않는다. 기존 오류 handler의 input 제외 정책을 유지하고 secret DTO repr/SQL parameter 로깅도 검증한다. DB/암호화 오류를 그대로 로그에 출력하지 않는다. 삭제는 활성 행의 비밀 제거이며 기존 DB 백업까지 즉시 지워진다는 보장은 하지 않는다.

AES-GCM 근거: [cryptography 공식 문서](https://cryptography.io/en/latest/hazmat/primitives/aead/)의 인증 암호화/AAD·nonce 재사용 금지. 구현 시 저장 ciphertext 길이와 nonce/AAD 조건을 격리 검증한다.

## 외부 호출·캐시·진행 결과

preview/siblings, 등록, 원정대 refresh, 장비 proof start/confirm, 전투력 profile의 **전체 REST 호출 경로**에 인증된 회원의 credential snapshot을 주입한다. 환경 LOSTARK_API_TOKEN을 읽는 REST 경로를 제거한다. 캐시 hit라도 외부 조회 명령은 현재 키 등록과 복호화 가능 여부를 먼저 확인한다. 사용자 추가 결정에 따라 diagnostic CLI도 제거한 공용 환경 키를 자동으로 사용하지 않도록 전환한다. 필요한 수동 진단은 명시적인 로컬 비밀 입력으로 분리하고 입력/원문을 출력하지 않는다.

- 기존 name-only PreviewCache/FetchLease를 `(user_id,credential_version,character_name)`으로 분리한다. 다른 회원 또는 다른 키 버전의 조회에 합류하지 않는다. 기존 공용 캐시 행은 개인 키 캐시 hit로 사용하지 않고 삭제/초기화 없이 별도 신규 구조에서 전환한다.
- power cache의 정상 과거 값/fetched_at은 저장자료 GET 표시용으로 보존한다. 조회 재사용 eligibility와 진행 lease에 credential version을 추가한다. 새 키 버전에서는 기존 success/failure/제한 캐시를 fresh hit로 인정하지 않는다. 기존 숫자·시각을 지우거나 키 삭제를 캐릭터 삭제로 해석하지 않는다. 과거 성공 관찰과 현재 키 유효성은 별개다.
- 외부 호출 전 회원/세션과 credential version을 재확인한다. 네트워크 동안 DB lock을 유지하지 않는다. 실제 transport 시작과 키 변경의 극소 race 및 이미 전송된 HTTP를 취소할 수 없다는 한계를 인정한다. 삭제 커밋 이후 새 명령은 이전 키를 읽거나 시작하지 않는다.
- cache/lease 완료, preview 반환 전, 원정대/장비/전투력·멱등 성공 반영 transaction에서 현재 credential version과 회원/세션을 재검증한다. 키 교체/삭제가 먼저 커밋되면 이전 결과·실패 상태를 캐시/업무 자료에 반영하지 않고 409 LOSTARK_KEY_CHANGED로 끝낸다. 원자적 batch 내 이미 수집한 값도 모두 미반영, 기존 저장값 유지. 성공 커밋이 먼저였다면 그 성공은 유효하다.
- credential snapshot version과 장비 challenge 생성 키 버전을 구분한다. pending 장비 challenge의 baseline은 원문 키를 포함하지 않으며 다음 confirm은 현재 키로 조회한다. confirm 도중 교체된 결과만 막고 기존 장비 proof 보류 정책은 유지한다.
- worker는 현재처럼 DB write 없이 결과만 반환한다. 기한 뒤 worker 결과 폐기, lease 해제는 회원/버전/generation이 일치할 때만 수행해 새 키 요청을 해제하지 않는다.
- 이미 완료한 외부 명령의 동일 key replay는 과거 성공 반환이고 외부 호출·키 복호화 없음. 새 요청은 현재 키 필요. 사용자 화면 최신 상태는 GET으로 확인한다. 키 변경 실패로 성공하지 않은 기존 명령은 새 명령/new key로 진행한다.

## 호출 제한·부분 결과

[Lost Ark 공식 안내](https://developer-lostark.game.onstove.com/getting-started)는 client당 분당100회다. 서버 정책은 token HMAC fingerprint별 분당80회 DB 공유 예산으로 전환한다. 같은 원문 token을 다른 회원/새버전에 등록해도 같은 예산을 공유하고 삭제/재등록으로 분당 예산을 초기화하지 않는다. 요청 자료·캐시·조회 합류는 여전히 회원별이며 quota만 같은 token 기준이다.

다른 JWT가 같은 발급 client에 속하는지 검증 없이 확정할 수 없으며, 앱 로컬 직접 호출도 서버에서 집계할 수 없다. 따라서 fingerprint별80회가 provider 한도 준수를 보장한다는 표현은 하지 않는다. 외부429를 처리하고, 추후 검증 가능한 client 식별 정책은 별도 검토한다. 전 회원 공통 provider-global 80/min은 제거하되 기존 transport 동시2는 서버 자원 제한으로 유지한다. 이를 회원별 동시2나 처리량 보장으로 표현하지 않는다.

기존 전투력 대상1700·입력20명·batch20초/Flutter30초·성공30분/실패10초·부분 결과·재시도 금지를 유지한다. 명령 진입 키 미등록/복호화 실패는 top-level 오류. 키 변경은 최종409로 batch 미반영. 외부조회 중 key 거절은 해당 item `failed/LOSTARK_KEY_REJECTED`, 이후 미시작 item은 `deferred/LOSTARK_KEY_REJECTED`; 이미 진행중인 호출은 정리하되 성공 결과는 최종 키 버전이 같을 때 기존 부분 결과 규칙으로 반영 가능하다. 외부429는 item failed/UPSTREAM_RATE_LIMITED·미시작 deferred/UPSTREAM_RATE_LIMITED, 서버 quota 부족은 기존 deferred/RATE_LIMITED. 원정대/proof 단건 경로는 오류표의 top-level 상태를 사용한다. power_reason/reason string의 새 허용 code를 정확히 계약에 명시한다.

## 구현·검증 단계와 협업 경계

1. Flutter가 DTO/DELETE200·query/version·저장 성공과 미검증 구분·오류/멱등·캐시/키 변경 처리를 검토한다. 합의 후 원본 OpenAPI에 새 API/정책/기존 외부조회 오류 의미를 추가한다.
2. 전용 credential 모듈·additive migration·암호화 설정 절차·HMAC 멱등, member/version별 캐시/lease 및 모든 호출 전환을 한 테스트 가능한 구간으로 구현한다. 저장만 구현하고 완료로 인계하지 않는다.
3. 격리 DB/mock provider로 암호문/다른회원AAD·nonce·no plaintext, 두 회원 각각 자기 키, 동일 토큰 quota 공유·서로 다른 token 예산 분리, 미등록 fallback0, 전체 호출 경로·교체/삭제 중 늦은 결과, 부분 실패/만료 거절, replay/버전/로그아웃/새세션·일반GET 보존을 검증한다. 외부 키 만료는 provider 거절 mock이며 실키 서명/만료 검증 완료로 보고하지 않는다.
4. 암호화 설정 준비는 비밀값 없이 존재 여부로 확인한다. 서버 설정 미준비만으로 독립적인 격리 구현/검증을 보류하지 않는다. 로컬적용은 기존 자료 보존 additive migration/계약 비교로 확인한다.
5. 검증된 작업 구간 commit/push·원격 확인 후 같은 Issue에 실제 SHA/branch/push/dev 여부·자동/실미확인을 인계한다. Flutter는 새 키 등록/교체/삭제와 서버 호출 연결을 검증하고 결과를 회신한다. 원문 키/민감한 원본 응답을 요청하지 않는다.

전체 Armory 자동 빌드/역할 Snapshot 저장, 로컬 직접 조회 삭제/자동 서버 전환, Firebase 자료이관·장비 보류 해제·배포·Issue 종료는 제외다. 계약 수용 후 Backend 구현·격리검증·로컬 적용을 완료했다. [실행/인계 상태](ISSUE_7_DEVELOPMENT.md)를 기준으로 확인하며 Flutter 적용·실provider 인수는 별도다.

## 계약 수용 후 추가 결정 — 공용 테스트 JWT 제거

[Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172158382)에 계약 수용과 Backend 구현 진행 요청, 사용자의 공용 테스트 키 제거 승인이 기록되어 있다. 구현 전환 시 실제 `.env`/Compose 등 주입 원천과 실행 API 환경에서 공용 Lost Ark JWT를 제거하고 해당 API 서비스만 필요한 재시작/재생성을 한다. 값이나 환경파일 본문은 출력하지 않으며 제거/반영 여부만 검증한다. 기존 공용 키를 회원 credential로 자동 등록하지 않는다. 사용자는 Flutter 연결 후 직접 개인 키를 등록한다. 발급 client/키 자체의 폐기, 인증·서명·암호화 키 삭제, 다른 서비스 변경, DB 초기화는 포함하지 않는다.

미등록 회원의 새 외부 조회는 기존 공용 캐시가 있어도 LOSTARK_KEY_NOT_CONFIGURED이며, 저장자료 GET은 유지한다. 로컬 키 입력 UX는 Flutter/사용자 별도 협의지만 Backend 구현의 대기 조건이 아니다. 다음 단계는 합의 계약 구현·격리 검증·공용 설정 제거/로컬 반영·인계용 commit/push 후 정확한 OpenAPI SHA 게시다. Backend 구현 단계에서 공용 키 제거·API 재생성까지 수행했다. 단계별 실제 결과는 실행 안내에 기록했다.
