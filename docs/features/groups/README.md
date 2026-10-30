# 그룹

기능별 현재 동작과 정책은 아래 문서에서 확인합니다. 구체적인 요청·응답 형태는 실행 OpenAPI, 현재 담당·미완료는 [NEXT_WORK](../../project/NEXT_WORK.md)가 원본입니다. 과거 작업 순서를 읽지 않아도 각 기능의 현재 설명을 이해할 수 있게 구성했습니다.

| 하위 기능 |
|---|
| [그룹 생성·검색·기본 설정](discovery/README.md) |
| [그룹 가입·초대·신청·차단](joining/README.md) |
| [그룹장 이전·탈퇴·정원 관리](management/README.md) |

[전체 문서 안내](../../README.md) · [이슈 추적표](../../project/ISSUE_TRACKER.md) · [원문 대응표](../../engineering/documentation/README.md)

## 1차 구현·개발환경 반영과 후속 후보 보완

2026-10-28 사용자 승인 설계는 [표시·활동 캐릭터·요청 집계](discovery/display-contract-proposal.md)와 [관리·레이드 생명주기](management/phase-one-contract-proposal.md)으로 구분한다. 기존 제공 기능을 대체하지 않는 계약 제안이며 이후사용자승인으로후보HTTP/두OpenAPI를구현·격리검증했다. 2026-10-29 sourcecf214d0/DB0034로 기존 개발환경 반영·실행검증까지 완료했고 기기인수는 별도다. 이후 초대후보 대소문자 검색/역할표시 보완도 같은 브랜치에서 구현·검증하고source5d24244/이미지507cd78a·DB0034로 개발반영했다. 실제초대성공·기기인수는별도다. [구현 기록](implementation-2026-10-28.md)을따른다.

최신 [#16 전체12번째 Flutter 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464943488): 그룹원 누구나 현재 조건으로 개설하며 해당 레이드 공대장이 관리한다. 그룹장 전용 공개전환/해산 명령은 제외하고 방/공대장 안내와 기존 상세를 사용한다.

후속 [모집 최초 연결·목록 그룹명·참가자 소속표시](raid-link-contract.md)는 같은 목적 브랜치에서 구현·격리검증·계약 인계하며 개발반영은source2602e45/5bd8dde6·DB0034로완료했고새UI/기기인수는별도다.

## 실제 주차별 그룹 변경·승계 후속

Issue16 전체27/28의 사용자 확정에 따라 [주차·세대별 그룹 정책](cycle-group-policy.md)을 구현했다. C/N 독립 그룹 변경·일반 전환·그룹원 우선 승계·외부 위임/승계 시 일반 전환·개방 상속과 모든 조회가0035 원본을 사용한다. [검증 집계](cycle-group-policy-verification.json)와 [대표 예시](cycle-group-policy.examples.json)를 따른다. 실제 개발서버는0035에 반영됐으며 고정 계약 소비·서버반영·기기 인수는 구분한다. 위 최초 연결 계약은 이전 실행의 근거다.

현재 주차별 그룹 정책은 [0035 개발반영/실행검증](../../engineering/operations/cycle-group-policy-rollout.md)을 완료했다(sourceb8542ef/이미지930c25f8). 새 Flutter 연결/기기 인수는 별도다.
