# 남은 파일의 2차 정리 계획

2026-11-09 작성. **계획 문서화 완료·2차 구현 미착수**다. 이번 승인은 문서 작성만 포함하며 아래 경로는 앞으로 만들 목표 경로다. 실제 앱·테스트 파일은 이동하거나 수정하지 않았다.

## 현재 상태와 범위

같은 `feat/character-lifecycle` 브랜치에서 1차 정리의 미커밋 변경을 보존한다. 1차는 업무95개·시험103개를 이동했지만 공개 DTO·라우터·OpenAPI·ORM 정의는 원래 경로에 남겼다. 따라서 남은 파일이 곧 누락 작업을 의미하지는 않는다. 이번에는 사용자가 선택한 **정의 파일까지 분류**를 2차 목표로 문서화한다.

대상은 기능 루트의 Python79개(레이드룸65개·게임 계정14개, 각 `__init__.py` 포함)다. 62개는 이동, 15개는 역할별 분리하고 기능 루트의 `__init__.py`2개를 유지한다. 연결된 `roster_metadata.schema.json`1개도 별도 자원 행으로 포함한다. 이 숫자는 새 파일 개수가 아니라 현재 파일 개수다.

1차 [분류 기준](source-layout.md)·[198파일 이동표](folder-layout-map.json)·[검증 결과](folder-layout-verification.json)는 당시 원본으로 보존한다. 본 계획은 그 완료 범위를 소급 변경하지 않으며, 향후 2차 구현에서 정의 경로 유지 제한을 해제할 범위를 정한다. 내부 정리로 API/사용자 정책을 변경하거나 Native에 반복 인수를 요청하지 않는다.

## 목표 구조와 책임

두 기능 안에 `api/`(HTTP·라우트 클래스), `schemas/`(공개 입출력·검증·타입 생성), `models/`(ORM), `contracts/`(OpenAPI 조립·스키마 자원)를 둔다. 기존 업무 폴더는 유지한다. 게임 계정의 여러 업무에서 공유하는 `support.py`만 `common/support.py`로 옮기며, 작은 단일 업무를 위한 추가 계층은 만들지 않는다.

```text
app/raid_rooms/
  __init__.py
  api/  schemas/  models/  contracts/
  admissions/  participation/  schedules/  outcomes/
  group_links/  reads/  compat/  common/
app/game_accounts/
  __init__.py
  api/  schemas/  models/  contracts/  common/
  rosters/  verification/  character_profiles/  power/  provider_io/
```

게임 계정의 `contracts/`는 계약 조립 코드가 실제로 필요할 때만 만든다. 현재 대응표에는 이곳으로 이동할 파일이 없다. 빈 폴더를 미리 추가하지 않는다. 새 패키지 `__init__.py`는 빈 파일을 기본으로 하고 일괄 import/재노출은 피한다. 현재 파일명·클래스·함수 이름은 유지하므로 `schemas/schemas.py`, `models/models.py`, `api/router.py`도 허용한다. 이름 개선·파일 통합은 이번 정리와 분리한다.

DTO의 validator·타입 별칭·동적 모델 생성 함수는 해당 DTO와 함께 둔다. 라우트 클래스와 HTTP 전용 JSON/query 검사는 `api`에 남긴다. 업무 함수는 기존 기능 폴더로 옮기며 트랜잭션 경계·예외·반환값·멱등 처리·읽기 중 쓰기 금지 기준을 바꾸지 않는다. DB 모델은 하나의 정식 모듈에서만 정의한다. 예전 경로용 shim·`sys.modules` 별칭·`__module__` 덮어쓰기나 루트의 일괄 재수출은 사용하지 않는다.

## 파일별 대응표

각 표의 현재·목표 경로는 제목의 기능 경로를 기준으로 한다. 주요 참조는 현재 앱·시험·도구·Alembic·현재 문서에서 확인한 대표 소비 파일 최대3개와 추가 파일 수다. 보관 문서·실행 시 구성되는 경로·상대 import는 이 목록의 완전성 보장 대상이 아니므로 구현 직전에 아래 참조 점검 절차를 다시 수행한다.

