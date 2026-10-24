# 모집 검색·그룹원 캐릭터 필터

실제 선택 주차의 모집방을 권한·레이드·그룹·캐릭터·남은 자리 조건으로 서버에서 검색한다. 단순 지속 회원 관계와 해당 주차의 실제 참가를 구분한다.

<a id="behavior"></a>

## 현재 동작

현재 선택 T/세대에서 로그인 본인이 실제 participating 또는 필요한 review 참가 중이고 활성 지속 관계가 일치하는 방은 **SQL 정렬·페이지 처리 전** 제외한다. 반대 T만 참가·미결 신청·종료/단순 지속 관계·비로그인을 잘못 제외하지 않는다. 탈퇴 이후에는 현재 관계와 head 기준으로 다시 노출될 수 있다.

그룹 연결 여부와 입장 공개 범위는 독립 조건이다. 그룹OR·회원AND·선택 회원의 캐릭터OR 등 합의한 논리를 적용하고, 다른 그룹의 동일 회원은 권한 context의 alias/member_ref로 연결한다. 전역 user UUID·전체 개인 설정을 공개하지 않는다.

정렬은 현재 지속 회원의 절대 인원 기준 member_count와 ascending/descending이다. 기본은 내림차순, 동률은 created_at DESC·room_id DESC다. remaining_slot_counts는1..7의 정확한 자리 수 OR 필터이며 []는 제한 없음이다. 역할/직업 자리 필터로 확대하지 않는다.

<a id="section"></a>

## 그룹원 캐릭터 후보·cursor

그룹원 활동 캐릭터 후보는 현재 그룹 권한·소유·활동·후보 세대를 확인하는 별도 조회다. 선택 후 검색 직전에 최신 context로 다시 검증한다. 캐릭터 이름·display값을 권한 ID로 바꾸지 않는다.

cursor는 actor·실제T·정규화 조건·권한/목록 세대·검색 의미를 결합한다. 의미/head 변경의 CURSOR_STALE409와 위조/다른 scope의400을 구분한다. 새 의미 `own-target-participation-excluded-v1`은 옛 cursor와 호환시키지 않는다. 페이지 뒤 필터나 카드별GET으로 서버 제외를 대체하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

페이지 이후 본인 참가 방을 숨기면 빈 페이지·누락이 생기므로 SQL 페이지 전에 제외한다. [검색 계약](../../../archive/work-records/features/recruitment/contracts/ISSUE_24_SEARCH_CONTRACT.md), [개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690), [정렬·자리 근거](../../../archive/work-records/features/recruitment/development/ISSUE_13_SEARCH_SORT_SLOTS.md). #24 Flutter 캐시/직접 연결·실회원 인수는 별도 미완료다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/raid-room-filter-context` |
| POST | `/v1/raid-rooms/search` |
| GET | `/v1/raid-rooms` |
| GET | `/v1/groups/{group_id}/raid-room-member-projections` |
| GET | `/v2/raid-rooms` |
| POST | `/v2/raid-rooms/search` |
| GET | `/v2/me/raid-room-filter-context` |
| GET | `/v2/groups/{group_id}/raid-room-character-candidates` |
| GET | `/v2/groups/{group_id}/raid-room-member-projections` |
