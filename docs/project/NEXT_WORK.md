# 다음 실행

## 현재 별도 개선 구간

2026-10-25 사용자 승인: **Backend 로깅·관측 보강**. `chore/backend-architecture-review`에서 세 번째 개선의 코드/후보 설정을 구현했다. [로그 항목·조회·보관 안내](../engineering/operations/logging.md)를 따른다. 기본 logging으로 허용된 JSON 필드만 기록하고 API 요청/DB 원인/worker 결과를 구분한다. Uvicorn 원래 access 기록을 차단하며 Compose api/db는10m×5 정책을 준비했다. **실제 개발 API/DB에는 아직 반영하지 않았고 재생성도 하지 않았다.**

다음은 변경 위험에 맞는 격리 검증 사용이다. 실제 개발 서버 반영이 요청되면 자료·키/환경·원본 실행 보존을 확인한 별도 구간에서 API 이미지를 교체한다. DB 로그 보관 설정을 적용하려고 이번에 DB를 재기동하지 않는다. 외부 서비스/대시보드/알림·전체 backlog 측정·장기보관은 미구현이다. 현재 개선은 로컬 커밋하며 push/PR/merge/배포·네이티브 추가시험 요청은 없다.

앞선 [격리 실행](../engineering/development/isolated-verification.md)과 [의존성 고정](../engineering/development/dependency-locking.md)은 구현·검증 완료다. 다른 구조 개선은 [점검 보고서](../engineering/development/backend-architecture-review.md)를 참고하되 아직 착수하지 않는다. 구체 시험·미실행·실패 수정은 DEV_LOG를 따른다.

아래 모집 대기 상태는 보존한다. 모집 기능 대응 재개 전 `feat/raid-recruitment` checkout과 점검/실행기 기록의 통합 여부를 확인한다. 임시 분기에서 계속 모집 기능을 수정하지 않는다. 새 네이티브 요청 여부는 공식 Issue에서 확인한다.

## 보존한 모집 구간

2026-10-25

- **작업 구간명:** 모집 Backend 구현·개발 반영·인수 기록 정리.
- **작업 내용:** 현재까지의 구현/검증/서버 반영/사용자 인수 근거를 정리하고 후속 Backend 차이 대응 기준을 유지한다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 구현·시험·계약·문서를 같은 목적 브랜치에 누적했다.
- **현재 코드:** 아이템레벨 보완 구현 source `f471e3133ad60befcad77d7123e1107ba7501bb4` 이후는 문서·인계 기록 변경이다.
- **실제 개발 반영:** 같은 source / 이미지6d5857b3…·177경로·DB0031. [반영 근거](../engineering/operations/application-item-level-rollout.md)·[실행 집계](../engineering/operations/records/application-item-level-rollout.json). 반영 당시 API/DB healthy·자료/키/설정 보존을 확인했다.

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

이번 최신화는 문서 작업이다. 기존 시험·서버를 반복 실행하지 않으며 API/OpenAPI·DB·키·실회원 자료를 변경하지 않는다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.
