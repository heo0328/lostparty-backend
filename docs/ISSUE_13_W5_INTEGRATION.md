# Issue #13 W5 — 통합 검증·성능·전환 준비

2026-10-22 / Backend / `feat/raid-recruitment` / 시작 `fff8806`.

AGENTS → 협업 → NEXT_WORK → AI_CONTEXT → 계약3판/4판/ACK를 확인했다. 공식 Issue 본문/전체89댓글은 [전체89번째 Backend · W4-D 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330758804)까지이며 새 요청/계약 변경·사용자 미커밋 변경은 없었다. 고정0.4.1/policy two-cycle-contract-4·53경로/56동작/204schema를 유지한다.

## 검증 상태

전체18파일 **303PASS/1855.45초** 후 리더 표시 이력 조회를 좁힌 최종 소스의 관련4파일 **31PASS/334.92초**·양 실행 종료0을 확인했다. 중복30을 제외한 **고유304PASS(신규7 포함)**다. 최종 단일304개 실행으로 확대하지 않는다. 예비29PASS 등은 중복 합산하지 않았다. 기존 BlockingPortal deprecation1건 외 최종 미해결 실패는 없다. 기본/준비 runtime 계약 전체 일치·변경 AST/JSON/문서 링크/diff 검사도 통과했다. 전용 runner·tmpfs DB/network만 정리했고 실제 개발 DB/API 이미지는 변경하지 않았다. 구간 commit/push·공식 게시 준비다.

## 이번 구간

- 검색 페이지를 SQL로 먼저 결정한 뒤 선택된 최대50개 actual cycle/generation의 리더·표시·본인 역할·정확한 lease 기반 인원 수·아이템·활성 그룹/세션을 요청 내부에서 묶어 읽는다. single-card 경로와 같은 값을 사용하며 응답/계약 변경은 없다. 프로세스 전역 캐시·회원 간 재사용은 도입하지 않는다. generation1은 실제 room/key, 재개 세대는 정확한 generation별 그룹 연결을 사용하고0025 단계 조회도 유지한다.
- 재개가 반복돼도 리더 표시의 과거 Assignment 전체를 가져오지 않고 기존 단건과 같은 첫 표시만 읽는다. 이력 증가와 무관하게 반환 행 수가 일정한지를 검증한다.
- 50개 합성 방·두 주차, 공개/그룹25개씩·그룹 페이지7개, 최대8인, 두 아이템/두 세션과 N취소→재개세대2를 원래 카드 조회와 대조한다. 익명/다른 회원·본인/리더의 역할/권한과 READ ONLY/전체 행·시각 불변을 검증한다.
- 50캐릭터·두 주차500summary의 SQL 수/반환 행 수/응답 크기/p50·p95와 현재 세대 근거 조회의 추가 비용을 측정한다. 기존 투영과 값이 같은 참가 자료를 사용하며 declined/review 새 정책의 회귀는 W4-D 시험으로 구분한다.
- 비어 있지 않은 legacy0023 자료·원 성공 ACK가 있는 상태의0024→0029 전체 이행에서 기존 모든 열/기록 시각·review/legacy_unknown과 원 ACK를 보존한다. 제한 LOGIN에서 새 준비검사와 worker의 review 자료 무변경을 확인한다.
- 준비 factory의 실제 JWT 인증으로 생성 context→C/N 묶음 생성/동일키 ACK→B의 N참가→회원별 카드/계정summary→C 접근 거절·disabled 회원 차단을 검증한다. 기본 앱과 준비 앱의 실행 OpenAPI 전체 비교 및 고정 명세 검증을 수행한다.

## 측정 방법·한계

전용 `lostparty-w5-test` tmpfs PostgreSQL17과 cached 시험 이미지의 최신 소스/제한 LOGIN·합성 자료다. 실제 개발 서버/provider/기기는 측정하지 않는다. 방50개 검증의 그룹 한도는 합성 test-server 권한으로60으로 설정하며 로그인 자료 준비 때만 인메모리 throttle을 비운다. 업무 API의 한도/권한을 우회하지 않는다.

