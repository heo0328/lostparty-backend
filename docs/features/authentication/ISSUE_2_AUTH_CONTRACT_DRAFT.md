# Issue #2 최종 계약 검토안

현재 상태: 합의된 6개 인증 API와 migration 구현 및 격리 PostgreSQL 자동 검증 완료. 실제 원본은 `openapi/openapi.yaml`이며, 아래 기획 당시의 미구현 설명은 설계 이력입니다. 최신 실행·미검증 범위는 [인증 개발 안내](AUTH_DEVELOPMENT.md)를 참고합니다.

**계약 합의 완료·구현 반영 문서**입니다. [Flutter 최종 동의](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149615842)를 근거로 [구현 계획](ISSUE_2_IMPLEMENTATION_PLAN.md)을 진행합니다. 실제 계약 원본 `openapi/openapi.yaml`에는 `/health`와 합의된 6개 인증 API가 있습니다. 이 초안은 Flutter 회신의 오류·만료·반복 로그아웃 의미를 보완하며, 인증 방식·refresh 복구 세부 정책·운영 정책의 최종 승인을 대신하지 않습니다. 로그인 TTL은 사용자 확정값이며 refresh는 제한된 재시도 복구안을 먼저 설계하기로 했습니다.

근거: [Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149284949), [기존 모델·인증 제안](ISSUE_2_GOOGLE_AUTH_PROPOSAL.md).

## 공통 DTO 규칙

- 경로 `/v1`, 필드 snake_case, UUID는 문자열, 시각은 UTC RFC3339 `Z` 표기.
- 아래 표의 필드는 모두 required이며 null을 허용하지 않습니다. optional profile, lastSeen, deleted/deletion_pending 상태, 임의 actor/role 입력은 없습니다.
- 요청의 알 수 없는 필드는 거절하고 입력 오류는 400/INVALID_REQUEST로 처리하는 후보안입니다. token·secret은 request body로만 받고 URL·로그에 남기지 않습니다.
- token은 opaque credential로 취급하며 Flutter가 claims를 권한 근거로 해석하지 않습니다. 일반 API Bearer는 자체 access token만 허용합니다.
- 모든 응답은 `Cache-Control: no-store`. 검증 대상 회원·session은 서버 DB로 조회합니다.
- 서버가 발급한 만료 시각이 최종 기준입니다. 클라이언트는 로컬 시계만으로 서버 허용을 단정하지 않습니다.

### 객체

| 객체 | 필드와 의미 |
|---|---|
| User | `id`: UUID, `status`: active/disabled 후보, `created_at`: 시각. Google subject·email·name·avatar·운영 권한 제외 |
| Session | `id`: UUID, `remember_me`: boolean, `created_at`: 시각, `absolute_expires_at`: 시각, `idle_expires_at`: 시각, `expires_at`: 두 만료 시각의 최솟값 |
| Tokens | `token_type`: 상수 Bearer, `access_token`: 비어 있지 않은 문자열, `access_expires_at`: 시각, `refresh_token`: 비어 있지 않은 문자열, `refresh_expires_at`: 시각, `session`: Session |
| LoginResult | Tokens의 필드 + `user`: User + `is_new_user`: boolean |
| ErrorResponse | `error`: {`code`: 문자열, `message`: 공개 안전 메시지, `request_id`: UUID}. message는 앱 분기 기준이 아님 |

## API 요청·응답 후보

| API | 요청 | 성공 |
|---|---|---|
| POST /v1/auth/google/challenges | `{transaction_secret_hash: string}` | 201 `{transaction_id: UUID, nonce: string, expires_at: timestamp}` |
| POST /v1/auth/google | `{transaction_id: UUID, transaction_secret: string, google_id_token: string, remember_me: boolean}` | 200 LoginResult |
| GET /v1/me | Authorization: Bearer access | 200 User |
| GET /v1/auth/session | Authorization: Bearer access | 200 Session |
| POST /v1/auth/refresh | `{refresh_token: string, refresh_request_id: string}` | 200 Tokens. 제한된 재시도는 복구 설계 참조 |
| POST /v1/auth/logout | `{refresh_token: string}` | 204, 응답 본문 없음 |

transaction secret은 32바이트 난수를 base64url padding 없이 표현합니다. hash는 그 ASCII 문자열의 SHA-256을 소문자 hex64자로 표현합니다. 서버 nonce도 32바이트 난수를 base64url padding 없이 표현하며 Google에 전달한 문자열과 claim을 완전 일치로 검증합니다. 임의 변환이나 클라이언트 생성 nonce로 대체하지 않습니다. challenge TTL 5분은 여전히 제안값입니다.