검증 코드: **R** import·문자열 참조·패키지/앱 로딩, **D** 두 전체 OpenAPI 및 직렬화/검증 계약, **O** 라우트 등록·순서·operationId·의존성, **M** 모델 등록·테이블/FK/index/DDL 동일, **B** 관련 업무 회귀, **S** 공유 상태·잠금·트랜잭션·rollback·동시성, **C** 계약 보정 순서·자원 로딩. 분리 행의 모든 대상은 묶음으로 적용하고 각 정의/함수는 정확히 한 곳에서 유지한다.

### `app/raid_rooms/`

| 현재 파일 | 방식 | 목표 경로와 분리 내용 | 주요 참조 | 검증 |
|---|---|---|---|---|
| `__init__.py` | 유지 | `__init__.py` — 기능 패키지 진입점 | `docs/engineering/development/folder-layout-map.json` | R |
| `admission_candidate_schemas.py` | 이동 | `schemas/admission_candidate_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admissions/admission_candidates.py`, `app/raid_rooms/cycle_router.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `admission_contract.py` | 이동 | `contracts/admission_contract.py` — OpenAPI 생성·보정 | `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/admissions/test_recruitment_admission.py` | R·D·C |
| `admission_router.py` | 이동 | `api/admission_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `app/raid_rooms/admission_contract.py`, `app/raid_rooms/completion_router.py` 외 12개 파일 | R·D·O·B |
| `admission_schemas.py` | 이동 | `schemas/admission_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admission_candidate_schemas.py`, `app/raid_rooms/admission_router.py`, `app/raid_rooms/admissions/admission_service.py` 외 12개 파일 | R·D |
| `application_display_schemas.py` | 이동 | `schemas/application_display_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admissions/application_display.py`, `app/raid_rooms/cycle_router.py`, `app/raid_rooms/group_link_display.py` 외 3개 파일 | R·D |
| `application_presets.py` | 분리 | `api/application_presets.py` — PresetRoute·라우터·read_presets/write_presets<br>`schemas/application_presets.py` — PresetItem/PresetPut/StoredPresetItem/PresetDocument<br>`admissions/application_presets.py` — document/get/put | `app/main.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/admissions/test_beta_recruitment.py` | R·O·B·D |
| `atomic_member_schemas.py` | 이동 | `schemas/atomic_member_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/participation/atomic_members.py`, `docs/engineering/development/folder-layout-map.json` 외 1개 파일 | R·D |
| `availability_contract.py` | 이동 | `contracts/availability_contract.py` — OpenAPI 생성·보정 | `app/raid_rooms/admission_contract.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/schedules/test_recruitment_availability.py` | R·D·C |
| `availability_router.py` | 이동 | `api/availability_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `app/raid_rooms/admission_router.py`, `app/raid_rooms/application_presets.py` 외 6개 파일 | R·D·O·B |
| `availability_schemas.py` | 이동 | `schemas/availability_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admission_schemas.py`, `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/availability_router.py` 외 12개 파일 | R·D |
| `beta_models.py` | 이동 | `models/beta_models.py` — ORM 정의 전체 | `app/raid_rooms/admissions/beta_search.py`, `app/raid_rooms/admissions/cycle_commands.py`, `app/raid_rooms/application_presets.py` 외 10개 파일 | R·M |
| `beta_schemas.py` | 이동 | `schemas/beta_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admissions/cycle_creation.py`, `app/raid_rooms/application_presets.py`, `app/raid_rooms/common/beta_output.py` 외 9개 파일 | R·D |
| `candidate_schemas.py` | 이동 | `schemas/candidate_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admissions/character_candidates.py`, `app/raid_rooms/cycle_router.py`, `app/raid_rooms/cycle_schemas.py` 외 2개 파일 | R·D |
| `character_change.py` | 분리 | `schemas/character_change.py` — 전체 DTO<br>`participation/character_change.py` — change | `app/raid_rooms/management_router.py`, `docs/engineering/development/folder-layout-map.json` | R·B·D |
| `command_schemas.py` | 이동 | `schemas/command_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/completion_router.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `commands.py` | 이동 | `schemas/commands.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/common/service.py`, `app/raid_rooms/http_schemas.py`, `app/raid_rooms/reads/queries.py` 외 5개 파일 | R·D |
| `completion.py` | 분리 | `schemas/completion.py` — 전체 DTO<br>`outcomes/completion.py` — 전체 업무 함수 | `app/main.py`, `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/common/readiness.py` 외 8개 파일 | R·B·D |
| `completion_correction_models.py` | 이동 | `models/completion_correction_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/outcomes/completion_correction.py`, `docs/engineering/development/folder-layout-map.json` 외 1개 파일 | R·M |
| `completion_correction_schemas.py` | 이동 | `schemas/completion_correction_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/cycle_router.py`, `app/raid_rooms/outcomes/completion_correction.py` 외 2개 파일 | R·D |
| `completion_router.py` | 이동 | `api/completion_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/outcomes/test_recruitment_completion.py` | R·D·O·B |
| `continuation.py` | 분리 | `schemas/continuation.py` — 전체 DTO<br>`admissions/continuation.py` — 조회·선택·다음 주 개설·process_due/process_room | `app/main.py`, `app/raid_rooms/common/worker.py`, `app/raid_rooms/compat/cycle_legacy.py` 외 8개 파일 | R·B·D |
| `continuation_router.py` | 분리 | `api/continuation_router.py` — ContinuationRoute·라우터·HTTP 함수<br>`schemas/continuation_router.py` — ChoiceView/Choices | `app/main.py`, `app/raid_rooms/compat/v1_compat.py`, `docs/engineering/development/folder-layout-map.json` 외 1개 파일 | R·O·B·D |
| `cycle_application_models.py` | 이동 | `models/cycle_application_models.py` — ORM 정의 전체 | `app/raid_rooms/admissions/application_display.py`, `app/raid_rooms/admissions/beta_search.py`, `app/raid_rooms/admissions/cycle_commands.py` 외 31개 파일 | R·M |
| `cycle_consent_models.py` | 이동 | `models/cycle_consent_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/schedules/cycle_times.py`, `alembic/env.py` 외 6개 파일 | R·M |
| `cycle_group_context_schemas.py` | 이동 | `schemas/cycle_group_context_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/participation/cycle_common.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `cycle_group_models.py` | 이동 | `models/cycle_group_models.py` — ORM 정의 전체 | `app/groups/raid_state.py`, `app/raid_rooms/common/readiness.py`, `app/raid_rooms/group_links/cycle_group_policy.py` 외 4개 파일 | R·M |
| `cycle_group_schemas.py` | 이동 | `schemas/cycle_group_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/cycle_router.py`, `app/raid_rooms/cycle_schemas.py` 외 5개 파일 | R·D |
| `cycle_lifecycle_models.py` | 이동 | `models/cycle_lifecycle_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/outcomes/weekly_summary.py`, `app/raid_rooms/participation/cycle_lifecycle.py` 외 8개 파일 | R·M |
| `cycle_models.py` | 이동 | `models/cycle_models.py` — ORM 정의 전체 | `app/groups/raid_state.py`, `app/raid_rooms/admissions/admission_history.py`, `app/raid_rooms/admissions/beta_search.py` 외 66개 파일 | R·M |
| `cycle_outcome_models.py` | 이동 | `models/cycle_outcome_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/outcomes/cycle_outcomes.py`, `app/raid_rooms/outcomes/cycle_resume.py` 외 7개 파일 | R·M |
| `cycle_planning_models.py` | 이동 | `models/cycle_planning_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/outcomes/cycle_outcomes.py`, `app/raid_rooms/outcomes/cycle_resume.py` 외 11개 파일 | R·M |
| `cycle_router.py` | 이동 | `api/cycle_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `app/raid_rooms/application_presets.py`, `docs/engineering/development/folder-layout-map.json` 외 10개 파일 | R·D·O·B |
| `cycle_schemas.py` | 이동 | `schemas/cycle_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/beta_schemas.py`, `app/raid_rooms/compat/v1_compat.py` 외 18개 파일 | R·D |
| `cycle_wire.py` | 이동 | `schemas/cycle_wire.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admission_candidate_schemas.py`, `app/raid_rooms/admissions/application_display.py`, `app/raid_rooms/admissions/cycle_commands.py` 외 47개 파일 | R·D |
| `group_connection.py` | 분리 | `schemas/group_connection.py` — TargetGroup/GroupConnectionContext<br>`group_links/group_connection.py` — snapshot/evaluate | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/group_links/cycle_group_policy.py`, `app/raid_rooms/participation/cycle_common.py` 외 2개 파일 | R·B·D |
| `group_link_display.py` | 분리 | `schemas/group_link_display.py` — 전체 DTO<br>`group_links/group_link_display.py` — get | `app/raid_rooms/cycle_router.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/group_links/test_cycle_group_policy.py` | R·B·D |
| `http_schemas.py` | 이동 | `schemas/http_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/router.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/common/test_raid_room_http.py` | R·D |
| `integrated_models.py` | 이동 | `models/integrated_models.py` — ORM 정의 전체 | `app/groups/raid_state.py`, `app/raid_rooms/admissions/admission_context.py`, `app/raid_rooms/admissions/admission_eligibility.py` 외 87개 파일 | R·M |
| `management.py` | 분리 | `schemas/management.py` — 전체 DTO<br>`participation/management.py` — settings_view/get_settings/command | `app/main.py`, `app/raid_rooms/compat/v1_compat.py`, `app/raid_rooms/management_router.py` 외 5개 파일 | R·B·D |
| `management_router.py` | 분리 | `api/management_router.py` — 라우터·HTTP 함수<br>`schemas/management_router.py` — ContinuationSettings/Settings | `app/main.py`, `app/raid_rooms/compat/v1_compat.py`, `app/raid_rooms/member_schemas.py` 외 2개 파일 | R·O·B·D |
| `member_router.py` | 이동 | `api/member_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json`, `tests/raid_rooms/participation/test_recruitment_member_reads.py` | R·D·O·B |
| `member_schemas.py` | 이동 | `schemas/member_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/compat/v1_compat.py`, `app/raid_rooms/member_router.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `membership_action_models.py` | 이동 | `models/membership_action_models.py` — ORM 정의 전체 | `app/raid_rooms/common/cycle_worker.py`, `app/raid_rooms/common/readiness.py`, `app/raid_rooms/participation/membership_actions.py` 외 5개 파일 | R·M |
| `membership_action_schemas.py` | 이동 | `schemas/membership_action_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/group_link_display.py`, `app/raid_rooms/participation/membership_actions.py` 외 4개 파일 | R·D |
| `models.py` | 이동 | `models/models.py` — ORM 정의 전체 | `app/raid_rooms/common/core.py`, `app/raid_rooms/common/readiness.py`, `app/raid_rooms/common/service.py` 외 18개 파일 | R·M |
| `participation_commands.py` | 이동 | `schemas/participation_commands.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admission_schemas.py`, `app/raid_rooms/admissions/admission_context.py`, `app/raid_rooms/admissions/admission_service.py` 외 9개 파일 | R·D |
| `resume.py` | 분리 | `schemas/resume.py` — ResumeRequest<br>`outcomes/resume.py` — 전체 업무 함수 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/completion_router.py`, `app/raid_rooms/continuation.py` 외 7개 파일 | R·B·D |
| `resume_models.py` | 이동 | `models/resume_models.py` — ORM 정의 전체 | `app/raid_rooms/common/readiness.py`, `app/raid_rooms/continuation.py`, `app/raid_rooms/resume.py` 외 6개 파일 | R·M |
| `resume_review_schemas.py` | 이동 | `schemas/resume_review_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/cycle_schemas.py`, `app/raid_rooms/group_link_display.py` 외 5개 파일 | R·D |
| `roster_api.py` | 이동 | `api/roster_api.py` — HTTP 경계·응답 메타데이터 처리 | `app/raid_rooms/admissions/admission_candidates.py`, `app/raid_rooms/participation/cycle_character.py`, `app/raid_rooms/participation/membership_readers.py` 외 3개 파일 | R·D·O·B |
| `roster_openapi.py` | 이동 | `contracts/roster_openapi.py` — OpenAPI 생성·보정 | `app/main.py`, `docs/engineering/development/folder-layout-map.json`, `docs/features/rosters/lifecycle/roster-participation-verification.json` | R·D·C |
| `roster_participation.py` | 분리 | `models/roster_participation.py` — Capability<br>`participation/roster_participation.py` — PROFILE·단일 _state·전체 업무 함수 | `app/raid_rooms/admissions/admission_candidates.py`, `app/raid_rooms/admissions/admission_eligibility.py`, `app/raid_rooms/admissions/cycle_admission.py` 외 15개 파일 | R·B·M·S |
| `router.py` | 이동 | `api/router.py` — HTTP 경계·응답 메타데이터 처리 | `app/raid_rooms/cycle_router.py`, `app/raid_rooms/member_router.py`, `app/raid_rooms/search_router.py` 외 8개 파일 | R·D·O·B |
| `schedule_heads.py` | 이동 | `models/schedule_heads.py` — ORM 정의 전체 | `app/raid_rooms/admissions/beta_search.py`, `app/raid_rooms/common/readiness.py`, `app/raid_rooms/reads/cycle_card_batch.py` 외 8개 파일 | R·M |
| `schedule_output.py` | 이동 | `schemas/schedule_output.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admission_schemas.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `schedule_router.py` | 분리 | `api/schedule_router.py` — 라우터·HTTP 함수<br>`schemas/schedule_router.py` — Candidate | `app/main.py`, `app/raid_rooms/compat/v1_compat.py`, `docs/engineering/development/folder-layout-map.json` 외 3개 파일 | R·O·B·D |
| `schedule_schemas.py` | 이동 | `schemas/schedule_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/resume.py`, `app/raid_rooms/schedule_router.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `schemas.py` | 이동 | `schemas/schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/reads/queries.py`, `app/raid_rooms/router.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `search_router.py` | 분리 | `api/search_router.py` — SearchRoute·라우터·HTTP 함수<br>`schemas/search_router.py` — 나머지 전체 DTO | `app/main.py`, `app/raid_rooms/compat/v1_compat.py`, `app/raid_rooms/cycle_router.py` 외 5개 파일 | R·O·B·D |
| `session_display_schemas.py` | 이동 | `schemas/session_display_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/admissions/cycle_commands.py`, `app/raid_rooms/admissions/cycle_continuation.py`, `app/raid_rooms/admissions/cycle_opening.py` 외 4개 파일 | R·D |
| `source_models.py` | 이동 | `models/source_models.py` — ORM 정의 전체 | `app/raid_rooms/admissions/admission_context.py`, `app/raid_rooms/admissions/admission_service.py`, `app/raid_rooms/admissions/beta_search.py` 외 62개 파일 | R·M |
| `weekly_links.py` | 이동 | `models/weekly_links.py` — ORM 정의 전체 | `app/raid_rooms/admissions/admission_eligibility.py`, `app/raid_rooms/admissions/cycle_admission.py`, `app/raid_rooms/character_change.py` 외 24개 파일 | R·M |
| `weekly_summary_router.py` | 이동 | `api/weekly_summary_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json` | R·D·O·B |
| `weekly_summary_schemas.py` | 이동 | `schemas/weekly_summary_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/raid_rooms/atomic_member_schemas.py`, `app/raid_rooms/completion_correction_schemas.py`, `app/raid_rooms/membership_action_schemas.py` 외 5개 파일 | R·D |

