# Issue #2 구현 계획

상태: **계약 기반 구현·자동 검증 완료 / 공동 실인증·게시 대기**. 아래는 구현 설계 근거이며 현재 실행 계획은 [NEXT_WORK](../../project/NEXT_WORK.md), 완료 이력은 [DEV_LOG](../../project/DEV_LOG.md)가 기준입니다. 실제 진행 결과는 [인증 개발 안내](AUTH_DEVELOPMENT.md)에 기록합니다.

## 기준과 범위

- 합의 근거: [Flutter 최종 동의](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149615842).
- 기준 Backend 커밋: `4ad30520f0afd52d1d5b6f27b103b83ebf1b1667`, 작업 브랜치 `feat/2-google-auth`.
- API/DTO: [계약 문서](ISSUE_2_AUTH_CONTRACT_DRAFT.md), 회전·암호화·복구: [복구 설계](ISSUE_2_REFRESH_RECOVERY.md).
- 포함: challenge, Google 가입·로그인, me, session, refresh, 현재 기기 logout의 6개 API와 최소 DB 모델·migration·자동 검증·계약 인계.
- 제외: 탈퇴·재가입 정책 구현, 운영자 API, Apple/Discord, 원정대 proof·파티·그룹, Firebase 이관·삭제·연결, Flutter 소스 수정, 외부 포트 공개·터널·운영 배포.
- 비로그인 실행에는 회원·UID·활동을 생성하지 않음. Google 로그인만으로 원정대 소유권·운영 권한을 부여하지 않음.

사용자 TTL과 복구 60초·추가 2회는 확정값입니다. 실제 Google nonce 확인·Android OAuth client ID 추가 입력은 공동 인수 조건이며 Backend mock/PostgreSQL 검증 착수를 막지 않습니다. 미등록 azp는 허용하지 않습니다.

## 모듈과 실행 구조

기능별 모듈형 모놀리스로 시작하며 불필요한 서비스 분리는 하지 않습니다.

```text
app/
  main.py                 앱 조립, 기존 /health, 오류 처리 등록
  core/
    config.py             환경 설정·키 참조·기간 검증
    errors.py             공개 오류와 request_id, 내부 로그 마스킹
    database.py           SQLAlchemy engine/session·transaction
  auth/
    router.py             합의된 6개 API와 Bearer 의존성
    schemas.py            strict Pydantic DTO·canonical 인코딩
    models.py             회원·identity·transaction·session·credential·recovery
    google.py             Google 검증 어댑터, 공개키 캐시·timeout
    tokens.py             자체 JWT·hash·AES-GCM·AAD
    service.py            가입·인증·갱신·로그아웃 transaction
    cleanup.py            만료 자료의 제한된 배치 정리
alembic/                  초기 additive migration
tests/unit/               DTO·시각·JWT·암호화 경계
tests/integration/        PostgreSQL·HTTP·동시성·rollback
```

SQLAlchemy 2 동기 engine + psycopg를 사용하고 DB·Google 동기 요청을 async 이벤트 루프에서 직접 블로킹하지 않습니다. 요청별 session을 공유하지 않습니다. Google 외부 검증은 DB 쓰기 잠금을 잡기 전에 완료하고 DB transaction에서 challenge 만료·소비를 다시 검사합니다.

Alembic·pytest·httpx를 추가하며 Google 검증은 공식 google-auth 기반, JWT는 PyJWT의 암호화 지원, 복구 암호화는 cryptography를 사용할 계획입니다. 정확한 버전은 구현 시 Python 3.12 호환성과 현재 공식 릴리스를 확인해 고정합니다. 테스트 의존성은 runtime과 분리합니다. 호스트 Python 3.14는 변경하지 않습니다.

## DB 설계와 변경 안전

| 테이블 | 주요 제약·인덱스 |
|---|---|
| users | UUID PK, status CHECK active/disabled, created/updated/last_login timestamptz |
| auth_identities | user FK, UNIQUE(provider, canonical_issuer, subject), user_id index |
| auth_transactions | UUID PK, nonce_digest UNIQUE, secret_digest, expires/consumed timestamptz, expires index, user FK 없음 |
| auth_sessions | UUID PK, user FK, remember boolean, absolute/idle expires, nullable revoked_at/reason, user_id·만료 index |
| refresh_credentials | UUID PK, session FK, generation, token_digest UNIQUE, UNIQUE(session_id,generation), issued/expires/consumed, nullable request_digest/successor FK, UNIQUE(session_id,request_digest) |
| refresh_recoveries | old credential FK UNIQUE, successor FK, request_digest, key_id/nonce/ciphertext, recovery_expires_at index, resend_count CHECK 0..2, UNIQUE(key_id,nonce) |

