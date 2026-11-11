# LostParty Backend 기능 지도

2026-11-11 KST 기준. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 공식 이슈 상태/담당은 [ISSUE_TRACKER](ISSUE_TRACKER.md), 완료·결정·검증은 [DEV_LOG](DEV_LOG.md)가 원본이다. Native 구현 판단은 담당자의 현재 코드 확인 결과로 구분한다.

## 현재 기준

- 공동 릴리즈 브랜치 `release/2.1.0`, Backend 고정 후보 `v2.1.1`/source `d16734d86e694579cd4e4e043c2ca89cc81c1b64`. full CI/불변이미지 확보·운영 preflight ready/applied=false까지 완료했다. [실행 설계](../engineering/operations/release-2.1.0.md)·[후보 검증/식별](../engineering/operations/records/release-2.1.0-preparation.json).
- 실제 운영은 v2.0.0/DB0035, 로컬 dev는 CORS 반영·DB0036을 유지한다. 서버 후보와 웹은 비활성 배치만 완료, 운영 migration/azp·서비스교체·웹 활성화/공동공개는 미실행이다. [운영/개발 구분](../engineering/operations/README.md).
- #49 W3/W4 합의와 Native 웹/APK2.1.0+6 고정 인계를 유지한다. [수령 원본](../engineering/operations/records/web-handoff-2.1.0.json). 기존 azp2개+새Android1개 추가안·서비스키/SSH 재사용, 실제 설정 적용과 Google·기기 인수는 미완료다.
- 다음은 사용자/Native 인수 시점 연결 후 직전 backup/점검 전환·실제 인수·공동공개다. [전체25 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6796938066)·[다음 실행](NEXT_WORK.md). 준비 상태를 운영 완료로 표시하지 않는다.
- #47/#48은 사용자 승인으로 completed 종료했다. #17 정리와 #15/#18/#19 선택은 공동 릴리즈 후 별도 진행한다.

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

선택 회귀·실제 로컬 지원·사용자 확인·운영 인수는 각각 구분한다. 이전 전체 시험의 미해결 기대 불일치를 새 선택 PASS로 덮지 않는다. 운영v2.0.0·백업/복원/자동화 상태는 기존 [운영 원본](../engineering/operations/README.md)과 [백업 원장](../engineering/operations/backup-and-recovery.md)을 참조하며 로컬 소스를 운영 반영 완료로 표시하지 않는다.

문서 최신화 직전의 상세 단계는 [이전 상태 기록](../archive/project/status-before-refresh-20261110/AI_CONTEXT.md)에 보존했다. 현재 문서에는 최신 기능 상태와 기준 링크만 유지한다.