### `app/game_accounts/`

| 현재 파일 | 방식 | 목표 경로와 분리 내용 | 주요 참조 | 검증 |
|---|---|---|---|---|
| `__init__.py` | 유지 | `__init__.py` — 기능 패키지 진입점 | `docs/engineering/development/folder-layout-map.json` | R |
| `batch_router.py` | 이동 | `api/batch_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json` | R·D·O·B |
| `batch_schemas.py` | 이동 | `schemas/batch_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/game_accounts/batch_router.py`, `docs/engineering/development/folder-layout-map.json`, `tests/game_accounts/test_startup_batches.py` | R·D |
| `bootstrap_router.py` | 이동 | `api/bootstrap_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json` | R·D·O·B |
| `bootstrap_schemas.py` | 이동 | `schemas/bootstrap_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/game_accounts/bootstrap_router.py`, `app/game_accounts/rosters/bootstrap.py`, `docs/engineering/development/folder-layout-map.json` | R·D |
| `lifecycle_router.py` | 이동 | `api/lifecycle_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/main.py`, `docs/engineering/development/folder-layout-map.json` | R·D·O·B |
| `models.py` | 이동 | `models/models.py` — ORM 정의 전체 | `app/game_accounts/character_profiles/presentation.py`, `app/game_accounts/character_profiles/profiles.py`, `app/game_accounts/character_profiles/representative.py` 외 102개 파일 | R·M |
| `power_success.py` | 분리 | `models/power_success.py` — RolePowerSuccess<br>`power/power_success.py` — capture | `app/game_accounts/character_profiles/profiles.py`, `app/groups/display.py`, `app/raid_rooms/admissions/admission_eligibility.py` 외 15개 파일 | R·B·M·S |
| `profile_router.py` | 이동 | `api/profile_router.py` — HTTP 경계·응답 메타데이터 처리 | `app/game_accounts/batch_router.py`, `app/main.py`, `docs/engineering/development/folder-layout-map.json` | R·D·O·B |
| `profile_schemas.py` | 이동 | `schemas/profile_schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/game_accounts/batch_schemas.py`, `app/game_accounts/bootstrap_schemas.py`, `app/game_accounts/profile_router.py` 외 9개 파일 | R·D |
| `roster_presence.py` | 분리 | `models/roster_presence.py` — RosterTransition/RosterRoomRecovery<br>`rosters/roster_presence.py` — 전체 업무 함수 | `app/game_accounts/rosters/presence_reads.py`, `app/game_accounts/rosters/service.py`, `app/raid_rooms/common/cycles.py` 외 9개 파일 | R·B·M·S |
| `router.py` | 이동 | `api/router.py` — HTTP 경계·응답 메타데이터 처리 | `app/game_accounts/batch_router.py`, `app/game_accounts/bootstrap_router.py`, `app/game_accounts/lifecycle_router.py` 외 21개 파일 | R·D·O·B |
| `schemas.py` | 이동 | `schemas/schemas.py` — DTO·타입 별칭·validator·타입 생성 함수 함께 유지 | `app/game_accounts/batch_schemas.py`, `app/game_accounts/bootstrap_router.py`, `app/game_accounts/bootstrap_schemas.py` 외 38개 파일 | R·D |
| `support.py` | 이동 | `common/support.py` — GameError·권한·잠금·멱등 처리·cursor 공통 함수 | `app/game_accounts/batch_router.py`, `app/game_accounts/bootstrap_router.py`, `app/game_accounts/character_profiles/presentation.py` 외 175개 파일 | R·B·S |

