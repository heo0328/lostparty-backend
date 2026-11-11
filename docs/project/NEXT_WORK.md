# 다음 실행

2026-11-11 KST 기준. 실제 Backend 코드/Git과 각 담당의 현재 코드 확인 결과를 사용한다. Native 코드 상태·완료 판단은 Native가 작성하며 Backend가 대신 검토하지 않는다.

## 현재 우선 — 공동 릴리즈 4단계 완료 / 5~6단계 인수 시점 조정

- **고정 후보:** Backend `v2.1.1` / source `d16734d86e694579cd4e4e043c2ca89cc81c1b64`. 구현을 dev/main 동일 통합·push하고 태그를 게시했다. [CI43022922694](https://github.com/heo0328/lostparty-backend/actions/runs/43022922694)의 새 full 회귀1968·도구80·두 전체 계약/게시 PASS, 운영자동deploy skipped. image `7aa19edf…c061d`·계약/DB0036·구성 식별과 최초 후보 제외/수정 근거는 [준비 기록](../engineering/operations/records/release-2.1.0-preparation.json)에 둔다.
- **실제 상태:** 운영은 계속 v2.0.0/DB0035다. 서버 별도 clean 후보·원3파일/비활성site 배치와 관리자 preflight ready/applied=false, 다음 일반배포 구성 일치까지 확인했다. current/maintenance 없음, 새 backup·migration·azp/서비스교체·공동공개는 미실행이다. 로컬 dev는 CORS 반영/DB0036을 유지한다.
- **공동 조합:** Native 웹/APK2.1.0+6 고정 인계를 재사용한다. 서로 다른 source·APK 검증의 Native 보고/Backend 확인 범위는 [수령 원본](../engineering/operations/records/web-handoff-2.1.0.json)을 따른다. 웹 재빌드/재압축·artifact 재제출은 불필요하다. 기존 azp2개+새Android1개 추가안·Web audience/서명/nonce 유지, 서비스키4개·기존SSH 재사용이다.
- **현재 대기:** [전체25 Backend/4완료·5~6시점조정](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6796938066)에서 사용자 Chrome/같은Wi-Fi 새APK 시험 준비와 Native 실제 인수·최종 동일bytes 공개 합류 시점을 연결한다. 미응답을 인수 완료로 간주하지 않고 기존 서비스를 유지한다. 사용자 PC 백업 폴더·시험 공인IP는 확인해 비공개 기록에 보관했으며 다시 요구하지 않는다.
- **다음 Backend:** 인수 시점 연결→직전IP 확인·새 날짜 DB/환경·기존키/동결구성·복구도구 backup→기존PC폴더 전송/독립hash 확인→잠금/점검/쓰기중지→0036/azp·동결구성/API·웹 전환→Backend 검사. fresh backup은 실제 변경 직전 확보하며 기존 사본을 덮어쓰지 않는다. [실행 명령·실패/복귀 원본](../engineering/operations/release-2.1.0.md)을 따른다.
- **다음 사용자/Native:** 웹 로그인·보호조회·모집생성/재조회·새로고침·로그아웃, 새APK 운영로그인/기존회원 연결을 확인한다. 양측 실제 결과와 합의 시점에 점검해제/Native Release를 공동 공개한다. 첫 웹은 새 탭/재접속 기준, 새 앱+구0035 제외·구APK 조건부 제한은 운영 설계의 표를 따른다.
- **완료 조건:** 실제 적용 조합·보존/검증·담당별 인수·실제 공개 상태를 배포 기록과 Issue49에 연결한다. CI/파일수령/비활성배치를 운영공개 완료로 표시하지 않는다. Issue 종료는 별도 판단이다. Git/검증 상세 이력은 [DEV_LOG](DEV_LOG.md)에 둔다.

## 별도 보류 — 기존 기능 이슈 정리

- #47 묶음 선택 완료와 #48 복구 안내/일정 읽기는 사용자 지시로 **completed 종료**했다. 추가 구현·계약 확인·동일 시험 대기는 없다. [완료 색인](ISSUE_TRACKER.md#completed)·[개발 이력](DEV_LOG.md).
- 공동 릴리즈 이후 선택할 순차 정리 대상은 [#17](https://github.com/heo0328/lostparty-backend/issues/17)이다. 완료 오류/기존 계정 복구는 사용자 인수·양측 dev 통합 완료다. 누락/부분 완료 자료와 해당 기기 경계·원래 생명주기 요구는 별도 남아 있다. Native가 현재 코드 기준으로 최신화한 본문과 Backend 구현을 구분해 잔여 범위만 정리한다. 지금 자료 생성·DB 조정·반복 기기 시험을 시작하지 않는다.
- **#15·#18·#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다.** 장기 계약/미구현 요구는 [이슈 추적표](ISSUE_TRACKER.md)에 보존한다. 자동 착수·미합의 계약 추가는 없다.

## 현재 코드·게시·실행 기준

| 구분 | 확인 기준 |
|---|---|
| checkout/배포 소스 | release/2.1.0 / 배포소스d16734d·v2.1.1 고정, 후행결과문서는같은브랜치에보존 |
| 이전 #47 업무 통합/원격 | 업무44eb4ba·반영 기록624ef00·문서962c1cd9321328f19a8e1ea6b5071fa07380782b를 dev에 이력 보존 병합·push. 원격 병합 SHA 일치/전체 feature tip 포함·동일 tree 확인. app/tests/openapi422파일은 기존 검증 코드와 동일 |
| 로컬 dev | 웹 CORS 추가 이미지986f8d80로 API 재생성/healthy·실제 HTTP 및 두 전체 계약 확인. DB0036 유지. 이전 업무 runtime ae6b3e0a/앱288파일 비교는 당시 근거. [반영 원본](../engineering/operations/records/batch-completion-local-rollout.json) |
| 전체 계약 | 기본125경로/142동작, two-cycle192경로/213동작. 정확한 hash는 [구현/계약 근거](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 후행 통합 기록 | 현재 브랜치/게시 상태·기능 브랜치 정리 결과는 dev의 후행 문서 커밋으로 보존. 업무 코드/시험/계약 변경 없음 |

이전 #47 구간에서 사용자 지시로 Backend dev 병합·push를 완료하고 feat/raid-batch-completion을 로컬/원격에서 정리했다. main·로컬 서버·운영은 당시 #47 통합에서 변경하지 않았다. 이후 새 게시/병합/배포는 별도 지시 범위다. 실제 개발 DB의 행 수는 사용자 테스트로 변할 수 있으므로 반영 시점의 건수를 현재 고정값처럼 사용하지 않는다.

## 담당별 후속을 구분

Native #47 게시47a30dad, #48 후속 lib/test/문서의 미커밋·미push·dev 미통합은 Native 담당 보고다. 두 이슈의 승인 범위 연결/추가 구현 없음도 Native 확인에 따른다. Penpot 디자인은 Native 차후 후속이며 종료된 이슈의 대기 조건이 아니다. 미보고 기기 경계·후속 갱신/레드닷·웹소켓을 이미 완료로 확대하지 않는다.

<a id="runtime-consolidation-followup"></a>

## 별도 선택 후속 — 실행 구성 단일화

[조사](../engineering/development/runtime-consolidation-review.md)와 [개선 대장](backend-improvement-plan.md#runtime-consolidation)은 보존한다. 기본0023 앱과 현재 two-cycle 실행을 혼용하지 않는다. 구현 착수/기존 코드 삭제·운영 반영은 별도 선택이다.

<a id="recovery-backup-closeout"></a>

## 환경·백업 보존

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본·운영 기준본을 재사용한다. 로컬 DB dump 제외 방침과 실제 복원/정기 자동화·외장 매체 미확인 상태는 그대로다. 새 백업/키 생성·자료 삭제 요청은 없다.

이전 실행/협의 경과는 [최신화 직전 기록](../archive/project/status-before-refresh-20261110/NEXT_WORK.md), 완료/결정·검증은 [DEV_LOG](DEV_LOG.md)를 따른다. 현재 상태를 과거 문단 위에 반복 누적하지 않는다.
