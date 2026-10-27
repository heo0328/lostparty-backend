# 원정대 등록·복원·목록 갱신

사용자가 게임 원정대를 조회·등록하고 현재 소유와 별도로 등록 관계·메인 원정대·캐릭터 목록을 관리한다. 앱 로그인만으로 등록을 생성하지 않는다.

<a id="behavior"></a>

## 현재 동작

미리보기는 입력 캐릭터로 원정대 목록을 확인하는 단계다. 등록·소유 인증·활동 선택은 각각 별도 상태다. 본인 등록 목록·캐릭터 조회는 서버 저장 자료를 읽고, 외부 목록 갱신은 명시 명령과 [개인 API 키](../../login-account/api-keys/README.md)를 사용한다.

등록 해제는 본인의 등록 관계 정리이며 게임 데이터·다른 회원 자료·완료 기록을 삭제하는 명령이 아니다. 같은 회원·원정대·소유 수명의 재등록에서는 합의된 저장 설정을 다시 연결할 수 있지만 다른 회원·새 canonical 캐릭터에 권한이나 설정을 자동 승계하지 않는다.

본인 목록 갱신은 정상 관찰한 roster를 반영하고 등록/roster revision을 갱신한다. 소유 인증 시각이나 ownership revision을 임의로 새 인증 성공처럼 바꾸지 않는다. 새 캐릭터를 발견했다고 활동/대표를 자동 저장하지 않는다. 기존 선택은 보존하고 사용할 수 없는 대상은 재구성 필요 상태로 구분한다.

<a id="section"></a>

## 식별·실패

입력의 ASCII 영문 대소문자를 유일한 공식 API 이름으로 해석하는 경계와 서버·고정대상·UUID·소유/claim 비교의 exact 경계를 구분한다. 이름만으로 캐릭터를 합치거나 저장 ID를 재작성하지 않는다.

일시적 HTTP 실패·부분 응답·목록 누락을 완전 소멸·자동 소유 이전으로 해석하지 않는다. 확실하지 않은 상태는 suspect/검토로 유지한다. 현재 소유·인증은 [소유권](../ownership/README.md), 이름·캐릭터 수명은 [생명주기](../lifecycle/README.md)를 따른다.

<a id="decisions"></a>

## 주요 결정과 근거

등록·조회와 실제 소유 증거를 분리해 단순 API 검색이 쓰기 권한을 만들지 않게 한다. [원정대 계약 수용](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616), [목록 갱신 원문](../../../archive/work-records/features/ownership/ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md). 초기 live 인증 보류 기록은 현재 구현 전체의 미구현 상태를 뜻하지 않는다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/game-accounts/preview` |
| GET | `/v1/me/game-accounts` |
| POST | `/v1/me/game-accounts` |
| PATCH | `/v1/me/game-accounts/{registration_id}` |
| DELETE | `/v1/me/game-accounts/{registration_id}` |
| GET | `/v1/me/game-accounts/{registration_id}/characters` |
| POST | `/v1/me/game-accounts/{registration_id}/refresh` |
