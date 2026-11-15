# 다음 실행

2026-11-15 KST 점검. 점검 기준은 dev04b0e9d였으며 사용자 지시로 최신화 문서를 게시하고 main을 dev와 같은 커밋으로 fast-forward한다. 현재 Git 기준은 dev/main 및 origin의 동일 tip으로 확인하며, 운영 소스와 구분한다. 상세 경과는 [DEV_LOG](DEV_LOG.md), 기능 지도는 [AI_CONTEXT](AI_CONTEXT.md), 협업 색인은 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다.

## Issue54 공동2.3.0 게시 마감

사용자 마감 진행 지시로 API·웹·Android 공개 결과와 검증 근거를 최종 정리하고 f7b7e8c로 commit·dev/main 통합·push하고 Issue54를 completed 종료했다. Backend 운영 source05daa42/tagv2.3.0·image71e30188…834d9d/DB0036, 웹2.3.0+8/source027f8215 및 [Native 전체18 공개 완료](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6888362725)의 공개APK 검증 보고를 보존한다. [운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). 후행 문서 통합은 운영 source/tag 이동이나 재배포가 아니다.

추가 공개·Backend 시험 대기는 없다. BUG-038은 Native 미해결 추적으로 유지하며 원문은 위 전체18 및 [배포 기록](../engineering/operations/release-2.3.0.md)에 남긴다. 사용자 기기 전수 인수/실제 DB 복원은 미실행이다. 완료 브랜치는 통합/push 확인 후 정리하고 dev에서 다음 사용자 작업 선택을 기다린다. Issue53·17·15·18·19는 이번 마감으로 종료/착수하지 않는다.

## 현재 다음 담당 — Issue53 Native 후속 확인

Backend 예약GET(fe5e082)·정책2(9308ce7/dev2ca8092)와 BUG-036(9a61d0e/dev4be81dc)은 구현·게시/dev 통합·로컬 지원을 완료했다. 정책2와 미개방 다음 주 상세의 사용자/Native 정상 확인도 수신했다. [BUG-036 전체44 인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875171401). 추가 Backend 계약 변경/수정·동일 시험 대기는 없다.

Native는 [전체47](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6883381413)에서 개인 주간 시간표/예약 알럿·방 이동까지 구현하고 사용자 정상 확인·dev통합c4156725를 보고했다. [전체48](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6884612427)에서는 휴대폰 카드/원정대 내부 주차·계정 콘텐츠 및 모집 생성 배치를 dev e1ce0576에 추가 통합/push했다. 전체3032PASS/analyze0은 Native 담당자 자동검증 보고이며 전 기기/응답유실·동시성 전수 인수는 아니다. 미확인 인증복원/탭·상세·생성 경계와 최종 완료 범위는 Native가 추적한다. 더 이상 개인 시간표를 미구현 또는 Native dev 미병합으로 안내하지 않는다.

다음은 Native의 잔여 확인/최종 인계 수신이다. Issue53은OPEN이며 main 동기화는 이번 사용자 지시 범위이며 운영 반영·Issue 종료는 별도 사용자 결정이다. 회신 확인만으로 새 기능이나 배포를 시작하지 않는다.

## 코드·계약·실행 구분

| 구분 | 점검 근거 |
|---|---|
| Backend Git | 사용자 지시로 문서 최신화 게시와 dev/main 동일 tip 동기화. 정책2·BUG-036 포함. main 이전 기준0911383은 이력 보존 |
| 로컬 dev 마지막 반영 | imageadd28707…1f71f2·현재 app.main:app·DB0036·Python296파일. [BUG-036 반영 원장](../engineering/operations/records/unopened-next-detail-local-rollout.json). 이번 문서 점검에서는 서버를 재검증/교체하지 않음 |
| 명세 | 현재 openapi.yaml194경로/216동작, legacy.openapi.yaml125경로/142동작. 과거 policy1 Schema/ACK는 복구용, 현재 관리 계약은 character-management-2 |
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

실행 이름 정리는 완료됐다. 현재 기본 app.main:app과 legacy DB0023 시험을 구분하며 [실행 안내](../engineering/development/runtime-configuration.md)를 따른다.

<a id="recovery-backup-closeout"></a>

기존 키/환경 유효 사본과 [백업 원장](../engineering/operations/backup-and-recovery.md)을 재사용한다. 로컬dump 제외·실제 복원/정기 자동화 미확인 상태는 그대로다. 문서 점검으로 서버/DB/환경을 바꾸지 않는다.
