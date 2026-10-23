# Issue #13 W1 — 두 주차 저장·참가자·공대장 기반

2026-10-21 / `feat/raid-recruitment` / 기준 HEAD `6490f69` / 구현 미커밋·미push.

기준은 [계약4판](../contracts/ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[공통 ACK](../contracts/ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md),
[전체84번째 Flutter·계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)이다.
W1은 내부 저장·트랜잭션 기반이며 신규 v2 HTTP·실제 서버 준비 완료가 아니다.

## 구현 구조

`0024_recruitment_cycles`는 실제 이전 head `0023_recruitment_resume`를 잇는 추가 이행이다.
`cycle_models.py`에 아래 10개 표를 정의하고 frozen DDL과 대조한다.

| 표 | 책임 |
|---|---|
| recruitment_room_cycles | 방/실제 주차 유일 식별자, 현재 세대 포인터, 주차별 revision·설정 스냅샷/출처 |
| recruitment_cycle_generations | 개방/재개 세대, 회차별 공대장·leadership revision·signed bigint 다음 참가순번 |
| recruitment_cycle_members | persistent membership과 별도인 실제 주차·세대 참가자, 현재 구간/순번 |
| recruitment_cycle_rounds | 기존 Round FK로 증명한 방·item·실제 주차와 세대 연결 |
| recruitment_cycle_assignments | 기존 Assignment 소유자·Round와 실제 주차 참가자를 잇는 복합 FK |
| recruitment_cycle_directory_heads | 실제 주차별 목록 revision; 읽기에서 미존재 값1·행 생성 없음 |
| recruitment_cycle_submissions | 주차·세대 참가자별 제출표; 과거 membership-wide 표와 분리 |
| recruitment_cycle_openings | 새 개방 원천의 세대별 유일성, 과거 개방의 보존 참조 |
| recruitment_participation_events | 참가 구간의 command/revision/Assignment 증거·불변 이력 |
| recruitment_legacy_cycle_evidence | 과거 원천의 주차 분류 및 미확정 이유; 실행 권한/동의로 사용하지 않음 |

기존 표에 nullable 열을 일괄 추가하는 대신 **추가 연결 표**로 이행한다. 기존 모델·이력·FK·원장/예약/원 ACK와 그 기록 시각을 그대로 보존하고, 새 참가자의 세대/실소유 연결에는 FK를 강제하기 위한 선택이다. 새 generation별 개방 유일성은 `cycle_openings`가 담당한다. 이전 OpeningEvent의 유일 제약을 바로 해제해 구 worker의 중복 개방을 허용하지 않는다. W3/W4의 실제 개방·취소는 새 원천만 사용해야 한다.

## 보존 이행

- 기존 Round의 `(room_id, cycle_key)`만 RoomCycle로 분류한다. 취소 의사·예약된 자동개방·choice 날짜만으로 회차를 만들지 않는다.
- 단일 Round가 있다고 개방 세대1·과거 공대장·참가 순서를 증명한 것은 아니다. 과거 RoomCycle/실참가자의 generation·순번·리더·설정 스냅샷은 미상으로 두고 `review_required`/`legacy_unknown`으로 보존한다. 과거 joined_at을 원래 참가 구간 시작이라고 재해석하지 않는다.
- Assignment는 실제 Round FK를 통해 주차가 확인된다. 기존 참가자를 N에 복사하지 않는다. 명시적 신규 bundle만 `CycleAssignment`와 `ParticipationEvent`를 기록한다.
- 세션은 모든 segment의 Round 주차와 binding→group 주차가 일치할 때만 주차를 분류한다. 혼합/불일치/누락은 미상이다. 주차 분류 성공도 동의/예약 복원은 아니다.
- 신청은 모든 targets의 실제 room/item/Round가 일치하고 주차가 하나일 때만 분류한다. 빈 배열/형식 오류/외부 ID는 미상으로 남긴다.
- 과거 개인 제출표·제안·resume·choice는 실행 세대/동의를 추정하지 않는다. 기존 원본은 남고, 신규 주차별 제출표와 참가 이벤트를 자동 생성하지 않는다.
- 기존 OpeningEvent는 해당 RoomCycle이 실제 존재할 때 review 참조만 추가한다. 대응 Round가 없는 예약/차단 이벤트는 원본에 그대로 보존한다. 이전 auto 값은 새 동의가 아니다.
- 파괴적 downgrade는 지원하지 않는다. 실제 DB 적용·review 해소·worker/API 동시 전환은 W4/W5의 별도 실행 작업이다.

## 내부 트랜잭션 기반

`cycles.py`는 C/N 명시 actual 날짜 검증, 06시 주차전환·수10시 플레이 하한, target/현재 Round resolver, G1의 C 우선·C 행이 없을 때만 N 선택을 제공한다. 과거/임의요일/C+14는 target로 허용하지 않는다.

`record_bundle_join`은 **상위 W2 서비스의 인증·소유/활동·역할·한도·context/입장 검증 후** 같은 transaction에서 실행할 finalizer다. 전체 item의 실제 Assignment·활성 Round·정확한 주간 lease를 검사하고, 주차 행/세대 잠금 아래 순번·참가자·복합 FK·불변 이벤트·해당 주차 목록 head를 기록한다. 이 함수만으로 사용자를 입장시키거나 참가 API가 준비되었다고 볼 수 없다.

순번은 signed bigint이며 `9223372036854775807`까지 할당한다. 마지막 값 사용 후 next=NULL은 고갈 표시이며 다음 참가는 `JOIN_ORDER_EXHAUSTED`로 무변경 거절한다. 재참가는 동일 세대 참가자 ID에 새순번/revision을 기록하고 이전 이벤트를 보존한다. 완료·stopped를 참가로 부활시키지 않는다. 승계/직접 위임 정책 실행은 W3이다.

`execute`는 기존 영속 명령 저장소와 actor/operation/key/body digest·lease를 재사용한다. 원 성공 ACK 복구 후에 새 명령의 context/경계/권한을 검증한다. commit_result와 실제 쓰기는 동일 transaction이며 경계 도중 변경은 rollback한다. W1에서 불변 원천과 저장소 동작을 검증하지만 신규 v2 HTTP 멱등 인수는 W2 이후다.

## 실행·검증 경계

- 실제 개발 DB/API 이미지에는 적용하지 않았다. 실행 원본 OpenAPI도 그대로다.
- 0024는 shadow head다. 이전 API 활성화와 이전 worker의 `process_due`/`process_room`은 0024를 거절한다. W1만 적용해 기존 0023 worker와 새 회차 쓰기를 혼용하지 않는다.
- 기존 HTTP 회귀 fixture는 실제 실행 기준 0023을 명시하고, 신규 0024 이행은 독립 임시 DB에서 제한 LOGIN으로 수행한다. W4 전환 시 runtime fixture와 날짜 표 검사도 함께 갱신해야 한다.
- 초기 W1 21 PASS/78.76초(중복). 실제 참가 복합 FK·혼합 자료/재참가/rollback 보완 후 관련 실행은 **56 PASS/1 FAIL/252.19초**였다. 실패는 재사용 테스트 이미지의 오래된 OpenAPI 파일로 인한 비교 실패이며 현재 저장소의 `openapi/`를 컨테이너에 동기화했다. 목록 head의 identity map 캐시 방지와 실제 권한 변경 후 원 ACK 복구 사례도 보완했다. 실패 항목·나머지 admission/날짜 표·영향 W1 재검증 **17 PASS/92.67초**, 앞선 실행과 중복10건이다. **고유63사례(W1 26+기존 회귀37) 모두 통과 확인**이며 단일 전체63 재실행 결과로 표기하지 않는다. 현재 소스 FastAPI/원본 OpenAPI 전체 일치도 재검증 통과했다.
- 운영 성능/실회원/provider/기기, 새 HTTP·실행 OpenAPI 전체 대조는 미실행이다. W1 내부 완료와 Flutter 소비 준비를 구별한다.

## 다음 W2

1. `/v2/raid-cycles`와 `/v2/me/raid-weekly-summary`·선택기에 필요한 실제 읽기 경로/권한 의존을 먼저 구현한다.
2. 신규 생성·일반 참가가 전체 admission/소유/한도/주간원장을 검증한 뒤 W1 finalizer를 같은 transaction에서 호출하도록 한다. 기존 v1의 전역 room revision 증가·현재주차 강제 입장 함수를 v2에 그대로 재사용하지 않는다.
3. 신규 target별 신청/스케줄/제안·설정과 현재 세대 조회를 추가 연결 표에 귀속시킨다. 기존 review 자료의 권한/세대가 자동 해소된 것으로 취급하지 않는다.
4. W3 개방/취소·W4 worker/v1 adapter가 호환되는 실제 소비 구간을 검증한 뒤 실행계약 반영·게시/원격확인·이슈 인계를 진행한다. 이번 내부 기반만으로 Flutter 기능시험을 요청하지 않는다.
