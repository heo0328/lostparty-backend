# Issue17 공개 계약과 부분 완료 교체 구현

최신: 사용자 승인 [전체18번째 로컬 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721249386)으로 실제 개발 API·DB0036 지원을 완료했다. [반영/보존·실행 확인](../../../engineering/operations/records/roster-participation-local-rollout.json)을 따른다. 기존114업무표99행/sequence/키 보존·실행 소스/두 계약 일치·healthy, Native 새 연결/기기·운영은 미완료다. 실행별 검증·당시 미반영 경과는 집계/DEV_LOG에 보존하며 현재 상태는 이 문서를 따른다.


2026-11-08 / `feat/character-lifecycle` / 사용자 지시에 따라 구현·검증·로컬 반영 문서를 최신화하고 같은 목적 브랜치에 게시한다. Git 게시 결과·고정 구현 SHA는 [DEV_LOG](../../../project/DEV_LOG.md)의 후행 게시 기록을 따른다. [Native 전체15번째 후보 소비 수용](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6720431541) 뒤 사용자 진행·중단 구간 재개 지시에 따른 Backend 구현이다. 실행 계약은 [기본](../../../../openapi/openapi.yaml)·[two-cycle](../../../../openapi/two-cycle.openapi.yaml), 검토 당시 고정 입력은 [후보](roster-participation-contract-candidate.md)다. **실제 로컬 API·DB0036 반영 완료, 운영 서버·DB는 미변경**이다.

## 구현한 동작

- 정상 소유 원정대 관찰만 누락/재등장·정상 근거를 남긴다. 실패/404/부분 응답을 삭제·개명으로 해석하지 않는다. `character_roster_transitions`와 원인 확인된 방 복구 근거는 불변 원장이다. 같은 ID 복구만 연결하며 새 이름/ID 자동 연결·설정 승계·퇴역/claim해제·자료 삭제는 없다.
- `GET /v2/me/raid-room-character-issues`는 페이지와 무관한 본인 실제 C/N 미완료 참가를 집계한다. memberships의 `include_character_issues=true`는 페이지의 본인 경고, detail/plan은 독립 권한을 확인한 두 주차 전체 참가자 요약·선택 주차 경고를 반환한다. 권한 없음은 필수 null이고 정상0과 구분한다. 갱신 registration_id는 본인 항목에만 제공한다.
- bootstrap/characters 모두 `include_roster_presence=true`로 같은 항목·scope DTO를 사용한다. 현재 캐릭터 ID에 대한 최신 관찰 근거를 배치 조회하며 같은 등록/소유/원정대/생명주기·관찰 근거는 같은 presence_revision이다. observed_at은 저장된 해당 상태의 증거 시각이며 GET 시각이나 provider 실시간 확인 시각이 아니다. 원본 캐릭터 행·설정·활동/이력/참가는 삭제하지 않는다.
- 현재 active 전체 M과 완료/종료 이력 P를 정확한 실제T/세대/회원/assignment 연결로 분리한다. 현재 캐릭터·공대장/후계 후보·그룹 참가 표시와 worker/일정의 자격 판단은 active를 우선하며 완료 카드/이력은 원본을 보존한다.
- `participation_profile=remaining-active-1`의 교체 후보 actor.assignments, preview.targets, 기존 POST assignments/target_items는 M 전체다. P는 최상위 participation_context에 별도로 제공한다. body/journal 필드를 재작성하지 않는다. 같은 M/P ID/revision·참가 관계·원본/정책/일정 근거와 새 선택 자격을 서명/CAS에 묶는다. 후보와 preview의 actor binding은 대상 후보 선택과 무관하다.
- 부분 완료 뒤 M만 한 transaction으로 교체하고 P·완료/역할/자리/일정 snapshot을 바꾸지 않는다. 기존 소유/claim/활동·역할·레벨·전투력·주간 점유·편성·기한/동의 검사를 유지한다. 남은 항목이 하나여도 원래 묶음 정원 정책을 유지한다. 경합/오류는 자동 일부 성공 없이 전부 rollback한다.
- 부분 완료 교체 성공 때 `roster_participation_capabilities`에 방·실제 주차·세대를 불변으로 기록한다. 경고 해제/재교체/active0에도 live 해당 세대의 구버전 제한은 유지하며 반대 주차/다른 방·새 세대로 승계하지 않는다. 원 ACK는 새 실행 검사보다 먼저 원래 shape로 재생한다. 종료 기록 reader도 기존 계약으로 보존한다.
- 구버전 live detail/plan·새 실행은 영향 범위에만 CLIENT_UPGRADE_REQUIRED. 본인 목록은 전체 실패 대신 해당 항목만 기존 복구/권한 표현으로 제한한다. 새 표식은 인증/권한이 아니며 원정대/주간·다른 방을 일괄 제한하지 않는다.

