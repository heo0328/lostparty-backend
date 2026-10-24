# Backend 구조 점검과 개선 후보

2026-10-25 / 작업 구간명: Backend 구조·개선 후보 점검.
작업 내용: 정적 코드/계약/도구 검토와 후보 우선순위 정리. 구현 변경은 하지 않았다.
브랜치: `chore/backend-architecture-review`, 기준: `feat/raid-recruitment`의 `c0128c3e56a7c47da5a9d845009fe067010497c5`(원격 SHA 동일 확인).
사용자의 별도 점검 브랜치 요청에 따라 분기했다. 이 문서는 개선 구현·API 변경·배포 승인이 아니다.

## 판단

현재 FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL 기반 기능별 모놀리스는 유지할 만하다. 프레임워크 교체나 Repository 계층 일괄 도입보다 검증의 재현성, 관측, 앱 구성과 계약 설명의 분리가 먼저다. 성능 병목·실제 결함을 입증한 감사 결과는 아니며 아래 항목은 조사에서 확인한 구조와 후속 검증 조건이다.

`app` Python 208파일/27,224행을 정적으로 확인했다. 기본 OpenAPI는116경로/133동작, two-cycle은177경로/197동작이다. API 수만으로 중복을 판단하지 않는다. `cycle_wire.py` 2,796행도 계약 DTO 규모이며 파일 크기만으로 분할 대상이라 단정하지 않는다.

## 유지할 구조와 기존 개선

- `app/raid_rooms/admission_service.py`의 snapshot은 REPEATABLE READ/READ ONLY이며 execute는 인증·명령 결과 저장·주차 최종검증을 트랜잭션으로 묶는다. 원ACK 재생과 현재 권한 확인의 순서를 보존한다. 별도 신규 transaction 프레임워크로 교체할 근거는 없다.
- `app/game_accounts/bootstrap.py`와 `bootstrap_router.py`에는 이미 첫 화면 일괄 읽기가 있다. `cycle_card_batch.py`도 페이지를 먼저 선택한 후 관계를 일괄 읽는다. `application_display.py`/`admission_eligibility.py` 등 공통 규칙 재사용이 존재한다. 모든 조회가 카드별 N회 SQL이라는 전제로 바꾸지 않는다.
- `app/game_accounts/provider.py`에는 동시 요청2개 상한·connect/read timeout·응답 크기/본문 deadline·redirect 거부가 있다. 비동기 HTTP로 바꾸거나 자동 재시도를 추가하는 것이 곧 개선은 아니다.
- `tests/test_recruitment_cycle_performance.py`에는 SQL 수·응답 크기·시간 측정이 이미 있다. 후속 성능 작업은 이 근거를 확장하고 새 모니터링 체계를 중복 구축하지 않는다.

## Backend 독립 개선 후보

2026-10-25 후속: 사용자 승인으로 첫 후보 **격리 검증 실행 경로 정리**를 적용했다. [실행 방법·범위](isolated-verification.md)를 따르며 아래 표는 조사 당시 판단/완료 조건으로 보존한다. 이후 두 번째 후보 **검증된 의존성 고정**도 승인되어 [버전·해시 고정](dependency-locking.md)을 적용했다. 다른 후보는 미착수다.

