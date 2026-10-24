# 캐릭터 식별·생명주기

현재 캐릭터 ID·이름 점유·관찰 상태와 과거 수명을 구분한다. 이름이 같다는 이유로 다른 캐릭터·회원의 소유·설정·모집 자리를 연결하지 않는다.

<a id="behavior"></a>

## 현재 동작

서버의 canonical UUID와 NameClaim·ownership/lifecycle revision을 기준으로 현재 사용 가능성을 판정한다. 현재 상태와 퇴역 이력은 별도 조회다. suspect의 기존 저장 자료를 읽는 것과 신규 사용·쓰기 허용은 다르며, retired/identity 충돌은 해당 권한·오류 규칙을 적용한다.

정상 본인 목록에서 새 이름은 새 canonical ID다. 개명으로 추측해 이전 UUID·빌드·대표 설정을 자동 승계하지 않는다. 단순404·네트워크 실패·부분 목록은 완전 소멸 근거가 아니므로 소유·claim을 자동 해제하지 않는다.

<a id="constraints"></a>

## 미완료·보존

확정 소멸 증거, suspect 해소/재등장, 이름 재사용·대표 대상404에 필요한 최소 계약은 생명주기 후속에서 검토 중이다. 근거가 부족한 `BindingEvidence`/`ROSTER_EVIDENCE_PENDING`을 문서 정리로 해제하지 않는다.

기존 참가 캐릭터가 사용할 수 없어져도 회원 자리를 새 소유자에게 넘기지 않는다. 기존 관계의 명시 교체·탈퇴는 [모집 참가](../../recruitment/participation/README.md)에서 처리하고 새 캐릭터에는 현재 소유 자격을 검사한다. 퇴역·과거 자료 자동 삭제나 운영 정리는 제공 완료로 표시하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

공급 API의 부재 응답만으로 동일성·완전 삭제를 증명할 수 없으므로 ID와 증거 수준을 분리한다. [공급 API 증거 검토](../../../archive/work-records/features/ownership/ISSUE_8_PROVIDER_EVIDENCE_REVIEW.md), [생명주기 후속 합의 범위](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6259126286).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v2/me/game-accounts/{registration_id}/characters` |
| GET | `/v2/me/character-retirements` |
