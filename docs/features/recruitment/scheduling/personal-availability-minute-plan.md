# 개인 레이드 가능시간 1분 입력 설계

2026-11-17 게시 완료: 구현 `5172c7535b556997e76b9d728dc4714a1988ab60`을 origin/refactor/lostark-server-processing에 push·원격 일치 확인. [전체3번째 댓글·Backend 구현/검증/로컬 지원 인계](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924012652). 현재 명세 SHA256 `2f0ae34849e99618e194ad158383091f71967d3c41083d17dfee32a175fd9c9f`。다음 Native 고정 명세 재생성/실제 저장·제출·기기 확인, Backend 결과 대응이며 Issue OPEN이다. 게시 상태 기록은 같은 브랜치에서 함께 보존한다.


2026-11-17 구현 갱신: 사용자 구현·검증·commit/push 지시로 아래 계획을 구현했다. AvailabilityClock/ScheduleClock 및 BInterval 공통 참조를 적용했고 저장/정규화·후보/예약 업무 로직은 재사용했다. 현재 OpenAPI 차이는 Interval/BInterval의 start/end 패턴4곳과 개인표 정책 설명이며191경로/211동작은 유지된다.

검증: 관련121개 실행120PASS/1FAIL(새 HTTP 시험의 동적 server time 비교) 후 fixture를 수정하고 실제 베타 후보/예약 경계를 더한 신규15개가 모두 PASS했다. 중복 시험 ID/benchmark 출력까지 대조해 고유122개 통과·미해결 실패0을 확인했다. 최초 import 위치 오류와 불변 예약 수정 fixture도 수정했으며 제품 동작 실패로 덮거나 한 차례 전체 green으로 표시하지 않는다. 도구87PASS·의존성/문서·동결 원문/JSON·compile/diff 및 생성 OpenAPI 전체 비교 PASS.

실제 로컬 API만 새 후보 이미지로 교체했다. DB0037 유지·회원/세션/게임 계정/등록/개인표 전후 행 수 동일, 실제 OpenAPI 전체 일치·health/공개 그룹200·개인표 미로그인401을 확인했다. DB migration·자료/키/환경 변경·운영 반영은 없으며 실제 사용자 개인표 PUT은 실행하지 않았다. Native는 게시 명세로 BInterval 정의/참조를 재생성하고 실제 사용자 저장/제출·복구와 웹/Android를 확인한다. 아래는 설계 당시 범위와 검증 계획이다.


