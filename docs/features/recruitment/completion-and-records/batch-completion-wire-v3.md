# Issue47 계약 v3 — 전체 효과 표시·누적 이력 집계

2026-11-10 / **Native 소비 수용·공개 API 로컬 구현/격리 검증 완료, 미게시·실제 서버 미반영**. Native4의 사용자 채택 보완과 사용자의 레이드별 집계·해시 선택을 반영했다. [v2](batch-completion-wire-v2.md)의 권한·탈퇴·state/leadership/revision·profile·원요청 복구를 유지하고 아래 필드만 변경한다. [전체 Schema](examples/batch-completion-v3.schema.json)·[v2 대비 정의 교체](examples/batch-completion-v3.delta.json)·[전체 응답12개](examples/batch-completion-v3.examples.json)를 제공한다. v1/v2 자료는 당시 제안으로 보존한다.

[전체5번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6761002885)으로 변경 정의·전체 예시를 전달했다. 내부 도우미/격리4PASS는 [검증 기록](batch-completion-preparation-verification.json)을 따르며 당시 공개 wire의 Native 소비 확인은 미완료였으며 아래 Native6으로 해소했다.

[전체6번째 Native 수용](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6761376813)으로 소비 필드 확인 대기를 해소했다. 다음 Backend는 아래 계약의 공개 DTO/API·원자 명령과 관련 검증을 구현한다. 아래의 소비 확인 대기 문장은 제안 당시 절차이며 현재 상태는 이 수용 기록과 NEXT_WORK를 따른다.

[공개 구현·검증 결과](batch-completion-implementation.md)와 [전체7번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6762507528)을 최신 상태로 따른다. 아래 구현/검토 절차와 제안 JSON의 상태값은 작성 당시 설명이며 실제 실행 계약 원본은 openapi/two-cycle.openapi.yaml이다.

## 소비 필드 변경

- 네 endpoint·명령 본문·선택 round_ids1~5개는 유지한다. contract_profile 실제 값은 beta-recruitment-1이다.
- display.rounds는 선택 목록이 아니라 **완료/취소/활성 보존 대상의 전체 current round**다. display.assignments의 round_id 집합과 정확히 같으며, round_ids는 그중 complete 효과의 선택 집합이다. 선택 여부를 display.rounds 포함 여부로 판단하지 않는다.
- display.assignments는 활성 효과만 포함한다. effect는 complete/cancel/preserve_active이며 preserve_completed 행은 나열하지 않는다. 공대 최대40개, 개인 최대5개는 이 활성 목록에만 적용한다. 각 활성 효과의 레이드 이름·난이도·캐릭터/참가 관계는 같은 context에서 확인할 수 있다.
- impact.preserved_completed_assignment_ids를 제거하고 **impact.preserved_completed**를 추가한다. 필수/추가 필드 금지 객체이며 assignment_count:정수>=0, digest:소문자 SHA256, raids:HistoryRaid 배열이다.
- HistoryRaid는 필수 raid_id:string, raid_name:string, assignment_count:정수>=1, digest:소문자 SHA256만 갖는다. raid_id 오름차순·중복 없음이며 건수 합계는 전체 assignment_count와 같다. 빈 이력은 count0/raids=[]/SHA256(JSON [])다.
- 완료/취소/활성 보존 assignment ID 배열은 정확한 정렬 집합으로 유지한다. 이들의 서로소·display 효과 대조는 v2와 같다. 완료 ID와 보존 이력의 개별 ID를 대조하려고 과거 ID를 내려받을 필요는 없다.
- 과거 완료 레이드 이름은 preserved_completed.raids에서 제공한다. 과거 round/다른 캐릭터 기록도 같은 context의 레이드별 집계에 포함된다. 역사 행·raid 그룹에는 활성 최대5/40을 적용하지 않는다. 기존 응답1MiB 보안 제한은 유지하되 응답이 개별 이력 행 수에 비례하지 않게 한다.
- 레이드 이름은 보유 카탈로그에서 해석하며 과거 ID가 현 카탈로그에 없으면 raid_id 자체를 표시값으로 반환한다. 과거 캐릭터/provider의 현재 자격이나 이름을 조회하지 않는다.

