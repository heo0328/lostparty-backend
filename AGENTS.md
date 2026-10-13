# LostParty Backend 작업 규칙

이 프로젝트는 초기 개발 단계입니다. 작업 규모에 맞게 아래 원칙을 적용하며, 모든 작업에 상세 설계서나 일괄 검증을 요구하지 않습니다.

- 시작할 때 AGENTS → [협업 규칙](docs/API_COLLABORATION.md) → [NEXT_WORK](docs/project/NEXT_WORK.md) → [AI_CONTEXT](docs/project/AI_CONTEXT.md) → 관련 계약 순서로 읽고 Git·코드 상태를 확인합니다. 문서와 실제 상태가 다르면 근거를 확인해 바로잡고 기존 사용자 변경을 보존합니다.
- Flutter와의 기본 소통 창구는 **Backend GitHub Issues**입니다. 관련 Issue와 합의된 계약을 기준으로 작업하고, 판단 근거가 부족하면 필요한 자료나 결정을 요청합니다. Flutter의 로컬 경로를 찾아 읽거나 소스를 수정하지 않습니다.
- 사용자가 작업을 지시한 관련 Issue에는 필요한 질문·제안·진행 및 검증 결과를 별도 허가 없이 댓글로 작성하고, 상대방이 확인하거나 답해야 할 항목을 명시합니다. 댓글 작성 권한은 미합의 계약의 구현, Issue 종료, 다른 Issue 변경, commit·push·배포 승인으로 확대하지 않습니다.
- 일반 작업은 목적에 맞는 작업 브랜치에서 진행합니다. main은 검증된 통합 기준으로 유지합니다. commit·push·PR·merge는 사용자가 요청하거나 승인한 범위에서 수행하며 같은 승인을 반복해서 묻지 않습니다.
- API 동작을 변경할 때 `openapi/openapi.yaml`과 구현을 함께 검토하고 계약 검증을 수행합니다. 미합의 기능을 계약에 추가하지 않습니다.
- 변경에 맞는 검증을 수행하고 실제 실행 결과와 미실행 항목을 구분해 보고합니다. 문서만 바꿀 때 서버나 DB를 재실행할 필요는 없습니다.
- 단계 종료 시 NEXT_WORK는 다음 실행 중심으로 갱신하고 완료·결정·검증·장애는 [DEV_LOG](docs/project/DEV_LOG.md)에 누적합니다. AI_CONTEXT는 기능 상태와 기준 링크만 유지합니다. 다음 채팅에서 이어갈 남은 입력과 작업을 명시하며 mock·Backend 완료·계약 인계·Flutter 적용·운영 완료를 구분합니다.
- `.env`, 인증정보, 비밀키, 개인정보를 출력·커밋하지 않습니다. DB 볼륨 삭제·초기화, 기존 Firebase나 기기 데이터 삭제, 운영 데이터 변경은 대상과 영향이 명시된 별도 승인 없이 실행하지 않습니다.
- force push와 공유 이력 재작성은 하지 않습니다. 예상하지 못한 원격 변경이나 사용자 변경 충돌은 확인 후 처리합니다.

상세 기준은 [개발 작업 흐름](docs/DEVELOPMENT_WORKFLOW.md)과 [API 협업](docs/API_COLLABORATION.md)을 참고합니다. 프로젝트 소개와 기술 구성은 [README](README.md)에 있습니다.
