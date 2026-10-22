# Issue #13 — 사전 참가 세션 표시 메타 구현

2026-10-23 / Backend / `feat/raid-recruitment`.

[Flutter110 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6344221859)과 [Backend111 경로 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6344566106)을 구현 기준으로 삼았다. 세부 의미·합성 예시는 [합의된 초안1](ISSUE_13_PREJOIN_SESSION_DISPLAY_DRAFT.md), 실행 REST 계약은 [two-cycle OpenAPI](../openapi/two-cycle.openapi.yaml)다. 기존 고정 계약0.4.1/policy4·기본0023 앱 OpenAPI는 유지한다.

## 소비 방법

다음 기존 GET에 `include_session_display=true`를 붙이면 `data.session_display`가 추가된다.

| GET | 표시 결과 |
|---|---|
| `/v2/raid-rooms/{room_id}/admission-context` | join/apply/change_character의 실제 선택 세션 |
| `/v2/me/raid-rooms/{room_id}/continuation-context` | join은 실제 N 세션, decline은 none |
| `/v2/me/raid-rooms/{room_id}/opening-context` | 생성/재개방은 opening_preview, already_open은 none |

생략/`false`는 기존 응답 그대로이며 새 필드는 없다. 빈값/null/1/TRUE/다른 문자열·중복 query는400이다. opt-in DTO 필드는 생략 가능하지만 명시null은 허용하지 않는다. 전체 응답 UTF-8 JSON이1MiB를 초과하면413 `RESPONSE_TOO_LARGE`; 일부 세션/후보를 자르거나 false 응답으로 대체하지 않는다. preview 수에 새로운 제한을 추가하지 않았다.

`existing`은 현재 실제T·generation·active schedule head의 unconfirmed/confirmed 세션을 UUID순으로 제공한다. `session_choices`와 ID·required·join_deadline·permission이 일치하며, 추가 필드는 revision/schedule_revision/state/starts_at/ends_at이다. 시각은 UTC/null이며 실제 session의 시작/끝은 둘 다 있거나 둘 다 null이다. 다른 세대·완료/취소 세션·개인 제출표/다른 회원 예약은 반환하지 않는다.

`opening_preview`는 기존 `schedule_inputs`의 source C 의도와 전체 item duration을 실제 N 날짜로 계산한다. prospective cycle/generation을 사용하며 plan_revision=null, sessions=[]다. preview_ref는 불투명 표시키이고 session_id는 항상null이다. 수동 each/단일후보는 on_open, 수동 복수 one_of는 after_group_selection, 조율은 after_coordination, 미지정은 not_scheduled다. 수요일00:00~05:55는 해당 주차의 끝 날짜로 계산한다. duration 근거가 없으면 미생성 preview만 start_only가 된다.

continuation/opening의 기존 `target_session_ids=[]`와 쓰기 본문은 유지한다. 화면 선택에는 실제 sessions와 기존 required/permission을 사용하며 preview_ref를 POST하지 않는다. opening ACK 후 현재T plan에서 실제 ID를 읽는다. 개방으로 생긴 참가관계는 시간확정 동의·예약 자동생성을 뜻하지 않는다.

## 토큰과 호환성

표시 객체는 같은 READ ONLY snapshot에서 생성하고, token 발급 전에 기존 admission policy와 lifecycle binding에 넣는다. true token 내부에 `session_display_version=1`만 추가하며 전체 표시 목록을 token에 넣지 않는다. 쓰기는 seal된 표지에 따라 표시 근거를 재계산한다. 표지가 없는 기존 token은 기존 계산 경로를 사용한다. 새 POST 필드·DB migration·endpoint·권한 확대는 없다.

시각/끝·revision·상태/선택 가능 목록·source 그룹/설정/세대가 바뀌면 기존 `SELECTION_CONTEXT_CHANGED`/`TARGET_CONTEXT_STALE`/CAS 오류로 거절한다. display_revision은 서버시각/발급시각 때문에 매번 달라지지 않는다. 이미 성공한 동일 command/body는 기존 실행 원장의 원 ACK 우선 반환을 유지한다.

## 검증·인계 상태

- 최종 격리 묶음47 PASS/410.22초와 현재DB0029 연계1 PASS/15.82초, 고유48 PASS다. 새 표시24개와 기존 명령/HTTP/라이프사이클24개를 구분하며 탐색 중 재실행은 합산하지 않는다. 기존 anyio deprecation warning1종 외 실패 없다.
- 생략/false의 닫힌 기존DTO·표지없는token·엄격query·읽기전용, actual ID/시각/권한·nullable 쌍·미정duration, 표시변경 거절·원ACK, join/apply/character/continuation/decline/open/reopen/noop를 확인했다. manual each/단일/복수후보·coordinated/주차전체/unscheduled, KST 수요일00:05, 새세대/이전세대 제외를 검증했다.
- 합성 Bearer HTTP의 정상조회/무인증·오류·폐기세션 거절, 참가전 private plan/소스권한 제한을 확인했다. 5,002개 저장후보를 모두 유지한 채 실제1MiB 초과413·토큰4096bytes 이하와 정상 크기 경계/false 호환을 확인했다. 성능 SLA 시험은 아니다.
- 새 이미지 `sha256:404cf8c4163af68a34bbb58435f4057c46eb555942616b3c4004330db6f78141`의 app/alembic Python221파일이 작업트리와 바이트 일치했다. 실제 개발API8000은 이 이미지·168경로·DB0029로 healthy다. 기본116경로/두주차168경로 OpenAPI 각각 전체 객체 일치, 변경은 기존3GET의 query/응답·해당표시schema다. base wire/기본 OpenAPI/고정0.4.1·policy4/canonical SHA는 불변이다.
- 교체 전후105표345행의 전체 내용 지문·환경/인증키mount·보안/포트/실행command가 일치했다. migration·DB 초기화/삭제·기존키 변경은 없다. 기존이미지는 `lostparty-backend-api:pre-session-display`로 보존했다. 실제health200/세GET의무인증·잘못된Bearer401/no-store 총7검사와 호스트health200을 확인했다.
- 이번 임시DB(tmpfs)/runner/network만 정리했고 기존API/DB 두 컨테이너만 healthy로 유지한다. 실제 정상로그인 회원 HTTP 성공·기기 표시/성능·Flutter 연결/F6/운영 인수는 미확인이다.

다음 Flutter 작업은 게시·실행 확인한 소비 SHA에서 이 세 GET의 opt-in DTO와 사전 참가 표시/선택을 연결하고 결과를 Issue #13에 회신하는 것이다. 이미 확인한 동일 정책 수용이나 기존 mock 시험을 반복 요청하지 않는다. 게시: 구현 `07c2b671d67e5dfcef5f873ef55ffcb54f87b365` commit/push·실제 원격SHA 일치 확인 후 [전체112번째 Backend · F5 사전 참가 표시 구현/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6345290060)에 회신했다. 본문 제외 실제전체순번112·Backend작성측·구현/인계단계를 재조회했다. 다음 담당 Flutter의 표시·선택 연결은 대기이며 Backend는 차이 대응이다.
