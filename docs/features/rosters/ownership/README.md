# 장비 소유 인증·소유권 분쟁

서버가 실제 장비 관찰을 확인해 소유 인증을 진행하고, 타인 소유 원정대에는24시간 소유권 도전·방어·최종 이전을 별도 상태로 처리한다.

<a id="behavior"></a>

## 현재 동작

1. V2 미리보기와 proof 생성으로 관찰 대상·회원·키 버전·시각·기대 상태를 고정한다.
2. 서버가 장비 해제 관찰의 범위·대상·유효성을 검사한다. 클라이언트가 verified/owner를 보내는 방식으로 확정하지 않는다.
3. 현재 본인 소유에는 중복 인증을 차단하고 같은 회원 재등록 연결은 별도로 처리한다. 타인 대상의 장비 확인 성공은 즉시 소유 이전 완료가 아니다.
4. proof·진행 분쟁 목록에서 ID를 모르는 새 기기도 현재 상태를 찾는다. 과거 원 ACK와 현재 상태 조회는 분리한다.
5. 유효 도전·방어·만료·settle 조건에 따라 서버 worker/명시 명령이 최종 상태를 판정한다. 이미 성립한 사건의 순서와 원자성을 보존한다.

<a id="section"></a>

## 분쟁과 데이터 경계

24시간 도전·회원별 동시 최대3건·선택 방어/일괄 방어 등의 정확한 조건은 실행 계약과 보존한 기술 계약을 따른다. 다른 유효 캐릭터로 방어할 수 있는 경계와 특정 관찰 proof의 고정 대상을 혼동하지 않는다.

소유 이전 때 과거 회원의 개인 설정·분석·완료·파티 snapshot을 새 회원에게 복사하지 않는다. 현재 참가 영향이 확정되지 않으면 `PARTY_IMPACT_REVIEW_REQUIRED` 등 검토 상태를 유지한다. 서버 V2 구현과 Flutter 분쟁 실기기 결과 인수는 별개이며 자동정리·자료 삭제는 미완료/별도 승인 범위다.

<a id="decisions"></a>

## 주요 결정과 근거

소유 증거 확인과24시간 권리 이전을 분리해 오인 소유권 이전을 막고 방어 기회를 제공한다. [V2 기술 계약](../../../archive/work-records/features/ownership/ISSUE_8_OWNERSHIP_DISPUTE_V2_CONTRACT.md), [Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245920315), [Flutter 후속 인수 보류 유지](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/me/game-account-verifications` |
| GET | `/v1/me/game-account-verifications/{challenge_id}` |
| DELETE | `/v1/me/game-account-verifications/{challenge_id}` |
| POST | `/v1/me/game-account-verifications/{challenge_id}/confirm` |
| POST | `/v2/game-accounts/preview` |
| POST | `/v2/me/game-account-verifications` |
| GET | `/v2/me/game-account-verifications` |
| GET | `/v2/me/game-account-verifications/{proof_id}` |
| POST | `/v2/me/game-account-verifications/{proof_id}/confirm` |
| POST | `/v2/me/game-account-verifications/{proof_id}/cancel` |
| GET | `/v2/me/ownership-disputes` |
| GET | `/v2/me/ownership-disputes/{dispute_id}` |
| POST | `/v2/me/ownership-disputes/{dispute_id}/cancel` |
| POST | `/v2/me/ownership-disputes/{dispute_id}/defenses` |
| POST | `/v2/me/ownership-disputes/{dispute_id}/settle` |

## 소유 이전의 그룹·레이드 후처리 검토

사용자 요청으로 [분쟁 영향 연결·정리/복구 정책 검토](dispute-impact-review.md)를 진행한다. 관계를 식별할 원본은 있으나 활성참가의 이전 후처리는 현재보류다. 새 탈퇴/복구/경고 계약은 미합의·미구현이며 현재원본/실자료는 변경하지 않는다.