### 연결 자원

| 현재 경로 | 방식 | 목표 경로 | 주요 참조 | 검증 |
|---|---|---|---|---|
| `app/raid_rooms/roster_metadata.schema.json` | 이동 | `app/raid_rooms/contracts/roster_metadata.schema.json` | `app/raid_rooms/roster_openapi.py`의 `Path(__file__).with_name(...)` | C·D |

### 분리 시 지킬 경계

- `application_presets.py`: DTO4개, HTTP 라우터/클래스, 업무 함수3개를 표대로 분리한다. 업무 함수는 HTTP 모듈을 import하지 않고 DTO/모델을 직접 참조한다. 공통 Principal/Key는 정식 API 모듈을 참조하되 새 인증 계층을 만들지 않는다.
- `beta_schemas.py`: `request`, `stored_text`, `annotation`, `output_model`, `ADDITIONS`와 캐시를 DTO 생성 책임으로 보고 함께 이동한다. 함수를 전부 업무 코드로 추출하지 않는다. 동적 모델의 이름·검증·cache 동작을 보존한다.
- `cycle_wire.py`: 대형 계약 타입 묶음을 파일 그대로 이동한다. 생성된 클래스명에 옛 모듈명이 들어 있어도 이름을 정리하거나 수동 재작성/임의 분할하지 않는다.
- `roster_participation.py`: Capability만 모델로 추출한다. `PROFILE`, `_state`, `using`, query/marker/metadata 처리와 나머지 함수는 하나의 업무 모듈을 사용한다. `roster_api`와 라우터도 같은 ContextVar를 참조하고 중첩·예외 종료 후 reset을 유지한다.
- `roster_presence.py`: 모델2개와 원정대 관측 함수를 분리한다. `db.info` 캐시는 원래 Session 범위로 유지하며 전역 cache로 바꾸지 않는다. `power_success.py`도 모델과 `capture`만 구분한다.
- `continuation.py`의 `process_due/process_room`는 해당 모듈과 함께 이동한다. 기존 worker 진입점에서 이를 호출하도록 참조만 갱신하고 worker를 중복 구현하지 않는다.
- 두 기능의 `models.py`는 여러 업무의 모델을 담지만 이번에는 파일 단위로 `models/models.py`에 둔다. 업무별 모델 재분할·테이블 통합은 별도 설계다.

