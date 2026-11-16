# 다음 실행

2026-11-17 Issue56 최신 상태: 사용자 구현·검증·게시 지시로1분 개인 가능시간을 구현했다. [변경/검증 기록](../features/recruitment/scheduling/personal-availability-minute-plan.md). 관련 고유122개·도구87개/전체 계약 비교 PASS, 실제 로컬 API 교체·DB0037/자료 집계 보존·실행 계약 일치 확인. 다음 Native는 게시 SHA의 내장 BInterval 재생성/원값·제출·ACK 소비 및 실제 저장/기기를 확인하고 Backend는 회신 대응한다. DB/키/운영 변경 없음. 아래 설계 완료/미구현 안내는 이전 단계 이력이다.


## 현재 실행 — Issue56 개인 가능시간1분 설계 완료

2026-11-17: 사용자 기획·설계 지시로 [구현 계획](../features/recruitment/scheduling/personal-availability-minute-plan.md)을 작성하고 [전체2 Backend·설계 결과](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6923635530)로 회신했다. 다음 Backend는 구현·격리 검증이다. AvailabilityClock1분/기존 일정 ScheduleClock5분 분리·BInterval 공통 참조, 원값/정규화·현재 C/N 제출/복사/ACK·후보/예약 경계를 검증하고 OpenAPI를 같은 변경에서 갱신한다. 새 API/DB migration·초기화/호환 flag는 없다. 이번에는 코드/명세/서버 미변경, 계획/기존 개발 반영 기록은 미커밋·미push다. Native는 게시 명세 수신 후 재생성/소비 대조·실제 저장 인수를 진행한다.

아래 Issue55 기록은 개발 반영/Native I1 후속 기준이다.

2026-11-17 실제 개발 반영 완료: 사용자 토큰 파일 준비 확인 및 로컬 DB 삭제 명시 승인 후 lostparty DB만 초기화·0037 적용, 게시 구현 b95cff5 기준 image c2b4a320…a2dc로 개발 API 전환/healthy 확인. 기존 볼륨·DB 역할·환경/키와 운영은 보존했다. OpenAPI 전체 일치·health/공개 그룹200·미로그인 주차/개인 bootstrap401·회원0·서버 키 로딩 PASS. 실제 provider·회원 수집/저장·기기 인수는 아직 미검증이다. [전체15 Backend·개발 전환 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6921019988). 다음 Native I1 새 로그인·원정대 등록/서버 분석 연동, Backend는 결과 대응이다. 초기화는 이미 완료했으므로 반복하지 않는다. 아래 이전 준비/승인 대기 문구는 전환 전 이력이다. 최신 준비/반영 기록은 미커밋·미push다.


2026-11-16 개발환경 준비: [실제 점검·전환 대상](../engineering/development/server-analysis-dev-preparation.md). 후보 이미지 빌드/전체 명세 비교 완료, 현재 API/DB0036 healthy 유지. 다음 입력은 로컬 lostparty DB 초기화(117표·1,562행) 별도 승인과 서버 token 파일 공급이다. 실제 초기화·migration/서버 교체는 미실행. 준비 기록은 미커밋·미push다.

2026-11-16 게시 갱신: 사용자 지시로 구현 `b95cff51f6eaf74d341115b2cc7868cc625ce626`을 `origin/refactor/lostark-server-processing`에 push하고 원격 일치를 확인했다. [전체10 Backend·B1/B2 게시 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6914931822). 아래 미게시 설명은 게시 전 이력이다. 다음은 Backend 실제 환경 준비이며 실제 DB/키/서버·운영은 미적용이다.

2026-11-16 KST: Issue55 B1/B2 Backend 로컬 구현·자동 검증 완료. checkout `refactor/lostark-server-processing`, 시작 HEAD cda4db3. 코드·명세·기록은 미커밋·미push이며 실제 개발 API/DB0036·키·운영에는 미적용이다.

## 다음 실행 — Issue55 게시·실제 환경 준비

