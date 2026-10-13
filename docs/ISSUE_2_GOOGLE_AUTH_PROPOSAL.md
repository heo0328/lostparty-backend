# Issue #2: Android Google 인증·회원·세션 제안

현재 상태: 합의된 6개 인증 API와 migration 구현 및 격리 PostgreSQL 자동 검증 완료. 실제 원본은 `openapi/openapi.yaml`이며, 아래 기획 당시의 미구현 설명은 설계 이력입니다. 최신 실행·미검증 범위는 [인증 개발 안내](AUTH_DEVELOPMENT.md)를 참고합니다.

상태: **초기 설계 이력 / 최종 합의·구현 완료**. 실제 계약은 `openapi/openapi.yaml`이며 최신 검증 상태는 인증 개발 안내를 참고합니다.

Flutter의 [회신](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6147579206)을 반영했습니다. 정확한 DTO·오류·만료 의미는 [후속 계약 초안](ISSUE_2_AUTH_CONTRACT_DRAFT.md)에 있습니다. TTL은 사용자 확정 완료이며 refresh는 [제한된 재시도 복구안](ISSUE_2_REFRESH_RECOVERY.md)을 먼저 설계합니다. 복구 세부 정책은 검토 전이며 탈퇴는 분리·보류합니다.

요청: https://github.com/heo0328/lostparty-backend/issues/2
Backend 조사 기준: `bfc51e4d9a8a5ced360247a8c60bf370f7ca84ad`.
Flutter 기준은 Issue가 제시한 `64b09bfb515ea5e81e798175b99d293a9a8a9a35`이며 Flutter 코드는 직접 조사하지 않았습니다. 본문에 확정된 사용자 요구를 우선합니다.

## 1. 유지할 요구

비로그인 앱 실행과 로컬 계정·캐릭터·빌드를 유지합니다. 익명 UID·회원·Player·회원 활동을 생성하지 않습니다. 공개 모집은 후속 공개 API로 분리합니다. Google 로그인은 앱 principal만 부여하고 원정대 소유권이나 운영 권한을 부여하지 않습니다.

최초 Google 인증은 회원 생성, 이후 동일 identity는 동일 회원 로그인입니다. 가입/로그인 화면 분리·별도 닉네임·비밀번호·첫 가입 동의 화면은 추가하지 않습니다. 로그인 성공 후 원래 화면으로 돌아가되 쓰기 작업을 자동 재실행하지 않습니다. Firebase 식별자를 수용하거나 이관하지 않고 로컬 자료도 삭제하지 않습니다.

## 2. 추천 인증 흐름과 선행 확인

**Android native Google ID-token 교환**으로 진행할 최종 초안입니다. [최신 Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149284949)에 따라 MethodChannel → Android Credential Manager의 Google 버튼 흐름에서 거래별 `GetSignInWithGoogleOption.setNonce`를 사용합니다. Flutter가 보고한 bridge 경계 테스트·Kotlin 컴파일 통과와 실제 Google nonce claim 검증은 구분합니다. 반복 initialize나 nonce 재사용을 사용하지 않습니다.

1. 앱이 무작위 transaction secret을 생성하고 SHA-256 digest만 challenge 요청에 전달합니다.
2. 서버는 회원과 무관한 5분짜리 인증 transaction과 무작위 nonce를 발급합니다. 이는 임시 사용자 ID가 아니며 로그인 취소 시 회원을 생성하지 않습니다. 만료 transaction은 정리합니다.
3. 앱은 Google 요청에 nonce와 등록된 server/web client ID를 설정하고 인증된 ID token을 얻습니다.
4. 앱은 transaction ID, secret, ID token, `remember_me`를 Backend에 전달합니다.
5. 서버는 transaction 유효성·secret digest·미소비 여부, Google 서명·허용 알고리즘·issuer·고정된 허용 audience·exp·시간 오차·nonce·subject를 확인합니다. `azp`가 있는 다중 audience 토큰은 승인된 client 정책으로 제한합니다. 공개키는 Google 공식 라이브러리로 검증하고 캐시·키 교체·외부 장애를 처리합니다. 앱이 보낸 email/subject/user ID/role을 믿지 않습니다.
6. 검증 후 한 DB transaction에서 challenge를 소비하고 identity·회원·session을 처리합니다. 중복 소비와 동시 가입은 DB 제약·잠금으로 직렬화합니다. 취소·무효 증거·외부 검증 장애·rollback 시 회원을 남기지 않습니다.

