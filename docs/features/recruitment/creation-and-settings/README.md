# 모집 생성·공통 설정·편성

레이드·난이도·캐릭터 구성·공개 범위와 주차 선택을 확인해 방을 만들고 공통/주차별 설정과 편성을 관리한다.

## 베타 최신 보완

베타 생성·현재/다음주 개방의 기본 출발은18:03 같은 UTC 정수분을 허용한다. context·POST·설치·최종 검사에 같은 정책을 사용하고 원래 분을 저장한다. 30분 미래/주차/점검/진행시간 경계와 원자성을 유지하며 개인표 밖 직접 지정도 기존 자격·표 복사 검사를 거친다. [명시 출발 구현](../weekly-cycles/explicit-minute-departures.md).

<a id="behavior"></a>

## 현재 동작

생성 context에서 현재 소유·활동·역할·레이드 입장레벨·주간 점유·일정·한도를 확인한다. C/N 선택은 하나의 생성 명령에서 전부 성공하거나 실패한다. title은 명시 필수 입력이며 클라이언트/서버가 과거 초안의 누락을 임의 기본 제목으로 보충하지 않는다.

방의 공통 제목·공개 범위와 실제 T의 설정·편성은 다른 자원이다. 공통 설정 권한은 실제 C 공대장을 우선하고 C가 없고 열린 N만 있을 때의 명시 경계를 따른다. C 리더가 review/탈퇴로 관리 불가하다는 이유로 N을 자동 승격하지 않는다. 설정 조회와 변경 context의 CAS 출처를 섞지 않는다.

편성은 앱4/8인 및 파티별 역할·직업 제한, 현재 참가·실제 assignment를 검사한다. 표시 자료의 역할/점수를 provider 인증값으로 승격하지 않는다. 그룹 연결과 공개/그룹 전용 입장은 독립이며 그룹장이 모든 모집 공대장 권한을 얻지 않는다.

<a id="section"></a>

## 계약·원자성

settings/common-settings/formation은 각 명령의 room/target/plan/members/leadership revision과 현재 권한을 다시 확인한다. 공통 설정의 성공 ACK는 해당 계약의 원 응답으로 검증하며 다른 최소 ACK와 임의 통합하지 않는다. 여러 레이드·주차 자원을 중간 commit하거나 공개API를 연속 호출하는 방식으로 원자성을 대체하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

공통 자원과 주차별 상태를 나눠 다른 T의 권한·완료를 보존한다. [공통 관리 구현](../../../archive/work-records/features/recruitment/development/ISSUE_13_W4C_CYCLE_MANAGEMENT.md), [공통 ACK 보완](../../../archive/work-records/features/recruitment/contracts/ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), [생성·제목 계약 보완](../../../archive/work-records/features/recruitment/contracts/ISSUE_13_TWO_CYCLE_CONTRACT_R4.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/raid-rooms` |
| GET | `/v1/me/raid-room-creation-context` |
| GET | `/v1/me/raid-rooms/{room_id}/settings` |
| PUT | `/v1/raid-rooms/{room_id}/settings` |
| PUT | `/v1/raid-rooms/{room_id}/visibility` |
| PUT | `/v1/raid-rooms/{room_id}/formation` |
| GET | `/v2/me/raid-room-creation-context` |
| POST | `/v2/raid-rooms` |
| GET | `/v2/me/raid-rooms/{room_id}/settings` |
| PUT | `/v2/raid-rooms/{room_id}/settings` |
| PUT | `/v2/raid-rooms/{room_id}/formation` |
| GET | `/v2/me/raid-rooms/{room_id}/common-context` |
| PUT | `/v2/raid-rooms/{room_id}/common-settings` |