[전체9번째 댓글·Backend B1/B2 구현 결과](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6914853896)를 게시하고 실제 순번을 재조회했다. Backend 로컬 단계 완료, 다음 Backend 게시/실제 환경 준비·Native 통합 대기이며 Issue는 OPEN이다.

[확정 계약](../features/rosters/power-and-profiles/analysis-refresh-contract.md)의 서버 키/순수 분석·새 POST/단일head·읽기/소비 전환과 옛 writer/개인키·과거 실행 제거를 완료했다. [구현·최종 검증/자료 경계](../features/rosters/power-and-profiles/server-processing-implementation.md)·[현재 시험 대응표](../engineering/development/current-test-consolidation.md). 최종 수집1,889개 항목의 통과 근거를 분할/재검증 로그로 대조했고 누락·미해결 실패0이다. 도구87PASS·현재 OpenAPI 전체 객체 비교 PASS. 한 번의 전체 green 실행이나 실제 Native/운영 인수로 표시하지 않는다.

다음 담당은 Backend다. 사용자가 게시를 지시하면 해당 범위만 commit/push하고 소비 SHA를 같은 Issue에 인계한다. 실제 환경 반영을 지시하면 백업 원장을 기준으로 token 공급/보관·기존 fingerprint 재사용과0037 비호환 표의 준비 대상을 확인한 후 승인 범위에서 dev DB/서버 전환·실제 HTTP를 검증한다. 코드 검증을 데이터 삭제/초기화·배포 승인으로 해석하지 않는다.0037은 비호환 행이 있으면 DDL 전에 거절하며 과거 자료 승계 shim은 없다.

Native 공통 UI/가상 예시 구현·통합/기기 인수는 Native 담당이며 게시/실행 환경 준비 후 확인할 경계다. 미게시 코드를 대상으로 원격 시험을 요청하지 않았다. Issue55는 OPEN이고 실제 token 설정·자료 정리/DB0037 적용·개발 서버 교체·운영은 미실행이다. 지금 commit/push/merge·배포를 실행하지 않는다.

## Issue54 공동2.3.0 게시 마감

사용자 마감 진행 지시로 API·웹·Android 공개 결과와 검증 근거를 최종 정리하고 f7b7e8c로 commit·dev/main 통합·push하고 Issue54를 completed 종료했다. Backend 운영 source05daa42/tagv2.3.0·image71e30188…834d9d/DB0036, 웹2.3.0+8/source027f8215 및 [Native 전체18 공개 완료](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6888362725)의 공개APK 검증 보고를 보존한다. [운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). 후행 문서 통합은 운영 source/tag 이동이나 재배포가 아니다.

추가 공개·Backend 시험 대기는 없다. BUG-038은 Native 미해결 추적으로 유지하며 원문은 위 전체18 및 [배포 기록](../engineering/operations/release-2.3.0.md)에 남긴다. 사용자 기기 전수 인수/실제 DB 복원은 미실행이다. release/2.3.0 완료 브랜치는 통합/push 확인 후 정리됐다. 현재 선택 작업은 위 Issue55 조사·설계다. Issue53·17·15·18·19는 이번 마감으로 종료/착수하지 않는다.

## 별도 유효 대기 — Issue53 Native 후속 확인

Backend 예약GET(fe5e082)·정책2(9308ce7/dev2ca8092)와 BUG-036(9a61d0e/dev4be81dc)은 구현·게시/dev 통합·로컬 지원을 완료했다. 정책2와 미개방 다음 주 상세의 사용자/Native 정상 확인도 수신했다. [BUG-036 전체44 인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875171401). 추가 Backend 계약 변경/수정·동일 시험 대기는 없다.

Native는 [전체47](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6883381413)에서 개인 주간 시간표/예약 알럿·방 이동까지 구현하고 사용자 정상 확인·dev통합c4156725를 보고했다. [전체48](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6884612427)에서는 휴대폰 카드/원정대 내부 주차·계정 콘텐츠 및 모집 생성 배치를 dev e1ce0576에 추가 통합/push했다. 전체3032PASS/analyze0은 Native 담당자 자동검증 보고이며 전 기기/응답유실·동시성 전수 인수는 아니다. 미확인 인증복원/탭·상세·생성 경계와 최종 완료 범위는 Native가 추적한다. 더 이상 개인 시간표를 미구현 또는 Native dev 미병합으로 안내하지 않는다.