| 우선 | 후보·확인 근거 | 기대 효과와 완료 조건 |
|---|---|---|
| 1 | **검증 실행 경로 정리.** `.github`에는 이슈 템플릿만 있고 CI workflow가 없다. `scripts/verify.py`는 DB probe 쓰기·컨테이너 stop/down/up을 포함한다. `tests/conftest.py`는 기본0023 fixture를 유지하며 two-cycle 검증과 구분된다. | 읽기 정적검사, 기본0023 회귀,0031 격리시험/계약 검증,환경 복구시험의 진입점을 명확히 분리한다. 기존 개별 시험의 runner/DB 준비 방식을 먼저 조사해 재사용한다. 완료 조건은 새 환경에서 지정 명령으로 대상 profile·DB·시험 범위와 결과를 재현하는 것. 개발DB/실키를 사용하는 CI는 만들지 않는다. |
| 1 | **전이 의존성까지 설치 결과 고정.** requirements는 직접 의존성을 `==`로 지정하지만 Pydantic/Starlette 등 전이 패키지의 고정 목록·해시 lock은 없다. Docker base도 가변 tag다. | 현재 검증 이미지의 설치 목록을 먼저 확인한 후 전이 의존성/해시를 포함한 재현 가능한 설치물을 만든다. 기존 패키지를 일괄 업데이트하지 않는다. 완료 조건은 새 빌드의 설치 목록 재현·기본/177 계약 동일·관련 격리회귀 통과. 라이브러리 보안 취약점 감사는 이번에 하지 않았다. |
| 1 | **장애와 지연 관측 보강.** `app/core/errors.py`는 오류 code/status/request_id를 기록하지만 SQL 오류 원인 분류는 없다. worker들은 일반 경고를 남기며 `/health`는 DB SELECT1을 확인한다. | 비밀정보를 제외한 예외 유형/안전한 분류, route template별 시간·상태, worker 최종 성공/실패·처리 지연을 관측한다. SQL문/파라미터·URL 원문·응답/인증정보는 기록하지 않는다. 먼저 표준 logging으로 가능하다. 완료 조건은 합성 장애를 구분하고 민감정보 미노출을 검증하는 것. 기존 health 계약 확대는 별도 판단한다. |
| 2 | **앱 조립과 OpenAPI 정책 설명 분리.** `app/main.py` 431행에 router 등록, 두 lifespan, 대량 `x-…-policy` 설명, 두 앱 factory가 함께 있다. 과거 단계의 설명도 남아 있다. | 정책 설명/스키마 장식을 별도 모듈로 옮기고 앱 구성 책임을 작게 만든다. 앱 기본0023/two-cycle0031 차이와 startup 검증을 보존한다. 완료 조건은 두 생성 OpenAPI 객체 전체 동일·router/예외/middleware/lifespan 회귀 확인. 과거 설명 정정은 단순 이동과 구분한다. |
| 2 | **정적 검사·가독성 기준 도입.** pyproject/Ruff 설정이 없고 여러 업무 파일에 한 줄 다중 명령이 있다. | Ruff를 개발 도구 후보로 검토한다. 먼저 진단만 수행해 오류성 규칙과 스타일 변경을 구분하고, 작은 변경 범위부터 적용한다. 전체 자동포맷/import 정리를 동시에 실행하지 않는다. SQLAlchemy 모델 등록의 side-effect import 등을 확인한다. 완료 조건은 합의한 규칙·대상에서 진단 재현과 변경 구간 검사 통과. |
| 3 | **업무 경계와 타입 명확화.** 모집에는 여러 세대의 service/commands/cycle_*·v1 adapter와 지연 import가 공존한다. 다수 함수가 dict로 실행 자료를 넘긴다. | 먼저 read/command/policy/projection/호환 adapter의 호출·트랜잭션 경계를 도식화하고 자주 변경되는 한 경로에서만 내부 타입을 보완한다. Repository/DI 프레임워크 일괄 도입은 보류한다. 완료 조건은 책임 설명과 동일 계약/권한·원ACK·rollback 회귀. 기본/구 API는 네이티브 소비·보존 계약 확인 없이 삭제하지 않는다. |

우선1의 세 항목 중에서도 가장 작은 첫 구현 후보는 **격리 검증 실행 경로 정리**다. 기존0031 시험 runner와 실행 기록을 먼저 조사해야 하므로, 현 conftest를 곧바로 head migration으로 바꾸면 안 된다. 그 다음 의존성 고정과 관측 개선을 각각 독립 구간으로 진행할 수 있다.

## 측정 후 판단할 항목