DTO non-null은 응답·요청 필드의 규칙입니다. DB의 미소비·미폐기 시각 등은 nullable로 정의하고 내부 필드를 응답에 노출하지 않습니다. UUID·생성 시각은 서버에서 정하고 email을 identity key로 쓰지 않습니다. 소유 관계 테이블은 만들지 않습니다.

초기 migration은 기존 DB에 새 테이블을 추가합니다. 기존 volume·테이블·계정·persistence_probe를 지우지 않고 자동 재초기화하지 않습니다. migration은 서버 부팅 시 자동 실행하지 않고 별도 명령으로 적용합니다. 현재 앱 DB 역할의 스키마 CREATE 권한을 우선 재사용하되 운영 역할 분리는 후속입니다.

테스트는 별도 Compose 프로젝트의 PostgreSQL 17과 별도 DB 이름·자격 증명·네트워크를 사용하고 기존 `postgres_data`를 연결하지 않습니다. 임시 테스트 DB 정리는 대상 확인 후 테스트 자원에만 적용하며 개발·운영 삭제 승인을 추정하지 않습니다. 초기 downgrade는 인증 테이블 삭제를 수반하므로 개발 DB에서 복구 방법으로 실행하지 않습니다. 적용 전 대상·기존 자료·백업 필요성을 확인하고 실패 시 원인 수정 또는 forward migration을 우선 검토합니다.

## 핵심 transaction과 동시성

1. 첫 가입: Google 증거 검증 → challenge 잠금/일치·소비 재검사 → identity 기준 회원 조회 또는 생성 → session·credential 발급 → challenge 소비 → 단일 commit. identity UNIQUE 충돌은 회원까지 rollback 후 새 transaction에서 기존 identity를 조회합니다. 무한 재시도하지 않습니다.
2. refresh: user → session → credential → recovery 순으로 잠급니다. user 정지·session 폐기·만료 우선순위와 request digest를 검사합니다. 새 credential 생성·old 소비·idle 갱신·암호화 응답·복구 기록을 하나의 commit으로 처리합니다.
3. replay 거절 때 session 폐기는 **오류 응답을 내기 전에 commit**합니다. HTTP 예외 때문에 폐기가 rollback되는 실수를 테스트로 방지합니다. 다른 기기는 유지합니다.
4. 동일 요청 복구: 후속 generation·시간·횟수·키를 검사하고 최초 응답만 반환합니다. 횟수 증가는 commit 후 전송하며 재전송 응답 유실도 허용 횟수에 포함합니다.
5. logout: hash 식별 후 같은 잠금 순서로 현재 session 폐기·복구 암호문 삭제. absolute 만료 전 반복 204, 이후 401로 통일합니다. 사용자 정지 상태에도 credential을 증명한 본인 logout은 허용합니다.
6. 보호 요청: 자체 JWT 검증과 DB user/session 상태 확인. 이번 GET 조회는 새 요청 기준으로 폐기를 반영하며 미래 쓰기 API는 쓰기 transaction에서 재확인합니다.

복구 기준 시각은 마지막 저장 단계의 DB clock_timestamp이며 성공 commit 이후만 응답합니다. commit 지연으로 응답 수신 후 복구 기간이 짧아질 수 있는 제약은 Flutter가 수용했습니다. 별도 commit·기간 연장으로 우회하지 않습니다.

## 보안·설정·운영 작업 경계

