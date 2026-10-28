# 그룹 가입·초대·신청·차단

초대·가입 신청·수락/승인·거절/취소·차단과 가입 코드를 통해 그룹 관계를 관리한다. pending은 정원 예약이나 확정 membership이 아니다.

<a id="behavior"></a>

## 현재 동작

일반 멤버도 초대할 수 있고 본인은 신청·취소, 수신자는 초대 수락/거절, 그룹장은 신청 승인/거절·차단/해제를 수행한다. 확정 직전에 현재 소유·활동·그룹장 정원·대상 가입 수·현재 세션과 관계를 다시 검사한다.

초대/신청은24시간 수명과 발신 membership의 유효성을 따른다. 같은 회원의 새 캐릭터나 코드로 차단을 우회하지 않는다. 거절·만료·권한 회복이 끝난 관계를 자동 부활시키지 않는다. 재가입은 새 membership UUID이며 과거 가입·종료 이력을 덮지 않는다.

<a id="section"></a>

## 가입 코드

그룹장만 생성·재발급·폐기·공개 설정을 변경한다. 코드는 혼동 문자를 제외한 영문 대문자·숫자6자리이고 각 종류를 포함한다. 공개ON은 일반 멤버의 조회/복사 허용, OFF는 원문 숨김이며 이미 복사한 코드의 무효화가 아니다.

재발급은10분 제한과 이전 코드 즉시 폐기를 적용한다. 폐기 뒤 새 생성으로 제한을 우회하지 않는다. 코드 원문은 암호화/digest로 관리하고 URL·로그·멱등 결과에 원문을 남기지 않는다. 원 ACK metadata와 현재 코드 GET은 다른 관찰이다.

<a id="section-2"></a>

## 원자성·소비

정원 마지막 자리 경쟁에서 회원 확정·pending 종료·사용량/목록 revision·ACK는 함께 성공하거나 실패한다. 승인 응답 Relation과 초대 수락/코드 가입 응답 GroupDetail을 구분한다. 재가입 뒤 과거 ACK 복구가 새 membership을 다시 끝내거나 권한을 복원하면 안 된다.

<a id="decisions"></a>

## 주요 결정과 근거

공개 설정·코드 유효성·관계 상태를 분리해 숨김을 폐기로 오인하지 않게 한다. [가입 계약](../../../archive/work-records/features/groups/ISSUE_12_GROUP_G2_SPEC.md), [소비 시 구분 확인](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6259124455).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/groups/{group_id}/invite-candidates` |
| POST | `/v1/groups/{group_id}/invitations` |
| POST | `/v1/groups/{group_id}/applications` |
| GET | `/v1/me/group-relations` |
| GET | `/v1/groups/{group_id}/join-relations` |
| GET | `/v1/group-relations/{relation_id}` |
| POST | `/v1/group-relations/{relation_id}/accept` |
| POST | `/v1/group-relations/{relation_id}/approve` |
| POST | `/v1/group-relations/{relation_id}/reject` |
| POST | `/v1/group-relations/{relation_id}/cancel` |
| GET | `/v1/groups/{group_id}/blocked-subjects` |
| POST | `/v1/groups/{group_id}/join-subjects/{subject_id}/block` |
| POST | `/v1/groups/{group_id}/join-subjects/{subject_id}/unblock` |
| GET | `/v1/groups/{group_id}/join-code` |
| POST | `/v1/groups/{group_id}/join-code` |
| POST | `/v1/groups/{group_id}/join-code/regenerate` |
| POST | `/v1/groups/{group_id}/join-code/revoke` |
| PUT | `/v1/groups/{group_id}/join-code/visibility` |
| POST | `/v1/group-join-codes/preview` |
| POST | `/v1/group-join-codes/join` |

## 표시·집계 보완 제안

차단 subject의 스펙과 정확한 개인/그룹 요청 배지는 [표시 조회 계약 제안](../discovery/display-contract-proposal.md)을 따른다. 현재 제공 API를 변경한 것이 아니며 과거 subject를 이름으로 새 캐릭터에 연결하지 않는다.
