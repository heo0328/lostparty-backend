# 다음 실행

2026-11-17 / Issue58 / 목적 브랜치 `feat/roster-refresh-policy`.
사용자 지시로 구현·계약·개발 반영·작업 기록을 현재 브랜치에 commit/push 완료했다. [전체7 Backend B4 게시인계](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945682966). dev/main 병합은 이번 범위가 아니다. 구현 SHA는 `8f29271d610aad83021ec3a00e5879f2adda76d5`, 문서tip/원격 확인은 [DEV_LOG](DEV_LOG.md)의 게시 기록과 Issue58 인계를 따른다.

## 현재 상태와 다음 담당

- Backend: 상세 분석 후보·복구/enum·명시제외 이력 보존 구현/격리검증 및 실제 로컬 dev0038/API 지원 완료. [전체4 Backend B3](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944629650)·[현재 계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md).
- Native: [전체5 기술 수용](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944827745)·[전체6 N1 일반 앱 연결](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945574683) 수신. 담당 보고상 전체2873PASS·후행 계정49PASS/analyze0, 미커밋·미push다. Backend 자체 검증이나 사용자 실기기 인수로 바꿔 표시하지 않는다.
- 다음 Native/사용자: 연결된 앱의 선택/신규후보·자동/인증1회·결과카드 닫기/재열기·실패/명시retry 결과를 같은 Issue58에 회신한다. 회원 실제 HTTP분석저장·신규후보/재등록·웹/Android 실기기는 아직 미확인이다. Backend는 구체 결과/오류에 대응하며 동일 시험을 추가 요청하지 않는다.
- Issue57은 사용자 작업완료 확인 후 식별정보 포함으로 사용자 직접 삭제했다. 추가 인수/회신 대기 없음. [보존 기록](bug-039-analysis-refresh.md).
- Issue55/56은 completed 종료, 사용자 앱 전반·비5분 입력 정상 확인까지 완료다. [종료 근거](issue55-56-closeout-review.md). 재개방/반복 인수 대기 없음.

## 코드·계약·실행 구분

| 구분 | 기준 |
|---|---|
| Git | 기준dev `4c2cff0` 위 `feat/roster-refresh-policy` 구현/문서를 사용자 승인으로 게시. dev/main 통합은 별도 |
| 로컬 실행 | image `9740bd51…a018`, DB0038. 기존114테이블794행·키5개/주요환경 지문 보존 |
| 명세 | 191경로/211동작, SHA256 `12634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665`; 실제 실행 전체일치 |
| 검증 | current131PASS/하위13PASS·bootstrap/설정/후보86PASS·최종표적17PASS. 겹치는 집계이며 합산하지 않음 |
| 실제 점검 | health200/미인증401·유효세션1명 저장bootstrap service 읽기. HTTP쓰기/기기 인수와 구분 |
| 운영 | v2.3.0/source05daa42·DB0036, [운영 원장](../engineering/operations/records/release-2.3.0-deployment.json). 이번 작업으로 변경 없음 |

실제 개발 반영/보존 근거는 [집계](../engineering/operations/records/analysis-candidates-local-rollout.json), 상세 결정·시험/오류 수정·협업 경과는 [DEV_LOG](DEV_LOG.md)와 [계약](../features/rosters/activity-and-presentation/refresh-candidate-contract.md)을 따른다.

## 별도 유효 대기

Issue17 잔여/기기·15 소유권 이전·18 활동 자동추가·19 통계는 기존 별도 후속이다. Issue58 상세 분석 후보가 Issue18 활동 자동추가의 완료/폐기를 뜻하지 않는다. [이슈 추적표](ISSUE_TRACKER.md). Issue53 기존 완료근거·정책2/BUG-036/예약GET에는 추가 Backend 동일시험 대기가 없다.

## 데이터·운영 경계

이번 요청은 문서 최신화·commit/push다. 실제 개발 반영은 앞선 별도 승인으로 완료했고 반복하지 않는다. DB 초기화/자료삭제·키변경·provider 한도 소진·운영 배포는 실행하지 않는다.

<a id="runtime-consolidation-followup"></a>

현재 create_app·DB0038로 개발한다. 과거 migration·동결 명세·배포 원장은 보존한다. [실행 기준](../engineering/development/runtime-configuration.md).

<a id="recovery-backup-closeout"></a>

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본과 로컬dump 제외 방침을 유지한다. 서버token 별도 사본·실제 복원/정기자동화 미확인 경계도 유지하며 게시/테스트 완료로 보관을 확인했다고 간주하지 않는다.
