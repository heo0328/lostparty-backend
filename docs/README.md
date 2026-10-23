# 문서 안내

현재 상태와 다음 작업은 [NEXT_WORK](project/NEXT_WORK.md)에서 확인합니다. 기능별 문서는 아래 안내에서 찾아가며, 이슈 번호·기존 파일명은 추적을 위해 유지합니다.

| 찾는 내용 | 위치 |
|---|---|
| 작업·협업 규칙 | [guides](guides/README.md) |
| 다음 작업·기능 지도·이슈·개발 이력 | [project](project/README.md) |
| 게임·DB 공통 기준과 비활성 보존 정책 | [reference](reference/README.md) |
| 인증 | [authentication](features/authentication/README.md) |
| 계정·캐릭터·회원 설정·대표/활동·일괄 조회 | [account](features/account/README.md) |
| 소유권·인증·분쟁·생명주기 | [ownership](features/ownership/README.md) |
| 레이드 카탈로그·주간 원장 | [raids](features/raids/README.md) |
| 그룹·가입·초대·한도·관리 | [groups](features/groups/README.md) |
| 모집·두 주차·일정·참가·완료·검색·탈퇴/해산 | [recruitment](features/recruitment/README.md) |
| 대체된 계약·과거 상태 기록 | [archive](archive/README.md) |

## 읽는 순서

[AGENTS](../AGENTS.md) → [API 협업](guides/API_COLLABORATION.md) → [NEXT_WORK](project/NEXT_WORK.md) → [AI_CONTEXT](project/AI_CONTEXT.md) → 관련 기능의 계약 순서로 읽습니다. 공식 협업 채널은 GitHub Issues입니다.

## 문서 배치 기준

- 최상위에는 이 안내와 분류 폴더만 둡니다. 공통 규칙은 guides, 현재 진행은 project, 공통 기준은 reference, 기능 문서는 features에 둡니다.
- 기능별 README에서 기준 문서와 전체 목록을 연결합니다. 모집처럼 문서가 많은 기능은 contracts·planning·development·feedback으로 나눕니다.
- JSON·예시·검증/생성 도구는 해당 기능의 artifacts에 함께 둡니다. 도구는 저장소 루트에서 실행합니다. 실행 API 계약 원본은 저장소의 openapi 폴더입니다.
- 완료된 구현의 유효한 안내·계약은 기능 폴더에 유지합니다. 대체된 문서만 archive로 옮기고 대체 문서를 연결합니다. DRAFT라는 파일명만으로 폐기/합의 상태를 결정하지 않습니다.
- NEXT_WORK는 다음 행동, AI_CONTEXT는 기능 상태·기준 링크, DEV_LOG는 완료·결정·검증·장애를 담당합니다. 같은 진행 이력을 여러 문서에 누적하지 않습니다.
- 문서를 이동하면 상대 링크와 코드/테스트의 파일 경로를 함께 수정합니다. 과거 Git 커밋에 고정된 외부 링크는 보존하며, GitHub Issue의 예전 경로는 파일명과 Git 이력으로 추적합니다.
