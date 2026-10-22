# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

[W5 통합·성능·전환 준비](../ISSUE_13_W5_INTEGRATION.md)의 자동 검증/검색 보완 구간 완료: 전체303PASS/1855.45초 후 최종 보강31PASS/334.92초(중복30 제외·고유304, 신규7 포함). 두 runtime 계약 전체 일치·세 문서 정식 OpenAPI 검증·고정 계약/DTO 검증·Compose override 정적 비교 통과. 구간 commit/push·원격 확인·공식 Issue 게시를 마치고 아래 실제 전환 준비로 이어간다. 실제 개발 서버/DB 전환·Flutter 적용은 미실행이다.

착수/인계 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 계약3판/4판/ACK를 읽고 Issue 본문/최신 댓글·Git/코드를 확인한다. 최신 공식 조회는 [전체89번째 Backend · W4-D 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330758804) 이후 추가 요청 없음이다. 계약0.4.1/policy two-cycle-contract-4를 유지한다.

## 다음 Backend — 실제 전환 준비·소비 가능한 구간 인계

1. **실제 상태/자료 영향 재확인**: 조회한 개발 대상은 DB0023·API114경로/새 factory 없음·healthy, 방7개/Assignment7개(활성 Assignment0)다. 인증 키 mount는 `/run/secrets` 읽기 전용이다. 소스 기본116/준비167과 다르며 실제 상태/자료를 임의로 새 세대·동의로 승격하지 않는다. 기존 자료의 legacy_unknown/review 영향과 소비 가능한 조회/차단 범위를 집계해 Flutter 적용 순서를 구체화한다.
2. **대상별 복구/전환 계획 확정**: [W5 전환 순서](../ISSUE_13_W5_INTEGRATION.md)의 검증된 source/이미지·DB23→29·자료/키 보존·백업/별도 복원 검증·구 API와 모든 worker 정지·시작/health/계약·복구 지점을 확인한다. [compose.two-cycle.yaml](../../compose.two-cycle.yaml)은 API command만 factory로 바꾸는 정적 검증 완료 override이며 실제 실행하지 않았다. 기본 `app.main:app`은23, `app.main:create_two_cycle_app`은29 전체 준비검사+새 worker/v1 adapter다. 실제 변경의 대상·영향/승인 범위를 확인하고 미승인 DB/서버 전환을 임의 실행하지 않는다.
3. **실제 소비 증명 후 Flutter 인계**: 실제 경로/실행 SHA·고정 계약·확인한 동작·미확인 범위를 준비하고 commit/push·원격 확인 후 같은 Issue로 메타/summary·주차 선택·계정 캐시 격리와 필요한 구간만 요청한다. v1 위험 방 쓰기409 CLIENT_UPGRADE_REQUIRED·원 ACK 우선·본인 수동 C/수10시와 개인표 유지 차이를 포함한다. 현재 소스 게시만으로 새 서버 시험을 요청하지 않는다.
4. **결과 구분**: 이번은 자동 통합/성능·전환 진입점 준비 완료다. W5 전체의 실제 서버 전환/소비 인계·Flutter 적용·실회원/provider/기기·운영 인수는 미완료다. 추가 제품 입력/동일 계약 재회신 대기는 없고 #19 통계는 별도 후속이다.

## 유지할 기준

- 06시 N→C는 같은 실제 UUID/세대·리더/순번·Assignment/세션·동의/예약이다. 새 N 자동 생성/가입0, 지난 실제 T만 정리하며 부적격/unknown source는 증거·lease를 보존해 review로 둔다.
- G1은 C 행이 없을 때만 N이다. 공통/전역 GlobalScope·persistent CAS/영향0·120초 context/원 ACK·완료 이력을 보존한다. GET/summary는 READ ONLY이며 실제 참가/점유가 현재 세대 declined/legacy intent보다 우선한다.
- 추가 DDL/계약 변경은 없다. 고정53경로/56동작/204schema·canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`을 유지한다. 기본116/준비167경로는 소스 계약이고 실제114경로 이미지는 미전환이다.
- [측정 artifact](../design/issue13-w5-performance.json)는 합성 자료·서비스 호출/SQL 반환 rows/compact JSON bytes 기준이다. 구 실행 이미지 전체/실제 서버·provider/기기 성능이나 SLO를 대체하지 않는다. 검증/게시 이력은 [DEV_LOG](DEV_LOG.md) 기준이다.