nonce는 challenge마다 새로 발급합니다. Google 증거의 서명·issuer·audience·만료와 transaction의 일치를 검증하고 DB에서 동일 transaction의 소비를 직렬화합니다. 소비된 transaction으로 새 session을 발급하지 않습니다. 새 transaction을 사용하는 동일 Google identity의 로그인은 허용하며 동일 회원을 반환합니다.

Google proof 검증 실패·provider 장애·입력 거절 시 회원을 만들지 않습니다. 서버가 commit 전에 통신 취소를 인지하면 rollback하지만 commit 이후 앱이 응답 수신을 중단한 경우까지 회원 미생성을 보장하지 않습니다. Google 인증 UI 취소 시에는 교환 API를 호출하지 않습니다.

### 만료 계산 후보

**사용자 확정 초기 TTL:** Access 10분, remember=true에서 절대 30일/idle 7일, false에서 절대 12시간/idle 2시간입니다. 기간은 향후 설정으로 관리합니다.

- `absolute_expires_at`은 session 생성 시 고정하고 refresh로 연장하지 않습니다.
- `idle_expires_at`은 로그인 및 성공한 refresh 시각에서 idle TTL을 더하고 absolute 시각으로 제한합니다. `/me` 조회·화면 전환·백그라운드 이동은 연장하지 않습니다.
- `session.expires_at = min(absolute_expires_at, idle_expires_at)`.
- `refresh_expires_at = session.expires_at`, `access_expires_at = min(발급 시각 + access TTL, session.expires_at)`.
- 현재 시각이 만료 시각과 같거나 이후면 만료입니다. Google/JWT 시계 오차 허용치는 별도 구현 설정으로 합의하고 session DB 만료를 연장하는 데 사용하지 않습니다.
- 계정 정지·session 폐기는 만료 시각보다 우선합니다. access JWT가 남아 있어도 서버 상태 검사로 새 요청을 거절합니다.
- remember=false도 앱 실행 중 refresh 가능하며 재실행 시 자동 Google 인증을 하지 않습니다. remember=true도 폐기된 session을 silent Google login으로 자동 재생성하지 않습니다.

### refresh 실패와 앱 처리

| HTTP / code | 구분 | Flutter 처리 |
|---|---|---|
| 401 REFRESH_INVALID | 비어 있지 않지만 DB에 해당 hash가 없는 credential, 또는 보관 종료 후 더 이상 식별 불가 | 현재 credential 정리, 로그인 안내 |
| 401 REFRESH_EXPIRED | 식별 가능한 credential/session의 absolute 또는 idle 만료 | 현재 credential 정리, 로그인 안내 |
| 401 SESSION_REVOKED | 유효 hash를 식별했지만 session이 로그아웃·관리자 조치 등으로 폐기 | 현재 credential 정리; Google 자동 재로그인 금지 |
| 401 REFRESH_REUSED | 이미 소비된 hash 재제출. 제한된 재시도 복구 조건 밖의 replay는 해당 family 폐기하는 후보안 | 복구 조건에 해당하면 동일 결과 수신, 조건 밖이면 로그인 안내. 동일 요청의 복구 종료는 409로 구분하며 다른 request ID의 소비 token 제출만 401/REFRESH_REUSED |
| 403 ACCOUNT_DISABLED | 회원이 정지 상태 | 갱신 반복 금지, 차단 상태 안내 |
| 429 RATE_LIMITED | 서버 요청 제한 | Retry-After를 참고하되 refresh 재제출 여부는 최종 정책에 따름 |
| 503 SERVICE_UNAVAILABLE / 네트워크 오류 | 서버·네트워크 장애, refresh 소비commit 여부를 알 수 없음 | 인증 실패로 단정하지 않음. 같은 요청 ID와 같은 refresh로 정해진 복구 범위 내 재시도하는 설계 후보. 즉시 인증 실패로 처리하지 않음 |

입력 형태가 잘못되면 400/INVALID_REQUEST입니다. 별도 시점의 유효성과 폐기 여부가 함께 성립할 때 식별 가능한 정지 회원은 ACCOUNT_DISABLED, 폐기 session은 SESSION_REVOKED, 다음으로 만료, 다음으로 소비 여부를 판단하는 후보입니다. 로그인 proof는 서버 검증 후에만 계정 상태를 조회합니다. hash 식별이 불가능하면 다른 상태를 노출하지 않습니다.

