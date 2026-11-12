# LostParty Backend 기능 지도

2026-11-12 KST 기준. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 공식 이슈 상태/담당은 [ISSUE_TRACKER](ISSUE_TRACKER.md), 완료·결정·검증은 [DEV_LOG](DEV_LOG.md)가 원본이다. Native 구현 판단은 담당자의 현재 코드 확인 결과로 구분한다.

## 현재 기준

- #50 모집 탐색은 Native전체4 수용 후 기존 POST의 discovery-1로 구현·선택검증·실제 로컬 반영 완료. 사용자 지시로 업무SHA `558ee6da4299dea49729ebaca5825ce9a235a42e` commit/push·원격일치확인, [전체7 고정계약 인계](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6821559025) 게시. [구현/검증](../features/recruitment/search/discovery-implementation.md). 다음Native 고정hash/DTO대조·앱적용/회신이며 dev/main통합·운영/기기인수는별도다.

- 공동 운영 릴리즈 완료: Backend `v2.1.1`/source `d16734d86e694579cd4e4e043c2ca89cc81c1b64`·DB0036/config lightsail-web-2.1.0·고정웹 일반공개, 웹/새APK는사용자실인수통과다. [배포·백업·최종공개 원장](../engineering/operations/records/release-2.1.0-deployment.json)·[운영/개발 구분](../engineering/operations/README.md).
- Native [최종v2.1.0 Release](https://github.com/heo0328/LostParty_flutter/releases/tag/v2.1.0)는공개완료, [전체34 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6798998431)를Backend독립다운로드/5파일hash·원본동일성확인으로수용했다. 원APK/웹source와최종태그source는원장에구분한다.
- 실제운영원장대기표기도완료로정정·PC사본보관했다. 운영코드/태그/이미지는불변이며추가배포·기기시험대기는없다. 사용자마감지시로최종문서를dev/main에동일통합·게시하고release/2.1.0을정리했다. #49는completed종료, 추가기술·인수대기는없다. [다음 실행](NEXT_WORK.md).
- #47/#48은사용자승인completed종료, #17정리와#15/#18/#19선택은별도구간이다. 로컬dev는위 discovery반영·DB0036을유지한다.

## 기능별 상태와 원본

| 기능 | 현재 상태·근거 |
|---|---|
| 로그인·회원·개인 API 키 | 기존 구현/기기 확인 유지. [로그인·계정](../features/login-account/README.md) |
| 원정대 등록·소유 인증/분쟁 | 기본 기능 구현. 최종 소유권 이전의 활성 참가 영향 정책/후처리는 #15 미합의·미구현. [소유권](../features/rosters/ownership/README.md) |
| 누락/재등장·참가 경고/교체 | Backend 공개 조회/active·완료 이력 분리·부분 완료 교체·후속 명령 구현/게시·dev 지원 완료. 완료 오류/계정 복구는 인수·양측 dev 통합 완료. 누락 자료/기기 경계와 원래 생명주기 요구는 #17에서 분리 정리. [구현](../features/rosters/lifecycle/roster-participation-implementation.md)·[인수](../features/recruitment/completion-and-records/completion-recovery-acceptance-20261110.md) |
| 활동·대표·표시 | 수동 설정 제공. 신규/첫1700 자동추가·명시제외 영속은 #18 계약 대기. [활동 제안](../features/rosters/activity-and-presentation/proposals.md) |
| 모집·일정·그룹 | 기존1차 구현/연동·보고된 정상 기기 인수 유지. 갱신/레드닷·웹소켓은 별도 후속. [모집](../features/recruitment/README.md)·[그룹](../features/groups/README.md) |
| 묶음 선택 완료 | #47 completed. 전용4경로·공대/개인 단일 원자 명령, 활성 ID/누적 이력 proof·원ACK 보존. 양측 구현/게시·dev 지원/담당 코드 근거 확인. [구현](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 복구 안내·일정 표시 읽기 | #48 completed. Native 담당의 앱 연결/2913PASS·analyze0 및 Backend 정책3항목 수용. 미게시 후속/새 카드 기기 세부 미확인·차후 Penpot은 별도. [종료 근거](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767764278) |
| 주간 이용 통계 | #19 초안/정책 대조 단계, 집계·조회 미구현. [통계](../features/raids/statistics/README.md) |

## 운영·검증 해석

선택 회귀·실제 로컬 지원·사용자 확인·운영 인수는 각각 구분한다. 이전 전체 시험의 미해결 기대 불일치를 새 선택 PASS로 덮지 않는다. 현재운영후보·백업/복원/자동화 상태는 기존 [운영 원본](../engineering/operations/README.md)과 [백업 원장](../engineering/operations/backup-and-recovery.md)을 참조하며 로컬 소스를 운영 반영 완료로 표시하지 않는다.

문서 최신화 직전의 상세 단계는 [이전 상태 기록](../archive/project/status-before-refresh-20261110/AI_CONTEXT.md)에 보존했다. 현재 문서에는 최신 기능 상태와 기준 링크만 유지한다.
