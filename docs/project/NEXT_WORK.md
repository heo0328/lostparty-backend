# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

W1/W2 `917123e`·W3 `13b655e`·W4-A1 `6d2b301`·W4-A2 `88583a9`와 게시 기록 `ef25c38`까지 push/원격 확인 완료. [W4-B 완료·정정·현재주 재개](../ISSUE_13_W4B_CYCLE_OUTCOMES.md)는 구현·격리 검증 완료(**132PASS/1081.82초**, 신규26 포함), 구현 `0d8b58111356b69d817b23b154a56efb64c974f9` commit/push·실제 원격 SHA 확인·[전체87번째 Backend · W4-B 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6319271776) 게시 완료. 다음 실행은 아래 W4-C이며 중간12/18/6PASS는 최종 고유 통계에 합산하지 않는다.

착수/인계 시 AGENTS → 협업 규칙 → 이 문서 → AI_CONTEXT → 계약4판/ACK 보완을 읽고 Issue 본문/최신 댓글·Git/코드를 확인한다. 최신 게시/조회는 [전체87번째 Backend · W4-B 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6319271776)이며 새 Flutter 요청·계약 변경은 없다. 계약0.4.1/policy two-cycle-contract-4 고정이고 추가 제품 입력/동일 계약 재검토 대기는 없다. 사용자 지시대로 작업 구간 종료마다 검증·문서 갱신·commit/push·GitHub 기록을 한다.

## 다음 W4-C — T 관리와 G1 공통/전역

고정 명세 중 후보 라우터에 남은9동작을 대조했다. 아래 C의8동작과 D의 legacy 함께하기 조회1동작이며, 이미 main 소스에 있는 주차/summary2동작은 별도다. W4-B 완료만으로 전체56동작 완료를 표시하지 않는다.

1. **T 관리4동작**: GET `/v2/me/raid-rooms/{room_id}/settings`, PUT `/v2/raid-rooms/{room_id}/settings`, PUT `formation`, POST `removals`. actual T/세대의 리더·open·현재 자격·설정/편성/CM CAS와 영향만 사용한다. 부분 완료 이력/원래 자리·다른 T·persistent 관계·기존 동의/해제 예약과 원 ACK를 보존하고, 제외 후 승계/현재 투표/새 시간 확인을 재평가한다.
2. **G1 공통/전역4동작**: GET `/v2/me/raid-rooms/{room_id}/common-context`, PUT `/v2/raid-rooms/{room_id}/common-settings`, POST `leave`·`end`. G1은 C row가 존재하면 closed/review C도 N fallback을 막는다. C가 없을 때만 N을 검토한다. 전역 context의 실제 전체 영향·persistent CAS를 사용하며 target가 없는 영향을 가짜 C/N으로 만들지 않는다.
3. 공통 설정200은 GlobalScope+CommonSettingsAck·수행 후 room_revision/실제 affected_cycle_keys이며 no-op 영향은[]이다. 전역 leave/end는 확인한 전체 영향만 원자 정리하고 현재 T 리더의 선행 위임/안전한 마지막1인 조건·과거 완료 보존을 지킨다. 원 ACK는 주차/권한·context 만료 재검사보다 먼저 복구한다.
4. 제한 LOGIN/전용 tmpfs PostgreSQL에서 C/N·closed/review/부재 C의 G1 권한, persistent-only/영향0, target 제외와 전역 종료의 차이, 부분 완료/재개 후 source·좌석·예약·원장 귀속, CAS/rollback·원 ACK·고정 HTTP/전체 계약을 검증하고 구간 게시한다.

첫 대조점은 기존 `management.py`·`management_router.py`·`completion.py`·`command_context.py`, `cycles.common_authority_cycle`와 `cycle_lifecycle`·`cycle_outcomes`·`cycle_resume`다. 기존 전역 Room/Member의 현재주 리더 가정을 target 계약에 그대로 재사용하지 않는다. 공통 설정 성공 응답은 [ACK 보완](../ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md)을 따른다.

## W4-B에서 보존할 기준

- actual C/수10시·120초 완료 context·명시 수동 정정·개인/공대장 완료·미완료 종료/재개. 마지막 개인 완료와 미완료 종료는 C 관계 이력을 보존하고 N/persistent를 자동 정리하지 않는다.
- shadow0029 불변 CycleOutcome/CycleResume2표. 중단 Round는 새 UUID로 대체하고 새 Assignment/세션·확인 구간을 만들며 completed item/개인 완료 이력·원래 formation_history와 이전 예약/동의/제출/투표 원천을 보존한다. 적용 투표 집합/이전 세대 상태도 source에 기록한다.
- 부분 완료자는 남은 활성 item만 일정 확인/예약·제안 분모에 포함한다. 재개 뒤 다른 사람을 위해 새 Round가 생겨도 본인 완료 raid를 다시 입장시키지 않는다. 이전 Assignment/예약·개인 제출을 자동 복원하지 않는다.
- 재개할 C 일정에서 빠진 전역 완료 item은 N의 전체 묶음 복사 시 captured settings 순서로 보완한다. 다른T를 변경하는 완료 효과가 아니라 이후 별도 N 개방 명령의 복사이며, N의 확인/예약 동의가 아니다.
- 추가 shadow 이행 시 `cycle_schedule.planning_enabled`·`cycle_times.ready`·outcome 준비 검사·readiness의 명시 허용 revision을 함께 검토한다. 구 API/worker의0023 활성 guard는 전환 검증 전까지 유지한다.

## 이후 전환·인계

- W4-D: 06worker/v1 adapter·legacy review·declined summary·GET `/v2/me/raid-rooms/{room_id}/continuation-choices` 보존 projection·실제 활성화 준비. legacy choices를 새 실제 N 참가나 동의로 쓰지 않는다. 기존 v1 수동 완료에도 C/수10시 guard와 원 ACK 예외를 연결한다.
- W5: 고정 전체53경로/56동작 대조·통합 보존/경합·성능·실제 소비 가능 구간 게시/Flutter 인계. 준비 경로·실행 SHA와 실회원/provider·캐시/계정 격리·미확인 범위를 구분한다.
- 후보42경로/45동작은 main 미등록. 로컬 main/원본 OpenAPI116경로, 실제 개발 DB/API 이미지·서버는 유지한다. source 게시와 서버 전환/배포·실회원/기기/운영 성능·Flutter 인수는 별도다. 후보 완료만으로 새 Flutter 서버 시험을 요청하지 않는다.
- 고정 명세는 `docs/design/issue13-two-cycle.full.openapi.json` / canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`. schema 합성 검증과 실행 HTTP/DB 검증은 별도 근거이며 [DEV_LOG](DEV_LOG.md)·각 구간 기록을 따른다. #19 통계 미확정은 별도 후속으로 유지한다.
