# 다음 실행

2026-10-21 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

W1/W2 `917123e`·W3 `13b655e`·[W4-A1](../ISSUE_13_W4A1_SUBMISSION_CONSENT.md) `6d2b301`의 구현/검증·push를 완료했다. 이번 [W4-A2 일정 조율·제안/투표](../ISSUE_13_W4A2_CYCLE_PLANNING.md)까지 구현·격리 검증하고 구간 commit/push·원격 확인 후 공식 Issue에 기록한다. 게시 SHA/댓글은 해당 기록·DEV_LOG를 따른다. 다음은 **Backend W4-B 완료/정정·현재주 재개**다.

작업 시작 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 관련 계약을 읽고 Issue 본문/최신 댓글과 Git·코드를 대조한다. 최신 확인 댓글은 [전체85번째 Backend · W4-A1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6314976554)이며 계약0.4.1/policy two-cycle-contract-4 고정이다. 추가 제품 입력·Flutter의 동일 계약 재검토 대기는 없다. 사용자 지시로 섹션 완료마다 검증·문서 갱신·commit/push·GitHub 기록을 수행한다.

## 다음 W4-B 작업

1. 고정 전체 명세의 완료 context·개인 item 완료·공대장 완료·방 전체 이번주 미완료 종료·수동 완료 정정·현재주 재개를 기존 완료/weekly/예약 원천과 대조한다. T=C와 수요일10시 이후 권한을 검사하고 N·persistent 관계를 C 완료만으로 임의 종료하지 않는다.
2. item별 완료는 해당 item/round/assignment와 정확히 귀속한 남은 segment 예약만 정리한다. 완료 이력과 다른 item의 참가·시각, N·이전 세대, 동의/예약/원 ACK는 보존한다. 본인 전체 완료와 공대장/전체 종료의 권한·함께하기 관계 정리는 합의 계약대로 구분한다.
3. 현재주 전체 미완료 종료는 실제 C 참가자 권한·미완료 round/남은 타임에 한정한다. 정정/재개는 완료를 자동 복구하거나 이전 assignment/예약/표를 되살리지 않도록 새 원천/세대/동의를 검토한다. 명시 N reopen과 현재주 resume을 혼동하지 않는다.
4. 제한 LOGIN/전용 tmpfs PostgreSQL에서 대상/권한·수06/10 경계·부분 완료와 정확 귀속 해제·경합/rollback·원 ACK·이전 원천/시각·fixed schema HTTP를 검증한다. 실제 개발 DB·API 이미지는 별도 전환 작업 전까지 유지한다.

첫 코드 대조점은 `app/raid_rooms/completion.py`·`completion_router.py`·`resume.py`, `app/raid_weekly` 원장과 `cycle_lifecycle`·`cycle_schedule`·`cycle_planning`이다. 기존 완료/재개 코드는 현재 주차·persistent 리더/일정·구 제안 원천을 사용하므로 새 T 권한/세대/불변 표와 대안 edition을 건너뛰어 직접 호출하지 않는다. W4-A2의 `CycleConsent`·`CycleVote`·일정 사건과 기존 해제 예약도 보존 대상으로 포함한다. 추가 shadow 이행을 만들면 `cycle_schedule.planning_enabled`·`cycle_times.ready`·readiness의 명시 허용 revision을 함께 검토한다. 구 API/worker의0023 활성 guard는 전환 검증 전까지 유지한다.

## 이후 순서

- W4-C: G1 공통 설정·GlobalScope/원 ACK·전역leave/end, persistent CAS/권한 내 영향 context·정확한 전체 관계 정리.
- W4-D: 06worker/v1 adapter·legacy review·declined summary·실제 활성화 준비. 구 API/worker는0023만 활성 허용하며 shadow0024~0028과 혼용하지 않는다.
- W5: 통합 보존/경합·성능·고정 전체56동작 대조·실제 소비 가능 구간 게시/Flutter 인계. 실제 서버 준비 경로·실행 SHA·미확인 범위를 먼저 확인한다.

## 현재 기준과 인계 경계

- [계약4판](../ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[ACK 보완](../ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md)·[전체 작업계획](../ISSUE_13_TWO_CYCLE_WORK_PLAN.md). 구현 명세는 `docs/design/issue13-two-cycle.full.openapi.json`이며 core 파일은 재현 입력이다.
- 고정53경로/56동작/204schema·canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`. 합성 schema 검증과 실행 HTTP/DB 검증은 별도 근거다.
- W4-A2: 실제 T/generation 그룹/후보/선택·초기 조율·세션별 정족수/명시 응답, shadow0028 불변4표·다중 세션 동의. 이전 예약/동의·다른 T/세대·원 ACK 보존. 상세 실행 결과는 A2 기록·DEV_LOG 기준이다.
- 후보36경로/39동작은 main 미등록, 실행 OpenAPI116경로 유지. 소스 게시와 실제 개발 DB/API 전환·배포는 별도다. 실제 회원/provider/기기·운영 성능·Flutter 인수는 미완료다.
- 다음 Flutter 구간은 주차 메타/actualcycle·계정summary/선택기이며 실제 서버 의존 준비 후 필요한 범위만 인계한다. 후보 소스 완료만으로 새 시험을 요청하지 않는다. #19 통계 미확정은 별도 후속으로 유지한다.
