# LostParty Backend 기능 지도

2026-11-17 최종 상태: 사용자 명시 지시로 Issue55·56을 completed 종료했다. [Issue55 전체26 Backend 종료](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6925201215)·[Issue56 전체9 Backend 종료](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6925204975). 사용자 앱 전반/캐릭터 조회·비5분 입력 정상 확인 및 종료 근거를 보존한다. 해당 기능의 추가 구현/재시험·인수 대기 없음. 아래 OPEN/종료 결정 대기는 이전 이력이다. 후행 문서는 이번 승인 범위로 commit/push하며 운영/서버/DB/키는 변경하지 않는다.


2026-11-17 종료 가능 여부 점검: Issue55·56 모두 완료 조건 충족으로 completed 종료 가능하다. [점검 원본](issue55-56-closeout-review.md)·[Issue55 전체25 Backend 판단](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6925089683)·[Issue56 전체8 Backend 판단](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6925093036). 사용자 앱 전반/캐릭터 조회·비5분 입력 실사용 정상 확인까지 반영했으며 추가 기능/동일 시험 대기는 없다. 실제 상태는 OPEN이고 이번 요청은 판단이므로 Close는 실행하지 않았다. 사용자 종료 지시에 따른 completed 처리를 완료했다. 운영/별도 후속은 종료 방해 조건으로 추가하지 않는다. 후행 문서는 미커밋·미push다.


Native [Issue56 전체7 사용자 정상 확인·통합 보고](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924853807)도 확인했다. Native dev/main/origin은 d8e91a4951d6baa6095a47326394563e9af44c83으로 통합됐으며 추가 Backend 변경/재검증 요청은 없다.

2026-11-17 사용자 실사용 확인 완료: API 변경 후 캐릭터 조회를 포함한 앱 전반 기능 점검이 모두 정상이었고,0/5분 단위가 아닌 시간 입력도 모두 정상 통과했다고 사용자가 직접 보고했다. 해당 범위의 실제 앱 동작·분 단위 입력을 미검증/인수 대기로 안내하지 않는다. 이 근거는 사용자 실사용 보고이며 Backend 자동 시험 집계와 별도로 보존한다. 동일 점검을 반복 요청하지 않으며 추가 문제 발생 시 해당 근거에 대응한다.


2026-11-17 기준. 다음 실행은 [NEXT_WORK](NEXT_WORK.md), 상세 작업/검증·병합은 [통합 기록](integration-20261117.md)·[DEV_LOG](DEV_LOG.md), 공식 담당/대기는 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다. 현재 목적 브랜치를 사용자 지시로 dev/main 병합4283c2c 및 동일 tip으로 통합했다. 운영은 별도다.

## 현재 기준

