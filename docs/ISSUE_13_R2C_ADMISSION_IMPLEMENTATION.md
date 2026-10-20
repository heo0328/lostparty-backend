# #13 R2-C 생성·신청/승인 명령과 미활성 HTTP

2026-10-20. `feat/raid-recruitment`에서 [R2-B 내부 연결](ISSUE_13_R2B_PARTICIPATION_IMPLEMENTATION.md)을 실제 명령 transaction과 HTTP에 연결했다. [최신 R3 입력 계약](ISSUE_13_R0_CONTRACT_R3.md), [소비 정정의 context/승인·조회 범위](ISSUE_13_R0_CONSUMER_CORRECTIONS.md), [최신 기술 경계](ISSUE_13_R0_TECHNICAL_BOUNDARIES_R4.md)를 따른다. 실제 main/API8000/개발DB0016 활성화는 R5이며, 이 문서의 구현은 격리 앱/DB 검증이다.

## 현재 실행 가능한 구간

`admission_router.py`의 미활성 HTTP 10동작:

| 동작 | 경로 |
|---|---|
| 생성 문맥 GET | /v1/me/raid-room-creation-context |
| 참가 문맥 GET | /v1/raid-rooms/{room_id}/admission-context |
| 생성 POST | /v1/raid-rooms |
| 즉시참가 POST | /v1/raid-rooms/{room_id}/join |
| 신청 POST | /v1/raid-rooms/{room_id}/applications |
| 승인 POST | /v1/raid-room-applications/{application_id}/approve |
| 거절 POST | /v1/raid-room-applications/{application_id}/reject |
| 본인 철회 POST | /v1/raid-room-applications/{application_id}/withdraw |
| 본인 계획 GET | /v1/me/raid-rooms/{room_id}/plan |
| 본인 최소 신청/관리 검토 GET | /v1/raid-room-applications/{application_id} |

**현재 성공 경로는 schedule_groups=[]인 완전 미정 방**이다. 방·전체 item/현재 round·persistent membership·assignment/WeeklyState를 만들며 임의 session/확인/예약을 만들지 않는다. 미정이 레이드 불참을 뜻하지 않는다. nonempty schedule_groups/기존 세션·일정 그룹/일정 target은 성공으로 무시하지 않으며 `RECRUITMENT_SCHEDULING_NOT_READY`503 또는 유효하지 않은 target400으로 거절한다. 정시 마감·최초 임계치 예외/기존 본인 확인·예약/시간 경고/투표·미래 choice는 **R3 연결 전 미구현**이다. 이를 제품 범위 축소나 Flutter 추가 결정 대기로 해석하지 않는다.

정확한 현재 미활성 계약은 [recruitment-admission.draft.json](../openapi/recruitment-admission.draft.json)이다. 구현 생성 객체와 전체 비교하며 실제400/no-store·401/멱등 진행중409 헤더를 반영했다. 기존 `openapi/openapi.yaml`/main 공개 계약과 R2-A 미활성 계약은 그대로이며 R5 때 통합한다. 아직 미구현인 방 탈퇴/리더 이전/종료 권한은 계획 응답에서 명시적으로 비활성화한다. 전체 목록/검색·나머지 상세/설정·관계 조정은 후속 통합 대상이다.

## 명령·경합·원 ACK

- 모든 명령은 현재 인증 → 독립 operation/UUIDv4 키·body digest 예약 → 기존 game mutation 잠금/현재 actor 재검사 → 서버 원천/CAS/권한 재검사 → 원자 효과+원 ACK 저장 → flush 뒤 DB clock 주차/만료 검사 순서다. 실패는 자료·ACK를 rollback하고 같은 body/key의 재시도가 가능하다. 원 성공 재송은 현재 인증을 거친 뒤 새 context·점수·만료 검사보다 먼저 원 최소 ACK를 반환하며 효과를 다시 실행하지 않는다.
- 생성은 최신 카탈로그/그룹 revision·본인 선택/주간 버전과 서버 문맥을 재검사한다. 새 room/item/round/membership/assignment의 초기 revision은1이고 실제 주간 점유는 기존 원장 revision을 올린다. nullable 숙련도와 나이스단/P1 독립성을 유지한다.
- item duration은 명시10..1440/5분 또는 null이며 canonical normal/hard/nightmare와 stage1/2/3의10/20/30 정책 `difficulty-duration-v1`을 설정 출처로 저장한다. 모르는 난이도는 임의 기본값을 적용하지 않는다. session 미정 상태에서 주간 전체 합계1440 제한을 새로 추가하지 않는다. 세션별 합계/경계 검사는 R3다.
- 최초 개시는 item별 서버 권위 시각과 고정+30분 floor/처리시각을 저장한다. 자동 개시 기본OFF이며 ON은 continuation 필요/다음 주차부터 효력이다. 미래 choice/실제 자동 실행은 R3 전 미구현이다.
- 신청은 pending snapshot일 뿐 슬롯/방 한도/WeeklyState를 예약하거나 소비하지 않는다. 본인 현재 소유·활동/역할·원장 등 자격과 정확한 target 귀속은 확인한다. 자리·방 한도 최종 증가는 승인에서 재검사하므로 신청을 허용했어도 승인에서 차단될 수 있다. pending 중복은409이며 이미 만료된 pending만 새 명령에서 종료 처리한다. 신청 만료는 현 cycle 종료이며 GET로 만료/시각 행을 갱신하지 않는다.
- 승인자는 현재 공대장이다. 요청에는 신청자 개인 소유/P1/원장 CAS를 넣지 않는다. 서버가 원 선택의 character/role/소유·lifecycle 세대를 보존하면서 현재 registration/roster/P1·성공값/한도·주간 revision을 읽고, 현재 자격/자리/구성을 검사해 승인한다. 신청 당시 높은 점수로 승인하지 않으며 신청 원본 selection/build는 갱신하지 않는다. 승인 도중 만료 정각에 도달하면 점유/assignment/승인상태/ACK를 모두 rollback한다.
- 거절은 현재 공대장과 application/room/members/plan CAS를 검사하고 본인 철회는 actor+application CAS를 검사한다. 새 참가 자격을 정리 명령에 강제하지 않으며 점유를 만들지 않는다. 철회/거절도 원 ACK와 최종 만료 검사를 갖는다.

