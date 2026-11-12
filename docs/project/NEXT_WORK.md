# 다음 실행

2026-11-12 KST 기준. 실제 Backend 코드/Git과 각 담당의 현재 코드 확인 결과를 사용한다. Native 코드 상태·완료 판단은 Native가 작성하며 Backend가 대신 검토하지 않는다.

## 현재 우선 — Issue50 Backend 구현/로컬 지원·고정 계약 게시 완료 · Native 적용 대기

- `feat/recruitment-discovery`에서 Native전체4 수용 계약으로 구현·선택검증·실제 로컬 API 반영을 완료했다. [전체5번째 Backend/구현·격리검증/로컬 결과](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6821288801)를 게시하고 실제순번5·본문일치 확인, Issue본문 상단 현재상태/다음담당을 갱신했다.
- [구현 인계](../features/recruitment/search/discovery-implementation.md)·[검증/소스·실행식별](../features/recruitment/search/discovery-verification.json). 기존 POST의 discovery-1 profile로50개·전체count·최소카드/그룹·조율·열람권한을 제공하며 새endpoint0개, 기존 응답/GET/context/후보는 유지한다.
- 신규13PASS(12+추가1 별도실행), 관련회귀52PASS, 두 전체계약 격리/실행컨테이너 일치·로컬HTTP·정적/문서/diff PASS. [합성 성능](../features/recruitment/search/discovery-performance.json)은 운영/밀집그룹·실기기 성능 인수와 별개다. 전체저장소회귀·실회원명령/기기시험은 미실행이다.
- 로컬 image87a918db…5c0bd·DB0036, 기존DB컨테이너·118테이블/행·키4개·환경/포트/명령/마운트 보존. migration/초기화·운영배포는 없다. 원래 백업사본/로컬dump제외 방침 유지.
- **게시 완료:** 사용자 직접 지시로 업무/계약/시험/문서를 `558ee6da4299dea49729ebaca5825ce9a235a42e`에 commit/push·원격일치확인했다. [전체7번째 Backend/고정계약 인계](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6821559025)와 [OpenAPI 고정파일](https://github.com/heo0328/lostparty-backend/blob/558ee6da4299dea49729ebaca5825ce9a235a42e/openapi/two-cycle.openapi.yaml)을 Native전체6 파일위치요청에 회신했다. SHA256은기존인계3fdc0661…7052와같다. 후행게시결과기록도같은목적브랜치에보존한다.
- **다음 Native:** 고정 SHA의 실제 hash/DTO 대조·캐시/화면 연결 후 같은Issue에 구현/자동검증·미확인을 회신한다. 이제 로컬경로 탐색이나 원격게시 대기는없다. dev/main 미통합·운영/기기인수 별도이며 새배포/동일시험 반복요청은없다.

## 공동 릴리즈 마감 완료

- **완료:** Backend2.1.1/source d16734d·image7aa19edf…c061d·DB0036/config lightsail-web-2.1.0 일반공개, 실제웹/새APK인수·Native최종v2.1.0 Release 및Backend공개5파일동일성검증까지완료했다. [배포·백업·최종공개/마감 원장](../engineering/operations/records/release-2.1.0-deployment.json).
- **마감:** 사용자 “마감 진행합니다” 지시로최종9문서를동일목적브랜치에서커밋·dev이력보존통합/main동일화·push하고작업브랜치를정리했다. #49는2026-11-12T08:57:44Z에completed종료했다. 실제Git게시/정리SHA근거는[#49 마감 댓글](https://github.com/heo0328/lostparty-backend/issues/49)에연결한다. 운영배포태그/이미지·코드·DB/키·접속정책은변경하지않는다.
- **추가 대기 없음:** Native회신·반복기기인수·재빌드/재압축·재배포요청은없다. 백업사본/무결성과실제복원시험·정기자동화는별개이며후자를이번마감의새조건으로붙이지않는다.
- **다음 업무:** 현재는 위 #50 구현 인계를 이어간다. 기존순차정리후보#17은아래보존범위에서별도선택한다. #15/#18/#19의미합의계약·자료/DB수정은자동착수하지않는다.

## 별도 보류 — 기존 기능 이슈 정리

- #47 묶음 선택 완료와 #48 복구 안내/일정 읽기는 사용자 지시로 **completed 종료**했다. 추가 구현·계약 확인·동일 시험 대기는 없다. [완료 색인](ISSUE_TRACKER.md#completed)·[개발 이력](DEV_LOG.md).
- 공동 릴리즈 이후 선택할 순차 정리 대상은 [#17](https://github.com/heo0328/lostparty-backend/issues/17)이다. 완료 오류/기존 계정 복구는 사용자 인수·양측 dev 통합 완료다. 누락/부분 완료 자료와 해당 기기 경계·원래 생명주기 요구는 별도 남아 있다. Native가 현재 코드 기준으로 최신화한 본문과 Backend 구현을 구분해 잔여 범위만 정리한다. 지금 자료 생성·DB 조정·반복 기기 시험을 시작하지 않는다.
- **#15·#18·#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다.** 장기 계약/미구현 요구는 [이슈 추적표](ISSUE_TRACKER.md)에 보존한다. 자동 착수·미합의 계약 추가는 없다.

## 현재 코드·게시·실행 기준

| 구분 | 확인 기준 |
|---|---|
| checkout/배포 소스 | feat/recruitment-discovery(b03595a에서 분기) / 배포소스d16734d·v2.1.1 고정, 최종문서는dev/main동일통합 |
| 이전 #47 업무 통합/원격 | 업무44eb4ba·반영 기록624ef00·문서962c1cd9321328f19a8e1ea6b5071fa07380782b를 dev에 이력 보존 병합·push. 원격 병합 SHA 일치/전체 feature tip 포함·동일 tree 확인. app/tests/openapi422파일은 기존 검증 코드와 동일 |
| 로컬 dev | discovery image87a918db…5c0bd/앱291파일·두 전체계약/실HTTP·보존 검사PASS·DB0036 유지. [최신 로컬 근거](../features/recruitment/search/discovery-verification.json). 이전986f8d80/ae6b3e0a는 당시 근거 |
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
