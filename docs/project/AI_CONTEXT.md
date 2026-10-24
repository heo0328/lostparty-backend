# LostParty Backend 기능 지도

현재 작업 구간은 **신청자 아이템레벨 누락 보완(#26)**, 브랜치는 **feat/raid-recruitment**, 실제 프로젝트 경로는 `/home/heowork/projects/lostparty-backend`다. 문서 정리와 최신 현황/회신 기록을 모집 코드와 이력 보존 통합했다. 문서 수정/기록이라는 작업 내용과 작업 구간명·브랜치를 구분하는 [제1원칙](../engineering/development/workflow.md)을 따른다. 브랜치 정리 이후 같은 브랜치에서 계약2 후보API를 구현·격리 검증했으며 실제 개발 서버177 반영·자료 보존 검증도 완료했다. 정상 로그인/기기 인수는 미완료다.

2026-10-25 기준. 현재 실행·다음 담당은 [NEXT_WORK](NEXT_WORK.md), 주제별 미완료는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 결정·검증 이력은 [DEV_LOG](DEV_LOG.md)를 따른다. 아래는 기능 상태와 기준 링크이며 UI 화면 동선을 추정한 분류가 아니다.

| 기능 | 상태·기준 |
|---|---|
| [로그인·계정](../features/login-account/README.md) | Google/자체 세션·복구·회원 설정·개인 게임키·한도 구현. 추가 공급자·탈퇴/운영정책은 별도 미완료. |
| [원정대·캐릭터](../features/rosters/README.md) | 등록/갱신·소유 인증/V2분쟁·현재/퇴역 읽기·전투력/분석·대표/활동/표시·일괄조회 구현. V2분쟁 실인수 보류, 생명주기 증거/활동 자동추가·명시제외 후속은 별도. |
| [레이드·주간 기록](../features/raids/README.md) | 공개 카탈로그·서버 주차·개인 완료/주간 summary 구현. 최신 게임패치 검증과 실제 이용 통계 집계는 별도 미완료. |
| [그룹](../features/groups/README.md) | 생성/가입/초대·코드/차단·관리조회·그룹장 이전/일반탈퇴 구현·dev통합. Flutter 연결/실기기와 조건부 해산·추방/대표변경 후속 미완료. |
| [모집·일정](../features/recruitment/README.md) | 기존176/DB0031 개발반영·#25 A/B/C/#24연결 보고수신. #26 계약2의 공통자격/변경원자성·후보GET 구현/격리 고유45PASS·후보177/기본116·기존DTO보존 완료, [실제 개발177 반영·자료보존검증](../engineering/operations/eligibility-rollout.md) 완료. [실행 소비 계약](../features/recruitment/participation/candidate-contract.md), Flutter 전체9 f89c009f 두intent 통합연결/493PASS 자체보고 수신·Backend 독립재현 아님. [전체11 Flutter 가입소수3항목 사용자 정상보고/표시계약 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003) 수신. [표시 계약 제안1](../features/recruitment/participation/application-display-proposal.md) 작성/22예시·음성15 정적검증 완료·[전체13 Flutter 소비수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384902537)·새프로필 구현/격리28PASS·기본116/소스177/기존DTO 보존 완료·[실제 개발반영/자료보존 검증](../engineering/operations/application-display-rollout.md) 완료. [전체16 Flutter 연결/413PASS 보고](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385536441) 수신·독립재현아님. 상세예시8 참조정정/추가12PASS 완료·API코드불변. [전체17 자료보완회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385820194) 완료·[전체19 아이템레벨누락](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761) 확인·나머지표시1/2정상사용자보고. [레벨출처보완](../features/recruitment/participation/application-item-level-proposal.md)은[전체21 Flutter 소비/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386405233) 완료·신규저장/기존누락읽기구현·격리35PASS/후보6d5857b3…·177/116/기존DTO보존·[실제개발 반영·자료보존 검증](../engineering/operations/application-item-level-rollout.md) 완료(sourcef471e31/이미지6d5857b3). [전체23 Flutter 연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386758343) 13fb5848/158PASS 자체보고 수신. [전체25 Flutter 보완 인수 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737) 확인: 레벨표시 기기 통과, current_saved/unavailable은 구현·자동검증 근거 수용/실제분기관찰 미수행. 다음Flutter 모집 전체5구간 점검·Backend 구체차이대응. #26 전체8의 1~5는 수동시험 분량만 구분/구현범위 제외 기준 아님. 실회원/기기·운영 인수 별도 미완료. |
| [공통 개발·운영](../engineering/README.md) | GitHub Issues·OpenAPI 계약 협업, 품질/트랜잭션/데이터보존 기준. 최신 전환 근거는API177/DB0031. 현황 조회에서 API/DB healthy·health200·DB0031을 읽기 확인했으며 실회원 명령 재검증은 아니다. |

현재 개발 실행 계약은 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../openapi/openapi.yaml)다. two-cycle은 실행 구성 이름이며0031은 DB마이그레이션 단계다.

[IF-001](../features/recruitment/completion-and-records/inactive-features.md)의 앱 비활성과 서버권한/구명령/원ACK보존을 구분한다. 공대장복구 UX는미승인 제안이다. Backend 구현·자동검증·계약인계·Flutter적용·실회원/기기·운영완료는 각각 별개이며 dev/main 통합·운영배포를 이번 문서 작업으로 완료하지 않는다.

과거 문서 위치와 작성 당시 상태는 [대응표](../engineering/documentation/README.md), [보관 문서](../archive/README.md)에서 확인한다. 작업자는 [AGENTS](../../AGENTS.md)와 [API협업](../engineering/collaboration/api-collaboration.md)을 따른다.
