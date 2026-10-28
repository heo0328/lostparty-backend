# 그룹장 이전·탈퇴·정원 관리

현재 그룹 관리 권한·정원·관계를 읽고 그룹장을 이전하거나 일반 회원이 탈퇴한다. 그룹 해산과 모집방 해산은 다른 기능이다.

<a id="behavior"></a>

## 현재 동작

그룹장은 현재 유효 멤버에게 즉시 이전하고 자신은 일반 멤버로 남는다. 새 그룹장의 유효 정원이 현재 인원을 수용해야 한다. 대표 기록·코드/쿨타임·가입 수는 보존하고 현재 역할 권한은 즉시 바뀐다. 이후 탈퇴는 새 revision을 조회한 뒤 별도 명령이다.

일반 탈퇴는 과거 membership을 보존하고 발신 pending 초대의 유효성을 정리하며 본인 사용량·group/member/directory revision을 함께 갱신한다. 과거 소유/활동 상실을 기존 관계 정리의 추가 차단 조건으로 만들지 않는다.

<a id="constraints"></a>

## 원자성·미완료

group/member CAS·명령 key와 최소 ACK를 사용한다. 관계 변경·head·초대 종료·ACK 저장은 같은 트랜잭션이다. 재가입 뒤 옛 탈퇴 key의 ACK 복구가 새 membership을 종료하지 않는다. ACK를 현재 관리 권한으로 사용하지 않고 management/detail/members를 다시 읽는다.

조건부 해산·그룹 추방·그룹 대표 변경·실제 그룹모집 후처리는 제공 완료가 아니다. 실제 활성 그룹모집 원본을0으로 가정하지 않으며 `GROUP_RECRUITMENT_STATE_UNAVAILABLE` 제한을 유지한다. [계정 한도](../../login-account/usage-limits/README.md)의 group_capacity와 가입 그룹 수를 구분한다.

<a id="decisions"></a>

## 주요 결정과 근거

기존 membership 정리와 새 참가 자격을 구분하고 과거 관계를 보존한다. [관리 명세](../../../archive/work-records/features/groups/ISSUE_16_GROUP_G3_SPEC.md), [구현 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6258994902), [dev 통합·미완료 유지](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/groups/{group_id}/management` |
| POST | `/v1/groups/{group_id}/leadership-transfer` |
| POST | `/v1/groups/{group_id}/leave` |

## 관리 1차 보완 제안

[해산·추방·대표 변경·레이드 생명주기 설계](phase-one-contract-proposal.md)는 Issue #16의 최신 개발 요청에 대한 구현 전 계약 제안이다. 그룹 소멸/탈퇴 후 기존 레이드 보존과 신규 참가 차단을 구분한다. 자격상실 정리·복구승계는 사용자 선택에 따라 별도 미결정이며 독립 관리 기능을 차단하지 않는다.

최신 [#16 전체12번째 Flutter 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464943488): 그룹원 누구나 현재 조건으로 개설하며 해당 레이드 공대장이 관리한다. 그룹장 전용 공개전환/해산 명령은 제외하고 방/공대장 안내와 기존 상세를 사용한다.
