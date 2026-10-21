# Issue #13 W2-A — 주차 메타·계정 주간 summary 조회

2026-10-21 / `feat/raid-recruitment` / HEAD `6490f69` / 미커밋·미push.

후속 [W2-B 생성·target 조회/일반 참가](ISSUE_13_W2_CYCLE_ADMISSION.md)도 로컬 구현·격리 검증을 마쳤다. 현재 다음 실행은 [NEXT_WORK](project/NEXT_WORK.md)의 W3이며 아래 다음 W2-B 표기는 W2-A 종료 당시 기록이다.

**W2 첫 조회 구간의 로컬 구현·자동 검증 완료. W2 전체 완료나 실제 서버/Flutter 인수 완료가 아니다.**
기준은 [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md)·[전체84번째 Flutter 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)이다.

## 실행 코드와 계약

| 경로 | 동작 |
|---|---|
| GET `/v2/raid-cycles` | 인증된 회원의 C/N 실제 날짜, 06시 시작/끝, 수10시 플레이 하한, 시간 정책의 coarse 권한과 `next_change_at` |
| POST `/v2/me/raid-weekly-summary` | 본인 소유 인증 캐릭터 고유1..50 × 실제 C/N 고유1..2 × 현재 카탈로그5레이드, 최대500항목. 단일 RR/READ ONLY 스냅샷 |

`weekly_summary.py`·`weekly_summary_schemas.py`·`weekly_summary_router.py`를 main에 연결했다. DB0023의 원장과 정확한 Assignment/Round/Occupancy·membership을 읽으며 0024 생성/이행은 필요하지 않다. 0024 API/worker 전환은 W4의 별도 작업으로 유지한다.

원본 `openapi/openapi.yaml`에는 구현한 **2경로·10schema만 추가**했다. 기존114경로/기존 모든 schema의 값은 변경0이며 현재116경로다. 합의 명세와 실제 두 경로의 입력/200 스키마를 ref 확장·annotation 제외 후 구조/필수/제약까지 대조했다. 신규 metadata도 합의대로 인증을 요구한다. JSON 중복 키/예상 외 query/GET body/32768bytes 초과 입력을 거절한다. 기존 bounded route의 413도 실행 계약에 명시했다.