## 후속 구현 순서

### 1. 시작 기준과 참조 고정

구현을 별도 승인받으면 당시 checkout·미커밋 변경·현재 실행 소스를 확인한다. HEAD만으로 1차 미커밋 상태를 복원할 수 있다고 가정하지 않는다. 앱·테스트·도구와 계약 자원의 파일 목록/hash, 테스트 수집 node, 두 OpenAPI 전체 객체, 모델 등록/DDL을 구현 전 기준으로 별도 보존한다. 1차 원본 파일을 덮어쓰지 않고 2차 이동표/검증 기록을 만든다.

표의 각 옛 모듈명·파일 경로를 `rg`로 검색한다. 절대/상대 import, `from package import module`, monkeypatch 문자열, subprocess 내 Python, importlib, 파일 깊이에 의존하는 Path, 실행기/배포 도구/문서 검사기, Alembic 등록, Docker COPY와 package data를 포함한다. 현행 참조는 갱신하고 과거 고정 SHA/실행 기록/동결 자원은 당시 원본을 보존한다. 보관 문서는 깨지는 로컬 링크 목적지만 수정한다.

### 2. 공개 계약 보존 가능성 확인

먼저 충돌하는 같은 이름의 DTO와 동적 생성 모델을 포함한 작은 묶음으로 방법을 검증한다. 파일 이동으로 Pydantic/FastAPI가 내보내는 모듈 한정 component key가 바뀔 수 있으므로 단순 re-export나 `title` 지정만으로 동일성을 보장하지 않는다.

