# Issue #2 후속 계약 초안

**합의 전·미구현 문서**입니다. 실제 계약 원본 `openapi/openapi.yaml`은 `/health`만 유지합니다. 이 초안은 Flutter 회신의 오류·만료·반복 로그아웃 의미를 보완하며, 인증 방식·refresh 복구 세부 정책·운영 정책의 최종 승인을 대신하지 않습니다. 로그인 TTL은 사용자 확정값이며 refresh는 제한된 재시도 복구안을 먼저 설계하기로 했습니다.

근거: [Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6147579206), [기존 모델·인증 제안](ISSUE_2_GOOGLE_AUTH_PROPOSAL.md).

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
| 401 REFRESH_REUSED | 이미 소비된 hash 재제출. 제한된 재시도 복구 조건 밖의 replay는 해당 family 폐기하는 후보안 | 복구 조건에 해당하면 동일 결과 수신, 조건 밖이면 로그인 안내. 세부 조건은 복구 설계 합의 필요 |
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

## 개발 접속·미확정 사항

현재 Compose 확인 결과 API·DB는 healthy, API는 **127.0.0.1:8000**에만 바인딩되어 있습니다. WSL 내부 `/health` 주소는 `http://127.0.0.1:8000/health`입니다. 조회된 WSL eth0 주소는 `172.29.72.78`이지만 이 주소로 API가 공개된 상태는 아니며 재시작 시 달라질 수 있습니다.

Android 실기기·에뮬레이터의 접속 주소는 아직 검증하지 않았습니다. 후보는 Windows에서 adb reverse와 WSL 루프백 전달을 확인하거나, 별도 승인된 개발 HTTPS 터널을 구성하는 방식입니다. 실제 접속 성공 전에 주소를 확정해서 인계하지 않습니다. 현재 서버는 HTTP이며 Google 증거·credential을 실기기에서 전송할 환경은 별도 HTTPS 접속 구성 검증이 필요합니다. Windows 호스트·adb·방화벽·포트 전달은 이번 작업에서 변경하지 않았습니다.

필요한 입력:
1. Flutter가 거래별 nonce를 전달할 구현 선택과 실기기 claim 검증. 반복 initialize/nonce 재사용 우회는 없음.
2. 운영자가 확인한 Android/Web 공개 client ID, 서명 fingerprint 등록 상태, consent screen 설정. 비밀자료는 Issue에 첨부하지 않음.
3. TTL과 refresh 복구 60초·추가 2회는 사용자 확정 완료. 저장 방식·오류 DTO와 Flutter 구현 합의가 필요.
4. 실기기 연결 방식·개발 HTTPS 주소. 운영 HTTPS 도메인·Caddy는 아직 구성하지 않음.
5. 탈퇴·재가입·보관·약관 URL/정책. 이번 1차 초안에서 탈퇴 API와 삭제 관련 상태는 제외하고 배포 전 의존성으로 유지.

이 입력을 기다리는 동안 DB/API를 미합의 정책으로 구현하지 않습니다. 계약 초안 검토와 확정 정책에 의존하지 않는 조사·검증 준비는 계속할 수 있습니다.
