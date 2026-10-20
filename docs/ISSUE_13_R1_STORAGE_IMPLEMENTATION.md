# #13 R1-A 통합 원천·보존 이행 구현

2026-10-20 / feat/raid-recruitment / 기준 ef17b5a. 구현 fdf2f58 로컬 커밋·미push.

공식 결과: [#13 전체52번째 Backend / R1-A 구현](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284008917). 다음 Backend 후속 구현이며 Flutter 시험 요청은 없다.

[Flutter 전체51번째 소비 대조 완료](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283811575) 이후 첫 구현 구간이다. **R1-A 저장 기반만 완료했으며 R1 전체/통합 모집/API·Flutter 적용 완료가 아니다.** 원본 OpenAPI와 실행 서버는 기존 API 그대로다. 이번에 서비스 경로/동작을 바꾸지 않아 새 API를 명세에 선공개하지 않았다.

## 구현

- app/raid_rooms/integrated_models.py: recruitment_rooms/items/rounds/memberships/assignments/sessions/segments의7개 모델. 지속 membership에는 round/캐릭터/주차를 고정하지 않고 주차 assignment에 소유·역할·슬롯·표시/빌드 snapshot을 보존한다. 공유 session은 item별 segment로 연결한다.
- alembic/versions/0019_integrated_recruitment.py: 0018 다음의 추가 이행. 변경되는 앱 모델을 실행 시 import하지 않는 고정 DDL이다. 기존 0017/0018을 수정하거나 기존 표를 삭제/치환하지 않았다.
- room/round/membership ID·원래 시각과 기록 시각을 유지한다. item ID만 room+raid에서 결정적으로 생성하며, assignment는 원래 membership ID를 별도 자원 식별자로 사용한다. 타입/소유 관계를 포함해 비교하며 bare UUID만 같다고 자원을 혼동하지 않는다.
- 원래 종료 사유를 증명할 자료가 없는 종료 관계는 legacy_ended로 보존하고 완료/탈퇴로 임의 분류하지 않는다. 기존 application/원장·ACK·인증·그룹/회원 원본은 그대로 보존한다.
- 가져온 방/일정은 legacy_review_required다. 원본 유한 구간은 보존하되 게임 일정 동의나 확정 예약의 증거로 승격하지 않는다. 기간이10..1440/5분에 맞지 않으면 duration=null/legacy_review_required로 남기고0분/가짜 기본기간으로 메우지 않는다. 예약은 만들지 않는다.
- 복합 FK로 다른 방/item/round/session·다른 회원의 assignment 연결을 막는다. 현재 회원 중복/활성 round 슬롯 중복, 역할·좌석 범위, 양끝 시각, 확정 session24시간 한계와 segment 기간 정합성을 검사한다. 회원 시간 중복 배타 제약은 추가하지 않았다.
- readiness.require_ready(integrated=True)는 새7개와 기존 표의 타입/null/PK/FK/unique/check/index·기록 trigger/앱 권한을 읽기 전용으로 검사한다. 기본 legacy 검사도 명시 검토한 추가 revision0019와0018만 허용하며 unknown head는 거절한다. 구조 검사 성공이 통합 서비스 활성화/데이터 검토 완료를 뜻하지 않는다.

## 실제 검증

전용 tmpfs PostgreSQL17에서 테스트를 실행했다. 제한 LOGIN 계정(NOSUPERUSER/NOCREATEDB/NOCREATEROLE)이 기존0018→0019 이행을 직접 수행했고, 이행 전 모든 기존 표의 전체 행·시각 hash가 이행 뒤와 동일함을 확인했다. 원본 행/키/개인정보는 출력하지 않았다.

실행: tests/test_integrated_recruitment_storage.py + tests/test_raid_room_migrations.py + tests/test_raid_room_preparation.py, **33 PASS / 28.78초**. 새8건은 원천/시각/표시·빌드 보존, 유효/미확인 기간, 교차 방·소유/슬롯/기간 위반 rollback, 그룹 연결 공개방·겹치는 별개 session 표현을 검증한다. readiness는 실제 SET TRANSACTION READ ONLY에서 통과했다. 나머지는 기존 이행/준비·정지/ACK/권한 및 API/OpenAPI 미변경 회귀다. 외부 인증/게임 제공자는 모의 값이며 실행 서버/Flutter·기기 인수는 아니다.

초기 실행의 DDL 나머지 연산자 이스케이프를 수정했고 테스트 fixture 의존성/활동 캐릭터·사용량 CAS 순서/타입 비교를 바로잡았다. 실패한 setup 잔여 자료는 이 검증 전용 tmpfs 환경에서만 분리했다. 최종33건 재실행 결과가 위 수치다. 관련 라이브러리의 기존 DeprecationWarning1건은 남아 있다.

개발 DB0016/실행 API8000/이미지·자료는 이행·재시작하지 않았다. 0019를 실제 개발 DB에 적용했다는 뜻이 아니다. downgrade는 보존을 위해 차단하고 추가 수정 이행으로 처리한다. 별도 활동 브랜치의 migration은0016까지여서 현재 새 head 충돌은 없다.

## 다음 구현과 제한

1. R1-B: 합의된 설정/일정그룹·참여/예약/제안/choice/이벤트와 P1 최근 성공 보존 등 나머지 원천을 추가한다. 이번7개 표만으로 전체 계약 저장을 끝낸 것으로 표시하지 않는다.
2. R2: 개인표/방 제출표·지속 관계/캐릭터 선택·원장 귀속을 새 원천에 연결한다. 기존 후보 서비스는 아직 legacy 표만 쓰며 새 원천으로 전환/이중 쓰기하지 않는다. 활성화 전에 legacy 쓰기 정지/검토·원천 전환을 원자적으로 묶고, old+new를 단순 합산해 사용량을 이중 집계하지 않는다.
3. R3/R4: 예약 생성/투표·확인/다음주와 부분 완료/전체 종료·정확한 원장 귀속/암호화 context/읽기 필터·원자성을 구현한다. confirmed session의 segment 전체 합계/순서와 현재 자격·혼합 구성 등 여러 행에 걸친 도메인 검사는 해당 쓰기 transaction에서 추가 검증해야 한다.
4. HTTP 구현 구간의 required/null·검색의 기존 raid/difficulty/정렬/자리 조건·권한/에러/ACK와 측정한 상한을 원본 OpenAPI에 함께 고정한다. R5 실제 준비 검증→구현 구간 commit/push/원격 확인→필요한 Flutter 동작 인계를 따른다.

이번 구간은 내부 저장 기반이므로 Flutter 테스트/새 설계 재검토를 요청하지 않는다. 원격 게시·실행 API 준비 여부는 실제 인계 단계에서 따로 확인한다.
