# LostParty Backend 기능 지도

2026-10-24 기준. 다음 실행과 담당은 [NEXT_WORK](NEXT_WORK.md), 주제별 협업 상태는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 결정·검증 이력은 [DEV_LOG](DEV_LOG.md)를 따른다. 아래는 기능 상태와 기준 문서이며, 과거 시점의 상세 기록은 [정리 전 기능 지도](../archive/project/AI_CONTEXT_2026-10-24.md)에 보존한다.

| 영역 | 기능 상태·기준 |
|---|---|
| 공통 작업·협업 | [작업 규칙](../../AGENTS.md), [API 협업](../guides/API_COLLABORATION.md), [품질·UX 기준](../guides/DEVELOPMENT_QUALITY_AND_UX_STANDARD.md). 공식 협업 채널은 GitHub Issues이며 Flutter 로컬 소스에 접근하거나 수정하지 않는다. |
| 실행 계약 | 현재 두 주차 개발 API는 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml) 176경로·DB0031, 기본0023 앱 계약은 [기본 OpenAPI](../../openapi/openapi.yaml) 116경로에 보존한다. [최근 전환·보존 근거](../features/recruitment/development/ISSUE_24_25_DEVELOPMENT_ROLLOUT.md). |
| 인증 #2 | Google 로그인·세션·복구 6 API 구현. 다른 공급자·운영 후속은 별도다. [인증 안내](../features/authentication/README.md). |
| 계정·캐릭터 #3~#8 | 등록·복원·전투력·회원 설정·개인 키·대표/활동 선택·역할 요약·개인 표시·첫 화면 일괄 조회 구현. 활동 자동추가/직접제외 후속은 #18, 미완료 상태는 추적표를 따른다. [계정 안내](../features/account/README.md). |
| 소유권·생명주기 #8/#15/#17 | 장비 인증·현재 소유/퇴역 이력·24시간 V2 소유권 분쟁 Backend 구현. V2 Flutter 구현 보고와 분쟁 실기기 보류는 구분하며, 생명주기 증거·자동정리 후속은 별도다. [소유권 안내](../features/ownership/README.md), [이슈 추적표](ISSUE_TRACKER.md). |
| 레이드·주간 원장 #10/#11 | 공개 카탈로그·서버 주차·개인 주간 상태/수동 완료 구현. 최신 게임 패치 검증과 실제 파티 기능 인수는 별도다. [레이드 안내](../features/raids/README.md). |
| 그룹 #12/#16 | G1/G2 및 G3 관리 조회·그룹장 이전·일반 탈퇴 구현/dev 통합. Flutter 연결·조건부 해산 등 미완료는 추적표를 따른다. [그룹 안내](../features/groups/README.md). |
| 모집 #13/#22~#25 | 두 주차·참가/일정·완료 정정·기록 보관·원자적 참가 관리 및 선택T 검색 제외/탈퇴·해산을 개발 API에 반영했다. 다음 Flutter는 #24/#25 직접 연결·정상 로그인 인수, Backend는 재현 가능한 차이 대응이다. 실회원 명령·기기/성능·dev/main 통합·운영 인수는 미완료다. [모집 안내](../features/recruitment/README.md), [구현 계약](../features/recruitment/development/ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md). |
| 비활성 보존 | 이번주 미완료 종료·같은 주차 재개는 앱 활성 기능에서 제외한다. 구 endpoint/권한/자료·원 pending/24h ACK는 보존하며 복구 UX는 제품 승인 전 제안이다. [IF-001 기준](../reference/INACTIVE_FEATURES.md). |
| 독립 후속 | #17 생명주기·#18 활동 정책·#19 통계, 명령 영속 복구·WebSocket·운영 배포 등은 별도 미완료다. [이슈 추적표](ISSUE_TRACKER.md), [다음 실행](NEXT_WORK.md). |

Backend 구현·자동 검증·계약 인계·Flutter 적용·실회원/실기기·운영 완료는 서로 별개다. 과거 문서의 당시 미구현/브랜치/DB 상태는 현재 상태로 해석하지 않는다.