native ID-token 흐름에서는 OAuth redirect/callback, authorization code, PKCE와 브라우저 state를 사용하지 않습니다. 대신 서버 nonce와 transaction secret이 거래를 묶습니다. 앱 client secret도 필요하지 않습니다. 동일 Google 증거는 소비된 transaction에서 재발급하지 않으며 로그인 응답 유실 시 새 transaction으로 로그인합니다. 미전달 세션은 만료 또는 다음 로그인 시 정리할 정책을 적용합니다.

전달받은 개발 입력:
- Google 프로젝트 `lost-party`, Android package `kr.co.heowork0921.lostparty`
- Web/server client ID `574337852234-vdkvdobbq8es2rdpumc1icqt6ja3a3cr.apps.googleusercontent.com`
- debug 서명 등록 일치, 외부/프로덕션 상태는 Flutter·사용자 보고로 확인. release/Play 서명과 Google 실인증은 미검증
- 로컬 HTTP 서버·Android 에뮬레이터 우선. 외부 HTTPS 터널은 이번 개발 범위에서 제외
- 프로필·lastSeen 제외 수용. 약관 URL과 탈퇴 정책은 출시 전 후속 항목

## 3. 최소 데이터 모델

SQLAlchemy 2·Alembic 도입을 제안하며 모든 시각은 PostgreSQL `timestamptz`, 응답은 UTC RFC3339, ID는 UUID입니다. 아래 이름은 제안이며 migration은 아직 만들지 않습니다.

| 테이블 | 주요 항목과 제약 |
|---|---|
| users | id UUID PK, status(active/disabled 후보), created_at/updated_at/last_login_at. 삭제 관련 상태는 탈퇴 정책 합의 전 제외 |
| auth_identities | id UUID PK, user_id FK, provider, issuer, subject, linked_at. UNIQUE(provider, issuer, subject), Google issuer의 두 허용 표기는 검증 후 canonical 값으로 통일 |
| auth_transactions | id UUID PK, nonce digest UNIQUE, transaction-secret digest, expires_at, consumed_at. user_id 없음; 요청량 제한과 만료 정리 |
| auth_sessions | id UUID PK, user_id FK, remember_me, created_at, absolute_expires_at, idle_expires_at, revoked_at/reason. 한 session이 한 refresh family |
| refresh_credentials | id UUID PK, session_id FK, generation, token_hash UNIQUE, issued_at/expires_at, consumed_at, successor_id. UNIQUE(session_id, generation), 이미 소비된 hash를 family 만료까지 보존 |

session·challenge secret과 refresh credential은 고엔트로피 난수이며 DB에는 hash만 저장합니다. nonce는 증거의 hash와 비교합니다. raw credential과 Google 증거를 로그에 남기지 않습니다. profile email/name/avatar와 lastSeen은 1차 저장·반환에서 제외하고 lastLoginAt만 성공 시 갱신합니다. 이메일은 identity key로 사용하지 않습니다.

동시 첫 로그인은 identity UNIQUE 제약을 최종 기준으로 삼습니다. INSERT 충돌 시 회원 생성까지 해당 transaction을 rollback하고 이미 생성된 identity로 재시도합니다. orphan user를 commit하지 않습니다. 상태 변경과 session 발급도 회원 잠금 순서를 통일해 정지 직후 신규 세션 발급을 막습니다.

원정대 소유 관계는 후속 별도 테이블로 user 참조와 검증 상태·차수·대표 character를 관리합니다. 이번 로그인에 game account/character 테이블을 만들지 않습니다.

## 4. 세션 정책 제안

