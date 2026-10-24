# 다음 실행

## 현재 실행 기준·다음 작업

2026-10-25 사용자 지시로 `chore/backend-architecture-review`의 구조 점검·개선 이력(`e13980b`/`94bd92d`/`8842b0f`/`65ab2a9`)을 **feat/raid-recruitment**에 이력 보존 병합했다. 현재 checkout과 작업 위치는 `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`다. 작업 구간명은 **Backend 개선 통합·모집 브랜치 복귀**, 작업 내용은 검증된 개선 코드/설정과 최신 기록을 한 기준으로 모으는 것이다.

- [격리 검증 실행](../engineering/development/isolated-verification.md): 실제 변경에 맞게 static/contracts/legacy/two-cycle/all을 선택한다. 개발 DB/실키와 분리한 시험 환경을 기본으로 사용한다.
- [의존성 고정](../engineering/development/dependency-locking.md): runtime31개+test전용12개의 검증 버전/해시 lock을 빌드에서 검사한다.
- [로깅·조회](../engineering/operations/logging.md): 허용 JSON 필드·API/DB/worker 관측과10m×5 정책을 소스에 통합했다. [실제 개발 반영](../engineering/operations/backend-improvements-rollout.md) 완료: source87c2a0e/이미지366e868a·177/DB0031. API·DB 모두10m×5/healthy이며108표993행·키/설정 보존을 확인했다.

다음은 네이티브 구체 차이 수신 시 아래 모집 협업 기준에 따라 대응하는 것이다. 개선은 소스 병합과 실제 개발 서버 반영까지 완료했다. 적용 과정/실행12PASS·로그 확인과 기존 격리시험은 [DEV_LOG](DEV_LOG.md)에서 구분한다. 원격 모집 브랜치는c0128c3이며 로컬 개선 병합/실제 반영 기록은 미push 상태다. 이번 반영은 PR/dev·main 통합/AWS 운영배포·Issue 게시/네이티브 추가시험 요청을 포함하지 않는다. 개선 브랜치는 dev통합·원격게시 정리 조건 전까지 보존한다. 다른 구조 개선은 [점검 보고서](../engineering/development/backend-architecture-review.md)를 참고하되 미착수다.

## 보존한 모집 구간

2026-10-25

- **작업 구간명:** 모집 Backend 구현·개발 반영·인수 기록 정리.
- **작업 내용:** 현재까지의 구현/검증/서버 반영/사용자 인수 근거를 정리하고 후속 Backend 차이 대응 기준을 유지한다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 구현·시험·계약·문서를 같은 목적 브랜치에 누적했다.
- **현재 코드:** 모집 업무 구현 기준은 아이템레벨 보완 source `f471e3133ad60befcad77d7123e1107ba7501bb4`이며, 이번에 격리 실행·의존성 고정·로깅 source `65ab2a9`까지의 개선도 통합했다. 실제 개발 실행 버전과 구분한다.
- **실제 개발 반영:** 개선 통합 source87c2a0e / 이미지366e868a…·177경로·DB0031. [최신 반영 근거](../engineering/operations/backend-improvements-rollout.md)·[실행 집계](../engineering/operations/records/backend-improvements-rollout.json). 아이템레벨 인수/기존 업무는 유지하며 개선 로깅/고정패키지를 적용했다.

## Backend 완료·인수 상태

| 구간 | 현재 상태·근거 |
|---|---|
| 신청·변경 통합 자격/일괄 후보 | 구현·격리45PASS·개발177 반영 완료. [계약2](../features/recruitment/participation/candidate-contract.md)·[반영](../engineering/operations/eligibility-rollout.md). |
| 신청 목록 분석/전투력·본인pending 상세 | application-display-1 구현·격리28PASS·참조보완12PASS·개발 반영 완료. [계약](../features/recruitment/participation/application-display-proposal.md)·[반영](../engineering/operations/application-display-rollout.md). |
| 신청자 아이템레벨 | 신규 snapshot 저장/기존누락 읽기 보완·격리35PASS·개발 반영 완료. [계약](../features/recruitment/participation/application-item-level-proposal.md)·[전체24 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386808894). |

[전체25 Flutter 인수 결과](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)에서 레벨 표시의 사용자 기기 통과를 확인했다. current_saved/unavailable은 구현·자동검증 근거로 사용자가 인수 수용했고 해당 분기의 실제 기기 관찰은 미수행이다. 추가 Backend 수정/재시험 요청은 없다.

Backend 격리시험·실제 서버 HTTP12건·Flutter158PASS 자체보고·사용자 기기 결과는 서로 다른 근거로 유지하고 합산하지 않는다. 전체 모집·변경/주차교차 인수 및 Issue26 전체 종료까지 완료된 것은 아니다.

## 다음 Backend 작업

네이티브의 구체 API/계약·데이터 차이가 보고되면 공식 Issue에서 상태/code·재현구간을 확인하고 재현→수정→필요검증→커밋/push→인계한다. 현재 새 Backend 코드/서버 수정 요청은 없다. 다음 대화에서는 #26 최신 회신과 직접 Backend 요청 여부를 확인한다.

사용자 지시에 따라 **네이티브 작업 순서·시험 진행은 네이티브 측에서 기록·관리한다.** Backend 문서에는 합의 계약·제공 소스/서버 상태·수신 결과와 직접 대응할 미완료만 유지한다. 이전 전체26의 순서 전달 이력은 [DEV_LOG](DEV_LOG.md)에 보존하며 별도 일정/상세 시험 순서를 중복 관리하지 않는다.

직전 모집 인수 최신화는 문서 작업이었다. 개선 코드 병합 때는 기검증 코드 동일성으로 pytest를 반복하지 않았다. 이후 사용자 정정에 따라 실제 서버도 교체했고 별도 실행/자료보존 검증을 완료했다. API 계약·기존 키·실회원 자료는 보존했다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.