인증 오류가 아닌 네트워크 장애에서는 앱 로컬 로그인 유지 선택을 끄거나 credential을 즉시 삭제하지 않습니다. 복구 경로는 [제한된 재시도 설계](ISSUE_2_REFRESH_RECOVERY.md)를 검토한 뒤 확정합니다. refresh single-flight는 Flutter 요구로 확인되었으며 동일 기기의 병렬 갱신을 막습니다.

무중단 응답 복구를 원할 경우 hash-only strict rotation과는 다른 설계가 필요합니다. 단순 grace 기간 동안 old token으로 서로 다른 후속 token을 여러 개 발급하는 방식은 채택하지 않습니다. 재시도 바인딩과 암호화된 단기 응답 보관 또는 sender-constrained 흐름을 별도 설계·합의해야 하며 현재 구현된 것으로 취급하지 않습니다.

### 로그아웃 반복 처리

- 식별 가능한 refresh hash로 해당 session만 폐기하고 204. access 만료여도 logout 가능.
- 소비된 old refresh도 보관 기간 내에는 동일 family를 식별해 logout 가능. 반복 요청은 204이며 다른 기기를 폐기하지 않음.
- 보관 기간은 **session 생성 시 정해진 absolute_expires_at까지** 제안합니다. 폐기·idle 만료 뒤에도 이 시각까지 credential hash와 session 폐기 자료를 보존합니다. 반복 확인이 탈퇴 시 보관 의무와 충돌하면 탈퇴 계약에서 재검토합니다.
- absolute 만료 이후 정리 대상으로 전환합니다. 동일 요청은 hash가 남아 있든 정리됐든 401/REFRESH_INVALID로 통일하여 204 반복 안전성 보장은 종료됩니다.
- malformed body는 400, 미존재 hash는 401/REFRESH_INVALID. 운영자가 임의로 정리한 데이터까지 반복 204를 보장하지 않음.

### 나머지 오류 후보

- 공통: 400 INVALID_REQUEST, 429 RATE_LIMITED(`Retry-After`: 초 단위 정수), 503 SERVICE_UNAVAILABLE.
- Google 교환: 400 AUTH_TRANSACTION_INVALID; 401 AUTH_TRANSACTION_EXPIRED / AUTH_TRANSACTION_CONSUMED / GOOGLE_PROOF_INVALID; 403 ACCOUNT_DISABLED; 503 AUTH_PROVIDER_UNAVAILABLE.
- `/me`, `/auth/session`: 401 ACCESS_INVALID / ACCESS_EXPIRED / SESSION_EXPIRED / SESSION_REVOKED; 403 ACCOUNT_DISABLED. access 만료 때만 보유 refresh를 이용한 갱신 후보이며 403/장애를 무조건 refresh로 처리하지 않음.
- 기존 `/health`의 응답은 위 신규 오류 형식으로 바꾸지 않음.

## 개발 접속과 완료 단계

사용자와 Flutter가 로컬 HTTP·Android 에뮬레이터 우선을 선택했습니다. Compose의 API는 호스트 `127.0.0.1:8000`에 유지합니다. Windows 호스트 후보는 `http://localhost:8000`, Android 에뮬레이터 후보는 `http://10.0.2.2:8000`이며 Windows→WSL 전달과 에뮬레이터 연결은 실제 검증 전입니다. WSL eth0 주소를 공개 API 주소로 인계하지 않습니다.

Flutter debug에서 필요한 로컬 주소만 HTTP를 허용합니다. release는 HTTPS를 사용하며 HTTP 전체 허용을 적용하지 않습니다. 실기기는 별도 연결 검증 대상으로 남기고 외부 터널·방화벽 공개를 임의로 구성하지 않습니다.

Google 프로젝트 `lost-party`, package `kr.co.heowork0921.lostparty`, server audience `574337852234-vdkvdobbq8es2rdpumc1icqt6ja3a3cr.apps.googleusercontent.com`를 사용합니다. native bridge의 거래별 nonce 전달 방향과 debug 서명 일치는 Flutter 인계로 확인했습니다. Backend Google 검증의 audience는 이 서버 설정값만 사용하고 요청에서 받은 audience/client ID로 바꾸지 않습니다. release 등록과 실제 token claim은 후속 검증입니다.

탈퇴·약관·재가입·운영 정지 절차는 별도 정책 작업입니다. `disabled` 상태에 대한 인증 거절은 구현하되 이번 범위에 운영자 정지 API를 추가하지 않습니다. 배포 전 정책 결정 의존성을 유지합니다.

