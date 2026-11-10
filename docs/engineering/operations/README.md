# 개발 서버 전환·백업·복구 기록

## 현재 개발 실행 — 2026-11-10

[묶음 선택 완료 반영 기록](records/batch-completion-local-rollout.json): 업무44eb4ba/게시624ef00, runtime ae6b3e0a·DB0036_roster_presence, 앱288파일·기본125/142/two-cycle192/213 전체 계약 일치·healthy를 확인했다. 현재 코드/실행 소스 동일성도 #47 정리에서 확인했다. #47/#48은 사용자 지시로 completed 종료됐고 운영은 이번 로컬 반영과 별개다.

반영 당시118테이블512행·스키마/sequence·키4개·환경/DB 컨테이너·볼륨 보존 근거는 JSON에 있다. 이후 실제 사용자 테스트로 자료가 변할 수 있으므로 당시 행 수를 현재 고정값으로 사용하지 않는다. 현재 단계와 다음 담당은 [NEXT_WORK](../../project/NEXT_WORK.md)·[AI_CONTEXT](../../project/AI_CONTEXT.md)를 따른다.

### 이전 실행/복구 근거

2026-11-09 당시 로컬 실행: [완료 프로필 보정·게시/반영](../../features/recruitment/completion-and-records/completion-profile-contract-fix.md)·[집계](records/completion-profile-contract-verification.json). source16c9cd4/API image101cd82d·DB0036, 앱285파일/282모듈·새 two-cycle 계약864de38b 일치다. 117표355행·구조/sequence·키4개/환경·DB볼륨 보존과 healthy/listener7개/로그오류0을 확인했다. Native 새 계약 연결/기기 인수는 별도이며 운영은 변경하지 않았다. 아래 실행은 각 당시 기록이다.

2026-11-09 당시 로컬 실행: [구조 정리 반영](source-layout-local-rollout.md)·[집계](records/source-layout-local-rollout.json). 게시 소스ccf091d·API image2f86172d/DB0036, 앱285파일/282모듈·두 전체 계약 일치·117표357행/구조/sequence·키4개/환경/DB볼륨 보존·API/DB healthy다. 실제 회원 쓰기·기기 인수·완료 profile 선언 오류 수정은 미완료이며 운영은 변경하지 않았다. 아래 이전 최신 실행/미반영 문장은 각 당시 기록이다.


## 2026-11-07 최신 — 환경 복구·운영 기준본 보관

