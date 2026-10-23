> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-records](../../../../features/raids/weekly-records/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 캐릭터 주간 상태·개인 완료 원장 (#11)

기준일 2026-10-17. [Issue #11](https://github.com/heo0328/lostparty-backend/issues/11), [첫 번째 Backend 계약](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230283275). 작업 브랜치 `feat/raid-services`에서 #10 카탈로그/주차에 이어 구현했다. 아래는 명세/Backend 구현 기준이며 Flutter 적용·실기기 완료와 구분한다.

### 이번 API

1. `GET /v1/me/raid-weekly-states?character_id=<UUID>&character_id=<UUID>[&cycle_key=YYYY-MM-DD]`
- 서버 세션 actor만 사용. character_id는1~50개 서로 다른 canonical UUID, 그 외 query/GET본문·중복cycle_key 거부400. 최대50캐릭터×카탈로그 레이드의 유한 전체 응답이므로 cursor 없음. 배치 중 타회원/알 수 없는 캐릭터가 있으면 전체404 CHARACTER_NOT_FOUND, 소유상실403 OWNERSHIP_REQUIRED. 회원의 현재 연결/소유·이름claim을 검사하며 private 타회원 참가를 섞지 않습니다.
- cycle_key 생략은 서버 현재 주차. 명시 시 유효한 KST 수요일 시작일이고 현재보다 미래가 아닌 주차만 허용합니다. 과거 조회는 저장 원장을 읽고 보존하며 현재 소유로 접근 가능한 캐릭터 범위입니다. 퇴역/소유상실 이력 전체를 새 공개 API로 확대하지 않습니다.
- 응답 필수 `current_cycle`(#10 RaidCycle), `cycle_key`(조회 주차), `catalog_version`, `entries` 배열. 항목은 character_id/raid_id/cycle_key/revision(미저장1)/ownership_revision/lifecycle_revision/state(`incomplete|participating|completed`), `completion_sources` 배열, `participation`(없으면null), `can_mark_completed`, `can_clear_manual_completion`, `mark_blocked_reason`(가능하면null).
- 완료 근거 항목은 source(`manual|party`), completed_at(UTC), difficulty_id(필수nullable), party_id(필수nullable, manual은null). 두 근거가 있으면둘다반환하며 수동정정은manual만 제거합니다. participation은 party_id/difficulty_id/joined_at UTC이며 본인 참조만 제공합니다. 파티snapshot/참가자 목록은 응답하지 않습니다.
- 차단 사유는 CURRENT_CYCLE_REQUIRED/RAID_INACTIVE/CHARACTER_UNUSABLE/PARTICIPATION_CONFIRMATION_REQUIRED 중 해당하는 값. 활동/표시 수/주간 표시 선택은 원장과 별도입니다.

2. `PUT /v1/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion`
- 인증·UUIDv4 Idempotency-Key 필수. 본문은 엄격 DTO, 필수 `completed`(bool), `difficulty_id`(문자열 또는null), `expected_cycle_key`, `expected_catalog_version`, `expected_revision`, `expected_ownership_revision`, `expected_lifecycle_revision`(revision은정수>=1). false는difficulty_id=null 필수. true는난이도미상null허용·명시한난이도는raid범위검사합니다.
- 성공200은 위 entry. 현재 주차만 쓰며 서버DB시각으로 최종commit전 다시 확인합니다. 주차가 바뀌면409 CYCLE_CHANGED, 버전은409 CATALOG_VERSION_CONFLICT/REVISION_CONFLICT. 초기미저장incomplete revision1에서true→revision2, 동일값은no-op·revision불변, false는manual근거만제거합니다. 레이드/난이도잘못된조합404 RAID_NOT_FOUND/DIFFICULTY_NOT_FOUND, 비활성true409 RAID_INACTIVE.
- 새완료기록은현재소유·active/confirmed·정상claim이필요합니다. 활동선택/대표/visible/count나새1700입장필터는개인의이미한완료기록조건으로추가하지않습니다. 파티입장자격은후속명령에서별도검사합니다. suspect의본인수동정정은허용하되소유/claim·예상revision은검사합니다.
- 활성참가가있는true명령은409 PARTICIPATION_CONFIRMATION_REQUIRED, 탈퇴·슬롯·책임자·점유를변경하지않습니다. false는현재참가를보존합니다. 이번에는영향확인토큰/확인실행API가없고 UI에서명령을자동확인/자동탈퇴로대체하면안됩니다.

본문 예시:
```json
{"completed":true,"difficulty_id":"normal","expected_cycle_key":"2026-10-14","expected_catalog_version":"2026.08.20","expected_revision":1,"expected_ownership_revision":1,"expected_lifecycle_revision":1}
```
미저장/무점유 entry 예시:
```json
{"character_id":"00000000-0000-4000-8000-000000000001","raid_id":"serca","cycle_key":"2026-10-14","revision":1,"ownership_revision":1,"lifecycle_revision":1,"state":"incomplete","completion_sources":[],"participation":null,"can_mark_completed":true,"can_clear_manual_completion":false,"mark_blocked_reason":null}
```

### 원장/동시성·멱등/파티 연결

- 신규0011은주간테이블만추가하며기존자료복사/이름기반이관/초기화없음. PK는user_id+canonical character_id+raid_id+cycle_key로difficulty를제외합니다. revision/수동근거와미래파티완료근거/확정점유를분리하고null일관성·완료/점유상호배제제약을둡니다. 아직없는파티테이블에가짜FK를만들지않으며party UUID참조는#13에서실제원본과연결합니다. 이선행단계에파티참조를쓰는공개명령은없습니다.
- 기존authorize(write=True)의게임변경락/회원·세션검사와reserve/commit_result를재사용합니다. CAS·근거변경·revision·멱등결과는동일transaction, 예외는전체rollback. 네트워크/provider호출없음.
- 재전송은같은actor/operation/key+정규화target/body를사용합니다. 다른본문409 IDEMPOTENCY_CONFLICT, 진행중409 REQUEST_IN_PROGRESS/Retry-After2, 보존기간지난키409 IDEMPOTENCY_EXPIRED. 성공replay는현재세션/소유·claim/ownership/lifecycle를재확인하되원주차/원응답ACK를돌려줍니다. 원명령의과거ACK는현재GET상태가아니고주차를넘겨재실행하지않습니다.
- 후속가입확정은같은DB게임변경락/주간키에서완료·점유를검사하고슬롯/참가와함께원자기록해야합니다. 내부가드와경합테스트를준비하지만실제파티가입완료로보고하지않습니다. pending은미점유이며개수무제한목록을원자처리에포함하지않습니다. 수동정정으로과거파티snapshot/가입·신청을부활시키지않습니다.
- 기존오류envelope/no-store/401 Bearer/403·503를재사용합니다. 400은입력수정,409 revision/주차/카탈로그는재조회후새의사결정,응답유실은새키가아닌원키/본문복구가우선입니다. 타회원ID/이름/클라이언트완료source·party_id를받지않습니다.


### 구현·검증

- `app/raid_weekly`에 엄격 DTO, API, 주간 상태 모델과 서비스를 추가했다. 조회는 REPEATABLE READ의 일관된 회원/캐릭터/원장 상태이며 쓰기는 기존 전역 게임 변경 락과 회원/세션 잠금·예상 revision·멱등 결과를 하나의 transaction으로 처리한다. 외부 네트워크나 개인 키는 사용하지 않는다.
- 관련 자동 검증은 주간51개 + 카탈로그31개 + 모델/migration 일치1개 = **83PASS, 34.57초**, 기존 Starlette/AnyIO 경고1개다. 실제 PostgreSQL은 개발DB와 분리된 tmpfs 테스트 프로젝트를 사용했다.
- 검증 범위: 읽기 기본값/쓰기0, 조회/배치/요청 형식, 회원·현재소유·사용불가·예상 revision, 같은 주간 권리의 난이도 변경/원명령 ACK/no-op/정정, 타회원 거부, 응답결과 저장 실패/주차 경계 rollback, 다음 주차/과거 보존, 수동 정정 중 party근거/점유 보존, 서로 다른 난이도 동시 CAS, 같은 게임 락의 내부 참가 모의명령과 완료 경합, PostgreSQL의 잘못된 원장 제약 거부.
- 참가 경합은 **내부 모의 참가 transaction**이다. 실제 모집/파티/슬롯 구현·최대8인 실제 완료·영향 확인 UI까지 검증한 결과가 아니다. party UUID는 아직 없는 파티 원본에 대한 공개 쓰기 권한이 아니며 #13에서 실제 FK/회차/참가 원장과 연결해야 한다.

### DB 적용·복구 및 후속

`0011_raid_weekly_states`는 신규 원장 테이블만 추가하며 기존 업무 테이블을 변경하거나 자료를 복사하지 않는다. 로컬DB에0010→0011을 적용하고 기존 회원/원정대/등록/캐릭터 개수 보존과 신규 원장0행을 확인했다. 실행OpenAPI 전체 일치, 실제HTTP의 새 경로 비인증401/Bearer/no-store·기존 카탈로그/주차200·API/DBhealth를 확인했다. 회원 완료 실제 쓰기·Flutter 실기기는 아직 검증하지 않았다. 구현/계약 `bce6133fcdcfd70d42691e3a4376c2eeaed69f0b`을feat/raid-services로push·원격확인 후 [두 번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6230329942)로 회신했다. dev/main 미병합이다. 자료를 지우는 downgrade는 거절한다. 이전 API 이미지로 되돌려도 추가 원장/과거 자료를 보존하고, 이후 수정 migration으로 전진한다. 백업·격리 복원·Firebase 자료 이관이나 DB 초기화를 설계/실행하는 작업이 아니다.

Flutter는 서버 자료로 주간 체크를 연결하고 원키/본문 응답 유실 복구와 현재 GET을 구분한다. 표시할 레이드 선택/순서는 완료 원장과 다른 설정이다. 실제 Flutter 연동·기기 확인은 별도다. Backend 다음 독립 구간은 #12 그룹 G1 기초 명세다. #13 참가 확정은 위 내부 가드와 동일 transaction에 주간 점유/슬롯을 연결한다. 점유 중 개인 완료의 영향 확인/명시 실행, 책임자/슬롯 정리, 전체 완료 권한은 후속으로 남긴다.
