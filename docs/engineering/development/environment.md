# 개발 환경·실행 구성·검증 안내

현재 실행·명칭 기준은 [실행 설정 정리](runtime-configuration.md), 다음 작업은 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다. Python3.12·FastAPI/Uvicorn·SQLAlchemy·Alembic·PostgreSQL17을 Docker Compose로 실행한다.

<a id="section-2"></a>

## 기존 로컬 DB 재기동

DB0036과 환경/키가 준비된 현재 개발환경에서는 기본 Compose 하나로 현재 앱을 시작한다.

```bash
docker.exe compose up -d --no-deps --build --wait --wait-timeout 180 api
python3 scripts/check_openapi.py --docker docker.exe --container lostparty-backend-api-1
```

`app.main:app`과 `create_app()`은 같은 현재 앱이다. `compose.two-cycle.yaml`을 추가하던 기존 명령도 호환되지만 필수 파일은 아니다. 시작은 DB를 검사하며 migration·초기화·legacy fallback을 하지 않는다. DB가 비었거나 지원되지 않는 단계이면 API 시작이 실패한다. 기존 DB에는 신규 설치 명령을 적용하지 않는다.

## 신규 로컬 환경

환경과 키는 [백업 원장](../operations/backup-and-recovery.md)을 따라 준비한다. 기존 키가 있다면 다시 생성하지 않는다. 별도 빈 환경은 `compose.fresh.yaml`의 프로젝트/볼륨/8001 포트로 분리한다. 다음은 **그 프로젝트의 빈 DB가 확인된 경우에만** 수행할 명시적 준비다.

```bash
docker.exe compose -f compose.yaml -f compose.fresh.yaml up -d --wait db
docker.exe compose -f compose.yaml -f compose.fresh.yaml build api
docker.exe compose -f compose.yaml -f compose.fresh.yaml run --rm --no-deps api alembic upgrade 0036_roster_presence
docker.exe compose -f compose.yaml -f compose.fresh.yaml up -d --no-deps --wait --wait-timeout 180 api
```

fresh DB는 host port를 게시하지 않아 기존 로컬 DB의5432와 충돌하지 않는다. fresh는 테스트 실행기가 아니며 기존 데이터/개발 dump를 자동 수입하지 않는다.

## 개발·운영 구분

| Native 빌드 | 연결 대상 |
|---|---|
| debug | 개발자 로컬 Backend |
| release | AWS 운영 Backend (`https://lostparty.duckdns.org`) |

운영은 HTTPS/Caddy·프록시 신뢰·worker1·운영 키 경로를 가진 독립 `compose.lightsail.yaml`을 사용한다. 로컬 Compose와 합치지 않는다. 현재 저장소의 운영 명령도 `create_app --factory`이며, 설치된 기존 운영은 승인된 이미지/동결 명령을 유지한다. [운영 반영 경계](workflow.md#local-dev-and-production)·[향후 도구 갱신과 배포](../operations/runtime-release-transition.md)를 따른다.

<a id="section-3"></a>

## 명세·시험

현재 명세는 [openapi.yaml](../../../openapi/openapi.yaml), 과거 DB0023 시험용은 [legacy.openapi.yaml](../../../openapi/legacy.openapi.yaml)이다. 현재192경로/213동작, legacy125경로/142동작이며 전체 생성 객체를 비교한다. HTTP Swagger/OpenAPI 공개 경로는 비활성이다.

```bash
python3 scripts/check_openapi.py --docker docker.exe --container lostparty-backend-api-1 --profile legacy
python3 scripts/verify_isolated.py contracts --docker docker.exe
python3 scripts/verify_isolated.py all --docker docker.exe
```

legacy 명세 생성은 DB를 연결하거나 과거 서버를 병행 실행하는 명령이 아니다. 과거 실제 앱 재현은 `uvicorn app.main:create_legacy_app --factory`를 DB0023의 격리 환경에서만 사용한다. 시험 fixture를 일괄 최신 DB로 올리지 않는다. [격리 검증](isolated-verification.md)에서 정확한 선택/환경과 결과 해석을 확인한다.

<a id="section"></a>

## 설정·의존성 보존

[의존성 고정](dependency-locking.md)에 따라 requirements.in/requirements-dev.in의 직접 요구와 requirements.txt/requirements-dev.txt의 전이 버전·SHA256을 관리한다. 호스트 Python에 같은 패키지를 전역 설치할 필요는 없다. `.env`·키·원문 응답은 비공개이며 공개 로그/문서에 출력하지 않는다.

2026-11-07 환경 복구·OAuth/키4개·기기 로그인 확인은 [당시 이력](../../project/DEV_LOG.md#development-recovery-20261107), 이후 개발 반영은 [운영 기록](../operations/README.md)에 보존한다. 과거 소스·경로 수·DB 단계는 그 시점의 근거다.
