# LostParty Backend 문서 안내

기능명으로 현재 동작과 계약을 찾고, 중요한 결정의 이유가 필요할 때 Issue·댓글·보관 원문으로 이동합니다.

| 상위 기능 | 포함 내용 |
|---|---|
| [로그인·계정](features/login-account/README.md) | Google 로그인, 세션·복구, 회원 설정, 개인 API 키, 이용 한도 |
| [원정대·캐릭터](features/rosters/README.md) | 등록·갱신, 소유 인증·분쟁, 생명주기, 전투력·분석, 대표·활동·표시, 일괄 조회 |
| [레이드·주간 기록](features/raids/README.md) | 카탈로그, 주차·시간 기준, 개인 완료·주간 상태, 이용 통계 미완료 제안 |
| [그룹](features/groups/README.md) | 생성·검색, 가입·초대·신청·차단, 멤버·그룹장·정원 |
| [모집·일정](features/recruitment/README.md) | 검색·생성, 현재주·다음주, 참가·일정·완료·기록, 탈퇴·추방·해산 |
| [공통 개발·운영](engineering/README.md) | 협업·개발·품질, 데이터 책임, 실행·전환·검증·복구 |

## 현재 작업과 근거

- [NEXT_WORK](project/NEXT_WORK.md): 다음 담당·행동·대기 사유.
- [AI_CONTEXT](project/AI_CONTEXT.md): 현재 기능 상태와 기준 링크.
- [ISSUE_TRACKER](project/ISSUE_TRACKER.md): 공식 이슈와 미완료 요구.
- [DEV_LOG](project/DEV_LOG.md): 완료·결정·검증·장애의 누적 이력.
- [원문 대응표](engineering/documentation/README.md): 기존 파일·섹션과 새 설명/보관 위치.
- [보관 자료](archive/README.md): 당시 작업·제안·검증 원문.

## 읽는 순서와 계약

작업자는 [AGENTS](../AGENTS.md) → [API 협업](engineering/collaboration/api-collaboration.md) → NEXT_WORK → AI_CONTEXT → 관련 기능 계약 순서로 확인합니다. 공식 소통 채널은 GitHub Issues이며 로컬 문서가 새로운 계약 합의를 대신하지 않습니다.

현재 개발 실행 계약은 [two-cycle OpenAPI](../openapi/two-cycle.openapi.yaml), 기본 앱 보존 계약은 [기본 OpenAPI](../openapi/openapi.yaml)입니다. 프로필·시점이 다른 계약 snapshot을 최신 실행 계약으로 해석하지 않습니다.

## 문서 유지 원칙

현재 기능의 설명은 기능별 원본 한 곳에서 유지하고 연계 기능에서는 연결합니다. Issue·작업 단계는 분류명이 아니라 중요한 결정/이력의 추적 근거입니다. 새 작업 단계마다 문서를 늘리지 않고 기존 기능 설명을 갱신하며 과거 인계·검증은 DEV_LOG나 보관 기록에 남깁니다. 구체 기준은 [문서 구성 기준](engineering/documentation/organization-plan.md)을 따릅니다.
