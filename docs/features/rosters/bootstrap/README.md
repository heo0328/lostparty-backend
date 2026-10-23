# 저장 정보 일괄 조회

첫 화면에 필요한 본인 저장 자료를 일관된 snapshot으로 한 번에 조회한다. 로그인·원정대 등록·장비 소유 인증이나 외부 게임 데이터 갱신을 수행하는 API가 아니다.

<a id="behavior"></a>

## 현재 동작

GET `/v2/me/account-bootstrap`은 회원·메인/등록 원정대·소유/활동·개인 profile/표시 설정·현재 주간 원장과 관련 정보를 묶는다. 반복가능읽기/읽기 전용 트랜잭션에서 같은 관찰을 사용하고 기존 단건 DTO의 필수/nullable·권한 의미를 바꾸지 않는다.

외부 HTTP·키 복호화·기본 설정행 생성·자동 캐릭터 선택은 없다. 사용할 수 없는 캐릭터는 unavailable 목록으로 구분하며 저장 자료 오류를 profile=null로 숨기지 않는다. 요청 범위와 오류의 원자성을 유지하고 응답 크기 상한16MiB 초과는 `BOOTSTRAP_RESPONSE_TOO_LARGE`로 구분한다.

주차 전환·소유/활동 변경 중에도 여러 단건 GET의 서로 다른 시점을 합친 것처럼 보이지 않게 한다. 조회 이후 쓰기 권한은 최신 command/context가 다시 판단한다. bootstrap 성공이 모든 기능의 최신 외부 상태나 전체 인수 성공을 의미하지 않는다.

<a id="section"></a>

## 소비·관련 기능

[회원 설정](../../login-account/member-settings/README.md), [캐릭터 profile](../power-and-profiles/README.md), [주간 기록](../../raids/weekly-records/README.md)의 원본 책임은 유지한다. 동일 자료를 이 문서에 별도 정책으로 복제하지 않는다. 오류면 기존 저장값과 조회 실패를 구분하고 초기값을 자동 PUT하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

초기 화면의 요청 수를 줄이면서 권한·관찰 일관성을 보존한다. [Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247620588), [기기 요청 수 관찰 보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248323346), [범위·SQL·크기 근거](../../../archive/work-records/features/account/ISSUE_8_ACCOUNT_BOOTSTRAP_DEVELOPMENT.md). 과거 요청 수 관찰을 전체 기기 성능 인수로 확대하지 않는다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v2/me/account-bootstrap` |