각 항목은 동일 자료/환경에서 warm-up2회 후12회 순차 호출한다. p50=중앙값, p95=nearest-rank12번째 표본이다. 측정 대상은 서비스 함수 호출 시간으로 HTTP 네트워크/JWT 검증·서버 부하가 아니다. 응답 bytes는 서비스 결과를 jsonable_encoder/compact JSON UTF-8로 직렬화한 크기이며 실제 HTTP 바이트와 구별한다. 묶음/두 세션 항목은 양측 모두 합성 actor 조회2SELECT를 호출 어댑터에 포함하고, 다른 항목은 actor를 미리 조회한다. 항목 간 절대값을 같은 HTTP 요청 비용으로 비교하지 않는다. 호출한 실행 thread의 SELECT 수와 psycopg cursor.rowcount의 반환 행 수 합계를 측정한다. 별도 cleanup thread의 SQL은 해당 요청 비용에 섞지 않는다. SET/transaction과 DB 내부에서 검사한 모든 행 수는 이 수치가 아니다. EXPLAIN(ANALYZE,BUFFERS,JSON)은 마지막 표본의 SELECT를 같은 DB에서 별도 실행하고 root rows/추정 rows·실행시간/버퍼를 집계한다. 50방 자료는 ANALYZE 후 측정한다.

검색 baseline은 동일 SQL 필터/정렬/페이지·스냅샷에 기존 per-card loader를 적용한 경로다. 쓰이지 않던 persistent membership 단건 조회 제거는 이 기준 경로에도 공통 적용되어 있다. 이전 커밋 전체/별도의 구 실행 이미지·DB23과 새 이미지·DB29를 그대로 비교한 결과는 아니다. summary baseline은 동일0029 자료에서 이전 cycle_evidence 없는 투영이며 새 declined/review의 정확성을 희생한 최적화 대안으로 사용하지 않는다. 예비 실패/중복 통과는 최종 집계에 더하지 않는다. 시간은 합성 환경 표본이며 일반 SLO/비용0을 보장하지 않는다.

재현: 전용 시험 컨테이너 안에서 requirements-dev의 jsonschema를 준비한 Python으로 다음을 실행한다. 실제 개발 Compose를 시험 대상에 재사용하지 않는다.

```bash
W5_REPORT_DIR=/tmp/w5-reports python -m pytest -q -s \
  tests/test_recruitment_cycle_performance.py \
  tests/test_recruitment_cycle_integration.py
```

집계 JSON은 SQL/파라미터·개인/인증 원본 없이 aggregate/plan 수치만 기록한다. 최종 소스 측정값을 아래와 저장 artifact에 기록했다. 예비 과정에서 합성 로그인 throttle/그룹 기본15인 한도·datetime 직렬화 준비를 바로잡았고, 통합 실행에서 다른 cleanup thread의 SELECT FOR UPDATE까지 계측되던 부분은 호출 thread로 한정했다. 업무 코드를 우회하거나 READ ONLY를 해제해 EXPLAIN을 실행하지 않았다.

## 최종 소스 측정값

[집계·EXPLAIN artifact](design/issue13-w5-performance.json). 모든 값은 위 합성 환경/방법 기준이며 전후 비교에서 동적 서버시각만 제외했다. 응답 크기·내용 일치와 회원/그룹·세대 격리를 함께 확인했다.

| 항목 | SELECT 전→후 | 반환 SQL rows 전→후 | JSON bytes(동일) | p50 ms 전→후 | p95 ms 전→후 |
|---|---:|---:|---:|---:|---:|
| C 50카드 | 507→15 | 356→306 | 80,774 | 255.558→19.583 | 271.942→95.465 |
| N 50카드 | 507→15 | 356→306 | 80,723 | 250.186→18.616 | 264.121→20.996 |
| 그룹 7개 페이지 | 80→18 | 109→102 | 12,045 | 44.256→17.511 | 46.834→19.115 |
| 8인 방 | 19→15 | 16→12 | 1,936 | 11.177→10.616 | 12.764→13.106 |
| 2아이템/2세션 | 21→17 | 22→18 | 2,368 | 12.683→11.294 | 14.938→13.24 |
| 50캐릭터/500summary | 10→13 | 60→63 | 292,106 | 13.896→16.231 | 15.09→18.067 |

50카드 검색은1개/50개 결과에서 SELECT 수가15로 일정하다. summary도1캐릭터/50캐릭터에서13으로 일정하며 실제 세대/declined 검증의3개 추가 SELECT와 시간 증가는 제거하지 않았다. 단일8인 방 p95는12.764→13.106ms로 소폭 증가했고, C50카드 최댓값95.465ms와 N20.996ms의 변동도 그대로 기록했다. 모든 요청의 시간 개선이나 SLO를 약속하지 않는다. 반복 재개3회의 실제 이력을 쌓아도 카드 loader의 반환 rows가 증가하지 않고 기존 첫 표시와 같음을 확인했다.

