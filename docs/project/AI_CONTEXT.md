# LostParty Backend 기능 지도

2026-10-24 기준. 현재 실행·다음 담당은 [NEXT_WORK](NEXT_WORK.md), 주제별 미완료는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 결정·검증 이력은 [DEV_LOG](DEV_LOG.md)를 따른다. 아래는 기능 상태와 기준 링크이며 UI 화면 동선을 추정한 분류가 아니다.

| 기능 | 상태·기준 |
|---|---|
| [로그인·계정](../features/login-account/README.md) | Google/자체 세션·복구·회원 설정·개인 게임키·한도 구현. 추가 공급자·탈퇴/운영정책은 별도 미완료. |
| [원정대·캐릭터](../features/rosters/README.md) | 등록/갱신·소유 인증/V2분쟁·현재/퇴역 읽기·전투력/분석·대표/활동/표시·일괄조회 구현. V2분쟁 실인수 보류, 생명주기 증거/활동 자동추가·명시제외 후속은 별도. |
| [레이드·주간 기록](../features/raids/README.md) | 공개 카탈로그·서버 주차·개인 완료/주간 summary 구현. 최신 게임패치 검증과 실제 이용 통계 집계는 별도 미완료. |
| [그룹](../features/groups/README.md) | 생성/가입/초대·코드/차단·관리조회·그룹장 이전/일반탈퇴 구현·dev통합. Flutter 연결/실기기와 조건부 해산·추방/대표변경 후속 미완료. |
| [모집·일정](../features/recruitment/README.md) | 주차별 생성/개방/참가·일정/완료·기록·검색/관계정리 구현·개발API반영. Flutter #25 A6968f47a의 명령/ACK 구현 보고수신, B메뉴/C기록·#24검색 연결/정상실회원·기기 전체 인수 미완료. |
| [공통 개발·운영](../engineering/README.md) | GitHub Issues·OpenAPI 계약 협업, 품질/트랜잭션/데이터보존 기준. 최신 전환 근거는API176/DB0031이며 문서 정리에서 실제 서버를 재검증하지 않았다. |

현재 개발 실행 계약은 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../openapi/openapi.yaml)다. two-cycle은 실행 구성 이름이며0031은 DB마이그레이션 단계다.

[IF-001](../features/recruitment/completion-and-records/inactive-features.md)의 앱 비활성과 서버권한/구명령/원ACK보존을 구분한다. 공대장복구 UX는미승인 제안이다. Backend 구현·자동검증·계약인계·Flutter적용·실회원/기기·운영완료는 각각 별개이며 dev/main 통합·운영배포를 이번 문서 작업으로 완료하지 않는다.

과거 문서 위치와 작성 당시 상태는 [대응표](../engineering/documentation/README.md), [보관 문서](../archive/README.md)에서 확인한다. 작업자는 [AGENTS](../../AGENTS.md)와 [API협업](../engineering/collaboration/api-collaboration.md)을 따른다.