- Google audience는 전달받은 Web client ID로 고정. azp allowlist는 확정 등록값만 사용하고 미확인 Android ID를 추정하지 않음.
- 자체 access JWT는 RS256·issuer/audience 고정·kid 기반 서명 키 참조를 구현 선택으로 사용. Google skew 30초와 자체 JWT 만료 정책은 분리. 키·credential은 보고하지 않음.
- 복구 AES-256-GCM 키와 JWT 서명 키는 분리해 런타임에 주입. 키 설정이 없거나 잘못되면 인증 발급을 fail closed하며 임의 기본 비밀키를 사용하지 않음. 기존 /health 상태 확인 동작은 유지.
- nonce·secret·refresh는 32바이트 난수, token/request ID ASCII SHA-256 digest만 장기 DB 저장. 복구 응답만 60초 상한의 암호문 저장.
- 정리는 30초 주기·500개 배치로 시작. 로그인 challenge는 5분 뒤 발급 불가, 소비/만료 transaction은 정리 대상. 복구 암호문은 만료·폐기·후속 사용 시 제거; replay/hash 이력은 absolute 만료까지 유지.
- 로그는 request_id·경로·오류 code만 기본 기록. request body·Authorization·Google 증거·키·refresh_request_id는 기록하지 않음. 신규 API는 no-store와 공통 공개 오류 적용; 기존 /health는 변경하지 않음.
- 공개 challenge/교환은 요청량 제한을 적용. 로컬 단일 API 실행 기준 IP별 1분 challenge 30회, Google 교환 10회, session별 refresh 30회 기본안. 반복 오류와 자원 정리를 테스트하며 다중 인스턴스 제한 저장은 후속 검토. 주소를 클라이언트 헤더에서 임의로 신뢰하지 않음.
- 개발 접속은 로컬 HTTP와 루프백 유지. Windows localhost→WSL, emulator 10.0.2.2는 연결 후보이며 실측 전 성공으로 보고하지 않음. release HTTPS·약관·탈퇴는 배포 전 의존성.

## 단계별 작업과 완료 조건

| 단계 | 작업 | 종료 조건 |
|---|---|---|
| 1 기반 | 의존성·설정·DB session·pytest·테스트 Compose·Alembic | Python 3.12 빌드·pip check, 테스트 DB 격리 확인, 기존 /health·계약 회귀 통과 |
| 2 모델 | 6개 테이블·초기 migration·index | 분리 PostgreSQL upgrade 통과, UNIQUE/CHECK/FK·동시 가입·rollback 검증 |
| 3 로그인 | strict DTO·challenge·Google 검증·회원/session 발급 | 무효 signature/issuer/aud/azp/exp/iat/nonce·secret·소비 거절, 취소·실패 시 미생성 |
| 4 세션 | me/session·자체 JWT·회전/복구/logout·정리 | 시간·재시도·409·replay·정지·폐기·원자성·키 실패 자동 테스트 통과 |
| 5 계약 | 실제 OpenAPI를 합의된 구현과 동시 반영 | 전체 schema 비교·HTTP DTO·오류·security·no-store·기존 /health 통과 |
| 6 인계 | 실행 조건·결과·계약 SHA·미검증 목록 게시 | 게시가 승인된 commit의 계약 SHA 인계, Flutter 연결 후 공동 실인증·접속 검증 |

작업 진행은 본 계획의 단계로 보고하고 완료되지 않은 체크를 완료 표시하지 않습니다. commit/push/PR/main·dev 병합은 해당 작업의 사용자 승인 범위에서 수행합니다.

## 필수 검증과 판정 범위

- 단위: strict boolean/추가 필드/null·base64url canonical·hex64, 시각 equality·skew 분리, JWT signature/issuer/aud/kid, AES tag/AAD/nonce 충돌·키 없음.
- PostgreSQL: 동일 identity 동시 첫 가입 user 1개·orphan 없음, challenge 1회 소비, 동일 refresh 동시 재전송·횟수, 다른 request ID replay 후 폐기 commit, 후속 소비와 지연 응답, 60초 equality·commit 지연·rollback, logout/정지/만료 후 복구 거절, 정리 지연.
- HTTP: 6개 API의 성공·상태별 error.code·request_id, 타인 session/actor 위조·guest 미생성, Retry-After·no-store, 보호 요청에서 Google proof 대신 자체 access 사용.
- 실인증: 실제 Google 등록·서명·nonce·azp와 Android 취소/재로그인 확인은 Flutter와 공동 검증. 테스트 token을 Issue나 로그로 보내지 않음.
- 접속: Backend 내부 /health와 Windows·emulator 접근을 별도 기록. Flutter secure pending·앱 재시작·늦은 응답 격리는 Flutter 증거로 확인.

자동 검증 통과는 실기기·실제 Google·Flutter UI 적용·운영 배포 완료를 뜻하지 않습니다. Android client ID 추가 입력이 필요한 경우도 미확인 azp를 허용하지 않고 해당 실인증만 미검증으로 남깁니다.
