# 전투력·역할별 분석 요약

역할별 분석은 서버가 수집·검증·계산한 최신 summary/detail head 하나를 사용한다. 일반 전투력 관찰 캐시는 원정대 표시의 별도 관찰 자료이며 역할 분석의 과거 성공값 fallback으로 쓰지 않는다.

[Issue55 확정 계약](analysis-refresh-contract.md)에 따른 Backend 로컬 구현·자동 회귀 검증을 완료했다. [구현/검증·실제 적용 경계](server-processing-implementation.md)가 최신 원본이며 실제 개발/운영 서버는 아직 이전 이미지다.

<a id="section"></a>

## 전투력 관찰

본인 원정대의 요청 대상 전체를 먼저 검증한 뒤 외부 profiles를 배치 조회한다. 범위 밖 대상이 있으면 외부 호출/부분 저장을 시작하지 않는다. 현재 기본 수집 하한1700은 수동 활동 선택의 하한이 아니다.

응답은 updated/cached/unavailable/failed/skipped/deferred와 사유를 구분한다. provider 실패·미제공은 최근 정상 수치·관찰시각을0이나 새 시각으로 덮지 않는다. 캐시 freshness·최근 확인 시각·과거 정상값을 분리하고, 실행 중 서버 키 세대이 바뀌면 옛 결과 반영을 차단한다.

<a id="section-2"></a>

## 역할 요약

개인 profile GET은 dealer/support의 저장 요약·상세와 실제 개인 표시 설정을 읽는다. 분석 POST는 서버가 감지한 역할의 expected version·ownership/lifecycle revision을 검사하고 반대 역할을 바꾸지 않는다. bootstrap은 요약만 포함한다. 미저장은 version1과 null이며 GET은 외부 호출·저장행을 만들지 않는다.

요약 source=`server_analysis`, trust=`server_computed`이며 공급자의 분석 보증을 뜻하지 않는다. 성공한 낮은 값·source 미제공null·세팅error를 최신값으로 저장하고 통신/형식/역할 실패만 head를 보존한다. 십진 문자열·관찰 시각·analysis_rules_version·integrity_status·issues·관찰 lifecycle을 함께 보존한다. 이름/legacy ID나 다른 소유 수명으로 자동 복원하지 않는다. suspect·retired와 현재 claim의 쓰기 제한을 유지한다.

<a id="decisions"></a>

## 주요 결정과 근거

최신 역할 head·무결성 경고와 과거 입장 snapshot을 구분한다. 아래 계약은 전환 전 이력이다. [전투력 수용](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166739099), [역할 요약 계약 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6193638580), [프로필 계약 원문](../../../archive/work-records/features/account/ISSUE_8_PROFILE_RESTORE_CONTRACT_DRAFT.md). 초기 문서의 P2 가상 preferences는 후속 실제 저장 구현으로 대체됐다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/me/game-accounts/{registration_id}/combat-power/refresh` |
| GET | `/v2/me/characters/{character_id}/personal-profile` |
| POST | `/v2/me/character-analysis/refresh` |
