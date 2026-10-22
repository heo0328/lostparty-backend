# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

[W4-D 전환·v1 호환·활성화 준비](../ISSUE_13_W4D_CUTOVER.md) 구현/격리 검증 완료: 관련7파일151PASS/611.48초(신규16 포함), 기본116/준비167경로 실행 계약 전체 일치·고정 계약/DTO 검증 통과. 구간 commit/push·원격 확인 및 공식 Issue 결과 게시를 마치고 아래 W5로 이어간다. 실제 개발 서버/DB 전환·Flutter 적용은 미실행이다.

착수/인계 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 계약3판 전환 기준/4판/ACK 보완을 읽고 Issue 본문/최신 댓글·Git/코드를 확인한다. 최신 조회는 [전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057)이며 새 Flutter 요청/계약 변경·추가 제품 입력 대기는 없다. 계약0.4.1/policy two-cycle-contract-4를 유지하고 구간 종료 시 검증·문서·commit/push·GitHub 기록을 한다.

## 다음 W5 — 통합 계약·보존/경합·성능·실제 인계

1. **전체 실행 계약/통합**: 고정53경로/56동작/204schema와 준비 앱167경로/전체56개 operation ID·실제 HTTP/DB 효과를 대조한다. 기본 앱116경로·v1 수동 완료10시/원 ACK 설명 및 PLAY_NOT_STARTED enum과 [전환 준비 계약](../../openapi/two-cycle.openapi.yaml)을 구분한다. `scripts/check_openapi.py --profile legacy|two-cycle`은 선택한 런타임 객체 전체를 비교한다.
2. **보존/경합**: 제한 LOGIN·격리 PostgreSQL의0023→0029와 원래 행/열·시각·legacy_unknown/review 보존, C/N·세대·현재/과거 완료·declined/일반 참가/다른 방 점유, worker/명령 경합·06/10시·원 ACK를 통합 검증한다. 옛 N의 생성일이 이전 C에 속한다는 이유로 제안/예약을 폐기하지 않는다. review 자료에 임의 실행 기본값·예약/동의를 채우지 않는다.
3. **성능**: 동일 합성 자료에서 구 기준/신규 SQL 수·rows·응답 bytes·p50/p95·EXPLAIN을 측정하고 비교한다. 최대8인·묶음/복수 세션·50캐릭터/두 주차500summary·그룹 필터/페이지와 앱별 캐시/계정 격리를 포함한다. 측정 없이 비용0/예상ms를 약속하거나 자동 테스트를 실제 provider/기기 성능으로 보고하지 않는다.
4. **실제 소비 준비/전환**: 먼저 실제 대상 DB revision·기존 이미지/설정·진입점·자료/키 보존 상태를 필요한 범위에서 조회하고, 대상별 이행/복구·구 API/모든 worker 정지 후 동시전환·계약/health 검증 계획을 구체화한다. 기본 `app.main:app`은0023, 전환 factory `app.main:create_two_cycle_app`은0029 전체 준비검사+새 worker/v1 adapter다. factory 생성이나 소스 게시 자체는 DB 이행·배포가 아니다. 실제 변경 대상/영향·기존 승인 범위를 확인하고 미승인 실제 DB/서버 전환을 임의 실행하지 않는다.
5. **Flutter 인계**: 실제 소비 가능한 의존/서버·고정 SHA/계약·미확인 범위를 준비한 뒤 구간 commit/push·원격 확인을 먼저 하고 같은 Issue에 필요한 테스트만 인계한다. v1 구 방 쓰기409 CLIENT_UPGRADE_REQUIRED, 본인 수동 체크/false 정정의 C/10시와 원 ACK 우선, 안전한 개인 시간표 유지 차이를 알린다. 현재 후보 소스 게시만으로 새 서버 시험을 요청하지 않는다.

## 보존 기준

- 06시 N→C는 같은 실제 UUID/세대·리더/순번·Assignment/세션·동의/예약이다. 새 N 자동 개방/가입·옛 auto_open_enabled/choice를 동의로 전용하지 않는다. 지난 실제 T만 worker가 정확히 정리하고 현재 부적격 명시 source는 자리/lease 증거를 유지하며 review로 분류한다.
- T 설정·편성·제외/일정·완료와 persistent 전역 효과를 구분한다. G1은 C 행이 없을 때만 N 리더이며 closed/review C를 N으로 메우지 않는다. GlobalScope·persistent CAS/영향0·120초 context/원 ACK·완료 이력을 유지한다.
- GET/summary는 READ ONLY다. 실제 참가/다른 방 점유가 해당 주차/세대의 declined/legacy intent보다 우선하며 unknown/review 점유는 confirmed가 아니다. legacy choice GET는 실제 T projection이며 빈 N을 만들지 않는다.
- 추가 DDL은 없다. 저장 head는0029, 옛 worker는0023만/새 worker는0029만 허용한다. 기본 앱116경로와 준비 앱167경로(신규 후보51경로/54동작+기존 메타/summary2동작)를 구분한다. 원본 고정 명세 canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`은 유지한다.
- 실제 개발 DB/API 이미지·서버/provider·실회원/기기·운영·Flutter 적용/인수는 별도 미완료다. #19 통계는 별도 후속이다. 검증/게시 상세는 [DEV_LOG](DEV_LOG.md)·각 구간 기록을 따른다.
