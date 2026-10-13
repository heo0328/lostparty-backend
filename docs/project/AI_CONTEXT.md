# LostParty Backend 프로젝트 지도

기준일 2026-10-14. 실행 계획은 [NEXT_WORK](NEXT_WORK.md), 완료·장애·검증 이력은 [DEV_LOG](DEV_LOG.md)에 둡니다. 이 지도에 긴 계획이나 실행 결과를 복제하지 않습니다.

| 영역 | 핵심 상태·기준 위치 |
|---|---|
| 실행 기반 | Python 3.12·FastAPI·PostgreSQL 17·Docker Compose. [README](../../README.md), [개발 흐름](../DEVELOPMENT_WORKFLOW.md) |
| 기존 health | DB 연결 /health 유지. `app/main.py`, [원본 OpenAPI](../../openapi/openapi.yaml) |
| Google 인증·세션 | 6개 API·DB migration·자동 검증 구현, debug azp 설정 후 emulator 로그인 성공·회원 저장 확인, 전체 세션/실기기 인수 대기. `app/auth`, `app/core`, [인증 개발 안내](../AUTH_DEVELOPMENT.md) |
| API·데이터 정책 | [합의 계약](../ISSUE_2_AUTH_CONTRACT_DRAFT.md), [복구 설계](../ISSUE_2_REFRESH_RECOVERY.md), [Issue #2](https://github.com/heo0328/lostparty-backend/issues/2) |
| 설계 근거 | [초기 모델 제안](../ISSUE_2_GOOGLE_AUTH_PROPOSAL.md), [구현 계획 이력](../ISSUE_2_IMPLEMENTATION_PLAN.md).현재 할 일은 NEXT_WORK가 기준 |
| 테스트·migration | `tests`, `compose.test.yaml`, `alembic/versions/0001_auth.py`. 실행 방법은 인증 개발 안내, 검증 기록은 DEV_LOG |
| 협업 | [API_COLLABORATION](../API_COLLABORATION.md). Backend Issues와 계약 SHA 기준, Flutter 소스 직접 수정 없음 |
| 후속 기능 | 탈퇴·약관·원정대·모집·파티·그룹·Apple/Discord·WebSocket은 이번 구현에 없음 |
| 운영 | Lightsail 배포 예정, 운영 HTTPS·배포·키 관리 준비는 완료로 간주하지 않음 |

인증·진단은 dev의 e18b71a까지 통합·게시됐고 main은4ad3052로 유지합니다. 완료된 작업 브랜치는 삭제했습니다. 현재 문서 작업은 dev에서 분기한 docs/branch-lifecycle이며 미커밋입니다. 게시·통합·Flutter 계약 소비 완료와 로컬 구현 완료를 구분합니다. 원격 상태가 바뀌면 근거 조회 후 이 요약과 NEXT_WORK를 갱신합니다.
