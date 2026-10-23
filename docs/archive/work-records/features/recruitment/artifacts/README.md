> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 계약·예시·도구 자료

설계 계약·예시·집계 근거입니다. 실행 API 계약 원본과 구분하며 과거 보고 자료를 현재 상태로 해석하지 않습니다. 생성/검증 Python 도구는 저장소 루트에서 실행합니다. `build_*`는 산출물 또는 모델을 쓰는 도구이며 검증만 할 때는 `validate_*`를 사용합니다. [기능 안내](../README.md).

- [build_issue13_two_cycle_contract.py](../../../../../features/recruitment/weekly-cycles/tools/build-contract.py)
- [build_issue13_two_cycle_examples.py](../../../../../features/recruitment/weekly-cycles/tools/build-examples.py)
- [build_issue13_w2_models.py](../../../../../features/recruitment/weekly-cycles/tools/build-models.py)
- [issue13-completion-correction.examples.json](../../../../../features/recruitment/completion-and-records/examples/completion-correction.json)
- [issue13-cutover-checkpoint.json](../../../../../engineering/operations/records/weekly-cycles-checkpoint.json)
- [issue13-group-character-candidates.draft.openapi.json](../../../../../features/recruitment/search/examples/group-character-candidates.openapi.json)
- [issue13-group-character-candidates.performance.json](../../../../../features/recruitment/search/validation/group-character-candidates-performance.json)
- [issue13-live-cutover.json](../../../../../engineering/operations/records/weekly-cycles-cutover.json)
- [issue13-prejoin-session-display.draft.json](../../../../../features/recruitment/participation/examples/session-display.schema.json)
- [issue13-restore-preflight.json](../../../../../engineering/operations/records/weekly-cycles-restore-preflight.json)
- [issue13-two-cycle.examples.json](../../../../../features/recruitment/weekly-cycles/examples/baseline/contract-examples.json)
- [issue13-two-cycle.full.openapi.json](../../../../../features/recruitment/weekly-cycles/examples/baseline/full.openapi.json)
- [issue13-two-cycle.openapi.json](../../../../../features/recruitment/weekly-cycles/examples/baseline/core.openapi.json)
- [issue13-two-cycle.route-map.json](../../../../../features/recruitment/weekly-cycles/examples/baseline/route-map.json)
- [issue13-two-cycle.routes.md](../../../../../features/recruitment/weekly-cycles/examples/baseline/routes.md)
- [issue13-w5-performance.json](../../../../../engineering/operations/records/weekly-cycles-performance.json)
- [issue22-23-atomic-member-actions.examples.json](../../../../../features/recruitment/membership-actions/examples/atomic-member-actions.json)
- [issue24-25-development-rollout.json](../../../../../engineering/operations/records/membership-actions-rollout.json)
- [issue24-25-implementation.examples.json](../../../../../features/recruitment/membership-actions/examples/membership-actions-implementation.json)
- [issue24-search-contract.json](../../../../../features/recruitment/search/examples/search-contract.json)
- [issue25-membership-actions.contract.examples.json](../../../../../features/recruitment/membership-actions/examples/membership-actions-contract.json)
- [issue25-membership-actions.contract.schema.json](../../../../../features/recruitment/membership-actions/examples/membership-actions.schema.json)
- [validate_issue13_group_character_candidates.py](../../../../../features/recruitment/search/tools/validate-character-candidates.py)
- [validate_issue13_prejoin_session_display.py](../../../../../features/recruitment/participation/tools/validate-session-display.py)
- [validate_issue13_two_cycle_contract.py](../../../../../features/recruitment/weekly-cycles/tools/validate-contract.py)