[백업 원장·사용자 안내 시점](backup-and-recovery.md)과 [실행 집계](records/backup-recovery-2026-11-07.json)가 현재 기준이다. 2026-11-07 당시 로컬 two-cycle/DB0035·Google 로그인 복구와 운영v2.0.0의 온라인 dump/설정/기존 키·복구 구성과 서버 밖 PC 사본의 읽기·해시 일치를 확인했다. 실제 서비스 복원·정기 자동화·외장 매체 보관은 미확인/미실행이다. [복구·검증 이력](../../project/DEV_LOG.md#development-recovery-20261107)을 따른다. 아래 실행 소스/경로 수·DB 단계는 각 전환 당시 이력이다.

<a id="section"></a>

## 현재 운영 경계

최신 개발 실행은 [그룹 후보검색/역할표시 반영 기록](../../features/groups/implementation-2026-10-28.md)·[집계](records/raid-group-link-rollout.json)다. source2602e45/이미지5bd8dde6·DB0034·two-cycle185/206(기본123/140). 기존114업무표2,015행/sequence·DB/설정/키보존·소스274/runtime31/두계약전체일치·READONLY목록그룹표시/프로필/HTTP12·worker/healthy/ERROR0확인. 안내된기존그룹정상흐름은Native#12전체36/#16전체21사용자기기보고통과이며Backend실회원쓰기시험과구분한다. 새최초그룹연결/목록표시후속도개발반영완료·새Flutter연결/기기는별도인수다. migration/병합/운영배포/초기화·삭제없음. 이전 [그룹1차집계](records/group-features-rollout.json)·[재신청 개발반영](reapplication-history-rollout.md)은당시이력으로보존한다.

직전 업무 보완은 [신청자 아이템레벨 보완 개발 반영](application-item-level-rollout.md)·[집계](records/application-item-level-rollout.json)다. sourcef471e31/이미지6d5857b3·177경로·DB0031, 기존자료/키보존·실행12PASS 완료이며 [전체25 Flutter 인수 결과](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)로 레벨표시 기기통과·두 예외분기 구현/자동검증 근거 수용을 확인했다. 두 예외분기의 실제 기기관찰과 전체모집 인수는 미완료다. 아래 표시프로필 반영은 직전 이력이다.

신청 목록 분석·본인pending의 [application-display-1](../../features/recruitment/participation/application-display-proposal.md)을 실제 개발서버에 반영했다. [최신 전환 기록](application-display-rollout.md)·[공개 집계](records/application-display-rollout.json)를 따른다. 경로수177은 같지만 입력/응답 계약이 갱신됐다.

직전 로컬 개발 서버는2026-10-25 #26 구현 source06ea4b2·이미지d24d7cbd, API177경로·DB0031_membership_actions다. 이전 자격기능 전환은 [당시 기록](eligibility-rollout.md)·[당시 집계](records/eligibility-rollout.json)를 따른다. 기본 앱116경로·DB0023 기준과 혼용하지 않는다. [구현 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395)와 별도 반영 구간을 구분한다. AWS 운영 배포·dev/main 통합·실회원 신규명령/실기기 인수는 완료 상태가 아니다.

이전 #24/#25 전환은 기존 DB 컨테이너/볼륨·키·환경을 유지하고 API/동일 lifespan worker를 교체했다. 비공개 백업을 별도 DB에서 제한 LOGIN으로 복원·이행 검증한 뒤 실제 DB를 이행했고 기존105개 업무 표의 모든 행·열 정의·기록시각·키·시퀀스를 보존했다.106→108표/603행, 새2표0행, 실행 계약 일치·health/공개검색/인증경계7검사는 당시 실제 실행 근거다. 합성38시험과 합산하거나 정상 회원 명령 성공으로 표시하지 않는다.

<a id="section-2"></a>

## 전환과 복구 원칙

현재 동작/API 기준과 이전 계약 snapshot·이미지를 구분한다. 복구 리허설은 격리 환경에서 하고 원본 비밀·백업 파일을 공개하지 않는다. 새 쓰기 이후 과거 checkpoint로 원본 DB를 덮어써 새 자료를 버리지 않는다. 구 worker를 새 DB에서 실행하거나 downgrade로 이력을 삭제하지 않는다. 신규 실제 이행·복원·운영 데이터 변경은 이 문서 정리의 실행 범위가 아니다.

<a id="section-3"></a>

## 당시 기록과 집계 자료

| 구간 | 원문 근거 | 집계 자료 |
|---|---|---|
| 두 주차 개발 전환 | [전환 원문](../../archive/work-records/features/recruitment/development/ISSUE_13_W5_LIVE_CUTOVER.md), [복원 준비](../../archive/work-records/features/recruitment/development/ISSUE_13_W5_RESTORE_PREFLIGHT.md) | [checkpoint](records/weekly-cycles-checkpoint.json), [복원 검증](records/weekly-cycles-restore-preflight.json), [전환](records/weekly-cycles-cutover.json), [격리 성능](records/weekly-cycles-performance.json) |
| 새 탈퇴·해산/검색 반영 | [개발 반영 원문](../../archive/work-records/features/recruitment/development/ISSUE_24_25_DEVELOPMENT_ROLLOUT.md) | [반영 집계](records/membership-actions-rollout.json) |

JSON 보고 안의 과거 경로·source/image/hash는 그 당시 스냅샷 값이다. 현재 경로로 고쳐 재현 근거를 바꾸지 않는다. 실제 파일의 현 위치는 위 링크와 [대응표](../documentation/README.md)로 찾는다.

<a id="status"></a>

## 공식 인계·다음 담당

[검색 개발 반영](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [탈퇴·해산 개발 반영](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996). Flutter 직접 연결/정상 로그인 인수·Backend 재현차이 대응의 현재 상태는 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다. 이전 전환 기록과 최신 #26 실제 검증은 위 링크로 구분한다. 아이템레벨 보완 인수는 수용됐으며 Backend는 구체 차이에 대응한다. 네이티브 작업 순서/시험 진행은 해당 측에서 기록한다.
