# Issue #13 두 주차 모집 구현 작업 계획

2026-10-21 / 담당 Backend / 작업 브랜치 `feat/raid-recruitment` / W1/W2 기준 `917123e` 이후 W3 완료 구간.

## 현재 기준과 진행 상태

[전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 남은 명세 충돌 없음과 구현 기준 고정 가능을 확인했다. **계약 0.4.1 / policy two-cycle-contract-4를 Backend 구현 기준으로 고정한다.** 동일 정책 재채택·동일 예시 재검토 대기는 없다. 이후 실제 구현에서 계약 변경이 필요하면 영향 범위를 다시 협의한다.

- 기준: [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md) + [공통 설정 ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), [전체83번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310051618).
- 전체 구현 명세: [full.openapi.json](design/issue13-two-cycle.full.openapi.json), 53경로/56동작/204schema. canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`. JSON 내부 candidate/not-implemented 표시는 미실행 상태를 나타내며, 검토 대기가 남았다는 뜻으로 해석하지 않는다. 재현 hash를 유지한다.
- Backend와 Flutter가 독립 재현한 것은 **84개 합성 schema 사례·global CAS 출처6쌍·공통 설정 endpoint 흐름2개**다. 실행 API/DB·원자성·멱등저장소/성능·디바이스 인수는 별도 미완료다.
- [W1 저장·참가자·공대장 기반](ISSUE_13_W1_CYCLE_FOUNDATION.md)은 로컬 구현·격리 PostgreSQL 검증 완료. W4~W5와 신규 v2 쓰기 API 공개는 미완료다. 기존 실행 구현은 cc003e9 계열이며 [원본 OpenAPI](../openapi/openapi.yaml)는 기존 실행 계약이다. 실제 개발 DB/API 이미지는 변경하지 않았다.
- [W2-A 주차 메타·계정summary](ISSUE_13_W2_READ_SLICE.md) 두 경로를 main/실행원본에 추가하고 고유107사례/검증 이미지·DB0023 호환을 확인했다. 기존114경로/schema 변경0. 실제 서버 반영·선택기 전체 의존/인수는 미완료다. [W2-B](ISSUE_13_W2_CYCLE_ADMISSION.md) 생성·조회/일반 참가와 [W3](ISSUE_13_W3_CYCLE_LIFECYCLE.md) 명시 N개방/참가·취소/위임도 로컬 구현·격리 검증 완료다. 후보27경로/29동작은 main에 미등록이다. 다음은 W4다.
- W1/W2는 `917123e`, W3는 `13b655e`로 관리한다. W4 준비 `e8deb02`까지 작업 브랜치 push·원격 확인 완료이며 실제 서버/DB 이행·Flutter 인수는 미완료다. 구 API/worker는0023만 활성화하며 shadow0024~0026과 혼용하지 않는다.

## 구현 순서와 완료 조건

| 순서 | 작업 제목 | 구현할 범위 | 완료 조건·확인할 동작 | 상태 |
|---|---|---|---|---|
| W1 | 주차별 저장 구조·참가자·공대장 기반 | RoomCycle/target head·generation, 실제 회차 참가자와 persistent 관계 분리, 주차별 leadership/참가순서, 명시 target resolver, 원장·멱등/개방 이벤트 기반, 10시 predicate, 기존 worker 전환 준비 | 격리 DB에서 additive 이행/기존자료 분류·보존, C/N 관계·리더 분리, FK/고유성·signed bigint 순번, 원ACK/동일방 한도 보존, 수06/10시 경계·잘못된target 거절 검증 | 로컬 구현·격리 검증 완료/미게시 |
| W2 | 주차 조회·검색·생성·일반 참가 | 주차 메타/actualcycle·계정 summary, 생성 context·C/N 원자 생성, 목록/search/detail/plan 등 target 조회, 일반 신청/승인·직접 참가 | C/N 정보·자리·가시권한 분리, 숙련도OR/무관·자리/정렬을 페이지 전 SQL 적용, cursor 조건 결합, 생성 N실패 전체rollback/원ACK 복구, 신청·마지막자리 경합 검증 | [A](ISSUE_13_W2_READ_SLICE.md)·[B](ISSUE_13_W2_CYCLE_ADMISSION.md) 로컬 구현·격리 검증 완료/미게시. B는 후보 라우터·서버 미공개 |
| W3 | 다음 주 참가·개방·취소·공대장 위임 | 명시 N개방/재개+최초참가, C참가자 N즉시참가·대체캐릭터, 충돌/불참·대상캐릭터변경, N취소·자동승계/직접위임 | source자격 재검사, B방보존·실패시 A점유0, bundle 원자성, N 마지막1인 N만 종료, 명시재개 새generation/기존UUID보존, 참가순번 승계·직접위임시 본인참가 유지·C불변 | [W3](ISSUE_13_W3_CYCLE_LIFECYCLE.md) 로컬 구현·격리 검증 완료/미게시 |
| W4 | 주차별 일정·완료·공통 관리·전환 | 일정/개인표·투표·확인예약, 현재주차 완료/미완료·정정/재개, 공통설정·전역leave/end, 06시 worker·v1 호환 adapter | 명시확인 없는 복사일정 예약0, 완료 T=C·수10시부터, C완료시N불변, G1 공통권한·GlobalScope ACK, persistent CAS/영향0·quota, 중복worker/원ACK·legacy자료 보존 | W1~W3 의존 |
| W5 | 통합 검증·성능·실행 계약·네이티브 인계 | 자료 보존/전체 회귀·SQL성능 측정, 원본 OpenAPI/FastAPI 전체 대조, 실제 소비 가능 구간 묶음의 commit/push·원격확인·인계 | 검증한 경로/환경·실행SHA/게시여부·미준비/미확인 범위 명시, Flutter가 소비할 실제 경로 준비 증명, Flutter 적용·실기기·운영완료를 구별 | 통합 마무리 미실행 |

W0 설계·소비 검토는 완료다. 이 표가 이전1판의 W0 대기/빈N개방·전역리더/매주자동개방 가정을 대체한다. W3에 명시개방/재개·공대장 위임을 포함하며, W4는 완료 재개와 주차 전환을 담당한다.

## W1 실행 기록의 기준 — 완료/다음 W2

W1은 `0024_recruitment_cycles`와 10개 추가 표·내부 finalizer/명령 wrapper로 구현했다. 추가 연결 표를 사용해 기존 모든 표/원장/ACK와 기록 시각을 보존했다. 세대·리더·순번·설정이 미상이면 review로 남기고, 기존 OpeningEvent 제약 대신 신규 generation별 opening 원천을 사용한다. 관련 고유63사례 통과 근거·기존 컨테이너 계약 파일 실패/재검증·한계는 [W1 기록](ISSUE_13_W1_CYCLE_FOUNDATION.md)에 있다. 아래 목록은 다음 작업 지시가 아니라 W1 착수 때의 대조 기준이다.

1. 현재 통합 모델 `app/raid_rooms/integrated_models.py`, 원천/원장 모델, `continuation.py`·`worker.py`, 명령/멱등·readiness와 `alembic/versions/0019`~`0023`을 대조한다. F1의 `models.py`를 통합모델로 오인하지 않는다. 일부 docstring의 not mounted 표시는 과거 기록이며 실제 main 연결을 확인한다.
2. 현재 코드의 방 전체 leader/members/plan revision·고유 제약을 찾고 주차별로 옮길 부분과 공통/persistent로 남길 부분을 나눈다. 새 migration의 실제 다음 번호·의존 head를 착수 시 확인한다.
3. RoomCycle/회차별 참가자·leadership/순서·generation/opening event의 실제 DDL과 기존자료 이행 코드를 작성한다. 기존 Round FK로 주차가 유일하게 증명되는 자료만 분류한다. 불명/혼합 자료는 review로 보존하고 임의 C 대입·N복제·동의 복원은 하지 않는다.
4. 격리 DB에서 이행·제약·원장/멱등·C/N격리·06/10시 guard를 검증한다. 현재 개발 DB나 실제 회원자료에 이행했다고 보고하지 않는다.
5. W1 결과와 남은 W2 의존을 기록한다. W1 내부 기반만으로 신규 v2 경로가 서버에 준비됐다고 인계하지 않는다.

## 확정 정책과 구현 경계

- C는 실제 현재 주차, N=C+7. 임의 요일 N선택 허용, C+14 없음. 수요일06시는 주차 전환, 플레이/완료는 수10시 하한이다.
- 최초 생성에서 체크한 C/N만 단일 명령으로 함께 확정한다. 이후 참가·탈퇴·자동승계·직접위임·완료는 T별 독립이다. C완료/미완료종료·N취소가 반대 주차를 자동 변경하지 않는다.
- 공통 권한 G1은 C 공대장, C 회차 자체가 없을 때만 N 공대장이다. 닫힘/review C가 있어도 N으로 대체하지 않는다. 공통설정 ACK는 GlobalScope+CommonSettingsAck이며 실제 영향목록과 성공 후 room revision을 반환한다.
- 자동 매주 N개방·기존 참가자 자동 N참가·복사일정 자동 예약동의는 추가하지 않는다. 열린 N의 OFF 철회 금지, N취소와 전역 leave/end를 구별한다.
- 한도는 persistent 고유방 기준 C/N 동일방1개다. N취소만으로 한도 회복하지 않는다. 과거 완료·원ACK·사용원천은 보존한다. 같은 키/불변본문은 경계·권한 재검사보다 원ACK 복구를 먼저 한다.
- #19의 통계 산정 미확정 정책은 독립 후속이며 모집 원천 보존/구현을 막지 않는다. 계정·그룹 등 무관 기능은 확대하지 않는다.

## 네이티브 인계 순서

Flutter가 밝힌 다음 작은 구간은 **주차 메타/actualcycle·계정 summary/선택기**다. Backend는 W1 기반을 먼저 만든 뒤 W2에서 이 읽기 구간의 준비 여부를 우선 확인한다. 최소 관련 경로는 GET `/v2/raid-cycles`, POST `/v2/me/raid-weekly-summary`이며 실제 선택기 연결에 필요한 본인 목록/target 계약 의존도 함께 확인한다. 기존 계정·캐시·회원격리 회귀는 Flutter 착수 시 확인 대상이다.

W5는 통합 완료 단계이며 중간 인계를 마지막까지 미룬다는 의미가 아니다. 실제 소비 가능한 구간은 **해당 의존/보존/검증 완료 → 구현+원본OpenAPI 일치 → commit/push·원격확인 → 이슈 #13 인계** 순서로 묶어 전달한다. 불완전한 쓰기·구 worker 혼용 상태는 실행서버에 노출하지 않는다. 실행 DB 이행/이미지 전환은 그 시점의 대상·영향·승인 범위를 확인하고 기능 계약 확정만으로 실행하지 않는다.

다음 작업자는 이슈 본문·최신 댓글/작업트리·원격 상태를 확인한 뒤 **W4부터** 이어간다. 사용자 추가 제품결정이나 네이티브의 동일 계약 재회신을 선행 조건으로 두지 않는다. W1~W3는 로컬 구현·격리 검증까지이며 후보의 실제 서버 공개/worker·v1 전환은 하지 않았다.

W4는 W3 취소/재참가에서 보존한 이전 예약·동의와 새 동의 구간을 분리하고, 명시 불참 결정의 summary projection을 연결한다. 이전 CycleSubmission은 취소 이벤트에 보존하고 현재 head는 정리하므로 재참가 시 이전 제출/확인을 자동 복원하지 않는다.
