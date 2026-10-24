# 회원 설정

회원 단위의 `nice_group_auto_refresh_enabled` 허용 설정을 저장·복원한다. 원정대별 설정이나 즉시 외부 데이터 갱신 명령이 아니다.

<a id="behavior"></a>

## 현재 동작

GET은 `{nice_group_auto_refresh_enabled, version}`을 반환한다. 미설정은 false/version1이며 행을 생성하거나 Lost Ark를 호출하지 않는다. 로그아웃·새 세션·같은 회원의 새 기기에서도 서버 저장값을 유지한다. GET 실패를 false로 간주해 자동 PUT하지 않는다.

PUT은 명시한 boolean과 조회한 expected_version, UUIDv4 Idempotency-Key를 사용한다. 실제 변경만 version을 올리고 no-op도 stale version은 거절한다. 설정 변경과 성공 ACK 저장은 같은 트랜잭션이다. 과거 ACK 재송은 과거 성공을 반환하며 현재값을 다시 덮지 않는다.

<a id="constraints"></a>

## 소비·범위

설정 스위치 즉시 저장은 캐릭터 선택의 저장/취소와 독립한다. 이 허용값 저장으로 전체 Armory 수집·역할 계산·자동 갱신이 실행되는 것은 아니다. 빌드 요약·개인 표시 저장은 [원정대·캐릭터](../../rosters/power-and-profiles/README.md)에서 설명한다.

<a id="decisions"></a>

## 주요 결정과 근거

회원 공통 설정과 캐릭터 선택을 분리해 다른 기기에서도 같은 명시 결정을 복원한다. [설정 계약](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6168785700), [Flutter 사용자3흐름 확인 보고](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6170736672). 재설치·다른 기기 전체 인수는 이 보고에 포함되지 않는다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/settings` |
| PUT | `/v1/me/settings` |