다음은 Native의 잔여 확인/최종 인계 수신이다. Issue53은OPEN이며 main 동기화는 이번 사용자 지시 범위이며 운영 반영·Issue 종료는 별도 사용자 결정이다. 회신 확인만으로 새 기능이나 배포를 시작하지 않는다.

## 코드·계약·실행 구분

| 구분 | 점검 근거 |
|---|---|
| Backend Git | 사용자 지시로 문서 최신화 게시와 dev/main 동일 tip 동기화. 정책2·BUG-036 포함. main 이전 기준0911383은 이력 보존 |
| 로컬 dev 마지막 반영 | imageadd28707…1f71f2·현재 app.main:app·DB0036·Python296파일. [BUG-036 반영 원장](../engineering/operations/records/unopened-next-detail-local-rollout.json). 이번 문서 점검에서는 서버를 재검증/교체하지 않음 |
| 명세 | 로컬 구현 openapi.yaml191경로/211동작, legacy.openapi.yaml125경로/142동작. 과거 policy1 Schema/ACK는 복구용, 현재 관리 계약은 character-management-2 |
| 운영 마지막 확정 | Backendv2.3.0/source05daa42·웹2.3.0+8/source027f8215·DB0036. [Issue54 원장](../engineering/operations/records/release-2.3.0-deployment.json). Android 공개는 Native 후속 |

## 종료/운영 반영 대기 구분

- Issue51은 API·웹·Android 공개 및 Native 후행 문서 통합 후 completed 종료됐다. [Native 전체6 공개](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6832046386)·[전체7 종료](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6845006123). Android 공개 대기는 해소됐다.
- Issue52도 completed 종료, 양측 dev 통합/push 완료다. Native 업무1a9c5304/dev a7d822ad는 [전체11](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6848167504). 운영 반영은 추가 개발 후 별도 릴리즈다. 기록 다중 페이지 수동 미확인·당시 상세403 원인 미확정은 [조사](../features/recruitment/membership-actions/issue52-investigation.md)에 보존한다.
- Issue50/47/48/49 완료와 이력은 [완료 색인](ISSUE_TRACKER.md#completed)에 있다. 종료된 협업에 반복 인수를 새 대기로 추가하지 않는다.

## 별도 보류

Issue17의 누락/부분 완료·기기 경계 및 원래 생명주기 잔여를 정리하는 일은 별도 선택 대상이다. Issue15 소유권 최종이전 영향·18 활동 자동추가/명시제외·19 통계는 OPEN/미합의·미구현 범위를 유지하고 자동 착수하지 않는다.

## 데이터·운영 경계

기존 유저 자료를 보존하려고 불필요한 구조를 추가할 필요는 없다는 설계 기준을 유지한다. **모든 환경 DB초기화는 대상/영향을 제시하고 사용자 사전 확인 후에만 실행한다.** 지금 승인/실행된 초기화는 없다. 키·환경·Firebase·기기 저장소 삭제로 확대하지 않는다.

<a id="runtime-consolidation-followup"></a>

실행 이름 정리는 완료됐다. 로컬 구현은 기본 app.main:app 단일 앱이며 DB0023 시험용 factory를 제거했다. 실제 dev/운영은 이전 원장을 유지하며 [실행 안내](../engineering/development/runtime-configuration.md)를 따른다.

<a id="recovery-backup-closeout"></a>

기존 키/환경 유효 사본과 [백업 원장](../engineering/operations/backup-and-recovery.md)을 재사용한다. 로컬dump 제외·실제 복원/정기 자동화 미확인 상태는 그대로다. 문서 점검으로 서버/DB/환경을 바꾸지 않는다.