## 문맥·원접수/읽기 권한

선택 문맥은 `s1.`+HMAC-SHA256 hex의 **67문자 opaque MAC**이다. 내부 자료를 평문으로 인코딩하지 않으며 actor/action·character/role/소유·주차·item/round·현재 source 버전/성공값 버전·한도/사용량·group/room/settings/plan/members/policy에 바인딩한다. GET는 RR READ ONLY/no-store이고 context 행/lease나 provider 요청을 만들지 않는다. 명령은 현재 원천으로 MAC를 재구성해 위조/다른 actor/옛 source를409로 거절한다. 당해 주차·정확한 snapshot이 수명이며 키 교체도 옛 context를 무효화한다. 임의의5분 TTL은 추가하지 않았다. R4 완료/종료용 짧은 AEAD context와 별개의 선택 문맥이며 해당 R4 보안 경계를 대체하지 않는다.

새 application의 원접수 scope/group은 서버가 저장한다. build snapshot에는 원 application/room/actor·scope revision/접수시각과 당시 선택 역할의 최근 성공 원본을 묶어 보존한다. 승인 때 이 원본의 귀속을 확인하며 `legacy_unknown`/증명 없는 자료를 공개 접수로 승격하지 않는다. 공개 접수 뒤 그룹 전용으로 복귀해도 그 원 application에는 외부 회원 승인 예외를 적용한다. 새 외부 신청/취소 후 재신청에는 현재 scope를 적용한다.

본인은 최소 ApplicationView만 읽으며 다른 사람의 application은 현재 공대장만 검토한다. 그룹 전용 관리 검토에는 현재 그룹 회원도 확인한다. 무관한 actor는404다. 관리 응답은 현재 평가 이유/선택 역할 comparison과 승인·거절 권한을 반환하되 다른 사람의 ownership/weekly CAS·selection token·다른 방 내역은 노출하지 않는다. 평가 불가 comparison은 required nullable이며 실패/만료를 성공 자격으로 표시하지 않는다. 기존 그룹 탈퇴 회원의 본인 계획/최소 신청 접근과 새 입장 자격은 분리한다.

본문 streaming/query byte 상한은32768, item 수는 현재 카탈로그의 중복 없는 raid 집합으로 제한한다. 중복 query/header/중첩 JSON 키·알 수 없는 필드·GET body를 거절하며 strict DTO/nullable/숙련도 enum·수치 타입·기간을 검사한다. 출력 계획은 현재 구현에 맞춰 일정·participation/proposal 배열이 비어 있음을 명시한다. 기술 측정·실행 결과는 DEV_LOG를 따른다.

## 다음·실제 상태

다음은 Backend **R3 일정 의도/세션·기간/주차·점검·floor/마감→신규 임계치/기존 본인 확인·예약·시간 경고→제안/정족수·다음주**다. 이어 R4 완료·전체 탈퇴/종료·권한·검색/목록·AEAD context, R5 실제 schema/앱·원본 OpenAPI 통합/commit·push·원격 확인 후 필요한 Flutter 인계를 진행한다. 현재 제품 설계 재협의/네이티브 테스트 대기가 아니다.

신규 migration은 없고 기존0021 저장 원천을 사용한다. 실제 API8000/개발DB0016/이미지·자료·외부 provider/Flutter 소스는 변경하지 않았으며 실제 서버/기기 인수 완료로 보고하지 않는다.