- #55: 서버 key·순수 분석/명령·최신 summary/detail head·소비 전환/옛 writer·개인키·과거 실행 제거와 개발 DB0037/API 반영 완료. [구현/검증](../features/rosters/power-and-profiles/server-processing-implementation.md)·[실제 반영](../engineering/development/server-analysis-dev-preparation.md).1889항목 분할 검증 근거 확인, 새 승인 없이 초기화를 반복하지 않는다.
- #56: 개인표1분/기존 일정·후보5분 분리·BInterval 소비,122항목/도구87PASS·실제 dev 지원 완료. [근거](../features/recruitment/scheduling/personal-availability-minute-plan.md).
- Native901de262 게시·명세 소비·최종2863PASS/analyze0·분 지정 정상 사용자 보고 수신. [#55 전체22](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6924581088)·[#56 전체5](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924582578). 사용자 앱 전반·비5분 입력 실사용 확인 완료, Backend는 추가 결과 대응. 추가 Backend 변경/동일 시험 요청 없음, Issue55/56 종료 가능 판정·현재 OPEN.

- #54: Backendv2.3.0/source05daa42·image71e30188…834d9d/DB0036와 웹2.3.0+8/source027f8215를 운영 반영했다. 표준43665092583 전체 성공, 두 명세/118테이블 행·환경/키/DB·Caddy 보존 및 HTTPS34자산 검증 완료. [전체16 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6887988908)·[운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). Native 전체18에서 Android 공개·실파일/서명·안내문 검증 완료 보고를 수신했다. 공개 대기는 해소됐고 사용자 지시로 후행 기록 통합/push·Issue54 completed 종료를 완료했다. Backend 추가 작업 대기 없음·사용자 기기 인수/BUG-038 해결과 구분하며 후행 문서 통합은 운영 재배포와 구분한다.

- #53 BUG-036: 미개방 다음 주 모집 상세500 수정·로컬지원·사용자/Native 정상 표시 확인을 마치고 수정9a61d0e/dev4be81dc 통합push 완료. [전체44 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875171401)·[원인/검증](../features/recruitment/membership-actions/unopened-next-detail.md). 추가 Backend 대기 없음, 전체 리메이크 후속·운영은 별도다.

- #53 대표/예약: 정책2 업무9308ce7/dev2ca8092와 예약GETfe5e082는 Backend dev 게시·로컬 지원 완료. Native 전체34 정상 확인 이후 시간표/예약 알럿도 전체47에서 구현·사용자 확인/dev통합했다. 전체48 Native dev e1ce0576에는 계정/휴대폰 카드와 모집 생성 배치까지 포함된다. [최신 회신](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6884612427). 추가 Backend 요청 없음, 최종 기기 경계/운영 반영은 별도다.

- #52 운영 기록 오류 조사: 기존 관계 복구 목록 계약을 보존하고 선택 주차 기록 표시·부가정책·cursor 소비 수정은 Native 구현/자동검증·dev 사용자 정상 보고까지 수신했다. 더 보기는 수동 미확인, Backend 기록 a790cbe는 사용자 승인으로 dev dc5aab0에 통합/push 완료했으며 Native도 전체11에서 업무1a9c5304/dev a7d822ad 통합·push를 보고했고 Issue52는completed 종료다. Native 기록 소비 수정은 Issue54 웹2.3.0+8 운영 게시에 포함했으며 Android도 Native 전체18에서 공개 완료를 보고했다. 생성 상세403의 과거 원인은 별도 미확정이다. [조사·검증·담당 경계](../features/recruitment/membership-actions/issue52-investigation.md).

- 실행 설정·명칭 정리는 `refactor/backend-runtime`에서 구현·검증·로컬 API 반영 완료다. 당시 기본 `app.main:app`과 DB0023 시험용 legacy를 분리했으며, #55 로컬 구현에서 시험용 factory를 제거했다. 명세 원문/DB 이력·자료·키/환경을 보존했다. 전체 회귀 고유2,001PASS·캐시 보완 후 58PASS·도구84PASS. [실행/검증](../engineering/development/runtime-configuration.md)·[운영 도구 전환 준비](../engineering/operations/runtime-release-transition.md). 사용자 직접 지시로 구현 8a54c485·로컬 dev 병합 e1e81b76 완료, dev/main9775c1e push·원격일치 및 완료 작업 브랜치 정리 완료. 이후 [Issue51 공동 배포](../engineering/operations/release-2.2.0.md)를 완료했으며 실제 운영은 v2.2.0/sourcec31d90da·DB0036·웹2.2.0+7로 반영 완료다. [전체5 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831720284)·[집계](../engineering/operations/records/release-2.2.0-deployment.json), Native Android 공개·문서 통합까지 보고됐고 Issue51은completed 종료다. 사용자 재시험 대기는 없다.

- #50 모집 탐색은 양측구현/담당자검증·사용자필터확인으로합의기능완료, 사용자지시로Backend dev0dc381ae 통합/push·작업브랜치정리 및Issue completed종료까지마감했다. [전체14 Backend](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036)·[구현/검증](../features/recruitment/search/discovery-implementation.md). Native최종dev83a55020, 업무소비558ee6da의#50계약은유지한다. 추가협업대기없음, main/운영·전수인수와구분한다.

- 이전 공동 운영 릴리즈 이력: Backend `v2.1.1`/source `d16734d86e694579cd4e4e043c2ca89cc81c1b64`·DB0036/config lightsail-web-2.1.0·고정웹 일반공개, 웹/새APK는사용자실인수통과다. [배포·백업·최종공개 원장](../engineering/operations/records/release-2.1.0-deployment.json)·[운영/개발 구분](../engineering/operations/README.md).
- Native [최종v2.1.0 Release](https://github.com/heo0328/LostParty_flutter/releases/tag/v2.1.0)는공개완료, [전체34 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6798998431)를Backend독립다운로드/5파일hash·원본동일성확인으로수용했다. 원APK/웹source와최종태그source는원장에구분한다.
- 실제운영원장대기표기도완료로정정·PC사본보관했다. 운영코드/태그/이미지는불변이며추가배포·기기시험대기는없다. 사용자마감지시로최종문서를dev/main에동일통합·게시하고release/2.1.0을정리했다. #49는completed종료, 추가기술·인수대기는없다. [다음 실행](NEXT_WORK.md).
- #47/#48은사용자승인completed종료, #17정리와#15/#18/#19선택은별도구간이다. 로컬dev는위 실행정리·DB0036을유지한다.

## 기능별 상태와 원본

| 기능 | 현재 상태·근거 |
|---|---|
| 로그인·회원·게임 API 키 | 로그인/회원 기존 확인 유지. #55 로컬 구현은 서버 키 단일 공급으로 전환하고 개인키 API를 제거했으며 실제 개발 서버는 적용 완료·운영은 별도. [로그인·계정](../features/login-account/README.md) |
| 원정대 등록·소유 인증/분쟁 | 기본 기능 구현. 최종 소유권 이전의 활성 참가 영향 정책/후처리는 #15 미합의·미구현. [소유권](../features/rosters/ownership/README.md) |
| 누락/재등장·참가 경고/교체 | Backend 공개 조회/active·완료 이력 분리·부분 완료 교체·후속 명령 구현/게시·dev 지원 완료. 완료 오류/계정 복구는 인수·양측 dev 통합 완료. 누락 자료/기기 경계와 원래 생명주기 요구는 #17에서 분리 정리. [구현](../features/rosters/lifecycle/roster-participation-implementation.md)·[인수](../features/recruitment/completion-and-records/completion-recovery-acceptance-20261110.md) |
| 활동·대표·표시 | main-only 자동 대표/관리 정책2 및 Native 사용 전원 표시 적용·확인 완료. 신규/첫1700 자동추가·명시제외 영속은 #18 계약 대기. [활동 제안](../features/rosters/activity-and-presentation/proposals.md) |
| 모집·일정·그룹 | 기존1차 구현/연동·보고된 정상 기기 인수 유지. 갱신/레드닷·웹소켓은 별도 후속. [모집](../features/recruitment/README.md)·[그룹](../features/groups/README.md) |
| 묶음 선택 완료 | #47 completed. 전용4경로·공대/개인 단일 원자 명령, 활성 ID/누적 이력 proof·원ACK 보존. 양측 구현/게시·dev 지원/담당 코드 근거 확인. [구현](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 복구 안내·일정 표시 읽기 | #48 completed. Native 담당의 앱 연결/2913PASS·analyze0 및 Backend 정책3항목 수용. 미게시 후속/새 카드 기기 세부 미확인·차후 Penpot은 별도. [종료 근거](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767764278) |
| 주간 이용 통계 | #19 초안/정책 대조 단계, 집계·조회 미구현. [통계](../features/raids/statistics/README.md) |

## 운영·검증 해석

선택 회귀·실제 로컬 지원·사용자 확인·운영 인수는 각각 구분한다. 이전 전체 시험의 미해결 기대 불일치를 새 선택 PASS로 덮지 않는다. 현재운영후보·백업/복원/자동화 상태는 기존 [운영 원본](../engineering/operations/README.md)과 [백업 원장](../engineering/operations/backup-and-recovery.md)을 참조하며 로컬 소스를 운영 반영 완료로 표시하지 않는다.

문서 최신화 직전의 상세 단계는 [이전 상태 기록](../archive/project/status-before-refresh-20261110/AI_CONTEXT.md)에 보존했다. 현재 문서에는 최신 기능 상태와 기준 링크만 유지한다.