2026-11-17 / [Issue56](https://github.com/heo0328/lostparty-backend/issues/56) / Backend 설계. 기준 HEAD e3ada17·구현 b95cff5, 현재 refactor/lostark-server-processing에서 기존 미커밋 개발 반영 기록을 보존한다. 이번에는 기획/소비 조사만 수행하며 코드·OpenAPI·실행 서버는 변경하지 않는다.

## 목적과 계약

개인 가능시간을18:03~20:17 또는 일요일23:57~다음날00:02처럼 입력·저장·재조회할 수 있게 한다. API/필드/계약 profile을 추가하지 않는다. 기존5분 입력은 같은 형식의 부분집합이므로 자료 변환·DB migration/초기화·호환 flag가 필요 없다.

개인표 Interval의 시각은 strict 문자열 HH:mm·00:00~23:59이며 정규식은 `^(?:[01][0-9]|2[0-3]):[0-5][0-9]$`다. timezone Asia/Seoul, ISO weekday1..7, strict 정수 end_day_offset0/1, 구간 길이0초과~1440분 이하를 유지한다. 정확24h는 같은 시작/끝 시각+offset1로 허용한다. offset0의 같은 시각/역전·24h 초과·24:00·초/소수초·공백·축약 시각은 거절한다.

## 생산·저장·소비 조사와 구현 결정

| 경계 | 조사 결과·구현 방향 |
|---|---|
| availability_schemas.Interval | 현재 공통 Clock이5분 시각이다. 개인표용 AvailabilityClock을1분으로 정의하고 Interval이 참조한다. |
| 기존 일정 DTO | admission_schemas/schedule_schemas/schedule_output도 같은 Clock을 import한다. 기존5분 시각을 ScheduleClock으로 명명하고 해당 소비처를 명시적으로 전환한다. 분 입력 확대가 옛 일정 생성/출력 계약을 넓히지 않게 한다. resume_review 자체5분 Clock은 이번 범위에서 유지한다. |
| cycle_wire.BInterval | start/end의 중복5분 정규식을 공통 AvailabilityClock 참조로 바꾼다. 컴포넌트 이름·필드·추가 필드 금지는 유지하고 BInterval 소비 제출/availability_copy/원ACK도 함께 확인한다. 새 beta 모델이나 별도 Interval 구현을 복제하지 않는다. |
| schedules.availability | 원본 intervals는 JSONB에 그대로 저장, normalize는 정수분 계산·일요일 넘침 분할·중복/인접/겹침 병합이다. 현재 로직에는5분 반올림이 없다. 검증에서 문제가 드러나지 않으면 저장/정규화 코드를 바꾸지 않는다. |
| schedules.cycle_times/beta_schedule | 명시 제출/개인표 복사는 원본·정규화 배열을 deepcopy하며 source revision을 보존한다. BInterval 응답 검증으로 비5분 값이 거절되지 않게 한다. 개인표 저장만으로 기존 제출/확정 일정은 바뀌지 않는다. |
| 조율/예약 | common.time_policy.covered는 정수분 전 구간 포함, 후보는 ceil_tick+TICK5분 및 실제 예약의 a<end and b>start로 검사한다. 원본 개인표/예약을5분으로 내리거나 올리지 않는다. scheduling/cycle_planning/beta_schedule에서 이 경계를 검증하며 전역 TICK·진행시간 배수·명시 출발 정책은 유지한다. |
| bootstrap/summary/상세 | 현재 account bootstrap·weekly summary에는 개인 Interval을 직접 추가하지 않는다. 실제 참조가 있는 제출/plan·member read·schedule view와 복사 snapshot을 추적해 분 원값을 검사하고, bootstrap/summary는 기존 shape·권한·조회 무부수효과를 보존한다. |
| 원명령/권한 | 기존 operation·원UUID/body digest·historical ACK·세션/소유 검증·CAS·동일 원본 noop을 유지한다. 새 멱등 namespace/변환·ACK 재생성·맹목 새 키 재시도를 도입하지 않는다. |

5분 탐색과1분 개인표는 별개 정책이다. 예를 들어 가능시간18:03~20:17, 진행30분, 다른 제약이 없다면5분격자 후보는18:05~19:45이며 범위 밖 시각을 허용하지 않는다. 일23:57~월00:02는 저장 가능한5분 구간이지만 기존 최소 진행시간10분 후보를 만들어야 한다는 뜻은 아니다. 경계가 맞닿는 예약은 비중첩,1분이라도 겹치는 예약은 중첩으로 처리한다.

## 구현 순서·검증·인계

1. 시간 타입/참조와 BInterval을 정리하고 같은 변경에서 생성 OpenAPI 전체 객체 및 현재 정책 설명·일정 문서를 갱신한다. 과거 동결 JSON/당시 명령 예시는 수정하지 않는다. availability_contract의 과거 draft 설명과 현재 main 정책을 조사해 개인표와 일정 정책이 혼동되지 않게 한다.
2. 현재 앱·일회용 PostgreSQL로 개인표 실제 HTTP 저장/GET·권한/버전/noop·원ACK 복구·순서 보존과 정규화를 검증한다.18:03~20:17, 정확24h, 일요일 넘침, 중복/인접·겹침, 모든 거절 경계를 포함한다.
3. 실제 C/N 참가/제출·개인표 복사·plan/BInterval 응답과 확정 일정/기존 예약 비변경을 검증한다. 개인표 수정 후 기존 제출 보존, 명시 재제출 후 source version 전환, 응답유실 재시도와 최신 자료를 과거 ACK로 덮지 않는 경계를 확인한다.
4. covered·후보 탐색·예약을 경계 분으로 검사한다. 범위 밖 반올림 금지·자정/주경계·최소 진행시간·예약 한 분 겹침/맞닿음과 기존5분 탐색/명시 분 출발 회귀를 실행한다. tests/raid_rooms/schedules의 현재 times/http·planning·personal_reservations·explicit_departure_minutes와 admissions/test_beta_recruitment를 변경 영향에 맞게 선택한다. 새 개인표 경계 시험은 같은 schedules 분류에 둔다.
5. 생성 OpenAPI 전체 비교·문서/동결 자료 검사 후 결과를 Issue56에 회신한다. 미커밋/미push이면 그대로 알리고 새 고정 SHA나 실제 dev 지원을 완료로 보고하지 않는다. 게시/서버 교체는 해당 사용자 지시 범위에서 별도로 진행한다. Native는 게시 명세로 BInterval 정의/참조 재생성 및 실제 저장·제출·복구 소비를 확인한다.

완료 조건은1분 원값 저장·제출·응답/복구 보존과 후보/예약 경계 회귀 통과, 기존 일정 정책/자료/권한 보존이다. Backend 로컬 구현·계약 게시·실행 서버 지원·Native 소비·웹/Android 인수는 분리한다. 사용자 설계 지시에 따른 이번 결과는 소스 조사/설계이며 새 동작 시험 통과가 아니다. 기존 운영·DB/키·Issue55와 사용자 자료는 변경하지 않는다.