새로 생성되는 식별자→기존 공개 식별자의 명시적 대응을 관리하고, 기본 앱과 two-cycle 양쪽에서 **기존 `_decorate_openapi`가 실행되기 전** 동일 보존 절차를 적용하는 방안을 우선 검증한다. component key, 실제 스키마 참조 `$ref`, discriminator mapping 등을 정확히 대응시키고 예시·설명·업무 문자열을 전역 치환하지 않는다. 여러 옛 타입이 같은 키로 합쳐지거나 키가 짧아지는 경우도 양쪽 전체 객체와 비교한다. 중복 목적지·미등록 변경·미해결 내부 참조는 오류로 검출하며 조용히 덮어쓰지 않는다.

보정 이후 공개 OpenAPI 전체 객체가 기존과 같아야 한다. schema 이름뿐 아니라 operationId, description, optional/null, validators, examples와 확장 필드를 포함한다. `app.main:app`, `app.main:create_two_cycle_app` 진입점은 유지한다. 계약 기준본은 경로 변경을 수용하려고 갱신하지 않는다. 기존 public builder 함수의 반환 계약도 확인한다. 동일성이 확보되지 않으면 해당 이동을 중단하고 이유와 대안을 사용자와 협의한다.

### 3. 의존 관계별 묶음 이동

