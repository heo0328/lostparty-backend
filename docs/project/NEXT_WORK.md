# 다음 실행

## 현재 기준 — 그룹 작업 착수 준비

2026-10-28 사용자 지시로 `main`을 최신 `dev`의 `1b6f57b`까지 fast-forward하고 원격 반영했다. 두 기준 브랜치의 커밋과 파일 전체가 같으며, 그 지점에서 `feat/group-management`를 생성·checkout했다. 이번 구간은 Git 기준 정렬과 그룹 작업 준비 기록이며 그룹 기능 구현은 아직 시작하지 않았다.

미완료 `feat/activity-selection`의 로컬 3개 문서 커밋은 통합하지 않고 보존한다. 활동 자동추가·명시제외는 사용자가 차후 Native 확인 후 별도 개발 구간을 정하기로 했다. 모집 재신청 보완과 1차 인수 마감은 기존 [통합 기록](../features/recruitment/reapplication-integration-2026-10-27.md)과 [Issue13](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)을 따른다.

## 다음 실행 — 그룹 범위 확인

- Backend: `feat/group-management`에서 [그룹 안내](../features/groups/README.md)·[이슈 추적표](ISSUE_TRACKER.md)를 기준으로 관련 Issue #12/#16 본문·최신 댓글과 구현/계약을 대조한다. 이번 Git 준비 구간에서는 Issue를 새로 조회하거나 협업 댓글을 게시하지 않았다.
- 사용자/Native와 현재 그룹 작업의 구체 범위·완료 조건을 확인한 뒤 기존 구현 보완과 미합의 후속을 구분해 진행한다. 조건부 해산·추방·대표변경 등 미합의 기능을 이 브랜치 생성만으로 구현 승인된 것으로 간주하지 않는다.
- 현재는 Git/문서 확인만 수행한다. 서버·DB 재실행이나 배포·자료 변경은 없다.

## 개발 실행·검증 기준

현재 개발 API sourcec1f86d8/이미지581a1a5e·DB0033·현재178/199/기본116/133. [재신청 구현](../features/recruitment/participation/reapplication-history-fix-plan.md)·[개발 반영](../engineering/operations/reapplication-history-rollout.md)·[공개 집계](../engineering/operations/records/reapplication-history-rollout.json)를 따른다. 고유 격리20PASS, 실행262소스/runtime31/두 계약·HTTP6·READONLY 목록/한도2계정 일치·anchor34/종료근거13·health/주기작업 확인이다. DDL 전후112업무표1,883행/sequence와 기존 DB/환경/키/API 설정을 보존했다.

이번은 코드/DB/계약을 바꾸지 않는 Git 통합/문서 정리다. 기존 기능·실행 검증을 재사용하며 문서 참조/diff·원격/포함 관계를 확인한다. 전체 회귀/DB 복원·실회원 명령·서버 재시작은 반복하지 않는다. DB33에서 구420 API만 단순 복귀하지 않고 자료·구조 유지 전진 수정이다.

## 다음 기능 작업·차후 보완

현재 추가 Backend 구현·시험 요청은 없다. [전체190 Native 인수/후속](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418)과 [전체191 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)의 정밀도 소비·개방 알럿·제안 발견성/소켓 등은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건으로 보존했다. 현재 착수/인수 선행 조건이 아니며 사용자와 별도 구간을 재시작할 때 최신 계약/코드·UX 및 새 주제 Issue를 확인한다.

다른 그룹·V2 분쟁·생명주기·활동 선택/통계 등의 열린 주제는 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다. 이번 준비로 다른 Issue를 종료하지 않으며 그룹 구현은 범위 확인 후 진행한다. IF-001/002/003 비활성·구명령/자료/원pending·ACK 보존과 별도 성능/실회원 원ACK 키 검증·출시 경계는 유지한다. Native 시험 순서와 구현 내부 이력은 Native가 관리한다. 과거 완료/결정/오류·사용자 정정은 [DEV_LOG](DEV_LOG.md)에 누적 보존한다.