EXPLAIN root의 실제/추정 rows·버퍼는 artifact에 기록한다. 표본 수12의 p95는 최댓값이므로 호스트 스케줄링/백그라운드 작업 변동을 일반 지연 보장으로 해석하지 않는다.

고정·기본·전환 준비 세 OpenAPI 문서를 별도 도구 venv의 openapi-spec-validator0.7.2로 정식 검증했다. 두 runtime 전체 객체 비교, 고정84합성/CAS6쌍/공통ACK2흐름·canonical SHA 불변, DTO 재생성 바이트 일치(SHA256 `7cc60c15569f3a3d6c0e0429aed16406e3be5f0d28f4bd51c2aba0ffa599cd7a`)도 통과했다.

## 실제 개발 환경 조회·전환 경계

읽기 전용으로 확인한 실행 대상은 `lostparty-backend-api-1`/`lostparty-backend-db-1`, DB `0023_recruitment_resume`다. 현재 API 이미지 ID는 `sha256:efde69d269a405358d99a45b1a2bbf243b0cb3f1408a29d878ee05e759d2b5fb`, 실행 명령은 `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers`, health는 healthy다. **실행 이미지에는114경로·새 factory 없음**을 확인했다. 소스 기본116/준비167경로를 실행 서버의 현재 상태로 표기하지 않는다. 실제 DB 이행/API 재생성·stop/restart·자료/키 변경은 하지 않았다. 추가 aggregate 조회에서 모집 방7개(활성7, migration_state=legacy_review_required 0), Assignment7개(활성0)를 확인했다. 빈 DB가 아니며 이 수치를 실제 자료의 전환 가능/원천 자격 증명으로 쓰지 않는다. 인증 키 mount는 `/run/secrets` 읽기 전용 bind다.

다음 전환 구간에서 준비할 구체적 순서:

1. 적용할 검증된 source SHA/이미지·대상 DB23·실행 설정과 본인 인증 키 mount를 대조한다. Compose 원본의 DB volume과 `.secrets` mount를 보존한다. 원본 비밀/사용자 자료는 문서·로그·Issue에 출력하지 않는다.
2. 실제 자료의 legacy_unknown/review 규모와 사용 가능 projection/차단 동작을 집계해 기존 앱의 영향과 Flutter 적용 순서를 확정한다. unknown을 명시 세대로 승격/동의 복원하지 않는다. 현재 합성 측정은 실제 자료 조사/인수의 대체가 아니다.
3. 대상별 승인 범위를 확인한 뒤 구 API와 모든 worker를 정지해 이행 중 쓰기를 막는다. DB/키 보존 백업과 별도 DB 복원 검증·복구 지점을 준비한다. 백업 파일 존재만으로 복원 완료를 표시하지 않는다. DB23 이미지로 DB29를 읽는 혼용/강제 downgrade를 복구로 쓰지 않는다.
4. [compose.two-cycle.yaml](../compose.two-cycle.yaml)은 검토 가능한 명시 진입점 override다. 기존 Compose에 이 파일을 더하면 API command만 factory로 바꾸고 DB volume/키 mount·보안·포트/health 설정은 유지한다. 이 파일은 생성/정적 검증만 했으며 실제 실행하지 않았다. 보존 검증한0023→0029를 적용하고 준비검사/원천 보존을 확인한다. 검증된 이미지에서 `uvicorn app.main:create_two_cycle_app --factory`를 선택하고 구 worker가 함께 돌지 않게 한다. 단순 factory 생성은 이행/배포가 아니다.
5. health·DB29 readiness·167경로의 이미지 내 계약 전체 비교·no-store/인증/기존 v1 읽기와 쓰기 upgrade·원 ACK·C/N·06/10시·review 차단을 검증하고 실행 SHA/게시 상태를 기록한다. 문제가 생기면 승인된 복구 지점/데이터 영향에 맞춰 중단/복구하며 forward 이력을 강제 재작성하지 않는다.
6. 실제 소비 가능한 서버 주소/실행 SHA·계약과 미확인 범위를 같은 Issue로 전달하고 Flutter에 필요한 메타/summary·주차 선택/계정 캐시 격리·v1 변경 검증만 요청한다. Flutter 적용·실회원/provider·기기·운영 인수는 별도 결과를 받아 기록한다.

현재는 이 계획 준비와 소스/격리 검증 구간이다. 실제 전환 승인 요청/실행·새 서버 Flutter 시험 요청은 하지 않는다. 다음 담당과 최종 통과/게시 근거는 [NEXT_WORK](project/NEXT_WORK.md)·[DEV_LOG](project/DEV_LOG.md)에 기록한다.