- Access: 서명된 JWT, 10분. sub=user UUID, sid=session UUID, iss/aud/exp/jti 검증. 알고리즘 allowlist와 키 교체 고려. 역할은 클라이언트 입력으로 받지 않음.
- 보호 API마다 user 상태와 sid 폐기를 DB에서 확인하여 로그아웃·정지 후 새 요청을 즉시 거절합니다. 이미 진행 중인 쓰기는 transaction에서 권한 상태를 다시 확인합니다.
- remember=true: session 절대 30일, idle 7일. remember=false: 절대 12시간, idle 2시간. refresh는 세션의 유효 기간을 넘지 않습니다. 이 기간은 사용자 확정 초기값입니다.
- 미선택도 현재 앱 실행 중 갱신은 허용하되 Flutter는 credential을 메모리에만 둡니다. 서버는 앱 종료를 알 수 없으므로 서버 세션은 만료까지 남을 수 있습니다. 회원 전역 로그인 유지 boolean은 두지 않습니다.
- 다중 기기 세션 허용, 로그아웃은 해당 sid만 폐기. 임의의 클라이언트 device ID를 인증 근거로 쓰지 않음.
- refresh는 session row 잠금 아래 1회 소비·회전. Flutter는 요청을 single-flight로 제한합니다.
- 사용자는 응답 유실 때 즉시 재로그인시키는 엄격 회전 대신 제한된 재시도 복구안을 먼저 설계하는 방향을 선택했습니다. 동일 요청에 동일 결과를 돌려주는 [복구 설계](ISSUE_2_REFRESH_RECOVERY.md)를 검토한 뒤 구현합니다. 단순 grace 기간에 서로 다른 후속 token을 발급하지 않습니다.
- hash만으로 후속 credential을 복원할 수 없으므로 암호화된 단기 응답 보관이 필요합니다. DB에는 raw credential을 저장하지 않고 암호화 응답·키 관리·보관 종료 처리를 별도 합의합니다.

## 5. API 계약 초안

기존 `/health`는 유지하고 신규 경로는 `/v1`을 제안합니다. 확정 전 OpenAPI에 추가하지 않습니다. credential 포함 응답은 `Cache-Control: no-store`, 인증은 자체 Bearer access만 사용합니다.

| API 후보 | 입력 / 성공 의미 |
|---|---|
| POST /v1/auth/google/challenges | transaction-secret SHA-256 digest → 201 transaction_id, nonce, expires_at |
| POST /v1/auth/google | transaction_id, transaction_secret, google_id_token, remember_me → 200 user{id,status}, is_new_user, session{id,expires_at}, access_token/access_expires_at, refresh_token/refresh_expires_at, token_type=Bearer |
| GET /v1/me | access Bearer → 200 본인 id/status/created_at. Google subject·hash·역할 내부 자료·원정대 데이터 제외 |
| GET /v1/auth/session | access Bearer → 200 본인 현재 session id/remember_me/만료 정보 |
| POST /v1/auth/refresh | refresh_token → 200 새 credential 쌍과 session 만료 정보 |
| POST /v1/auth/logout | refresh_token → 204 해당 session 폐기. 이미 폐기된 credential도 family 내 hash로 검증해 204, 알 수 없는 credential은 401. 폐기 hash의 보관 기간까지 반복 안전성 보장 |
| 회원 탈퇴(별도 보류) | 경로·상태·응답은 정책 합의 후 확정. 이번 1차 초안에는 DELETE /me를 포함하지 않음 |

공통 오류 후보: `{error:{code,message,request_id}}`. 클라이언트는 code로 분기하며 내부 예외·credential을 반환하지 않습니다.