계약 보존 방법이 확인된 뒤 (1) 순수 DTO·계약 조립/JSON 자원, (2) 순수 ORM와 Alembic 등록 import, (3) 혼합 파일의 DTO/ORM 추출과 업무 모듈 이동, (4) 라우터 이동·앱 등록 순으로 진행한다. 각 묶음은 필요한 소비 참조를 동시에 수정하고 import·관련 계약/회귀를 확인한 후 다음 묶음으로 간다. 순환 참조가 생기면 우선 타입 import 방향을 바로잡고 이름 변경이나 새 서비스 계층으로 우회하지 않는다.

같은 basename의 기존 업무 파일과 충돌하지 않는지 실행 직전에 확인한다. `models.py`→`models/`, `schemas.py`→`schemas/` 전환은 패키지/모듈 충돌을 남기지 않게 한 묶음으로 수행한다. ORM 등록은 `alembic/env.py`와 실제 앱/시험 등록 지점을 직접 갱신하되 과거 migration 파일은 수정하지 않는다. 라우터 include 순서·접두사·태그·route_class·dependency와 함수 이름은 유지한다. 계약 자원은 `roster_openapi.py`와 함께 이동하고 파일 로딩 기준을 확인한다.

### 4. 전체 검증과 인계

테스트 경로·fixture는 추가로 재분류하지 않고 바뀐 import/문자열 참조만 수정한다. 실행기·배포 검사·문서 검사기의 재귀 검색과 기존 legacy/two-cycle 시험 묶음 구성을 유지한다. 새 구조의 실제 결과와 잔여 항목을 기록하고 완료 시 분류 지침을 현행화한다. 소스 정리 완료, commit/push, 실제 개발서버 반영, Native 연결/사용자 기기, 운영 반영은 별도 상태로 인계한다.

