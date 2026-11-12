# Backend 실행 설정·명칭 정리

2026-11-13 / `refactor/backend-runtime` / 기준 dev `ffda8db8a00e50719b104605225dc5249f4ae171`。사용자 승인 범위는 실행·명세·도구·안내 정리와 격리 검증 후 로컬 API 교체다. 이후 사용자 직접 지시로 구현 `8a54c485` 커밋과 로컬 dev `e1e81b76` 병합을 완료했다. push·운영 배포는 별도 지시 대상이다.

## 이름과 실행의 대응

| 역할 | 변경 전 | 변경 후 |
|---|---|---|
| 일반 ASGI 시작점 | `app.main:app` = DB0023 앱 | `app.main:app` = 현재 앱 |
| 현재 앱 factory | `create_two_cycle_app()` | `create_app()` |
| DB0023 재현 factory | 전역 `app` | `create_legacy_app()` |
| 개발 실행 | Compose + two-cycle override | `docker compose up -d --no-deps --build --wait api` |
| 운영 실행 설정 | `create_two_cycle_app --factory` | `create_app --factory`（설치 운영 반영은 별도） |
| 현재 계약 | `openapi/two-cycle.openapi.yaml` | `openapi/openapi.yaml` |
| 과거 계약 | `openapi/openapi.yaml` | `openapi/legacy.openapi.yaml` |

`two-cycle`은 당시 현재주/다음주 구현을 구분하던 실행 이름이다. `0035_cycle_group_policy`, `0036_roster_presence`는 DB 구조 이행의 순서와 목적을 나타내는 Alembic 식별자다. 서버 두 개나 DB 두 개가 필요하다는 뜻이 아니다. migration 파일은 누적 이력이므로 이름을 바꾸거나 단일 파일로 합치지 않는다. 업무상 `cycle`도 유지한다.

## 앱 조립과 호환 경로

현재·legacy는 공통 라우터·health·오류 처리·인증·CORS·no-store 등록 함수를 이용해 각각 만든다. 다른 앱 객체의 라우트를 복사하지 않으며 dependency override와 명세 캐시는 앱별이다. 현재 worker는 인증·소유권·현재 모집 한 벌이고 legacy는 과거 모집 processor를 사용한다. 정상/예외 종료 모두 세 task를 취소하고 기다린다. 앱 생성과 OpenAPI 생성은 worker를 시작하지 않는다.

`create_two_cycle_app()`은 `create_app()`에 위임하는 호환 함수다. `compose.two-cycle.yaml`은 같은 `api` 서비스를 덮어쓰는 호환 파일이며 별도 서버를 추가하지 않는다. 기본 실행의 필수 파일에서 제외했다. 외부 명령·설치 환경과 남은 시험 import가 새 이름으로 전환됐다는 근거를 확인한 뒤 제거한다. 지금은 옛 이미지/명령 복귀와 기존 시험 소비를 지원한다.

`create_legacy_app()`·legacy 명세는 DB0023 회귀, 원 ACK/이력 보존 및 당시 복구 재현을 위해 유지한다. 제거하려면 해당 검증을 대체할 근거가 필요하다. legacy 앱으로 DB0036을 실행하는 것은 복귀 방법이 아니다. 현재 앱의 v1 adapter·구 데이터 reader를 과거 서버와 혼동해 삭제하지 않는다.

## 시작과 DB 준비

[개발 환경](environment.md)의 기본 Compose와 fresh는 현재 이미지 CMD를 사용한다. 운영 Compose도 같은 현재 factory를 선택하며 HTTPS/Caddy·신뢰 프록시·worker1·운영 키 경로와 보안 설정은 유지한다. fresh는 별도 프로젝트/볼륨/8001을 사용하고 DB host port는 게시하지 않는다.

시작은 읽기 준비 검사만 수행한다. 빈 DB·미지원 중간 단계는 거절하고 자동 migration·downgrade·stamp·legacy fallback을 하지 않는다. 신규 설치는 확인한 빈 DB에서만 명시적으로 Alembic0036까지 준비한다. 기존 DB는 현재 단계와 이미지 호환성을 확인한 뒤 API만 교체한다. 기존 readiness가 지원하는 현재 계열 단계0029~0036을 이번 이름 정리로 변경하지 않았다.

## 계약과 도구 참조 조사

현재192경로/213동작과 legacy125경로/142동작의 JSON 원문 바이트·전체 객체를 그대로 이동했다. 경로·메서드·operation ID·DTO·인증 경계는 변경하지 않았다. 현재 원문 SHA256은 `3fdc06616d64e19aa7abf35b548cf1156fa7fbee6bcfb02c1dccf4ce9a9d7052`, legacy는 `18491bc066d08a578aa9228cd0da85eee508288c28d14d563d788e73e324c3dd`다.

