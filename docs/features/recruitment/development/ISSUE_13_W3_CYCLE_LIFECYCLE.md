# Issue #13 W3 — 명시 N개방·참가·취소·승계/위임

2026-10-21 / `feat/raid-recruitment` / 구현 시작 `917123e` 이후 변경.

기준: [전체84번째 Flutter 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)·[계약4판](../contracts/ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[ACK 보완](../contracts/ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md). 착수 시 Issue 본문과 실제84개 댓글을 조회했고 이후 계약 변경·신규 요청은 없었다. 고정 전체 명세 0.4.1/policy4·53경로/56동작/204schema와 canonical hash는 유지한다.

## 구현 범위와 실행 경계

W3의 로컬 구현과 격리 검증을 완료했다. 실제 서버·개발 DB를 전환하거나 Flutter 구현시험을 요청하지 않았다. 구 API/worker는 0023만 활성화하며 0024~0026은 shadow 저장 구조다. W3 후보는 main에 등록하지 않았고 실행 `openapi/openapi.yaml`은 기존116경로 그대로다. W2 후보에 **10동작/10경로**를 추가해 후보 합계 **27경로/29동작**이다.

| 경로 | 동작 |
|---|---|
| GET `/v2/me/raid-rooms/{room_id}/opening-context` / POST `recruitment-openings` | 실제 C 리더의 명시 N개방/재개와 본인 첫 bundle 참가 |
| GET `continuation-context` / POST `continuation-participations` | 유효한 C 참가자의 N 승인 생략 참가, 기본 C 캐릭터/역할·명시 대체 선택 |
| POST `continuation-declines` | N 미참가자의 명시 불참 원천 기록, 점유·예약0 |
| GET `participation-cancellation-context` / POST `participation-cancellations` | N 본인 bundle 취소, 유효 순번 후임 승계·마지막이면 N만 cancelled |
| GET `leadership-transfer-context` / POST `leadership-transfers` | T 현재 리더의 명시 대상 위임, 본인 참가/슬롯/예약 유지 |
| POST `character-changes` | 미완료 T bundle만 소유·활동·역할·구성/주간 CAS 재검사 후 원자 교체 |

캐릭터 교체 context는 기존 후보 GET `/v2/raid-rooms/{room_id}/admission-context?intent=change_character`에 연결했다. 해당 입장 context의 `permissions`는 요청 intent 한 키만 반환한다. plan/settings의 완료된 W3 명령 권한을 실제 T와 source C 자격에 맞게 연결했다. 후속 W4 명령은 계속 미준비 상태다.

## 저장·보존

`0026_cycle_lifecycle`은 **추가2표**다. 기존 표의 행/열을 수정하거나 구 의사 선택을 새 동의로 복원하지 않는다.

- `recruitment_cycle_decisions`: actual cycle/generation·actor·command에 연결한 명시 불참/직접위임/자동승계/마지막 미래취소 원천. UPDATE/DELETE를 DB trigger로 거절한다. 같은 actor의 새 결정을 새 명령/이벤트로 기록한다.
- `recruitment_cycle_schedule_groups`: 방·cycle/generation·일정 그룹의 정확한 복합 FK. 기존 명시 generation1의 증명 가능한 그룹만 연결하고 legacy unknown은 추정하지 않는다. 재개 때 새 세대 그룹을 별도 ID로 보존하며 기존 그룹/Session/Alternative를 삭제·덮어쓰지 않는다. 내부 저장 key와 wire의 원래 client key를 분리한다.

취소 후 같은 세대 재참가는 기존 Assignment ID를 재활성화해 기존 UNIQUE를 지킨다. CycleMember도 같은 ID지만 새 joined_order/revision/참가 이벤트를 받으며 이전 취소 구간을 보존한다. 완료된 Assignment는 이 경로로 부활하지 않는다. 참가·취소·캐릭터 변경의 이벤트에는 당시 캐릭터/역할·편성·display/build·소유/생명주기·입장 근거를 보존한다.

취소 시 현재 제출표는 이벤트에 원문·source revision/시각을 보존한 뒤 현재 head만 정리한다. 같은 CycleMember로 재참가해도 이전 제출표를 자동 복원하지 않는다. 개인표 원본·C 제출표는 건드리지 않는다. 이전 예약 행은 해제 근거/시각을 유지하고 삭제하지 않는다.

## 명령 의미

### 개방·재개

- target는 실제 N만, source는 실제 C의 유효한 persistent/실참가 관계다. source C 리더만 명시 개방/재개하며 N 리더라는 이유로 C 권한을 얻지 않는다. C의 completed/stopped는 source를 자동 소멸시키지 않지만 명시 cancelled/removed·전역 관계 종료는 source가 아니다. 현재 회원·소유/활동/역할·입장레벨/전투력·그룹·한도도 재검사한다.
- GET은 UUID 후보를 token에 결합할 뿐 row/점유/예약을 만들지 않는다. 신규 N은 scope의 ID/revision/generation=null이며 POST expected_target_revision도 null이다. 성공 뒤 최초 target revision1/순번1/리더를 한 transaction으로 확정한다.
- 이미 열린 N의 새 open context는 `already_open`·POST noop이며 기존 리더를 덮거나 본인을 암묵 추가하지 않는다. cancelled N은 open으로 복원하지 않고 명시 reopen만 허용한다. 같은 RoomCycle UUID·generation+1·새 Round/CM/Session으로 재개하며 target epoch는 context의 prospective 값으로 정확히 한 번 전진한다.
- C의 현재 조건/묶음·기간·일정 의도를 target 날짜로 복사한다. N 복사 일정은 확인 대기·예약0이다. 이전 세대의 참가자·제출표·예약·동의/취소 이력을 복원하지 않는다. 수10시·개시+30분·5분 정렬/최대24시간·cycle 끝 검증은 유지한다. 새 N 자동 생성/가입 worker는 추가하지 않았다.

### 기존 참가자의 명시 참가·불참

- 기본 C 캐릭터/역할을 GET이 제공하므로 정상 진입에 재선택을 요구하지 않는다. 대체 조회의 character_id/selected_role은 둘 다 제공해야 한다. N의 leader_only도 source C 자격에 한해 승인 단계를 생략하며 전체 bundle/슬롯·선택 역할 최신 성공 전투력·현재 소유/활동/한도·주간 CAS/마감을 생략하지 않는다. OFF/자동참가 정책을 새로 추가하지 않는다.
- B방 점유는 `TARGET_CHARACTER_CONFLICT`와 권한 내 최소 충돌 정보로 안내한다. B를 자동 취소하거나 A에 부분 참가시키지 않는다. 대체 캐릭터는 새 context·명시 명령으로 확인한다. 대체 역할의 별도 power source revision도 token에 결합한다.
- 명시 불참은 예약/실제 참가가 아니다. 이미 N 참가중이면 불참 기록으로 우회하지 않고 취소 명령을 사용한다. 불참 이벤트는 캐릭터·raid·actual target 원천을 보존한다. 기존 W2-A 실행 summary의 새 이벤트 projection 연결은 W4 전환 때 처리하며, 아직 구 서버가 새 원천을 표시한다고 보고하지 않는다.

### 취소·승계·위임·교체

- N 취소는 본인의 해당 generation 활성 Assignment/정확한 weekly lease·예약/participation만 정리한다. old 캐릭터의 현재 소유/활동 성공을 취소의 선행 조건으로 삼지 않는다. persistent 관계·방 한도·C 리더/참가/완료/예약은 보존한다.
- 리더 취소의 후임은 실제 participating/completed/stopped 관계 중 현재 자격이 유효한 최초 `(joined_order, cycle_member_id)`다. review/신청/legacy 의사는 후보가 아니다. 후보가 없는데 다른 실제 관계가 있으면 승계를 거절한다. context 뒤 자격/후보가 바뀌면 `SUCCESSOR_UNAVAILABLE`로 다시 확인하며 다른 후보에게 몰래 넘기지 않는다.
- 마지막1인 N 취소는 해당 세대 Round·Session/제안/pending 신청만 종료·취소한다. 실제 주간 미완료종료와 다른 `future_empty_cancelled` 원천이며 Room.ended_at/C/완료 원천을 바꾸지 않는다. N 취소로 persistent 방 한도를 자동 회수하지 않는다.
- 직접 T 위임은 현재 리더와 실제 후보의 revision·leadership/target/context를 검사한다. actor는 남고 후보의 joined_order/자리·캐릭터·예약은 그대로다. completed/stopped T의 유효한 관리 관계도 이 위임을 사용할 수 있다.
- 대상 캐릭터 교체는 기존 원장을 정확히 해제·새 원장을 확보하고 같은 Assignment ID/슬롯에 새 선택 근거를 기록한다. old 캐릭터가 suspect/소유 변경이어도 새 선택이 유효하면 교체할 수 있다. 현재 및 반대 주차/타 방의 완료·점유를 덮지 않는다. 기존 일정 확인은 자동 승계하지 않고 확인 대기로 돌린다.

## context·권한·계약

context는 actor/명령/actual T·현재 C/Room·source CM·전체 bundle·선택·카탈로그/그룹/한도·원장/전투력·후보/영향 snapshot에 결합한 AEAD다. 유효시간은 120초와 C 종료 중 짧은 값, 최대4096bytes다. GET은 단일 RR/READ ONLY snapshot이며 provider/키 캡처를 하지 않는다.

새 명령은 최종 DB 시각으로 주차·마감을 재검사하고 실패 시 원장/순번/이벤트·준비 ACK까지 rollback한다. 원키·불변본문의 원 ACK 복구는 context 만료·현재 주차/권한 재검사보다 먼저다. 경합·stale은 자동 새키/다른 후임 선택·부분 재시도로 우회하지 않는다.

정적 `cycle_wire.py`는 기존 생성기에 고정 W3 root schema를 추가해 생성했다. 앱은 docs를 읽지 않는다. candidate와 runtime OpenAPI/서버 준비를 구별한다. HTTP 입력·성공/오류·context는 고정 전체 명세의 실제 ref/format으로 검증한다.

## 검증 기록

- 초기 명시 개방/기존 N noop·source 권한 2PASS, 기본 명령11PASS.
- 확대 검증 중 source cancelled/removed 합성 fixture의 시각 조회가 중간 autoflush를 일으켜 CHECK 위반을 발견했다. 상태 변경 전에 DB 시각을 확보하도록 fixture를 수정했고 26PASS/192.25초로 재검증했다. 실제 명령은 처음 확보한 stamp를 사용하며 이 중간 상태를 만들지 않는다.
- W3/W2 후보 묶음63PASS/396.12초를 확인했다. 이후 취소 시 제출표 보존/현재 head 정리와 대체 역할 power revision 결합을 보완했다. 전투력 갱신 합성 fixture는 DB 보호 규칙에 따라 관측 시각도 함께 전진하도록 수정했다. 최종 보완 W3 신규30+기존 회귀134 **총164PASS/503.70초**다. W1 주차/원장·W2-A summary·v1 참가/일정/제출·계정 bootstrap·기록시각 및 실행 FastAPI/원본116경로 전체일치가 포함된다. 기존 BlockingPortal deprecation1건 외 실패는 없다. 앞선 2/11/26/63은 중복이며 합산하지 않는다. 완료·중단 상태와 명시 일정 확인은 합성 fixture로 준비한 W3 검증이며 W4 완료/확인 HTTP 구현 증거가 아니다.

- 고정 계약 검증53경로/56동작/204schema·84합성사례/CAS6쌍/endpoint흐름2개와 canonical hash 불변을 확인했다. 정적 DTO 생성/검증 사용본 SHA256 `593b2dd5e4a30030a1382572b33b2fc8c3c7512de5b83d53ba6f1c8395c3d8c1` 일치, 변경 Python AST·문서 링크·diff 공백 검사를 통과했다. 위 schema 합성 검증은 실행 테스트와 별도다.

## 다음 작업·게시

다음 W4는 target별 제출표/조율·투표·확인 예약·완료/정정/현재주 재개, G1 공통 명령·전역 leave/end, 06시 worker/v1 adapter·legacy review 전환이다. 특히 같은 세대 재참가 후 동일 session/schedule_revision을 새로 확인할 때 이전 해제 예약을 덮거나 UNIQUE와 충돌하지 않도록 새 동의 구간을 모델링해야 한다. W3는 재참가를 확인 대기/예약0으로 두며 이 후속 확인 API의 완료를 주장하지 않는다.

W4에서 새 declined 원천을 summary에 연결하고, legacy review·닫힘/재개 세대 projection과 전체 실행 권한을 검증한다. W5는 전체 계약/FastAPI·보존/SQL/성능·실제 소비 가능 구간의 게시/네이티브 인계다. 실제 준비가 된 중간 구간은 검증·commit/push·원격 확인 뒤 인계하며 W5까지 무조건 미루지 않는다.

구간 완료 시 검증·문서와 함께 커밋하는 사용자 상시 지시를 따른다. 이번은 로컬 후보 구현이며 push·Issue 시험 요청·merge·배포·실제 개발 DB/컨테이너 변경은 별도 수행하지 않았다.
