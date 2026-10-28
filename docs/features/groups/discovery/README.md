# 그룹 생성·검색·기본 설정

원정대/활동 캐릭터와 연결한 그룹을 만들고 공개 검색·회원별 목록·상세·멤버를 조회한다. 그룹 관계와 실제 모집 참가 관계는 분리한다.

<a id="behavior"></a>

## 현재 동작

생성·설정 변경은 활성 회원·현재 소유/활동 대상·가입/정원 한도와 revision을 검사한다. 공개 검색과 회원 전용 상세/본인 관계 조회의 공개 필드는 다르며 응답의 permissions를 현재 조회 관찰로 사용한다.

목록은 서버 필터·정렬·서명 cursor를 사용한다. 다른 회원이나 권한 scope에 cursor를 재사용하지 않는다. 권한·목록 세대 변경은 처음부터 현재 조건으로 재조회하며 페이지 뒤에서 임의로 회원을 추가 조회해 권한을 보충하지 않는다.

GET은 그룹·회원·설정 기본행이나 외부 게임 호출을 만들지 않는다. 캐릭터의 전체 개인 설정이나 다른 원정대 자료를 그룹 공개 필드로 확대하지 않는다.

<a id="section"></a>

## 연결·권한

초대/신청·코드 가입은 [가입 관리](../joining/README.md), 그룹장 이전·탈퇴·정원은 [멤버 관리](../management/README.md)가 담당한다. 그룹장과 모집 공대장은 다른 권한이며, 그룹 가입이 그룹 모집방의 실제 참가를 자동 생성하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

공개 탐색과 현재 회원 권한을 구분하고 가입 확정과 사용량을 같은 원본으로 검증한다. [그룹 명세](../../../archive/work-records/features/groups/ISSUE_12_GROUP_G1_SPEC.md), [Flutter 연결 미완료 확인](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6259124455). Backend 구현/dev 통합과 Flutter 화면 연결·실기기 인수는 별도다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/groups` |
| GET | `/v1/groups` |
| GET | `/v1/groups/{group_id}` |
| PATCH | `/v1/groups/{group_id}` |
| GET | `/v1/me/groups` |
| GET | `/v1/me/groups/{group_id}` |
| GET | `/v1/groups/{group_id}/members` |

## 표시 조회 보완 제안

[그룹원 카드·활동 캐릭터·활동시각/요청 집계 설계](display-contract-proposal.md)는 Issue #12의 1차 개발 요청에 대한 구현 전 계약 제안이다. 현재 API 표와 분리하며 신규 profile/경로는 아직 제공하지 않는다.