## 인코딩과 검증 세부 정의

- transaction_secret, nonce, refresh_token, refresh_request_id: 각각 32바이트 난수의 canonical base64url, padding 없음, 43자. 허용 문자는 A-Z/a-z/0-9/_/-이며 디코드 후 32바이트와 재인코드 일치를 검사합니다.
- transaction_secret_hash: 전달된 secret의 ASCII 바이트를 SHA-256한 소문자 hex64자. raw 난수 바이트를 hash한 값과 혼용하지 않습니다.
- refresh_request_id도 ASCII SHA-256 digest로 DB에 저장합니다. error.request_id는 별도의 서버 진단 UUID이며 재시도 식별자와 다릅니다.
- Google ID token: JWT 문자열, 최대 16384자. access token도 최대 16384자. refresh/token/secret에 실제 값 예시를 첨부하지 않습니다.
- 요청은 strict 타입·extra 필드 금지. remember_me는 JSON boolean이며 문자열/숫자를 강제 변환하지 않습니다. User.status의 응답은 로그인 성공 시 active이며 disabled는 서버 계정 상태 값으로 보호 요청에서 403 처리합니다.
- challenge는 5분으로 Backend 기본안을 제시합니다. Google 증거 검증 시 서명·RS256·issuer 두 허용 표기·고정 audience·exp·iat·subject·nonce 검사. clock skew 30초는 Google 증거 검증에만 적용하고 DB 세션 만료와 자체 access exp에는 적용하지 않습니다.
- azp가 존재하면 등록된 client allowlist로 제한합니다. 아직 전사되지 않은 Android client ID가 실제 token의 azp로 나타나면 이를 추정해 허용하지 않고 공개 client ID 확인 후 반영합니다.
- 최초 가입/로그인 응답은 200으로 통일하고 is_new_user로 구분합니다. User와 session의 ID는 별개이며 원정대 권한이나 Firebase ID를 포함하지 않습니다.

## refresh 409와 상태 우선순위

인코딩 검증 → hash 식별 → 회원 정지 → session 폐기 → session 만료 → 사용 상태 및 request ID → 후속 generation 상태 → 복구 시간 → 복구 횟수 → 암호문 반환 순으로 판단합니다.

| 조건 | HTTP/code | 결과 |
|---|---|---|
| 소비 old token + 다른 request ID | 401 REFRESH_REUSED | 해당 session 폐기, 다른 기기는 유지 |
| 동일 요청 + 후속 token 이미 소비 | 409 REFRESH_RESULT_SUPERSEDED | 더 최신 credential을 덮어쓰지 않음 |
| 동일 요청 + 복구 시각 도달 | 409 REFRESH_RECOVERY_EXPIRED | 재발급 없음, 이 이유만으로 family 폐기하지 않음 |
| 동일 요청 + 추가 재전송 2회 사용 | 409 REFRESH_RECOVERY_LIMITED | 재발급 없음, 이 이유만으로 family 폐기하지 않음 |
| 동일 요청 + 모든 조건 유효 | 200 최초 Tokens | 동일 credential·동일 만료 재전송 |

네트워크/503는 계정 무효를 뜻하지 않습니다. 재시도는 동일 old token·request ID, 최대 3회 총 전송으로 제한합니다. 오류/뒤늦은 응답은 현재 session·generation·pending 작업과 일치할 때만 적용합니다. 이미 더 최신 credential을 받은 경우 오래된 작업의 409나 401로 새 상태를 지우지 않습니다. 정상 logout 또는 서버 폐기는 확인된 현재 상태에 적용합니다.

## 구현·검증 착수 기준

Backend의 계약 검토안 정리는 완료했습니다. Flutter가 DTO·인코딩·409·오류 처리와 DB 시간 계측 제약을 수용했습니다. 최종 합의는 확인했으며 구현 단계에서 코드·migration·실제 OpenAPI를 함께 반영합니다. 현재 실제 계약은 6개 인증 API를 포함하며 실제 Google·Flutter 적용 완료와는 구분합니다.

검증은 분리된 PostgreSQL에서 동시 가입/회전/rollback, mock Google 증거 실패, 실제 Google 서명·nonce, Windows→WSL 및 에뮬레이터 접속, Flutter 재시작·secure pending·늦은 응답 격리를 구분합니다. mock-only 통과를 실인증 성공으로 보고하지 않습니다.