| 참조 대상 | 처리 |
|---|---|
| check_openapi / isolated_checks / API map | 현재 파일·factory 기본. `--profile legacy` 명시 선택, 기존 `two-cycle` profile은 현재 alias. 교체 전 구형 이미지의 명칭도 읽기 지원 |
| 기존 테스트·conftest | 이전 전역 app 소비는 `create_legacy_app()` 명시. DB fixture·업무 기대값 유지 |
| 최신 기능 테스트 | 기존 호환 factory도 동일 현재 앱. 새 실행 시험은 `create_app()` 사용 |
| release / deployment / maintenance | release.json schema2 생성·schema1 읽기 유지. [전환 설계](../operations/runtime-release-transition.md) |
| README·현재 환경/검증 안내·기능별 명세 링크 | 현재/legacy 목적에 맞는 파일로 전환 |
| archive·동결 계약·Native 고정 commit/hash·기존 Release | 내용/식별자 보존. 로컬 Markdown 링크 목적지만 유효 경로로 교정 |
| recruitment_snapshot / recruitment_restore_preflight | DB0023→0029 당시 복원 리허설. legacy 생성만 명시하며 옛 이미지 fallback 지원. prepared의167경로 단정·과거 DB 조건 유지 |

마지막 두 복원 도구는 최신 DB의 일반 복원 명령이 아니다. 현재 DB 보존 검증은 새 격리 시험과 로컬 교체 전후 비교로 수행한다. 과거 재현 목적을 없애기 위해 검증 수치를 최신 값으로 바꾸지 않는다. 저장소 전체 시작점/파일명 검색에서 남은 옛 이름은 호환 함수·시험/복귀·형식1·과거 고정 기록으로 분류했다.

## 검증·반영 결과

2026-11-13 로컬 API 반영 완료. [실행·보존·검증 집계](../operations/records/runtime-consolidation-local-rollout.json)에 image/source manifest·HTTP·시험 구성을 기록했다. 현재 이미지는 `sha256:170d3a2505963e37a910bfc463092ab92239b607ff755f271aa28f639a3601bb`, 앱291파일과 저장소의 앱 파일 전체가 같다.

| 검증 | 결과 |
|---|---|
| 전체 앱 회귀 | 고유2,001PASS. 초기998PASS 후 정상 SIGINT로 분할, 나머지366/325/311PASS에서 중복12개 제외해 원래1,988개 전체 포함. 추가 현재DB 공통13PASS. 한 차례 전체 green으로 표시하지 않음 |
| 최종 캐시 보완 | 관련4파일 58PASS, 두 전체 계약·반복 생성/캐시 초기화·후보 이미지 재생성 일치 |
| 도구·정적 | 84PASS·의존성/문서/보관본문/동결JSON 검사 PASS |
| 배포 호환 | 형식1/2·구/신 이미지 probe·기존/신형 실제 Docker 교체/실패 복귀·실제 합성 DB0035→0036 maintenance probe PASS |
| 실제 로컬 | 기본 Compose 단독·`app.main:app`, API/DB healthy·실제 HTTP·두 생성 명세 전체 일치 |
| 보존 | DB컨테이너/볼륨·118표 982행 전체 hash·DDL·sequence·DB0036·환경/키4개·포트/mount/보안 설정 동일 |

첫 교체에서 반복 OpenAPI 호출의 중복 가공을 발견해 직전 image/명령으로 자동 복귀했다. 복귀 후에도 전체 행·DDL·sequence·키/환경 동일성을 확인했다. 완성된 명세를 앱별로 캐시하고, 캐시 삭제 후 재생성·타 앱 생성 이후 반복 호출까지 계약 보존을 확인해 재반영했다. 현재/legacy 명세 원문은 수정하지 않았다.

현재 앱/DB0036의 로그인·refresh·권한·설정/원ACK·원정대/소유·bootstrap·그룹·개인원장 시나리오는 기존 시험을 새 현재 앱/DB에서 재사용했다. 기존0023 fixture·업무 기대값과 migration 보존 시험은 유지했다. worker는 선택한 모집 processor 한 벌만 시작하고 오류 종료 시 세 task를 취소한다. 실제 로컬 worker 관찰 결과는 위 집계에 연결한다.

기존 AnyIO deprecation·SQLAlchemy null PK 경고는 유지했다. 정상 provider/기기·운영 인수와 과거0023→0029 원본 복원 리허설은 이번에 재실행하지 않았다. 운영은 기존 v2.1.1/DB0036이며 다음 배포 포함 기능/도구/복귀는 [운영 전환 안내](../operations/runtime-release-transition.md)를 따른다. 구현 `8a54c485`은 로컬 dev `e1e81b76`에 병합했다. 미push이며 main·운영 배포는 변경하지 않았다. 원격 게시 확인 전까지 작업 브랜치를 보존한다.
