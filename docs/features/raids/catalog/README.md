# 레이드 카탈로그

서버가 합의된 레이드·난이도·입장 기준·주간 공유 관계를 제공한다. 클라이언트가 표시 순서나 이름으로 난이도 권리·기간을 추론하지 않는다.

<a id="behavior"></a>

## 현재 동작

GET `/v1/raid-catalog`는 비로그인도 읽을 수 있는 공개 계약이다. catalog_version과 실제 raid/difficulty ID·순서·기준을 사용한다. 동일 레이드의 공유 주간 완료 관계와 난이도별 입장레벨은 각각의 명시 필드를 따른다. 개인 설정이나 회원·완료 행을 만들지 않는다.

현재 게임 패치와의 최신성 검증은 카탈로그 API 구현 완료와 별도다. 과거 초기 카탈로그 버전을 오늘 게임 데이터의 검증 결과처럼 표시하지 않는다. 기본 레벨·외부 호출 관련 값은 [게임 기본 기준](game-defaults.md)을 따른다.

<a id="decisions"></a>

## 연결·근거

[주간 원장](../weekly-records/README.md)과 [모집 생성](../../recruitment/creation-and-settings/README.md)은 같은 ID와 입장·기간 원본을 사용한다. 별도 게임 원장을 복제하지 않는다. [공개 조회 명세](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6229990139), [카탈로그 원문](../../../archive/work-records/features/raids/ISSUE_10_RAID_CATALOG_DEVELOPMENT.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/raid-catalog` |
