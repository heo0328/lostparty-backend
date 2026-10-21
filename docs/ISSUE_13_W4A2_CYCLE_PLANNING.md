# Issue #13 W4-A2 — target 일정 조율·제안/투표

2026-10-21 / `feat/raid-recruitment` / 시작 `e8e4bcf`.

기준은 [전체85번째 Backend · W4-A1 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6314976554), [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), 고정 전체 명세0.4.1/policy two-cycle-contract-4다. 착수와 인계 준비 시 Issue 본문·전체85댓글을 확인했고 새 Flutter 요청이나 계약 변경은 없었다.

## 구현 범위

| 후보 동작 | 처리 |
|---|---|
| PUT `/v2/raid-rooms/{room_id}/schedule-groups` | 실제 T/generation 공대장·target/plan/members/leadership/group CAS, 미확정 그룹 편집 |
| GET `/v2/raid-schedule-groups/{group_id}/candidates` | 실제 T 제출표·자격·활성 예약을 사용한 읽기 전용 후보 계산 |
| POST `/v2/raid-schedule-groups/{group_id}/selections` | 수동 대안 선택 또는 조율 의도 선택; 조율형 임의 시각 입력 없음 |
| POST `/v2/raid-rooms/{room_id}/schedule-proposals` | 세션/일정 revision과 전체 활성 item 기간을 고정한 불변 제안 |
| POST `/v2/raid-schedule-proposals/{proposal_id}/responses` | 현재 CM revision의 명시 응답, 각 세션 정족수 충족 후 일괄 적용 |

개인표 저장 자체는 조율/투표/예약을 전파하지 않는다. T 제출·참가/승인·명시 다음주 참가·취소/캐릭터 변경 쓰기에서만 필요한 재평가를 한다. 확정된 초기 일정은 표 재제출/인원 변동만으로 이동하지 않는다. 별도 변경 제안은 현재 참가 집합으로 재평가한다. 조회는 REPEATABLE READ/READ ONLY이며 제안을 적용하거나 자료를 만들지 않는다.

후보는 저장된 개시 floor·DB 현재 시각·실제 T의 수요일10시를 하한으로 5분 단위/한 주 이내에서 탐색한다. 실제 제출표 교집합·선택 요일/공대장 latest·최대24시간 합계·다른 활성 예약 회피를 검사한다. 최초 조율은 추가인원 최소1이고 저장 floor에 다시30분을 더하지 않는다. 이미 확정된 일정의 일반 신규 모집은 `now < starts_at-30분`을 유지한다. 최종 DB 시각 검사와 원 ACK는 동일 트랜잭션이다.

정족수는 세션별 N1=1(별도 본인 명시 응답), N2=2/N3·4=2/N5·6=3/N7·8=4다. N2 이상 제안자의 제안은 본인1표를 기록하되 생성만으로 적용하지 않는다. 여러 타임은 모두 충족한 뒤 함께 적용한다. 수락자만 새 일정 확인/예약을 기록하고 미동의자의 이전 해당 예약은 해제하여 확인 대기로 둔다. 명시 수락/확인은 개인표 밖이나 시간 중복을 이유로 거절하지 않는다. 후발 참가자는 pending이고, 취소·재참가/캐릭터 변경 후 과거 표를 자동 복원하지 않는다.

## 저장과 보존

shadow `0028_cycle_planning`은 불변 제안 귀속/내용·CM revision별 표·일정 사건·대안 edition 매핑4표를 추가한다. 기존 모든 행/열/기록시각은 이행 전후 지문으로 대조한다. 동의 유일키는 `(user_id,command_id,participation_id)`로 확장하여 한 명령의 여러 세션 동의를 허용한다. 활성 예약 partial UNIQUE와 복합 소유 FK는 유지한다.

그룹 ID/수정 revision을 유지하면서 이전 대안·세션을 삭제하지 않고 사건에 편집 전 snapshot을 기록한다. 최신 대안은 edition 매핑으로 구분한다. 변경 전 일정/segments·해제 예약·동의·선택 캐릭터/build·제출 근거와 다른 T/세대는 보존한다. 기존 원 ACK는 탈퇴/일정 변경 후에도 원 명령으로 복구한다. 네 신규 표의 불변 guard와 시각 trigger도 readiness에서 검사한다.

## 검증과 실행 경계

신규31개·기존 회귀218개, 고유249개를 분리 실행으로 확인했다. 최종 묶음247PASS/1379.73초(A2 신규29·기존218)와 추가2PASS/33.11초(나머지29 deselected)이며 예비23PASS 등은 중복 합산하지 않는다. 실패0, 기존 BlockingPortal deprecation1건만 남았다. 테스트는 전용 `lostparty-w4a2-test` tmpfs PostgreSQL/제한 LOGIN과 cached 검증 이미지의 `lostparty-w4a2-runner`에서 합성 자료로만 실행한다.

고정 계약53경로/56동작/204schema·84합성 사례/CAS6쌍/endpoint흐름2개 검증 통과. canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`은 불변이다. 정적 DTO SHA256 `7d6ecf3be8d5ecc65764b2b1002ac875cc0d5381fcd97a01944d481c78d39482`는 검증 사용본과 일치한다.

실행 FastAPI/원본 `openapi/openapi.yaml` 전체 일치·116경로 유지, 신규 후보는 전체36경로/39동작이다. main 미등록이고 구 API/worker는0023만 활성 허용한다. 실제 개발 DB/API 이미지·서버는 전환하지 않았다. 실제 provider/회원/기기·운영 성능·Flutter 적용/인수는 미검증이다.

실제 N1/N2/N3 및 세션별 N1/N2 혼합 정족수·1..8인 순수 정책, 동시 중복/원 ACK·재참가/캐릭터 변경 표 무효화·후발 미동의자 해제/확인 대기, 다중 세션 원자 rollback, 읽기 무쓰기·T 권한/CAS·요일/순서/latest·자동 중복 회피·개시 floor/최초 예외/최종 시각·기간 경계와 고정 schema HTTP5동작을 확인했다. 비어 있지 않은 기존 동의/예약을 생성한 뒤0028 이행 전후 모든 기존 행/열/시각 지문도 일치했다. 실제8인 서버/회원 시험을 수행한 결과는 아니다.

## 다음 담당과 완료 조건

다음 Backend는 **W4-B 완료/정정·현재주 재개**다. item별 완료/남은 예약의 정확 귀속 해제·C 수요일10시 이후 권한, 완료 없이 현재주 전체 미완료 종료·정정/반복 재개와 이전 세대 보존을 구현한다. 이후 W4-C G1 공통/전역 관계 → W4-D 06worker/v1·legacy/declined summary·활성화 검증 → W5 통합/성능·실제 인계다. 같은 계약 재검토나 새 제품 입력은 선행 조건이 아니다.

이번 구간의 구현/검증·commit/push/원격 확인을 공식 Issue에 기록한다. 후보 미등록 상태이므로 새 Flutter 서버 시험을 요청하지 않는다. W4-A1/A2 소스 완료와 W4 전체·실제 서버 공개·Flutter 인수는 구별한다.