설계 재현 도구는 원래 cc003e9 실행 계약을 입력으로 사용한다. 현재 실행 원본이 성장해도 같은 설계 hash를 재현하도록 pinned Git snapshot을 읽는 fallback과 archive용 `--base-openapi`를 추가했다. 재생성 결과의 계약0.4.1 canonical SHA256은 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`로 유지한다.

## 의미·권한·보존

- character/target/카탈로그 순서로 반환하며 모든 행은 actual target 키를 가진다. 없는 주간 원장은 revision1·완료 source=[]·participation=null이다. 조회에서 기본 행/멱등 요청/예약/개인 설정을 쓰지 않는다.
- current 등록·현재 소유/인증·이름 claim을 batch 검증한다. 타인·미상·등록해제·이전 소유 캐릭터가 한 개라도 섞이면 전체403이며 부분 성공하지 않는다. 소멸/identity 충돌은 기존409 경계를 유지한다. 1700 하한/활동 선택/한도를 조회 조건으로 새로 추가하지 않는다.
- 실제 원장과 lease·Assignment·Round를 대조한 현재 점유만 `confirmed`다. 오래된 ownership/lifecycle·종료 관계·review 방은 점유 증거를 남기되 `review_required`로 구분한다. 과거 lease가 없어도 실제 동일 Round/Assignment가 하나로 증명되면 review로만 표시한다. 연결이 불명확하면 전체503으로 거절해 빈 참가나 임의 ID로 위장하지 않는다.
- 함께하기 choice는 `legacy_intent`/`blocked`이며 실제 참가 `i`가 아니다. 실제 참가가 확인된 경우에만 confirmed를 반환한다. W3의 명시 불참 원천은 아직 없어 조회가 과거 released choice를 새 `declined` 동의로 해석하지 않는다.
- 기존 membership/그룹 공개 권한에 따라 제목을 제한한다. 비공개 방 접근 권한이 사라지면 `room_title=null`, `can_view_detail=false`다. 다른 회원 ID·build/장비 원문을 반환하지 않는다.
- manual/party 완료 source를 각각 보존한다. 수06시에는 actual C가 바뀌고 수10시 전/미래 주차에는 완료·정정 권한이 false다. 시간상 다음 변화가 알려진 권한에 `next_change_at`을 반환한다. coarse 권한/캐릭터 권한은 정책 정보이며 아직 없는 v2 쓰기 경로의 실행 준비를 보장하지 않는다. 실제 완료 writer의10시 통일은 W4다.
- provider/장비/키 캡처·bootstrap 전체 재조회가 없다. 모든 응답과 오류는 no-store다. 별도 Idempotency-Key가 필요 없는 읽기 전용 POST다.

## 검증 결과

- 최초 **28PASS/1FAIL/22.21초**. 합의 명세 대조가 Permission의 필수 `next_change_at`과 revision 상한 누락을 발견했다. DTO와 실제 응답을 보완했고 이 오류를 검증 정규화로 숨기지 않았다.
- 보완 후 신규29 + 기존 주간원장/첫 화면/모집 조회/기록시각74 = **103PASS/108.10초**.
- 추가한 동시 탈퇴 RR 일관성·비활성 회원/취소 세션 = **3PASS/6.09초**. 앞선 실행과 중복 없는 **고유106사례**의 통과를 확인했다. 단일 전체106 실행 결과라고 표기하지 않는다.
- 최종 검토에서 같은 actual 주차의 종료 세대 이력을 읽기에서 제외하도록 원장/활성 Assignment·실제 lease 조건을 SQL에 추가했다. 종료 세대25개가 있어도 현재 source1개만 읽는 사례를 추가하고 신규 조회 전체 **33PASS/20.27초**로 재검증했다(중복32/추가1). 최종 확인 범위는 **고유107사례(신규33+기존 회귀74)**다. 검증 이미지도 이 보완까지 다시 빌드했다.
- 최대 배치 측정 재실행 **1PASS/5.15초**는 중복이다. 합성50캐릭터/두 주차500항목 응답287861bytes, 시각을 고정한 내부 서비스 측정 SELECT9회로1캐릭터와 동일했다. HTTP 인증과 실제 server_now SQL은 이 측정 범위 밖이다. 운영 지연/p50/p95·비용 보장이 아니다.
- 기존 모든 실제 테스트 표/열 지문 보존, provider/키 호출 금지, 타인 혼입 전체403, 요청 형식/중복·범위/캐시 경계, 정확한 현재·미래 점유/legacy 의사 분리, 제목 권한·끊긴 원장 거절, 수06/10시 경계, 동시 탈퇴 후 RR 이전 스냅샷 일관성을 확인했다.
- bootstrap 보존 시험은 ORM에 로드된 0024 shadow 모델이 아니라 실제 runtime 표 전체를 inspect해 비교하도록 보완했다. 원래 runtime 표의 보존 검사를 축소하지 않는다.
- 현재 소스로 별도 `lostparty-w2-read-api` 이미지를 빌드했다. 해당 이미지의 FastAPI/원본 OpenAPI 전체 비교 **PASS/116경로**, 격리 DB0023 startup readiness **PASS**. 개발 API 이미지 태그/컨테이너와 실제 개발 DB는 전환하지 않았다.
- `git diff --check`·Python AST·문서 링크·설계 hash 재현 확인. 기존 BlockingPortal deprecation 경고 외 신규 경고 없음. 관련107은 이번 조회 구간이며 W1/전체 모집/실회원·기기 검증 수와 합산하지 않는다.

## 다음 실행·인계 경계

Backend 다음은 **W2-B 생성 context·C/N 원자 생성·target 목록/검색/detail/plan·일반 신청/승인/직접참가**다. W1의 실제 회차 finalizer 앞에 소유/활동/역할·한도·context 검증을 연결하고, target별 신청·스케줄/설정·조회 CAS를 구현한다. 숙련도OR/자리·정렬/회원·캐릭터 필터는 SQL pagination 전에 적용한다.

W2-A의 두 경로는 main 소스와 검증 이미지에서 준비됐으나 기존 개발 서버에 반영하지 않았다. Flutter의 selector에 필요한 본인 target 목록/상세는 아직 없어 전체 선택기 연결 완료로 인계하지 않는다. 서버 준비·필요 의존·실행 SHA/게시가 확인된 뒤 실제 소비 가능 구간을 묶어 commit/push·원격확인하고 Issue에 인계한다. 이번에는 소스 미게시·서버 미반영 상태이므로 새 Flutter 기능시험이나 같은 계약 재검토를 요청하지 않았다.