## 검증과 완료 기준

이번 문서 작업은79개 대상의 누락·중복0, 실제 현재 경로 존재, 목표 경로 중복/기존 파일 충돌 없음, 자원1개 연결, 링크/문서 검사와 diff를 확인한다. 목표 경로는 아직 존재할 필요가 없으며 검증을 위해 앱 폴더를 만들지 않는다. 문서만 변경하므로 서버·DB·전체 업무 회귀를 다시 실행하지 않는다.

향후 실제 정리는 다음 조건으로 완료를 판단한다.

- 이동 전후 테스트 수집을 경로 대응표로 비교해 누락·중복0을 확인한다. 시점에 따라 수가 달라질 수 있으므로 1차1916개를 무조건 새 기준으로 강제하지 않는다.
- 앱 진입점·패키지 전체 import, 라우트 등록/순서·모델 등록과 ORM 테이블/FK/index/DDL이 같다. 모델 클래스와 요청 ContextVar가 중복 생성되지 않는다.
- 기본·two-cycle OpenAPI **전체 객체**가 각각 직전 기준과 같다. 자원 로딩·dynamic schema·schema 참조가 유효하고 계약 기준본을 변경하지 않는다.
- 격리 PostgreSQL 전체 업무 회귀와 도구 시험을 수행한다. 교체/누락 복구·현재/다음주·완료 이력·권한·타회원 보호·동시성·rollback은 관련 기존 시험을 포함한다. 운영 DB나 개발 실자료를 초기화하지 않는다.
- 1차의 기존 실패2개는 별도로 비교한다. 그룹 활동 해제 뒤 기존 참가 거절 기대, stopped 상태 뒤 미선택 N 개설 허용 기대를 통과시키기 위해 업무 정책이나 기대값을 임의 변경하지 않는다. 새 실패/누락을 기존 실패로 처리하지 않는다.
- 현행 참조에 옛 경로가 남지 않고 과거 검증 원본·동결 자료가 보존돼야 한다. 향후 실제 실행 결과와 미확인 항목은 별도 기록한다.

## 이번 문서 작업의 검증 결과

실제 루트 Python 파일 목록과 대응표를 비교해79개 전부 일치·누락/중복0을 확인했다. 유지2개를 포함한 목표 Python 경로95개의 중복·기존 파일 충돌이 없으며 연결 JSON1개를 명시했다. 문서 검사에서262개 Markdown·상대 링크/앵커2887개·기준 원본171개·보관 본문128개·동결 JSON20개·API 분류209개 검사가 통과했다. `git diff --check`도 통과했다. 이 결과는 문서/경로 검사이며 앱·서버·DB 시험을 실행한 결과가 아니다.

## 승인과 제외 범위

현재는 **계획 문서 작성 완료·실제 2차 구현 미착수**다. 다음은 사용자의 별도 구현 지시가 있을 때 본 문서와 당시 Git/코드 상태를 대조하는 것이다. 브랜치를 바꾸지 않으며 기존 미커밋 변경을 보존한다. commit·push·merge·실제 개발서버 반영·운영 배포·DB 구조/자료·키/환경·백업·Native 코드/화면은 이번 승인 범위에 없다. 업무 정책/API 계약 변경이 필요해지면 정리 작업의 재량으로 확정하지 않는다.
