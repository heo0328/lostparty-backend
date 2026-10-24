# 대표·활동 선택·개인 표시

본인 캐릭터 중 사용할 활동 대상·대표와 개인 선호역할·표시 순서를 저장한다. 현재 소유 인증과 게임 레이드 입장 자격은 별도다.

<a id="behavior"></a>

## 현재 동작

활동 선택은 현재 본인 소유·사용 가능한 canonical 캐릭터를 대상으로 명시 저장한다. **1700은 최초 기본 선택 기준이며 수동 선택의 레벨 하한이 아니다.** 모집 입장레벨은 선택한 raid/difficulty에서 따로 검사한다.

대표 빠른 선택은 현재 본인 소유 메인 등록의 선택된 활동 대상을 받는다. registration/settings/ownership/roster revision을 검사하고 대표만 변경한다. 활동·configuration 상태를 자동 수정하지 않는다. 기존5분 대기 판정은 제거됐으며 현재 settings의 next_change_at은 null이다.

개인 preferences는 preferred_role/visible/display_order와 독립 version을 가진다. 미저장 기본값은 version1/null/true/null/null이며 GET은 행을 만들지 않는다. no-op도 stale version은 충돌이고 실제 변경만 version/saved_at을 갱신한다. 숨겨진 대표를 자동 표시하거나 한 캐릭터 순서 변경으로 다른 캐릭터를 재정렬하지 않는다. 원정대 표시 개수도 별도 저장 설정이다.

<a id="constraints"></a>

## 미완료·관련 기능

신규 발견/첫1700 도달의 자동추가와 사용자의 직접제외를 영속 보존하는 후속은 계약 검토 단계다. 미선택을 명시 제외로 추정하거나 신규 발견만으로 자동 선택을 승인하지 않는다. 기존 수동 선택·대표 저장 구현과 구분한다. 상세 미결정은 [활동 정책 검토](proposals.md)에 모은다.

<a id="decisions"></a>

## 주요 결정과 근거

초기 기본값과 사용자의 명시 선택을 구분한다. [수동 저레벨 선택 정책](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230281148), [대표 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184322765), [표시 저장 원문](../../../archive/work-records/features/account/ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| PUT | `/v1/me/game-accounts/{registration_id}/character-settings` |
| GET | `/v1/me/game-accounts/{registration_id}/representative` |
| PUT | `/v1/me/game-accounts/{registration_id}/representative` |
| PUT | `/v2/me/characters/{character_id}/personal-preferences` |
| GET | `/v2/me/game-accounts/{registration_id}/presentation-settings` |
| PUT | `/v2/me/game-accounts/{registration_id}/presentation-settings` |
