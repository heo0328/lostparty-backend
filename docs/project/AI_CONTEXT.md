# LostParty Backend 기능 지도

2026-11-13 KST 기준. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 공식 이슈 상태/담당은 [ISSUE_TRACKER](ISSUE_TRACKER.md), 완료·결정·검증은 [DEV_LOG](DEV_LOG.md)가 원본이다. Native 구현 판단은 담당자의 현재 코드 확인 결과로 구분한다.

## 현재 기준

- [전체41 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875007986)에 BUG-036 미개방 다음 주 모집 상세500의 합성 재현·수정/로컬 반영을 회신했다. include_group_state=true 경로가 없는 N RoomCycle을 참조한 AttributeError이며 group_state=null 정상 relation_only200으로 수정했다. [조사/한계](../features/recruitment/membership-actions/unopened-next-detail.md). 격리5PASS/73.40초·두 생성명세 불변·로컬 imageadd28707…1f71f2/app296파일·health200이다. DB 컨테이너/0036·키/환경·포트/mount 보존, 관측중 자료1행 차이로 전체자료 동일성은 미확인이다. 미커밋·미push/현재 fix/recruitment-detail, 전체43 Native가 사용자 정상 표시 확인/기존 응답 소비를 수용해 해당 화면 대기는 해소됐다. 사용자 지시로 문서·게시/dev 통합을 진행한다. 운영/merge·초기화·이슈종료는 하지 않았다.

- #53 후속 대표 정책: 정책2 구현·격리 검증/로컬 지원을 마치고 사용자 지시로 업무9308ce7·dev2ca8092 통합/push를 완료했다. [전체32 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873586100). 작업 브랜치 정리/현재dev, 다음Native 정책2 연결·원ACK/복귀 재조회 검증이며 기기 인수·운영 반영은 후속이다.

- #53 내 계정 리메이크: 합의한 개인 예약 조회를 구현·격리검증/로컬 dev 반영했다. 기존 표시 설정/충돌·legacy 계약 보존, 예약은 Native 게시 계약 소비 검증 단계다. 추가 관리 즉시저장도 최종계약을 구현·격리검증하고 로컬dev에 반영했다. 신규관리도026a74f로commit/push·원격일치확인, Native 연결/기기확인은별도다. [구현/한계](../features/rosters/activity-and-presentation/my-account-reservations-implementation.md).

- #52 운영 기록 오류 조사: 기존 관계 복구 목록 계약을 보존하고 선택 주차 기록 표시·부가정책·cursor 소비 수정은 Native 구현/자동검증·dev 사용자 정상 보고까지 수신했다. 더 보기는 수동 미확인, Backend 기록 a790cbe는 사용자 승인으로 dev dc5aab0에 통합/push 완료했으며 Native Git 상태는 담당자 회신으로 확인한다. 운영 배포는 사용자 결정으로 추가 개발 후 일괄 진행한다. 생성 상세403의 과거 원인은 별도 미확정이다. [조사·검증·담당 경계](../features/recruitment/membership-actions/issue52-investigation.md).

- 실행 설정·명칭 정리는 `refactor/backend-runtime`에서 구현·검증·로컬 API 반영 완료다. 기본 `app.main:app`은 현재 앱, legacy는 DB0023 시험용이다. 명세 원문/DB 이력·자료·키/환경을 보존했다. 전체 회귀 고유2,001PASS·캐시 보완 후 58PASS·도구84PASS. [실행/검증](../engineering/development/runtime-configuration.md)·[운영 도구 전환 준비](../engineering/operations/runtime-release-transition.md). 사용자 직접 지시로 구현 8a54c485·로컬 dev 병합 e1e81b76 완료, dev/main9775c1e push·원격일치 및 완료 작업 브랜치 정리 완료. 현재는 release/2.2.0에서 [Issue51 공동 배포](../engineering/operations/release-2.2.0.md)를 진행하며 실제 운영은 v2.2.0/sourcec31d90da·DB0036·웹2.2.0+7로 반영 완료다. [전체5 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831720284)·[집계](../engineering/operations/records/release-2.2.0-deployment.json), 다음은 Native Android 공개이며 사용자 재시험 대기는 없다.

- #50 모집 탐색은 양측구현/담당자검증·사용자필터확인으로합의기능완료, 사용자지시로Backend dev0dc381ae 통합/push·작업브랜치정리 및Issue completed종료까지마감했다. [전체14 Backend](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036)·[구현/검증](../features/recruitment/search/discovery-implementation.md). Native최종dev83a55020, 업무소비558ee6da의#50계약은유지한다. 추가협업대기없음, main/운영·전수인수와구분한다.

- 공동 운영 릴리즈 완료: Backend `v2.1.1`/source `d16734d86e694579cd4e4e043c2ca89cc81c1b64`·DB0036/config lightsail-web-2.1.0·고정웹 일반공개, 웹/새APK는사용자실인수통과다. [배포·백업·최종공개 원장](../engineering/operations/records/release-2.1.0-deployment.json)·[운영/개발 구분](../engineering/operations/README.md).
- Native [최종v2.1.0 Release](https://github.com/heo0328/LostParty_flutter/releases/tag/v2.1.0)는공개완료, [전체34 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6798998431)를Backend독립다운로드/5파일hash·원본동일성확인으로수용했다. 원APK/웹source와최종태그source는원장에구분한다.
- 실제운영원장대기표기도완료로정정·PC사본보관했다. 운영코드/태그/이미지는불변이며추가배포·기기시험대기는없다. 사용자마감지시로최종문서를dev/main에동일통합·게시하고release/2.1.0을정리했다. #49는completed종료, 추가기술·인수대기는없다. [다음 실행](NEXT_WORK.md).
- #47/#48은사용자승인completed종료, #17정리와#15/#18/#19선택은별도구간이다. 로컬dev는위 실행정리·DB0036을유지한다.

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
