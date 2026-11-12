# Backend 실행 구성 단일화 조사

2026-11-06 / Backend / 조사 기준 `f211342dd6f7df24971582bd36604402f05bbf1b` / 작업 구간: 실행 구성 관계 조사·후속 등록 / 브랜치: `chore/backend-runtime-consolidation`.

**아래는 2026-11-06 조사 당시 기록이다. 2026-11-13 사용자 승인으로 구현에 착수했으며 현재 상태·이름은 [실행 설정 정리](runtime-configuration.md)를 따른다.**

**당시 판단: 조사 완료·단일화 구현 미착수.** 현재 개발·운영의 실행 기준은 two-cycle이다. 두 서버를 동시에 실행해야 한다는 근거는 확인되지 않았다. 그러나 기존0023 실행은 테스트 fixture·계약 생성·복원 리허설 코드에 연결돼 있어 지금 즉시 삭제할 수 있다고 결론 내리지 않는다. 권장안은 **최신 실행을 기본으로 통일하고, 기존0023 실행은 명시적인 회귀 시험용으로 먼저 분리**하는 것이다. 해당 수정과 실제 실행 검증은 차후 선택할 별도 구현 구간이다.

## 1. 이번 로컬 기동 문제와 조사 필요성

### 사용자 실행 결과와 확인 범위

사용자가 환경 재구축 후 이 대화에 제공한 결과는 다음과 같다. 조사자가 Docker/DB에서 독립 재현한 결과가 아니다.

- `docker compose ls`: `compose.yaml` 단독 사용. DB는 healthy, API는 `app.main:app`으로 반복 재시작했다.
- DB의 `public.alembic_version` 조회는 테이블 부재 오류였고 `public` 일반 테이블 조회는0행이었다. 이는 조회한 DB의 public 앱 스키마 미준비 근거이며, 다른 DB/스키마·외부 백업 전체의 부재 증거는 아니다.
- `0035_cycle_group_policy`까지 준비하고 two-cycle 구성으로 실행하는 절차를 안내한 뒤, 사용자가 API 이미지 `lostparty-backend-api:two-cycle`·factory 명령·API/DB healthy·로컬8000 `/health`의 `status=ok,database=ok`를 보고했다. 최종 `alembic current` 출력은 별도로 제공되지 않았다.
- 원본 API 로그는 `server_event`만 반복했다. 정확한 예외 stack은 확보하지 않았으나, 빈 DB에서 시작 검사가 직접 조회하는 테이블이 없다는 실패 조건은 코드로 확인된다. 이 실행에서는 DB0035와 기본 앱0023의 불일치가 실제로 발생했다고 단정하지 않는다. 빈 DB 문제를 해소한 뒤 기본 앱을 그대로 사용하면 불일치가 추가로 발생할 수 있다.

[DB 초기화 스크립트](../../../docker/init-db.sh)는 역할과 스키마 권한만 만들며 업무 테이블을 만들지 않는다. [기본 lifespan](../../../app/main.py)과 [readiness](../../../app/raid_rooms/common/readiness.py)는 준비된 DB를 요구하고 자동 migration을 하지 않는다. [로그 formatter](../../../app/core/observability.py)는 임의 Uvicorn 메시지/예외 원문을 그대로 출력하지 않아 현재 시작 실패 원인을 사용자에게 설명하기 어렵다.

문제는 빈 DB 준비 절차와 실행 구성 선택이 함께 필요하지만, 가장 짧은 기본 실행이 과거 앱을 선택한다는 점이다. 데이터 손실이나 운영 장애를 이번 결과로 추정하지 않는다. 운영 서버에는 이번 조사에서 접속하지 않았다.

## 2. 현재 실행 구조와 분리 배경

### 분리 당시와 전환 이후