| HTTP | code 후보와 앱 처리 |
|---|---|
| 400 | INVALID_REQUEST / AUTH_TRANSACTION_INVALID: 입력 수정 또는 새 로그인 transaction |
| 401 | GOOGLE_PROOF_INVALID / AUTH_TRANSACTION_EXPIRED / AUTH_TRANSACTION_CONSUMED: 새 Google 로그인 |
| 401 | ACCESS_EXPIRED: 유효 refresh로 갱신. SESSION_INVALID / REFRESH_REUSED: credential 정리 후 재로그인 |
| 403 | ACCOUNT_DISABLED / FORBIDDEN: 갱신으로 해결되지 않음. 삭제 관련 오류는 별도 보류 |
| 429 | RATE_LIMITED: Retry-After 이후 재시도, credential replay 정책 준수 |
| 503 | AUTH_PROVIDER_UNAVAILABLE / SERVICE_UNAVAILABLE: 잠시 후 새 로그인 가능, refresh는 제한된 복구 조건에 따라 재시도하는 설계 검토 중 |

Flutter의 기술적 기본안 회신을 반영해 신규 `/v1` 입력 검증은 공통 INVALID_REQUEST/400으로 제안합니다. `/health`는 변경하지 않습니다. 탈퇴 유예·보관·재가입·identity tombstone 및 미래 그룹장/활성 파티 관계가 미정이므로 탈퇴 API·삭제 관련 상태는 별도 합의 전 구현하지 않습니다. Google 계정 삭제·Firebase 삭제와 구분합니다.

약관은 로그인 화면의 안내·링크만으로 특정 동의가 증명됐다고 기록하지 않습니다. Google 제공자 동의를 서비스 약관 동의로 간주하지 않습니다. 정책 버전 기록이나 추가 동의가 필요한지 운영자가 결정한 뒤 가입 흐름에 반영하며, 이번 제안으로 법적 충족 여부를 단정하지 않습니다.

## 6. 구현·검증·인계 계획

합의 후 순서: DB 도구·분리된 테스트 PostgreSQL 구성 → 최소 migration → challenge/Google 검증 → 회원·session → refresh/logout/me → 합의된 탈퇴 → OpenAPI 비교·pytest. 개발 DB를 삭제하거나 초기화하지 않습니다.

pytest 대상: 잘못된 서명·issuer·audience·만료·nonce·transaction secret·consumed transaction, 취소/외부 실패/rollback 시 회원 미생성, PostgreSQL 동시 첫 로그인 user 1개, refresh 회전·동시·응답 유실·replay, 로그아웃·정지 후 거절, session 타인 접근·actor/role 위조, guest 회원/활동 미생성. mock 검증과 실제 Google 등록·서명 검증을 별도 보고합니다.

실기기 확인은 Flutter가 nonce 전달/claim, debug/release 로그인, 취소, 로그인 유지별 앱 재실행, 복귀 후 쓰기 미재실행, 메모리 credential 정리, single-flight refresh를 검증합니다. 클라이언트 작업 완료를 Backend 테스트만으로 선언하지 않습니다.

후속 분리: 공개 모집 allowlist/비공개 접근 거절, 원정대 proof 및 소유권·character API, Firebase principal을 새 user/session으로 전환하는 Flutter bootstrap/router/repository 작업. 기존 Firebase 파티/그룹 흐름의 자동 호환을 약속하지 않습니다.

## 7. 합의가 필요한 입력

1. native bridge 방향·Web client ID·debug 등록 확인 완료. 실제 claim과 release 등록은 후속 검증
2. native ID-token+server nonce 선택, `/v1` 경로·오류 형식. TTL은 사용자 확정 완료
3. 최종 DTO·오류·복구 저장 설계의 Flutter 확인. 60초·추가 2회와 single-flight·pending 보관 방향은 확인 완료
4. 최소 프로필·lastSeen 제외, 탈퇴/정지/재가입/보관 및 약관 정책

pytest·migration·신규 API 검증은 완료했으며 실제 Google 및 Android 공동 인수는 미실행입니다.

## 공식 근거

- Android nonce 및 server client ID: https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation
- Google ID-token 서명·issuer·audience·만료·subject 검증: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- refresh rotation과 reuse 탐지: https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14

공식 지원 사실과 본 프로젝트의 transaction·TTL·DB·오류 설계 제안은 구분합니다.
