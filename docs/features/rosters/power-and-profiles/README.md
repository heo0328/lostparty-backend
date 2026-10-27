# 전투력·역할별 분석 요약

서버의 게임 API 전투력 관찰과 Flutter가 계산한 역할별 분석 요약을 별도 출처로 저장한다. 화면에 쓰는 숫자가 같아도 검증 수준과 저장 책임은 다르다.

<a id="section"></a>

## 전투력 관찰

본인 원정대의 요청 대상 전체를 먼저 검증한 뒤 외부 profiles를 배치 조회한다. 범위 밖 대상이 있으면 외부 호출/부분 저장을 시작하지 않는다. 현재 기본 수집 하한1700은 수동 활동 선택의 하한이 아니다.

응답은 updated/cached/unavailable/failed/skipped/deferred와 사유를 구분한다. provider 실패·미제공은 최근 정상 수치·관찰시각을0이나 새 시각으로 덮지 않는다. 캐시 freshness·최근 확인 시각·과거 정상값을 분리하고, 실행 중 개인 API 키 버전이 바뀌면 옛 결과 반영을 차단한다.

<a id="section-2"></a>

## 역할 요약

개인 profile GET은 dealer/support 요약과 실제 개인 표시 설정을 읽는다. 역할 PUT은 해당 역할의 expected_version·ownership/lifecycle revision을 검사하고 반대 역할을 바꾸지 않는다. 미저장은 version1과 null로 표현하고 조회에서 저장행을 만들지 않는다.

요약의 source는 `flutter_analysis`이며 서버가 게임 계산의 정확성을 인증한 값이 아니다. 십진 문자열·관찰 시각·analysis_rules_version·integrity_status·issues·관찰 lifecycle을 함께 보존한다. 이름/legacy ID나 다른 소유 수명으로 자동 복원하지 않는다. suspect·retired와 현재 claim의 쓰기 제한을 유지한다.

<a id="decisions"></a>

## 주요 결정과 근거

서버 관찰과 클라이언트 분석을 분리해 원천·오래된 값·무결성 경고를 숨기지 않는다. [전투력 수용](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166739099), [역할 요약 계약 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6193638580), [프로필 계약 원문](../../../archive/work-records/features/account/ISSUE_8_PROFILE_RESTORE_CONTRACT_DRAFT.md). 초기 문서의 P2 가상 preferences는 후속 실제 저장 구현으로 대체됐다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/me/game-accounts/{registration_id}/combat-power/refresh` |
| GET | `/v2/me/characters/{character_id}/personal-profile` |
| PUT | `/v2/me/characters/{character_id}/role-summaries/{role}` |
