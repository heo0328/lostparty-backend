# 다음 실행

2026-11-13 KST 기준. 실제 Backend 코드/Git과 각 담당의 현재 코드 확인 결과를 사용한다. Native 코드 상태·완료 판단은 Native가 작성하며 Backend가 대신 검토하지 않는다.

## 현재 작업 — Issue51 공동 운영2.2.0

- 사용자 지시로 dev/main을9775c1e에 맞춰 atomic push·원격 일치 확인, 완료 refactor/backend-runtime 로컬 정리 후 release/2.2.0에서 진행한다.
- #50 탐색과 실행 정리를 함께 배포한다. 운영은2.1.1·DB0036·웹2.1.0으로 정상이며 현재 자료/키/환경은 유지한다. DB migration/키 교체 없이 배포 도구 선갱신과 웹 파일명 처리 보완이 필요하다.
- 사용자 확정에 따라 dev 기능 시험·제한 접근/임시 계정/사용자 재인수는 반복하지 않는다. 기존2001+58 근거의 고정 source/hash 재사용과 새 도구·고정 산출물·실제 배포 검증을 구분한다.
- 다음 Backend: 새 백업/기존 PC 사본 → 설치 도구 갱신/preflight → 표준 API 배포 → 고정 웹 활성/HTTPS/hash → Issue51 실제 결과 회신. 다음 Native는 서버/웹 성공 후Android Release 공개다.
- [실행 계획/복귀](../engineering/operations/release-2.2.0.md)·[웹 원본 수령](../engineering/operations/records/web-handoff-2.2.0.json)·[전체4 Backend 준비](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831158426).

## Issue50 마감 완료 / 다음 업무 선택

- 사용자지시로최종문서011375bf를커밋하고Backend업무558ee6da와함께dev `0dc381ae646fba062f008d26c58b20e653a6de67`에이력보존병합·push/원격일치확인했다. Issue50은2026-11-12T14:52:57Z(KST23:52:57) completed종료다. [전체14 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036). 당시checkout은dev, 완료작업브랜치feat/recruitment-discovery는로컬/원격에서정리했다.
- Native최종dev83a55020·담당자보고2927PASS/analyze0·사용자필터성공보고/Penpot02통합과Backend13최종점검으로합의기능/협업완료를확인했다. 추가Native작업·자료/기기인수·계약확인대기는없다. [구현/검증](../features/recruitment/search/discovery-implementation.md).
- 업무/시험/계약bytes는기존검증/로컬image87a918db…5c0bd·DB0036과같아재시험/재반영을반복하지않았다. main/운영/DB·키변경은없으며전수기기/신청/성능인수완료로확대하지않는다.
- 후속선택한실행정리는위와같이완료했다. 기존#17정리후보와#15/#18/#19보류범위는아래그대로보존하며자동착수하지않는다. 마감결과기록은dev후행문서커밋으로보존한다.

## 공동 릴리즈 마감 완료

- **완료:** Backend2.1.1/source d16734d·image7aa19edf…c061d·DB0036/config lightsail-web-2.1.0 일반공개, 실제웹/새APK인수·Native최종v2.1.0 Release 및Backend공개5파일동일성검증까지완료했다. [배포·백업·최종공개/마감 원장](../engineering/operations/records/release-2.1.0-deployment.json).
- **마감:** 사용자 “마감 진행합니다” 지시로최종9문서를동일목적브랜치에서커밋·dev이력보존통합/main동일화·push하고작업브랜치를정리했다. #49는2026-11-12T08:57:44Z에completed종료했다. 실제Git게시/정리SHA근거는[#49 마감 댓글](https://github.com/heo0328/lostparty-backend/issues/49)에연결한다. 운영배포태그/이미지·코드·DB/키·접속정책은변경하지않는다.
- **추가 대기 없음:** Native회신·반복기기인수·재빌드/재압축·재배포요청은없다. 백업사본/무결성과실제복원시험·정기자동화는별개이며후자를이번마감의새조건으로붙이지않는다.
- **다음 업무:** #50은위와같이마감했다. 기존순차정리후보#17은아래보존범위에서별도선택한다. #15/#18/#19의미합의계약·자료/DB수정은자동착수하지않는다.

## 별도 보류 — 기존 기능 이슈 정리

