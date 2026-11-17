# 다음 실행

2026-11-17 사용자 게시 지시:0038 호환복구 `08212c31215adae1c3a09cb9705409103af1ebdd` 및 누적계약/개발반영 기록을 dev에 병합·push한다. [Native 전체12 복구수용](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947614833) 수신으로 Backend 지원대기는 해소됐고 사용자 두화면 확인만 남았다. 실제실행image eadaa2cc…37b9/DB0038·계약hash12634daa…b9665는 그대로이며 이번게시를 서버재교체/운영배포로 확대하지 않는다. 정확한 병합·원격확인은 DEV_LOG 게시 영수증을 따른다. 아래 미커밋/미push 설명은 당시 이력이다.

2026-11-17 Issue58 B6:0038 모집/현황 호환 회귀 직접복구·개발API 반영 완료. [전체11 Backend B6](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947547141). 누락3곳에0038 명시지원, 기본current136PASS/하위13PASS·모집관련67PASS·계약불변. 실제인증HTTP 현재/다음주 모집검색200(각0건)·참가목록200(각2건), group policy=True/API·DBhealthy. [상세](../engineering/development/schema0038-recruitment-recovery.md)·[집계](../engineering/operations/records/schema0038-recruitment-recovery.json). 다음Native/사용자 두화면확인, Backend오류대응. 복구소스 미커밋·미push, DBmigration/자료·키/환경·운영 변경 없음.


2026-11-17 / Issue58 / 목적 브랜치 `feat/roster-refresh-policy`.
사용자 지시로 구현·계약·개발 반영·작업 기록을 현재 브랜치에 commit/push 완료했다. [전체7 Backend B4 게시인계](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945682966). 이번 사용자 지시로 dev 병합·push를 진행하며 main은 변경하지 않는다. 구현 SHA는 `8f29271d610aad83021ec3a00e5879f2adda76d5`, 문서tip/원격 확인은 [DEV_LOG](DEV_LOG.md)의 게시 기록과 Issue58 인계를 따른다.

## 현재 상태와 다음 담당

- Backend: 상세 분석 후보·복구/enum·명시제외 이력 보존 구현/격리검증 및 실제 로컬 dev0038/API 지원 완료. [전체4 Backend B3](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944629650)·[현재 계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md).
- Native: [전체5 기술 수용](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944827745)·[전체6 N1 일반 앱 연결](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945574683) 수신. 담당 보고상 전체2873PASS·후행 계정49PASS/analyze0, 미커밋·미push다. Backend 자체 검증이나 사용자 실기기 인수로 바꿔 표시하지 않는다.
- 다음 Native/사용자: 복구된 모집목록·레이드현황 두화면만 확인하고 Issue58에 회신한다. [전체8 Native](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6946846800)의 사용자10항목/실패표시 확인은 유지하며, 신규/소멸 실제사례는 사용자결정으로 운영피드백 후속이다. 앱전반 반복시험/자료조작은 요청하지 않는다.
- Issue57은 사용자 작업완료 확인 후 식별정보 포함으로 사용자 직접 삭제했다. 추가 인수/회신 대기 없음. [보존 기록](bug-039-analysis-refresh.md).
- Issue55/56은 completed 종료, 사용자 앱 전반·비5분 입력 정상 확인까지 완료다. [종료 근거](issue55-56-closeout-review.md). 재개방/반복 인수 대기 없음.

## 코드·계약·실행 구분

| 구분 | 기준 |
|---|---|
| Git | 기준dev `4c2cff0` 위 `feat/roster-refresh-policy` 구현/문서를 사용자 승인으로 게시. 이번 사용자 지시로 dev 통합·push, main은 별도 |
| 로컬 실행 | 복구 image `eadaa2cc…37b9`, DB0038·API/DB healthy. [최신복구집계](../engineering/operations/records/schema0038-recruitment-recovery.json); DBmigration 재실행 없음 |
| 명세 | 191경로/211동작, SHA256 `12634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665`; 실제 실행 전체일치 |
| 검증 | 복구 기본current136PASS/하위13PASS·모집관련67PASS. 후보기능 기존검증은 DEV_LOG를 따르며 겹치는 집계는 합산하지 않음 |
| 실제 점검 | 현재/다음주 인증HTTP 모집검색200(각0건)·참가목록200(각2건). 읽기만 검증, 두화면 시각 인수 대기 |
| 운영 | v2.3.0/source05daa42·DB0036, [운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). 이번 작업으로 변경 없음 |

실제 개발 반영/보존 근거는 [집계](../engineering/operations/records/analysis-candidates-local-rollout.json), 상세 결정·시험/오류 수정·협업 경과는 [DEV_LOG](DEV_LOG.md)와 [계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md)을 따른다.

## 별도 유효 대기

Issue17 잔여/기기·15 소유권 이전·18 활동 자동추가·19 통계는 기존 별도 후속이다. Issue58 상세 분석 후보가 Issue18 활동 자동추가의 완료/폐기를 뜻하지 않는다. [이슈 추적표](ISSUE_TRACKER.md). Issue53 기존 완료근거·정책2/BUG-036/예약GET에는 추가 Backend 동일시험 대기가 없다.

## 데이터·운영 경계

이번 요청은 승인된 호환복구계획 구현·검증·개발API 교체다. 이번 사용자 지시로 복구 커밋과 문서를 dev에 병합·push한다. DB 초기화/자료삭제·키변경·provider 한도 소진·운영 배포는 실행하지 않는다.

<a id="runtime-consolidation-followup"></a>

현재 create_app·DB0038로 개발한다. 과거 migration·동결 명세·배포 원장은 보존한다. [실행 기준](../engineering/development/runtime-configuration.md).

<a id="recovery-backup-closeout"></a>

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본과 로컬dump 제외 방침을 유지한다. 서버token 별도 사본·실제 복원/정기자동화 미확인 경계도 유지하며 게시/테스트 완료로 보관을 확인했다고 간주하지 않는다.
