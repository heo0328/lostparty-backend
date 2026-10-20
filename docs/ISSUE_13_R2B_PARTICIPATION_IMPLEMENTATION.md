# #13 R2-B 관계·캐릭터/슬롯·주간 원장 연결

2026-10-20. `feat/raid-recruitment`의 **내부 transaction 기반 구현**이다. 새 생성/신청/승인 HTTP를 활성화한 것이 아니다. [R3 입력 계약](ISSUE_13_R0_CONTRACT_R3.md)과 [P1 성공값 계약](ISSUE_13_R0_CONSUMER_CORRECTIONS.md)의 R2 구간을 연결한다. 다음은 R2-C 생성/신청/승인 명령과 context/CAS·ACK·조회/정확한 HTTP 계약 통합이며, R3 일정/예약·R4 완료/종료·R5 실제 활성화는 계속 미완료다.

## 구현한 경계

- `participation_commands.py`의 strict Selection/Target은 현재 합의된 CharacterSelection/TargetItemSelection 필드를 따른다. 이 타입 자체는 공개 REST 계약이 아니다.
- `participation_core.admit_bundle`은 호출자의 인증·game mutation 잠금·room/context CAS·권한/마감 검사 transaction 안에서 사용한다. 내부 함수가 직접 신청을 승인하거나 공대장/직접참가 권한을 부여하지 않는다. 이번 구간은 모든 활성 item/현재 주차 round의 완전한 target 집합을 검사해 persistent membership·개별 assignment·주간 점유를 같은 transaction으로 만든다. 부분 item 불참/참가를 허용하지 않는다. 일정 미정에도 실제 레이드 참가 관계를 만들되 session/참가 확인·예약은 추정 생성하지 않는다.
- 현재 인증 소유/등록·활동 캐릭터·생명주기/claim과 registration/ownership/roster/lifecycle/역할 head·한도/사용량·round/주간 CAS를 검사한다. 종료/검토 전 방·닫힌/과거 round·현재 카탈로그와 게임 인원 불일치·완료/점유 중 원장은 거절한다. 주차가 쓰기 도중 바뀌면 transaction을 rollback한다.
- 앱 정원은 혼합 묶음4, 단독은 게임4/8이다. 혼합4는 각 item에서 party1만 허용하고 단독8은 party2를 유지한다. 파티별 빈 1..4 슬롯을 서버가 배정하고 3딜러/1서포터 및 딜러 동직업 제한을 검사한다. 앱 membership 수·슬롯·모든 item의 자격을 확인한 뒤 저장한다.
- 새 membership은 현재 방 수 한도를 소비한다. 기존 persistent membership의 후속 round 연결은 방 수를 중복 소비하지 않는다. 기존 회원 초과에 따른 방 제한, 그룹 전용 입장의 현재 그룹 회원/그룹 자체 정원·가입 한도 초과를 검사한다. public + group_id는 그룹 입장 조건을 강제하지 않는다.
- `room_count`는 통합 방이 있으면 종료된 관계까지 새 원천을 기준으로 삼고, 아직 통합 방이 없는 legacy 방만 구 원천에서 보완한다. 보존된 구 행이 새 관계 종료 후 사용량을 되살리거나 같은 방을 이중 집계하지 않는다. 실제 기존 한도 HTTP의 adapter는 변경하지 않았고 R5에서 일괄 연결한다.
- 선택 역할의 현재 P1 head CAS와 `RolePowerSuccess`의 실제 최근 성공 값/원본 version·관측/저장시각·경고를 구분한다. Decimal 직접 비교로 unrestricted/missing/below/meets를 판단한다. NULL head에서 최근 성공 유지, 낮아진 최신 관측 채택, 다른 역할/과거 최고값 대체 없음이며 TTL·강제 갱신도 없다. assignment build에 성공 snapshot과 판정 출처를 함께 보존한다.

## 주간 원장 세대·추가 이행

`0021_recruitment_weekly_links`는 새 `recruitment_weekly_occupancies`와 복합 FK용 unique alias만 추가한다. 기존 0019/0020을 수정하지 않는다. 기존 모든 행·시각 hash 보존을 검증하며 **옛 주간 점유에 assignment 연결을 추정 backfill하지 않는다**. 기존 WeeklyState 열·기존 GET/PUT 응답은 그대로다.

새 원장 연결은 `(user,character,raid,cycle)` PK와 assignment 고유키를 가지며 다음을 DB 복합 FK로 확인한다: 실제 WeeklyState 키, assignment의 room/item/round/user/character, item의 raid, round의 cycle. 같은 캐릭터/레이드/주차의 새 연결은 단일 행이다. record timestamps trigger와 새 원천의 DELETE 권한까지 준비 검사에 포함한다. 준비 검사는 구 0018/0019/0020 지원을 유지하면서 해당 revision에 실제 존재하는 제약만 요구한다.

`release_assignment`는 이미 끝난 assignment 재처리는 noop이다. 활성 assignment는 **해당 연결 ID·원장 room/difficulty/joined_at**가 확인될 때만 점유를 해제한다. 연결 없는 legacy 활성행/다른 세대는 거절하고, 불일치 자료를 지우거나 다른 방의 새 점유를 해제하지 않는다. 전체 탈퇴/종료 transaction의 내부 primitive이며 item 단독 탈퇴 API가 아니다. persistent membership은 이 함수에서 끝내지 않는다. 실제 완료/이전/묶음 탈퇴·예약 정리/관련 revision 갱신은 R4 명령의 책임이다.

## 검증 및 실제 상태

전용 tmpfs PostgreSQL17/제한 LOGIN·합성 사용자·모의 인증을 사용했다. 이행 전 모든 기존 표/행·시각 보존과 읽기 전용 readiness, 레거시 이중 집계/종료 후 되살림 방지, 미정 묶음의 전체 assignment/원장·세션/예약 미생성, 부분 target 거절·실패 rollback·CAS, 정확한 해제/다른 방 새 점유 보존, 동시 주간 점유 단일 성공, 정밀 전투력/최근 낮은 성공·NULL head·타 역할 분리, 소유·활동/구성/그룹·한도, 단독8/혼합4 경계, 유효한 다음주 원장 키가 있어도 틀린 round 귀속 거절과 legacy 미증명 해제 거절을 검증한다. 실제 실행 수치·Git/Issue 링크는 DEV_LOG/NEXT_WORK에 기록한다.

원본 `openapi/openapi.yaml`/main 및 R2-A 미활성 draft HTTP는 변경하지 않았다. 현재 작업은 내부 서비스/추가 원천이므로 미완료 HTTP를 공개 계약에 추가하지 않는다. 개발DB0016/API8000/이미지·자료에 0021을 적용하거나 서버를 재시작하지 않았다. 실 provider/Flutter/기기 시험 및 원격 테스트 인계는 미실행이며 같은 제품 설계 회신 대기가 아니다.