- `app/game_accounts/support.py`의 `game-mutations-v1` advisory lock은 여러 쓰기의 일관성을 묶는다. 잠금 범위 축소는 계정/그룹/주간/모집의 교차 불변식을 깨뜨릴 수 있다. 먼저 격리 부하에서 대기시간·트랜잭션 시간·충돌률을 측정하고 실제 병목일 때만 설계한다.
- provider semaphore와 `app/core/rate_limit.py`의 메모리 제한은 프로세스 단위다. provider의 DB 제한(`app/lostark_keys/rate_limits.py`)과 구분한다. 다중 worker/인스턴스 운영 전 제한의 적용 범위를 검증한다. 현 단일 실행을 곧바로 장애나 Redis 필요로 해석하지 않는다.
- SQL/인덱스는 대표 데이터 크기와 query plan으로 판단한다. 이번 점검은 실행 DB 조회/EXPLAIN/부하시험을 하지 않았다. 응답시간 단축·누수 해소를 주장하지 않는다.

## 네이티브 협의가 필요한 API 통합 후보

실제 앱 호출 내역은 읽지 않았고 UI 동선을 추정하지 않았다. 다음은 확정 중복이 아닌 조사 묶음이다.

| 조사 묶음 | Backend에서 확인할 내용 | 네이티브가 제공할 내용 |
|---|---|---|
| 첫 진입 account-bootstrap과 개별 profile/weekly 조회 | bootstrap 포함 필드·별도조회 목적·갱신 범위 | 화면별 동시 호출과 bootstrap 뒤 즉시 재조회 이유 |
| 모집 목록 카드/방 상세/본인 참가·주간 요약 | 필드와 권한·실제T·generation·snapshot 차이 | 같은 진입에서 반드시 함께 필요한 자료·로딩/부분실패 처리 |
| 후보 목록/admission-context/신청·변경 command | 일괄후보와 선택 후 최신검증의 역할·provider 호출 여부 | 캐릭터 선택 전후 실제 요청 수·변경 시 무효화 범위 |

통합 판단에는 호출 순서/빈도·요청 크기·지연·실제 중복 필드, 인증/회원·room/실제T와 스냅샷 수명, 부분실패·쓰기 후 갱신 범위가 필요하다. 함께 읽어도 되는 데이터만 통합 조회 후보로 검토하고 독립 조회는 필요하면 유지한다. **원자 command·최신 권한/CAS·원ACK와 현재 상태의 차이를 통신1회 목표로 제거하지 않는다.** 후보GET과 context도 단순 중복이 아니다.

## 라이브러리 판단

- 현 웹/ORM/DB 스택 유지. 별도 서비스 분리·Redis/Celery/Kafka·전면 async 전환은 이번 조사에서 필요 근거를 얻지 못했다.
- [Ruff 공식 문서](https://docs.astral.sh/ruff/)는 lint/format 기능을 제공한다. 이번 권고는 개발 도구 후보이며 설치·버전 선택·실행은 하지 않았다.
- [pip 재현 설치](https://pip.pypa.io/en/stable/topics/repeatable-installs/)의 전이 의존성 고정·hash 검증 방식을 우선 검토한다. uv/Poetry 등 패키지 관리 도구 교체는 목표가 아니다.
- 표준 logging/기존 SQLAlchemy 측정으로 필요한 관측 항목부터 정하고 외부 관측 라이브러리는 운영 요구가 생길 때 비교한다.

## 검토 범위·다음 작업

정적 파일·OpenAPI JSON 객체의 경로/동작 수·Git/원격 SHA·공식 #26 최신 인계 댓글을 확인했다. Python208파일 AST parse 통과. 문서 링크/추적 검사는 이번 기록 마감에 실행한다. 서버/DB/기기·provider 호출·패키지 설치·pytest/부하/보안 감사는 하지 않았다. 현재 기능 전체의 무결성 검증 결과가 아니다.

네이티브 대기 기준은 [NEXT_WORK](../../project/NEXT_WORK.md)의 모집 구간과 [#26 전체26 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386892285)를 유지한다. 새 Issue/댓글·API 계약 변경·운영 반영은 없다. 사용자에게 후보를 제시한 뒤 선택한 구간의 세부 범위/검증을 정해 구현한다. 모집 기능 대응을 재개할 때는 `feat/raid-recruitment` checkout을 확인하고 이 점검 브랜치의 기록 통합 여부를 먼저 정한다. 현재 점검 브랜치를 모집 작업 브랜치 대신 사용하지 않는다.
