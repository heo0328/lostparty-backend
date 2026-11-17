# 이슈 주제별 추적표

2026-11-17 현재: #58 Backend dev0038 지원·Native N1 일반연결/자동검증 완료 보고 수신, 사용자 결과 대기. 작업브랜치 게시와 dev/main·운영 반영을 구분한다. 정확한 SHA·인계는 [DEV_LOG](DEV_LOG.md), 다음 실행은 [NEXT_WORK](NEXT_WORK.md).

## 열린 이슈

| 이슈 | 현재 상태 | 남은 작업·담당 |
|---|---|---|
| [#58 상세 분석 후보](https://github.com/heo0328/lostparty-backend/issues/58) | Backend 구현 `8f29271d`/격리검증·실제dev0038 지원. [Native 전체6 N1](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945574683) 일반앱 연결/자동검증·미게시 보고 수신 | Native/사용자 실제HTTP저장·신규후보/재등록·웹/Android 결과, Backend 구체 오류 대응. [현재 계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md) |
| [#53 내 계정 리메이크](https://github.com/heo0328/lostparty-backend/issues/53) | 정책2 게시/dev 통합·Native 정상보고. BUG-036 수정·5PASS/로컬지원·사용자/Native 정상 확인·9a61d0e/dev4be81dc 통합push | [전체41 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875007986)·전체43 Native 수용/사용자 정상 확인. [전체44 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875171401) 게시/dev 통합 완료, 이 오류의 추가대기 없음. 정책2 사용자 확인 후 개인시간표/예약까지 구현·확인, [전체48 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6884612427) deve1ce0576 추가 통합/push. 추가 Backend 요청 없음, 최종 경계 확인/운영은 별도. Issue54 API·웹/Android 게시 포함·초기화 사전확인 필수 |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) 누락/생명주기·기존 참가 복구 | 완료 오류/기존 계정 복구 인수·양측 dev 통합 완료. Native가 현재 경고/관리 왕복 연결과 별도 누락/부분 완료 기기 경계를 본문에 최신화 | 다음 순차 정리 대상. Backend 현재 구현과 Native 담당 근거로 완료/잔여 범위를 확정. 누락 자료/원복·기기 확인 착수는 별도 후속이며 현재 생성/DB 조정 요청 없음 |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) 소유권 최종이전 영향 | 기본 인증/분쟁 연결 완료. 활성 참가가 있으면 최종이전 보류, 영향 정리/복구 정책·adapter 미합의/미구현 | Native 소비검토5항목·사용자 제품 정책 결정, 합의 후 Backend 원자 설계. [검토 원본](../features/rosters/ownership/dispute-impact-review.md) |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) 활동 자동추가·공통정책 | 상세 분석 후보는 #58로 분리, 추가2개 제품경계도 사용자 확정 | 원래 활동 자동추가는 미착수. 공통 관찰/제외 사실 모델은 #58 구현과 중복 생성하지 않음. [현재 계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md) |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) 주간 이용 통계 | Native 초안 검토 회신, 집계/조회 미구현 | Backend 확정/제안 분리 초안·집계 예시/원천 대조 보완, 양측·사용자 정책 합의. [현재 원본](../features/raids/statistics/README.md) |

#15/#18 활동자동추가/#19는 독립 후속으로 유지하며 #58 진행을 그 착수 승인으로 확대하지 않는다. 이 표 갱신은 새 기능 구현·계약 확정·대량 회신 승인이 아니다.

<a id="completed"></a>

## 최근 완료·별도 후속

| 이슈/구간 | 완료 근거 | 별도 보존 |
|---|---|---|
| #57 BUG-039 완료·사용자 삭제 | 사용자 작업 완료 확인. 계정 ID·캐릭터명 포함으로 Close 대신 사용자 직접 삭제 | 추가 구현/인수/회신 대기 없음. 저레벨 조회 제외는 별도 미착수 제안. [보존 기록](bug-039-analysis-refresh.md) |
| [#56 개인 가능시간1분](https://github.com/heo0328/lostparty-backend/issues/56) completed | 사용자 비5분 입력 정상 확인·양측 구현/검증/명세 소비·통합 완료, [전체9 Backend 종료](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6925204975) | 추가 구현/인수 대기 없음. [종료 근거](issue55-56-closeout-review.md). 기존 일정/후보5분 유지. |
| [#55 서버 수집·분석/비로그인 공통 UI](https://github.com/heo0328/lostparty-backend/issues/55) completed | 사용자 정상 확인·양측 구현/검증/개발 지원·통합 완료, [전체26 Backend 종료](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6925201215) | 추가 구현/재시험 대기 없음. [종료 근거](issue55-56-closeout-review.md). 운영·별도 오류/진단 후속 유지. |
| [#52 운영 웹 오류 조사](https://github.com/heo0328/lostparty-backend/issues/52) completed | Backend a790cbe/devdc5aab0·Native1a9c5304/deva7d822ad 게시·통합. [전체11 Native](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6848167504) | 운영은 추가 개발 후 별도. 기록 다중페이지 수동 미확인/당시403 원인 미확정 보존 |
| [#51 공동2.2.0 배포](https://github.com/heo0328/lostparty-backend/issues/51) completed | API·웹·Android 공개/Native 문서 통합 후 [전체7 종료](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6845006123) | 고정 source/태그·백업은 기존 원장 보존. 새 dev 기능 운영 반영과 구분 |
| [#50 모집 탐색](https://github.com/heo0328/lostparty-backend/issues/50) completed | 사용자지시·Backend업무558ee6da/최종문서011375bf를dev0dc381ae에병합/push·로컬/원격작업브랜치정리, [전체14 마감](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036). Native최종dev83a55020·담당자검증/사용자필터확인 | main통합/운영반영은#51에서완료. #50추가협업대기없음·전수기기/신청/성능인수와구분 |
| [#49 웹·공동 릴리즈](https://github.com/heo0328/lostparty-backend/issues/49) completed | 사용자 “마감 진행합니다” 지시·2026-11-12 completed종료. [Native34 최종공개](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6798998431)·[Backend35 독립검증](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6819138326)·[최종원장](../engineering/operations/records/release-2.1.0-deployment.json). 문서dev/main통합·게시/작업브랜치정리 | 배포Backend소스d16734d·Native원웹89951f4b/APKe9bfa96·최종태그9019ee0 구분. 추가재배포/반복인수대기없음 |
| [#47 묶음 선택 완료](https://github.com/heo0328/lostparty-backend/issues/47) completed | 사용자 종료 지시·[전체13번째 Backend](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6767992300). Backend44eb4ba/실제 dev·Native47a30dad 및 현재 담당 연결/잔여 없음 확인 | 미보고 기기 경계는 사실대로 보존. 후속 갱신/레드닷·웹소켓·누락 자료를 새 대기로 붙이지 않음 |
| [#48 복구 안내/일정 읽기](https://github.com/heo0328/lostparty-backend/issues/48) completed | 사용자 종료 지시·[전체3번째 Backend](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767764278). Native 현재 연결/추가 구현 없음·Backend 정책3항목 수용 | Native 미게시 후속·새 카드 세부 기기 미확인. Penpot은 Native 차후 후속이며 종료 보류 조건 아님 |
| #17 완료 오류/기존 계정 복구 구간 | [Native52 인수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756433040)·[Native54 dev 통합](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756668809), Backend dev 통합 aa7058c/후행084a6af | Issue17 전체는 OPEN, 누락 자료/기기와 원래 생명주기 요구 구분 |

#46 백업 요청·#38 초대 검색·#34 릴리즈 협의·#42 활동 해제 참가 보존·#41 일괄 갱신 및 기존 #13 모집1차 등은 각각 사용자 승인 종료 근거를 유지한다. 이 문서 정리에서 재개하거나 새 시험을 요구하지 않는다.

## 코드·게시·실행은 별개

현재 운영 마지막 확정은 Backend v2.3.0/source05daa42·웹2.3.0+8/source027f8215·DB0036이며 Android 공개까지 #54에서 마감했다. 이번 사용자 지시로 현재 구현/기록을 dev/main 병합4283c2c 및 동일 tip에 통합·게시했다. [정확한 통합 근거](integration-20261117.md). 로컬은 image c720c438…66013/DB0037이며 운영 소스/태그와 구분한다. [최신 운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). 과거 배포의 고정 source/검증은 각 원장에 보존한다.

[점검/정리 결과](OPEN_ISSUE_REVIEW.md) · [NEXT_WORK](NEXT_WORK.md) · [DEV_LOG](DEV_LOG.md) · [최신화 전 단계/댓글 순번 기록](../archive/project/status-before-refresh-20261110/ISSUE_TRACKER.md)

### Issue54 공동2.3.0 게시 마감

Backend API·웹 실제 반영/검증 및 [Native 전체18 공개 완료](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6888362725) 수신 완료. 사용자 지시로 후행 기록 통합/push 및 completed 종료를 완료했다. BUG-038은 Native 미해결이며 배포 마감으로 해결 처리하지 않는다. [운영 원장](../engineering/operations/records/release-2.3.0-deployment.json).