## 원본 범위와 해시 규칙

완료 이력은 CycleAssignment의 **room_id/room_cycle_id/target_generation**과 round.cycle_key=실제T, assignment.state=completed로 정한다. current round 여부·cycle member 종료 여부·현재 캐릭터 소유자로 필터링하지 않는다. 공대는 이 범위 전체, 개인은 CycleAssignment.user_id=인증 회원으로 제한해 재가입 전 본인 기록까지 포함한다. 다른 세대/방/T·다른 회원 자료를 개인 집계에 섞지 않는다.

각 증거 record의 정확한 키는 다음과 같다.

- assignment: RecruitmentAssignment의 모든 persisted 열(UTC 시각/UUID는 프로젝트 lifecycle.digest의 default=str 규칙으로 문자열화).
- binding: CycleAssignment의 모든 persisted 열.
- raid_id: Item.raid_id.
- round: id, item_id, cycle_key, difficulty_id, catalog_version. 변경 가능한 current 표식·round 상태/revision은 넣지 않는다.

record를 assignment.id UUID 오름차순으로 정렬한다. 전체 digest는 **lifecycle.digest(list(records))**와 바이트 동일한 SHA256, 즉 json.dumps(records, sort_keys=True, default=str)의 UTF-8 해시다. 이는 display_revision의 공백 없는 JSON 해시와 별개 규칙이다. 레이드별 digest는 같은 순서의 해당 raid record 부분집합에 동일 규칙을 적용한다. 이름은 증거에 넣지 않는다. 서버는 `[`·각 record JSON·`, `·`]`를 순차 해시해 전체 이력을 메모리에 적재하지 않는다. DB result는 배치로 소비하고 닫는다.

토큰은 실제 scope/selection/active effect/profile·revision 및 이 증거를 묶는다. 실행 전 동일 scope로 다시 집계해 stale을 검사하고, 실행 후 이번 newly completed ID만 제외한 증거가 원 context와 같은지 확인한다. 새 완료는 completed_assignment_ids로만 표시한다. ACK의 preserved_completed는 **실행 전부터 있던 기록**의 proof이므로 원 context와 완전히 동일하다. 새 완료를 포함한 현재 전체 완료 건수와 혼동하지 않는다. 원ACK는 이 proof를 포함해 그대로 재생한다.

## 내부 구현과 검증 단계

활성 snapshot은 현재 세대의 실제 active assignment만 별도로 읽고 활성 중복/슬롯/현재 round/동일 member의 현재 캐릭터를 검증한다. 점유/예약·권한·캐릭터 자격의 나머지 검사는 이후 명령 트랜잭션에서 수행한다. 과거 완료를 같은 item의 활성 중복으로 취급하지 않는다. 이력 집계 도우미는 DB 읽기만 하며 자체 인증·commit·token·route가 없다. 호출자가 인증·snapshot/직렬화 트랜잭션을 소유한다.

다음 Native는 필드 교체·전체 레이드 표시·이력 proof를 기존 단일 저장/context/ACK 대조에 연결 가능한지 확인한다. 최종 공개 DTO/API는 그 확인 후 확정한다. 그동안 Backend는 내부 snapshot/집계와 격리 시험을 진행한다. 실행 API/두 전체 OpenAPI에는 미확정 v3를 추가하지 않는다. DB migration·원본/키/환경 변경은 계획하지 않는다.

검증은 Schema/전체 예시와 별도로 실제 격리 PostgreSQL에서 >40 공대/>5 개인 완료 이력, 다른 캐릭터·재가입·과거 round, 범위/개인정보 분리, 신규 완료 제외 proof, 원본 불변과 digest 일치를 확인한다. 이후 공개 명령 구현 때 전체 선택 완료/취소·승계/마지막 종료·경합/rollback·HTTP/원ACK 회귀를 수행한다. 내부 도우미 검증을 전체 기능 완료로 표시하지 않는다.