## 검토 후보와 실제 계약의 차이

제품 정책/화면 흐름 변경은 없다. 새 metadata의 필드·필수/nullable은 수용한 후보와 같다. 실제 route operationId·설명·기존 response component를 기준으로 두 OpenAPI를 생성/전체 비교한다.

- 후보 생성기가 잘못 확장한 V1 detail/memberships/admission-context/plan의 opt-in 변형10개는 실행 계약에 싣지 않는다. 협의한 확장 대상은 V2이며 V1 기존 DTO·호환 어댑터는 보존한다.
- apply/join 후보·preview에는 기존 참가 actor가 없으므로 participation_context를 새로 합성하지 않는다. 참가 교체에만 기존 actor metadata를 제공한다. 이때도 기본 본문은 기존 계약 그대로다. 실제 OpenAPI의 기존/확장 union을 따른다.
- 기존 ACK·기록은 새 metadata를 덧붙여 다른 shape로 바꾸지 않는다. 과거 세대 기록에 현재 세대 참가 metadata를 합성하지 않는다. 기록 요청의 경고 opt-in은 현재 조치 권한을 뜻하지 않는다.
- 새 query는 생략 시 기존 shape다. 명령의 표식은 opaque token에 함께 서명하고 재검증하며, ACK replay는 표식 검사 전에 처리한다. 커서는 회원/세션·실제T·기존 필터/reader와 새 옵션·본인 경고 관찰 epoch를 묶는다.

고정 후보 파일은 과거 검토 입력으로 보존한다. 생성기는 현재 실행 OpenAPI가 그 당시 baseline과 다르면 중단하며, 이미 수용한 파일을 현재 구현으로 덮어쓰지 않는다. 최신 구현 기준은 위 실행 OpenAPI와 실제 시험이다.

## 검증과 남은 단계

실행별 결과·실패/수정·자동검증과 미실행 구분은 [검증 집계](roster-participation-verification.json)에 기록한다. 격리 PostgreSQL·합성 회원/관찰·TestClient HTTP는 실제 dev 서버나 실회원/provider/기기 인수가 아니다. Native 기존 본문 파서 수용(당시5PASS+수정2PASS)도 새 metadata DTO 전범위·실서버 연결 수용이 아니다.

로컬 schema0035→0036 반영 전 대상·복구/백업 범위를 확인했고, 새 원장3개 추가·기존 업무자료/키 보존과 새 API 지원을 검증했다. 로컬 DB dump 제외 결정과 기존 보관 키/환경 재사용은 유지했다. 다음 운영 반영은 별도 승인·대상/복구/백업 확인이 필요하다. [백업 기준](../../../engineering/operations/backup-and-recovery.md)을 따른다.

Native 연결 기준은 실제 공개 계약/지원 조합·서버 지원 상태다. dev 서버는 신계약을 지원하며 원격 구현 SHA는 이번 사용자 승인 게시 결과를 따른다. 새 화면/Penpot·기기 재개/시험은 요청하지 않는다. 이번 commit/push는 사용자 지시 범위이며 merge·운영 배포·자료 복구·Issue 종료는 별도다. Penpot·Native 화면 구현/기기 보류도 유지한다.


공식 인계는 [#17 전체16번째 Backend 구현·검증](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721042421)이다. 최종 공개7PASS·주차 권한 보강1PASS(기존 시험 확장)·두 OpenAPI 전체 객체 일치 PASS이며, 앞선 관련 회귀와 실패 수정은 실행별 집계에 그대로 보존한다. 전체18번째로 실제 로컬 지원을 인계했고, 게시도 후속 사용자 지시 범위에 포함됐다. Native 신규 연결/기기 인수와 운영은 별도다.