- #47 묶음 선택 완료와 #48 복구 안내/일정 읽기는 사용자 지시로 **completed 종료**했다. 추가 구현·계약 확인·동일 시험 대기는 없다. [완료 색인](ISSUE_TRACKER.md#completed)·[개발 이력](DEV_LOG.md).
- 공동 릴리즈 이후 선택할 순차 정리 대상은 [#17](https://github.com/heo0328/lostparty-backend/issues/17)이다. 완료 오류/기존 계정 복구는 사용자 인수·양측 dev 통합 완료다. 누락/부분 완료 자료와 해당 기기 경계·원래 생명주기 요구는 별도 남아 있다. Native가 현재 코드 기준으로 최신화한 본문과 Backend 구현을 구분해 잔여 범위만 정리한다. 지금 자료 생성·DB 조정·반복 기기 시험을 시작하지 않는다.
- **#15·#18·#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다.** 장기 계약/미구현 요구는 [이슈 추적표](ISSUE_TRACKER.md)에 보존한다. 자동 착수·미합의 계약 추가는 없다.

## 현재 코드·게시·실행 기준

| 구분 | 확인 기준 |
|---|---|
| checkout/배포 소스 | dev(구현 8a54c485 / 병합 e1e81b76, 미push) / 배포소스d16734d·v2.1.1 고정, #49당시최종문서는dev/main동일통합 |
| 이전 #47 업무 통합/원격 | 업무44eb4ba·반영 기록624ef00·문서962c1cd9321328f19a8e1ea6b5071fa07380782b를 dev에 이력 보존 병합·push. 원격 병합 SHA 일치/전체 feature tip 포함·동일 tree 확인. app/tests/openapi422파일은 기존 검증 코드와 동일 |
| 로컬 dev | runtime image sha256:170d3a2505963e37…3601bb / 현재 앱·DB0036·앱291파일/두 계약·실HTTP/보존 PASS. [근거](../engineering/operations/records/runtime-consolidation-local-rollout.json) |
| 전체 계약 | 현재192경로/213동작(openapi.yaml), legacy125경로/142동작(legacy.openapi.yaml). 정확한 hash는 [구현/계약 근거](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 후행 통합 기록 | 현재 브랜치/게시 상태·기능 브랜치 정리 결과는 dev의 후행 문서 커밋으로 보존. 업무 코드/시험/계약 변경 없음 |

이전 #47 구간에서 사용자 지시로 Backend dev 병합·push를 완료하고 feat/raid-batch-completion을 로컬/원격에서 정리했다. main·로컬 서버·운영은 당시 #47 통합에서 변경하지 않았다. 이후 새 게시/병합/배포는 별도 지시 범위다. 실제 개발 DB의 행 수는 사용자 테스트로 변할 수 있으므로 반영 시점의 건수를 현재 고정값처럼 사용하지 않는다.

## 담당별 후속을 구분

Native #47 게시47a30dad, #48 후속 lib/test/문서의 미커밋·미push·dev 미통합은 Native 담당 보고다. 두 이슈의 승인 범위 연결/추가 구현 없음도 Native 확인에 따른다. Penpot 디자인은 Native 차후 후속이며 종료된 이슈의 대기 조건이 아니다. 미보고 기기 경계·후속 갱신/레드닷·웹소켓을 이미 완료로 확대하지 않는다.

<a id="runtime-consolidation-followup"></a>

## 실행 구성 단일화

사용자 승인으로 위 현재 작업에서 구현·검증·로컬 반영을 완료했다. [현재 구현/유지 조건](../engineering/development/runtime-configuration.md)·[당시 조사](../engineering/development/runtime-consolidation-review.md)·[개선 대장](backend-improvement-plan.md#runtime-consolidation)을 연결한다. 과거 코드 전체 삭제·운영 반영 승인은 포함하지 않는다.

<a id="recovery-backup-closeout"></a>

## 환경·백업 보존

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본·운영 기준본을 재사용한다. 로컬 DB dump 제외 방침과 실제 복원/정기 자동화·외장 매체 미확인 상태는 그대로다. 새 백업/키 생성·자료 삭제 요청은 없다.

이전 실행/협의 경과는 [최신화 직전 기록](../archive/project/status-before-refresh-20261110/NEXT_WORK.md), 완료/결정·검증은 [DEV_LOG](DEV_LOG.md)를 따른다. 현재 상태를 과거 문단 위에 반복 누적하지 않는다.