| 근거 | 당시 목적·현재 해석 |
|---|---|
| [8085e90](https://github.com/heo0328/lostparty-backend/commit/8085e90877561c28c45eb7279929d790da0a7c5b), [W4-D 원문](../../archive/work-records/features/recruitment/development/ISSUE_13_W4D_CUTOVER.md) | 2026-10-22 기본0023 서버를 바꾸지 않고0029 기반 C/N·새 worker·v1 adapter를 별도 factory로 준비했다. 소스 준비와 실제 DB/API 전환 승인을 구분하기 위한 분리였다. |
| [Issue13 전체89번째 Backend · W4-D](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330758804), [전체90번째 Backend · W5 준비](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6331483028) | 기본0023 유지·별도 factory·백업/복원·구 worker 중지·실제 전환의 경계를 명시했다. |
| [3c26cdb](https://github.com/heo0328/lostparty-backend/commit/3c26cdb6fd8a17c0bf0d7afaa3bbd93d1f4f3176), [전환 원문](../../archive/work-records/features/recruitment/development/ISSUE_13_W5_LIVE_CUTOVER.md), [전체92번째 Backend · 실제 전환](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6332478347) | 같은 날 기존 개발 DB0023→0029·API/worker를 실제 전환했다. 기존 API/DB 두 컨테이너를 유지한 전환이며, 구 서버와 신 서버를 상시 병행한 기록이 아니다. 과거 자료·원 ACK는 보존했다. |
| [Lightsail 첫 설치 기준](../operations/lightsail-first-deploy.md), [v2.0.0 배포 기록](../operations/records/backend-v2.0.0-deployment.json) | 운영도 최신 factory·DB0035 기준이다. 기본 Docker CMD가 과거 앱이어도 운영 Compose의 명시 command가 이를 덮어쓴다. |
| [Issue34 전체13번째 Backend · 운영 완료](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609667274), [전체14번째 Native · APK 게시 완료](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609824463) | Backend v2.0.0 운영 반영·Native v2.0.0 게시가 보고됐다. 이번에는 본문과 최신 댓글을 읽기 조회했으며 게시/재인수 요청은 하지 않았다. 실시간 운영 정상·새 APK 전체 기기 인수의 증거로 확대하지 않는다. |

위 조회의 댓글 순번은 본문을 제외한 전체 순서다. Issue13은194개, Issue34는14개 댓글을 조회했다. 확인한 기록에는 기본 실행을 언제 최신으로 바꾸거나0023 실행을 제거한다는 확정 기한이 없었다. 데이터 보관 기간에 따라 두 서버를 반드시 유지한다는 합의도 확인되지 않았다.

### 두 시작점의 실제 차이

| 항목 | 기본 `app.main:app` | `app.main:create_two_cycle_app --factory` |
|---|---|---|
| 생성 | 모듈 전역 FastAPI 객체 | 기본 앱의 APIRoute들을 새 앱에 등록하고 cycle router·신청문구 preset 추가 |
| DB 시작 검사 | `require_active`: 정확히0023 | `require_two_cycle_active`:0029~0035의 명시 목록과 해당 구조/권한 검사. 현재 최신 head는0035 |
| 공통 처리 | 오류 경계·no-store·인증/계정/그룹 등 | 같은 함수·라우터를 재사용하되 앱에 독립 등록. 동작은 DB 단계별 분기도 확인해야 함 |
| 내부 작업 | 인증 정리·분쟁 worker·기존 모집 processor | 인증 정리·분쟁 worker·cycle 모집 processor |
| 생성 계약 | 기본 OpenAPI | two-cycle OpenAPI·추가 정책 metadata |

[main](../../../app/main.py)·[readiness](../../../app/raid_rooms/common/readiness.py)·[worker](../../../app/raid_rooms/common/worker.py)가 근거다. factory는 실행할 업무 체계를 고르는 입구이지, DB migration 실행기가 아니다. 같은 DB에 두 모집 processor를 함께 실행하는 수정은 하지 않는다.

## 3. 기능·계약·도구별 비교 결과

### 정적 계약 비교

원본 JSON 두 개를 Python 표준 라이브러리로 읽어 비교했다. 앱 import·DB·lifespan·HTTP 실행은 하지 않았다.

- [기본 계약](../../../openapi/legacy.openapi.yaml):125경로·142동작. [최신 계약](../../../openapi/openapi.yaml):187경로·208동작.
- 기본 `(HTTP method,path)`142개는 모두 최신에도 존재한다. 최신 전용66개이며 경로/메서드 기준 누락은0개다.
- 공통 operation 객체는128개 동일·14개 상이하다. 14개는 모집 search/create/join/apply/approve/reject·편성/내보내기/위임·일정 설정/제안/응답/선택/참가확인의 requestBody 참조가 다르다.
- components schema는288개/740개다. 이름 중복 해소 등으로 기본 이름20개가 최신에 같은 이름으로 없고 공통 이름24개가 상이하다. 이는 기능20개 누락이라는 뜻이 아니다. 같은 operation 객체도 참조 대상 schema가 달라질 수 있으므로128개를 전체 wire 동등성 판정으로 사용하지 않는다. 차후 구현 전 참조를 따라 입력/응답 구조와 HTTP 동작을 대조해야 한다.

### 기능별 판정

| 영역 | 판정 | 근거·경계 |
|---|---|---|
| 인증·세션·회원 설정·개인 API 키 | 동일 제공(공유 구현 기준) | 동일 router/service 사용. 이번에 로그인/provider/기기 동작을 새로 시험한 것은 아님. |
| 원정대·소유 인증/분쟁·대표/활동·분석·일괄 조회 | 동일 제공(공유 구현 기준) | 최신 앱도 기존 APIRoute 등록. 소유권 분쟁 후처리 등 기존 미완료는 단일화로 해결되지 않음. |
| 레이드 카탈로그·개인 주간 기록 | 공통 제공·일부 변경된 방식으로 대체 | 공유 router이나 주간 서비스의 DB 단계 분기·현재 실제T/개인 수동완료 제약은 유지. |
| 그룹 | 공통 제공·최신DB 기반 보완 | 공유 router와0034 기능/0035 주차별 그룹 정책. 같은 경로라고0023에서 최신 그룹 기능까지 이용 가능하다는 뜻은 아님. |
| 모집 검색·명단·상세·현재주 조회 | 변경된 방식으로 대체 + 과거 호환용 유지 | [v1_compat](../../../app/raid_rooms/compat/v1_compat.py)가 최신 DB에서 현재 실제C를 v1 DTO로 투영. N을 C로 가장하거나 GET로 참가/주차를 만들지 않음. |
| 모집 생성·참가·관리·일정·완료 | 최신 v2 체계로 대체, 과거 일부 쓰기는 제한 | [admission_service.execute](../../../app/raid_rooms/admissions/admission_service.py)는 인증된 원 ACK 복구를 먼저 처리한 뒤 신규 위험 v1 쓰기를 `CLIENT_UPGRADE_REQUIRED`로 거절. 개인 시간표·수동완료의 합의된 경로는 유지. 전체 v1 기능이 예전과 똑같다는 판정은 불가. |
| 이전 요청·ACK·과거 기록 | 과거 호환용 유지 | 원 method/path/body/key와 멱등 namespace·과거 evidence/보류 상태 보존. [비활성 기능 기준](../../features/recruitment/completion-and-records/inactive-features.md)도 별도 보존 의무. 실행 입구 제거만으로 adapter·reader·원응답을 삭제하지 않음. |
| 모집 worker | 변경된 방식으로 대체 | 구 processor는0023 guard, 새 processor는cycle guard. 인증·분쟁 worker는 공유. |
| 미확인·누락 | 경로/메서드 누락 없음, 전체 동작 대체는 미확인 | 정적 비교와 과거 시험 근거만 확보. 모든 역할·권한·경합·실회원·업그레이드 조합을 이번에 검증하지 않음. |

### 실행·검증·배포 사용처

| 사용처 | 현재 연결·차후 영향 |
|---|---|
| [Dockerfile](../../../Dockerfile), [compose.yaml](../../../compose.yaml) | 이미지 기본 CMD는 과거 앱, Compose 기본은 이를 상속. 단일화 첫 변경 대상. |
| [compose.two-cycle.yaml](../../../compose.two-cycle.yaml) | 최신 이미지 태그와 factory 명령만 덮어써 공통 DB/키/포트를 재사용. 향후 기본과 겹치는 부분을 호환 override로 유지한 뒤 소비처 정리. |
| [compose.fresh.yaml](../../../compose.fresh.yaml) | 별도 프로젝트/8001/이미지 태그만 지정하고 최신 command는 지정하지 않음. 이름이 fresh라고 최신 DB를 준비하거나 migration하지 않음. 사용자 사용 여부는 미확인. |
| [tests/conftest.py](../../../tests/conftest.py) | 공통 DB0023와 기본 `TestClient(app)` 사용. 전체 fixture를 즉시 최신으로 올리면 과거 회귀 의미·migration 보존 시험이 변함. |
| [isolated_checks](../../../scripts/isolated_checks.py), [check_openapi](../../../scripts/check_openapi.py) | 두 생성 계약 모두 비교. 실행 컨테이너 비교 도구의 기본 profile은 legacy. 최신 기본 실행과 함께 기본 profile도 맞춰야 함. |
| [격리 runner](../../../scripts/verify_isolated.py), [시험 Compose](../../../compose.test.yaml) | 별도 tmpfs PostgreSQL·시험 키·worker 비활성. 최신 기능 fixture는 별도 단계 DB를 사용. `legacy`는 운영 서버 종류가 아니라 지정된 회귀 묶음 이름이기도 함. |
| [CI](../../../.github/workflows/backend-release.yml), [regression](../../../scripts/deployment/regression.py) | 계약 gate가 두 앱에 의존하고 전체 회귀 분할은0023 fixture도 포함. 기본 실행 통일을 이유로 기존 시험/계약 gate를 삭제하지 않음. |
| [release](../../../scripts/deployment/release.py), [서버 제어기](../../../scripts/deployment/server.py), [운영 Compose](../../../compose.lightsail.yaml) | 단일 Dockerfile로 이미지 게시, 운영은factory 명시. 제어기는 이미지 migration head와DB revision·동결구성·health를 확인하고 자동 migration하지 않음. 기존 Release/태그/동결 구성은 수정하지 않음. |
| [snapshot](../../../scripts/recruitment_snapshot.py), [복원 리허설](../../../scripts/recruitment_restore_preflight.py) | 전환 당시0023 source/구 이미지 복원과0029 factory를 사용하며 과거167경로 단정도 남음. 최신 DB에 재실행할 일반 복구 도구로 안내하면 안 됨. 역사 재현용 보존 또는 대체 여부를 명시해야 함. |
| [환경 안내](environment.md), [격리 검증 안내](isolated-verification.md), 협업/운영 문서·README | 일부 경로 수·DB 단계는 과거 값. 현재 사용 안내와 역사 원문을 구분해 전자를 정정하고 archive·동결 자료를 덮어쓰지 않음. |

## 4. 현재 유지 필요성에 대한 결론과 미확인 사항

1. **실서비스 실행:** 확인한 로컬/운영 기준은 이미 최신 방식으로 전환됐다. 과거 실행을 기본으로 남겨야 할 현재 제품상 근거는 찾지 못했다. 확인하지 않은 개인 환경·외부 소비처까지 사용하지 않는다고 단정하지 않는다.
2. **시험/역사 재현:**0023 기본 앱과 계약을 실제 참조하는 코드가 있으므로 유지 이유가 존재한다. 이는 사용자가 과거 서버를 실행해야 할 이유와 다르다. 먼저 시험 전용으로 분리해야 한다.
3. **API/데이터 보존:** 현재 factory에 v1도 포함되며, 최신 모집 의미에 맞게 호환한다. 과거 데이터 보관 기간 경과와 서버 실행 경로 제거는 독립 판단이다. migration chain·reader·원 ACK·보류 evidence를 삭제할 승인이나 근거는 없다.
4. **대체 판정:** 최신 경로 집합은 기존을 포함하지만 전체 wire·업무 동작의 일치나 구 동작 완전 복제는 증명되지 않았다. 일부 거절/대체는 이미 합의된 의도적 변경이다. 따라서 “둘 다 실서비스에 필요”도 “기존 코드를 모두 즉시 삭제 가능”도 결론이 아니다.

남은 확인은 외부에서0023 실행을 쓰는지, 공통 기능의 최신DB 회귀가 충분한지, schema 참조 차이의 의미, 과거 복원 도구의 보존 목적이다. Backend가 먼저 저장소/격리 시험으로 확인하고, 외부 소비처가 실제로 남을 때만 해당 담당에게 좁게 확인한다. 사용자에게 과거 정책을 일괄 재결정하도록 요청하지 않는다.

## 5. 권장 수정안·작업 순서·영향 범위

다음은 **미적용 수정안**이다. 이번 조사·문서 게시를 코드 변경·운영 반영 승인으로 사용하지 않는다.

### A. 기본 실행을 최신으로 통일

1. 구현 착수 시 Git/실행DB/현재 사용 명령을 다시 확인하고 영향을 받는 파일·소비처 목록을 고정한다. 기존 로컬DB는 보존하며 운영에는 접속하지 않는다.
2. 최신 factory를 유지하면서 Dockerfile 기본 CMD를 해당 factory로 변경한다. Compose 단독과 이미지 단독 모두 최신을 선택하도록 한다. `compose.two-cycle.yaml`과 기존 factory import 이름은 첫 구간에서 호환 입구로 남겨 명령 사용자를 깨뜨리지 않는다.
3. 최신 factory가 기본 앱의 route를 복사하는 의존을 분리한다. 공통 라우터 등록을 재사용하고 기존0023 앱은 명시적인 `create_legacy_app()` 회귀용 factory로 옮기는 안을 적용한다. 초기에는 기존 `app` import의 테스트 의존을 보존하는 호환 alias를 유지하고 생산 실행 CMD로 선택하지 않는다. 최신 앱이 legacy 객체의 수명/worker 설정에 의존하지 않게 한다. API method/path·operation ID·DTO·인증 dependency override 격리를 보존한다.
4. `check_openapi` 기본 profile을 최신으로 바꾸되 legacy 명시 옵션과 두 계약 검사를 유지한다. 시험 fixture의 legacy 선택을 명시하고 기존 DB0023·원 ACK·전환 보존 시험을 유지한다. 최신DB에서 공통 기능 시험을 보강하며 전체 fixture를 무조건 최신 head로 바꾸지 않는다.
5. 환경/README·검증 도구·fresh override·CI·운영 명시command 참조를 함께 정리한다. 단독 Compose 기본 기동은 최신 앱을 뜻하지만 **빈DB의 migration까지 자동 수행하지 않는다.** 기존DB 재기동/빈DB 설치/백업 복원을 각각 안내한다.
6. 시작 실패는 빈스키마/미지원revision/권한·연결 문제를 비밀 없는 제한된 code로 식별하도록 제안한다. 기존 안전 formatter를 풀어 원문 예외/접속문자열을 출력하지 않는다. F03 장애 추적과 겹치는 변경만 조정하고 외부 HTTP 오류 계약 확대는 별도 협의한다.

### B. 과거 실행 경로의 추가 제거

A의 검증 후 legacy 앱·별도 계약·구 processor·시험 도구의 각 참조를 다시 분류한다. 최신DB에서 대체되는 회귀를 이관하고,0023→최신 보존/ACK·복구 역사 시험은 독립 유지한다. 과거 baseline 전체 계약을 계속 생성해야 하는지, 고정 snapshot과 migration 시험으로 충분한지 근거를 정리한 뒤 별도 구현 구간으로 선택한다. 제거 시 v1 호환 adapter·데이터 reader·migration 파일을 연쇄 삭제하지 않는다. 현재는 제거 완료일이나 전체 삭제를 확정하지 않는다.

### 실패·복귀·운영 경계

- 빈DB는 연결 대상과 public 테이블·revision을 먼저 확인하고 명시적 신규 준비를 한다. 기존DB는 현재 revision과 지원 범위를 확인하며 낮은 단계라고 자동 upgrade·downgrade·stamp·초기화하지 않는다.
- 최신DB를 기본0023 앱으로 되돌리는 것은 rollback이 아니다. A의 변경에서 문제가 나면 같은DB와 호환되는 직전 two-cycle 이미지/명시command를 사용한다. 데이터 손실을 수반하는 snapshot 복원은 하지 않는다.
- 로컬 검증 실패·API/권한 차이·worker 중복·보존 불일치가 있으면 인계를 멈추고 관련 변경을 수정한다. 운영은 승인된 별도 릴리즈에서만 반영하며 기존 동결 Compose·기존 Release를 소급 수정하지 않는다. 구 이미지가 아닌 DB호환 최신계열 이미지의 복귀 가능성을 먼저 확인한다.

## 6. 향후 검증 시나리오·완료 조건·근거 링크

### 구현 구간에서 실행할 검증

| 시나리오 | 통과 조건 |
|---|---|
| 빈DB 신규 설치 | 격리 PostgreSQL17에서 명시적0035 준비 후 기본 Compose·이미지 CMD가 최신으로 기동. 테이블 미준비 시 자동쓰기 없이 안전한 원인 식별. |
| 기존 최신DB 재기동 | 별도 합성/복원 시험DB에서 DB/키/볼륨 유지·준비 검사·API/DB health·worker processor 선택 확인. 기동만으로 migration하지 않음. |
| 미지원DB·권한/연결 오류 | 알 수 없는/미지원 중간revision은 명확히 거절하고 우회·자동변환 없음. 시작 실패를 비밀 없이 구분. |
| 계약·공통 기능 | 두 전체 생성 계약 및 참조 schema 비교. 최신DB의 인증·계정·소유/그룹·개인원장·batch 권한/타인거절/멱등성 회귀. |
| 모집 호환 | v1 C 투영·신규 위험쓰기 거절·원 ACK 복구·v2 C/N·주차/세대·일정/완료·비활성 보존·그룹정책 회귀. |
| 수명/분리 | 단일 앱만 해당 모집 processor를 시작. 인증·분쟁 작업과 종료/취소 보존. 시험 앱의 dependency override와 worker 설정 격리. |
| 도구·CI·배포 | 두 contract gate·회귀 분할·기본 profile·fresh 구성 확인. 운영 구성과 기본 최신 의미 일치, 자동 migration 금지·이미지/DB 호환·복귀 보호 유지. 배포 제어 smoke는 실제 앱DB 검증과 구분. |

**최종 단일화 완료 조건:** 기본 명령으로 최신 앱을 선택하고 신규/기존 환경 안내가 일치하며, 필요한 과거 실행은 시험용임이 명시돼야 한다. 최신 공통기능·모집/API 호환·DB/ACK/이력 보존과 CI 영향 검증을 통과하고, 남은 구 실행 경로는 유지 이유·제거 선행 조건이 추적돼야 한다. 코드 통합·로컬 실행·운영 배포·실회원 인수는 따로 보고한다.

이번 조사에서는 코드/계약/이력 정적 확인과 문서 검증만 수행했다. 기능 테스트·Docker build/기동·DB 조회/migration·실회원/provider·기기·운영 검증은 실행하지 않았다. 사용자 로컬 결과와 과거 보고된 시험을 이번 신규 통과로 합산하지 않는다. `.env`·키·개인정보 원본은 읽거나 게시하지 않았다.

다음 담당은 Backend이며 개발자가 이 후속 구간을 선택하면 A의 대체/참조 확인과 최소 검증부터 진행한다. 조사 상세는 이 문서에만 유지하고 [개선 대장](../../project/backend-improvement-plan.md#runtime-consolidation)·[다음 실행](../../project/NEXT_WORK.md#runtime-consolidation-followup)·[조사 이력](../../project/DEV_LOG.md#runtime-consolidation-review)에서 연결한다.
