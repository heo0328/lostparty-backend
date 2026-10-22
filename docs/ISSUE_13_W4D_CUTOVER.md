# Issue #13 W4-D — 주차 전환·v1 호환·활성화 준비

2026-10-22 / `feat/raid-recruitment` / 시작 `3176c4f` / 구현·격리 검증 완료. 구현 `8085e90877561c28c45eb7279929d790da0a7c5b` commit/push·실제 원격 SHA 확인·[전체89번째 Backend · W4-D 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330758804) 게시 완료.

[전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057), [계약3판 전환 기준](ISSUE_13_TWO_CYCLE_CONTRACT_R3.md)·[4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[공통 ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), 고정0.4.1/policy two-cycle-contract-4 기준이다. 착수 시 Issue 본문/전체88댓글·Git/코드를 대조했고 추가 요구/계약 변경·사용자 미커밋 변경은 없었다.

## 주차 전환·보존

- `cycle_worker`는 game mutation lock과 실제 RoomCycle/generation을 사용한다. 지난 실제 주차의 활성 Assignment/정확한 lease·예약·참여·제출/제안/신청만 정리하고 불변 ParticipationEvent에 원천을 남긴다. 완료 Assignment/원장·이미 해제된 예약·persistent 관계/한도와 다른 주차는 보존한다.
- 06시 N→C는 같은 실제 날짜 행의 표시 전환이다. UUID/세대/리더/순번/Assignment/세션·동의/예약을 새로 만들거나 복원하지 않는다. 생성일이 지난 C에 속해 있어도 실제 대상이 새 C인 제안은 유지한다. 새 N의 자동 개방/가입·auto_open_enabled/옛 choice 기반 자동 참가0이다.
- 현재 주차로 이어받은 명시 source의 현재 자격이 무효이면 lease/자리·과거 증거를 유지하고 실제 row/세대를 review_required로 분류한다. 기존 legacy_unknown/불명 세대는 실행 기본값으로 승격하거나 임의 복구하지 않는다. 새 review 사유는 보존 evidence에 기록하며 자동 삭제/임의 외부 승계는 없다.
- 중복 worker는 같은 결과로 수렴하고 최종 DB 주차가 바뀌면 전체 transaction을 rollback한다. 옛 auto-enrol worker는0023만 허용하고 새 worker는0029만 허용한다.

## v1 호환·summary

v1 모집 조회는 actual C의 카드/검색·detail/plan/settings·회원/신청 목록·개인 제출/익명 busy/겹침/후보·legacy choice projection으로 변환한다. 새 T 필드를 원래 v1 DTO에 끼워 넣거나 N 리더/캐릭터/설정·옛 전역 RoomSettings로 권한을 추정하지 않는다. 읽기 권한은 유지하고 중첩된 구 쓰기 권한은 CLIENT_UPGRADE_REQUIRED로 표시한다. 입장/생성/완료 등 구 command-context는 새 명령의 실행 권한으로 쓰지 않는다. 없는 C를 읽기에서 만들지 않는다.

0029의 구 방 쓰기는 저장된 원 성공 ACK를 먼저 복구하고 새 명령은409 CLIENT_UPGRADE_REQUIRED로 거절한다. 개인 play-availability와 본인 manual-completion은 안전한 쓰기로 유지한다. v1 수동 체크/false 정정도 actual C/수10시 이후만 허용하며 최종 주차/시각·원 ACK를 같은 transaction으로 확인한다. 원 ACK는 현재 소유/주차·자격 재검사보다 먼저 복구하되 현재 회원/session 인증은 유지한다. `WeeklyEntry.mark_blocked_reason`에 PLAY_NOT_STARTED를 추가하고 본인 주간 조회/첫 화면 일괄 조회에도 해당 시각을 적용했다. 수동 정정은 party 완료 원천을 지우지 않는다.

account weekly summary는 현재 실제 주차/세대의 불변 declined 결정과 정확한 lease·CM 관계를 배치 대조한다. 실제 참가가 선언/옛 의사보다 우선하고 다른 방의 점유를 덮지 않는다. review/불명 source의 점유는 blocked/review로 표시하며 confirmed 기본값을 부여하지 않는다. GET/summary는 READ ONLY이고 새 행/참가·확인을 만들지 않는다.

GET `/v2/me/raid-rooms/{room_id}/continuation-choices`는 actual T의 legacy 읽기 전용 projection이다. 없는 N이면 target UUID/revision은 null이며 GET로 회차를 만들지 않는다. 실제 참가/동의의 근거가 아니고 v2 PUT/자동 개방 설정은 추가하지 않았다. 후보51경로/54동작 + 기존 메타/summary2동작으로 고정53경로/56동작을 모두 연결했다. 전체56개 operation ID도 고정 명세와 일치한다.

## 전환 진입점·실행 계약

기본 `app.main:app`과0023 시작/worker 경계는 유지한다. 별도 ASGI factory `app.main:create_two_cycle_app`은0029 전체 준비검사를 통과해야 시작하며 새 router/worker와 v1 adapter를 함께 등록한다. factory는 DB 이행·이미지 전환·설정/자료 변경을 수행하지 않는다. route를 독립 등록하여 앱별 인증 의존성/설정을 공유하지 않는다.

- 기본 실행 계약: [openapi.yaml](../openapi/openapi.yaml),116경로. v1 수동 완료의10시/원 ACK 설명·PLAY_NOT_STARTED enum만 함께 보완했다.
- 전환 준비 계약: [two-cycle.openapi.yaml](../openapi/two-cycle.openapi.yaml),167경로. 기존 타 기능/v1 호환+합의된 신규 v2 경로를 포함한다. 이는 현재 개발 서버의 노출 상태가 아니다.
- `scripts/check_openapi.py --profile legacy|two-cycle`로 각 런타임 생성 객체 전체를 비교한다. 격리 runner는 `--docker docker.exe --container lostparty-w4d-runner`를 사용한다. 기본 옵션은 기존 Compose api 비교를 유지한다.
- 실제 전환 때는 검증된 소스/이미지·대상 DB revision/지원 이행0023→0029·기존 자료/키 보존·구 API와 모든 worker 정지·ASGI factory 선택·시작/health/계약·복구 계획을 대상별로 검토한다. 새 worker는 신규 N을 자동 생성하지 않는다. 이 작업에서 실제 서버/DB 전환을 실행하지 않았다.

## 검증·다음 담당

전용 `lostparty-w4d-test` tmpfs PostgreSQL/제한 LOGIN·격리 앱·합성 자료에서 관련7파일 **151PASS/611.48초**(신규16 포함, 최종 단일 실행·종료 코드0)를 확인했다. W4-D/W4-C·기존 weekly/summary/bootstrap/continuation/기록시각 회귀를 포함한다. 예비9PASS/보강7PASS와 중복 합산하지 않는다. 기존 BlockingPortal deprecation1건 외 최종 미해결 실패는 없다. API 식별자 특례와 앱별 인증 의존성을 위한 route 독립 등록은 최종 실행에 포함했다.

고정84합성/CAS6쌍/공통ACK2흐름·canonical SHA 불변, 기본116경로/준비167경로의 FastAPI 생성 객체 전체 일치, 정적 DTO 재생성 바이트 일치(SHA256 `7cc60c15569f3a3d6c0e0429aed16406e3be5f0d28f4bd51c2aba0ffa599cd7a`), 변경 Python AST/문서 링크/diff 검사를 통과했다. 전용 runner·시험 DB/network만 정리했고 실제 개발 DB/API 이미지·서버는 변경하지 않았다.

다음 Backend는 **W5 전체 실행 계약·통합 보존/경합·성능·실제 소비 가능 구간 인계**다. 전체 route 연결과 자동 검증/전환 준비 완료를 실제 개발 서버 적용·Flutter/실회원/provider·기기·운영 인수 완료로 확대하지 않는다. 실제 전환은 그 시점의 대상/영향/승인 범위를 확인한다. 불명 legacy 자료는 계속 review로 보존하고 임의 정리/동의 복원은 하지 않는다.

공식 Issue 본문 상단을 W4-D 완료/다음 Backend W5로 갱신하고 기존 원문/합의 이력 보존을 재조회했다. 본문 제외 실제 전체 댓글 순번89·Backend 작성 측·W4-D 단계를 확인했다. 다음 Backend W5 대기이며 Flutter 시험 요청/실제 서버 전환은 아직 없다.
