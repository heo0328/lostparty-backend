# 인증 API 개발·검증

Issue #2의 합의된 6개 API는 `app/auth`, DB 연결·설정·오류는 `app/core`에 있습니다. 실제 원본 계약은 `openapi/openapi.yaml`이며 공개 Swagger/OpenAPI HTTP 경로는 계속 꺼져 있습니다.

## 최초 준비와 실행

Ubuntu WSL2의 프로젝트 루트에서 실행합니다. 기존 `.env`와 DB volume은 유지하고 인증 키는 Git·Docker 빌드에서 제외되는 `.secrets`에 둡니다.

```bash
docker compose build api
mkdir -p .secrets
# 최초 1회. 키가 하나라도 존재하면 덮어쓰지 않고 종료합니다.
docker run --rm --user root \
  --mount type=bind,source="$PWD/.secrets",target=/run/secrets \
  lostparty-backend-api python scripts/create_auth_keys.py
# DB 테이블 추가만 수행. 초기화·자동 downgrade 없음.
docker compose run --rm --no-deps api alembic upgrade head
docker compose up -d --wait api
python3 scripts/check_openapi.py
```

로컬 키는 컨테이너 UID 10001 전용 권한입니다. API에서는 읽기 전용으로 마운트합니다. 운영 키와 동일하게 사용하지 말고 별도 운영 준비에서 주입합니다. 키가 없으면 인증 발급은 503으로 거절하지만 기존 /health는 DB 검사로 유지됩니다. 기존 DB 역할의 schema CREATE 권한을 migration에 사용하고 운영 역할 분리는 후속입니다.

## 격리 테스트

```bash
docker compose build api
docker compose -f compose.test.yaml up -d --wait test-db
docker compose -f compose.test.yaml build tests
docker compose -f compose.test.yaml run --rm tests
```

test-db는 별도 프로젝트·네트워크·`lostparty_test` DB·tmpfs를 사용하며 개발 volume을 연결하지 않습니다. 테스트 내부에서 해당 DB의 인증 테이블을 초기화합니다. 운영/개발에서 이 초기화 코드를 사용하지 않습니다. 테스트 키는 일회성 컨테이너의 /tmp에만 생성합니다. 전체 환경 제거 대신 테스트 DB를 멈추려면 `docker compose -f compose.test.yaml stop test-db`를 사용하며 tmpfs 테스트 자료는 유실될 수 있습니다.

테스트 실행 결과와 장애·경고는 [DEV_LOG](project/DEV_LOG.md)에 누적합니다. 모의 Google 증거 검증과 실제 Google 인증을 구분합니다.

## API·접속·검증 범위

- challenge: POST /v1/auth/google/challenges
- Google 가입·로그인: POST /v1/auth/google
- 본인 조회: GET /v1/me
- 현재 session: GET /v1/auth/session
- 회전·복구: POST /v1/auth/refresh
- 현재 기기 logout: POST /v1/auth/logout

필드·만료·오류·인코딩은 [계약 문서](ISSUE_2_AUTH_CONTRACT_DRAFT.md), 암호화·복구는 [복구 설계](ISSUE_2_REFRESH_RECOVERY.md)를 참고합니다. no-store와 strict 400 검증을 적용하고 보호 API는 자체 RS256 JWT 및 DB 상태를 확인합니다. refresh는 session별 1분 30회, 공용 IP별 300회 제한을 추가 적용합니다. challenge/Google 교환은 IP별 30/10회입니다. 이 제한은 단일 API 프로세스 메모리 기준이며 다중 인스턴스의 통합 제한은 후속입니다.

기간은 합의값을 코드에 적용했습니다. 기간을 환경별로 바꾸는 설정 기능은 아직 없으며 변경 시 계약과 Flutter 영향을 다시 확인합니다.

실행한 HTTP·migration·계약 검증과 기존 흐름 보존 결과는 [DEV_LOG](project/DEV_LOG.md)를 참고합니다. 현재 남은 공동 검증 순서는 [NEXT_WORK](project/NEXT_WORK.md)에 있습니다.

후속 확인: 실제 Google 서명·nonce·azp, Windows localhost→WSL와 Android 10.0.2.2 접근, Flutter 화면/bootstrap·secure pending·앱 재시작·늦은 응답 격리. 현재 host 루프백 HTTP만 확인했으며 외부 터널/포트 공개는 하지 않았습니다. 탈퇴·약관·release 등록·운영 배포는 별도 작업입니다.

## 키 설정과 갱신

Compose는 GOOGLE_CLIENT_ID, GOOGLE_AZP_ALLOWLIST(쉼표 구분 확정 client ID만), JWT_KEY_ID, RECOVERY_KEY_ID를 전달합니다. `.env`에 값을 추가할 경우 비밀은 출력하거나 커밋하지 않습니다. 기존 Web audience는 기본값으로 적용했고 미확인 Android azp를 추정 허용하지 않습니다.

현재 JWT는 `jwt.pem`과 JWT_KEY_ID를 사용합니다. 이전 JWT 공개키를 유지하는 자동 rotation 기능은 아직 없으므로 JWT 키를 교체하면 기존 access가 거절될 수 있습니다. 별도 계획 없이 키를 교체하지 않습니다.

복구 키는 현재 `recovery.key`와 RECOVERY_KEY_ID를 사용합니다. 구키 복호화가 필요하면 안전한 런타임 디렉터리에 `recovery-<old-key-id>.key`를 유지하고, 최대 복구 기간 및 처리 중 요청을 고려한 뒤 제거합니다. key ID는 경로 문자를 허용하지 않습니다. 암호문 물리 정리가 늦어져도 만료 뒤 반환하지 않습니다.

cleanup은 API lifespan에서 30초마다 배치 실행합니다. DB·잠금 실패 시 민감값 없이 실패를 기록하고 다음 주기에 재시도합니다. 최초 migration을 startup에서 자동 적용하지 않습니다. 신규 환경에서는 API 실행 전에 upgrade 명령이 필요합니다.
