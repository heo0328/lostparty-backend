# 관계 정리 명령의 계약·호환 경계

<a id="section"></a>

## 명령군

| 명령군 | context/쓰기 | 보존할 차이 |
|---|---|---|
| 개인 완료후 탈퇴 | personal-completion-departure-context / personal-completion-departures | 선택 raid 완료+본인T 다른 active 정리. 남는 실제 관계가 있는데 적격 후계자가 없으면 SUCCESSOR_UNAVAILABLE로 전체 거절. |
| 동일회원 추방 | member-removal-context / member-removals | source 실제CM·현재만/양T 옵션별 token. both 불가를 다른 동작으로 대체하지 않음. |
| 일반 탈퇴·해산·복구 | membership-action-context / membership-actions | leave_target/leave_all/dissolve_led_targets/recover_leadership. 새 전용 Context/Result·선택 영향 검증. |
| 기존 명령 | participation-cancellations, leave/end/removals 및 v1 경로 | 기존 입력·효과·namespace·ACK·보관 기한을 유지. |

정확한 path와 required/nullable·상태코드는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 따른다. 위 문자열은 경로 suffix 설명이며 새 endpoint를 뜻하지 않는다.

<a id="section-2"></a>

## 동의와 영향

새 Context의 입구는 활성 지속Member다. 각 옵션은 현재 actualT의 actor·target·leader·검토 상태·영향을 독립 계산한다. 선택 옵션의 token은 해당 영향과 기대 상태를 결합하며 단순 토큰 발급시각 갱신과 동의 내용 변경을 구분한다.

명령 입력6필드는 expected_cycle_key/view_cycle_key/actor_membership_id/expected_actor_membership_revision/action/context_token이다. 원 명령의 Idempotency-Key와 본문/token을 pending에 고정한다. 재송에 현재 context를 새로 받아 원동의를 교체하지 않는다. 새 선택은 새로운 동의·key를 사용한다.

선택 영향 집합과 권한을 전부 검증한 뒤 C→N 순서로 처리하고 최종 주차·만료·감사·ACK까지 한 트랜잭션이다. room/Member/CM/members/leadership의 자원별 equal/increase/exact_after 및 plan/target 증가 규칙은 계약과 전용 Result의 실제 값으로 검증한다. 모두 같은 +1이라고 단순화하지 않는다.

<a id="section-3"></a>

## 자기 탈퇴와 추방

새 일반 탈퇴는 본인 source·점유 정리가 증명되면 후계자의 부적격 때문에 막지 않는다. 적격 후임이 없고 관계가 남으면 review/null 리더를 남길 수 있다. GET/worker가 자동 복구하지 않고 명시 복구POST가 현재 자격을 검사한다. 기존 개인완료후탈퇴의 거절 정책을 변경하지 않는다.

추방 current_only는 source의 실제CM/양수generation/점유 근거가 확정된 review 대상을 정리할 수 있다. 반대T의 무관 변경을 선택 동의에 강제로 결합하지 않는다. both는 양T 정상 관계·권한·대상 조건을 모두 검사하고 하나라도 실패하면 양T 모두 변경하지 않는다.

<a id="status"></a>

## 기록·소비 상태

관계 종료 뒤 자기 기록은 본인 membership+CM anchor와 opt-in reader_profile로 읽는다. 새 참가가 과거 기록의 쓰기 권한을 얻지 않는다. 오래된 ACK는 현재 상태·현재 권한이 아니다. command 성공과 후속 refresh403/404는 별개이며 성공을 재송해 현재 자료를 다시 맞추지 않는다.

[새 계약·기록 보완](../../../archive/work-records/features/recruitment/contracts/ISSUE_25_CONTRACT_REVIEW_V2.md), [실제 개발 반영](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996), [Flutter A만 완료·B/C 미완료](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371981415).

[기능 설명](README.md)
