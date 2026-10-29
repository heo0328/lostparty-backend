# 현재주·다음주 모집 관리

하나의 모집방에서 현재주와 다음주의 참가·일정을 별도로 관리한다. 방이 유지된다는 사실과 특정 주차에 실제 참가한다는 사실은 다르다. 현재 동작은 이 문서와 [계약·처리 경계](contract.md)에서 확인하고, 정책 선택 이유는 [결정 근거](decisions.md)에서 확인한다.

[그룹 최초 연결·목록 표시 후속](../../groups/raid-link-contract.md)은 기존 생성/공통설정 명령을 재사용한다. 후보 구현·검증과 실제 개발반영을 구분한다.

## 베타 최신 보완

베타 생성·개방은 각 T의 기본 출발을 UTC 정수분으로 받는다. 실제 T 참가 때 개인표 복사와 기본 약속 예약을 같은 거래에서 저장하고, 전역 번호/5자리 비밀번호는 해당 T의 현재 참가 권한에만 제공한다. [베타 계약](beta-contract-wire.md)·[명시 분 구현](explicit-minute-departures.md).

활성방 한도는 서버 C/N의 유효한 실제 참가 방 ID 합집합이다. 같은 방 양주차는1개, 과거/관계전용은 제외하고 유효한 현재 review는 포함한다. 시작 시간 경과만으로 참가가 끝나지 않는다. [공통 한도 판정](active-usage-and-wait-implementation.md).

<a id="section"></a>

## 용어와 식별

| 용어 | 의미 |
|---|---|
| 방·지속 회원 관계 | 주차를 넘어 남을 수 있는 모집방과 회원의 관계. 실제 모든 주차의 참가를 뜻하지 않는다. |
| 현재주 C·다음주 N | 서버가 계산한 실제 주차. 화면의 상대 이름이며 API에는 실제 `target_cycle_key`를 사용한다. |
| 주차별 참가 | 특정 방·실제 주차·세대에 연결된 캐릭터 묶음과 참가자. 권한·예약·완료 판단의 단위다. |
| generation | 같은 주차를 재개방할 때 과거 참가·완료·명령과 새 참가를 구분하는 세대. |
| 주차별 공대장 | 해당 실제 주차의 관리 주체. 지속 회원·그룹장이라는 사실만으로 권한을 얻지 않는다. |

<a id="behavior"></a>

## 현재 동작

1. 서버 주차 메타에서 실제 C/N과 시각별 허용 조건을 읽는다. 클라이언트 날짜나 이전 화면의 C/N을 명령 권한으로 사용하지 않는다.
2. 생성 context에서 주차와 현재 자격을 확인한 뒤, 사용자가 선택한 C/N을 하나의 생성 명령으로 확정한다. 두 주차를 선택했으면 일부만 생성하는 성공을 허용하지 않는다.
3. 열린 주차는 해당 T의 참가 context와 조회·신청·승인을 사용한다. 다른 T에 참가했다는 사실만으로 이 T의 실제 참가·예약이 생기지 않는다.
4. 다음주가 없으면 명시 개방을 사용한다. 유효한 현재주 참가자의 ‘다음주 함께하기’도 context와 명시 명령으로 다음주 참가를 확정한다. 단순 설정값이나 목록 조회는 동의가 아니다.
5. 수요일 06시 기존 N이 C로 바뀌어도 같은 주차 ID·세대·참가·예약을 이어간다. 새 N을 자동 생성하거나 과거 인원을 자동 가입시키지 않는다.
6. 주차별 취소·위임은 대상 T의 현재 상태와 권한을 다시 검사한다. 다른 T의 참가·일정·완료를 함께 지우지 않는다.

<a id="section-2"></a>

## 취소·공대장과 다른 주차 보존

다음주 참가 취소는 해당 주차의 참가와 미완료 예약을 정리한다. 유효한 순번·자격의 후임이 있으면 자동 승계하며, 마지막 참가자 취소는 그 미래 주차만 종료한다. 방의 지속 관계가 없어졌거나 다른 주차까지 종료됐다고 추정하지 않는다.

현재 일반 탈퇴·모두 탈퇴·본인이 리더인 주차 해산은 별도 원자 명령을 사용한다. 과거 ‘전역 마지막 1인 종료’ 제한을 새 명령의 제한으로 옮기지 않는다. 새 명령의 선택 옵션·영향 미리보기·후계자 없음·기록 접근은 모집 안내의 탈퇴·해산 기능에서 설명한다. [최신 구현 근거](../../../archive/work-records/features/recruitment/development/ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md).

<a id="constraints"></a>

## 비활성 기능과 범위

이번주 미완료 종료와 **같은 주차** `weekly_resume`는 앱 활성 기능에서 제외됐다. 기존 서버 endpoint·권한·stopped/제안/완료 이력과 원 pending/최대24시간 ACK 복구는 보존한다. **다음주** 명시 개방/`reopen`, 공대장 `recover_leadership`과 서로 다르다. 공대장 복구의 제품 UX는 승인 전 제안이다. [비활성 보존 기준](../completion-and-records/inactive-features.md).

검색·그룹 필터, 상세 일정 조율, 완료 정정, 서버 이행은 주차 관리와 연계되지만 각각 독립 기능/운영 문서가 담당한다. 이 묶음을 단순히 ‘두 주차 생성 기능’으로 해석하지 않는다.

<a id="status"></a>

## 상태와 확인 범위

Backend 주차 관리와 후속 검색·탈퇴 명령은 개발 API에 반영됐다. Flutter의 개별 연결 보고·합성 자동 시험과 실제 회원 명령·기기 인수는 구분한다. 현재 담당·미완료는 [NEXT_WORK](../../../project/NEXT_WORK.md)가 원본이다. 이 문서 작업에서 서버·DB·앱을 실행하거나 변경하지 않는다.

[모집 안내](../../../archive/work-records/features/recruitment/README.md) · [실행 계약](../../../../openapi/two-cycle.openapi.yaml)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/raid-rooms/{room_id}/continuation-choices` |
| PUT | `/v1/me/raid-rooms/{room_id}/continuation-choices` |
| PUT | `/v1/raid-rooms/{room_id}/continuation-settings` |
| POST | `/v1/raid-rooms/{room_id}/recruitment-openings` |
| POST | `/v1/raid-rooms/{room_id}/transfer-leadership` |
| GET | `/v2/me/raid-rooms/{room_id}/continuation-context` |
| POST | `/v2/raid-rooms/{room_id}/continuation-participations` |
| POST | `/v2/raid-rooms/{room_id}/continuation-declines` |
| GET | `/v2/me/raid-rooms/{room_id}/opening-context` |
| POST | `/v2/raid-rooms/{room_id}/recruitment-openings` |
| GET | `/v2/me/raid-rooms/{room_id}/participation-cancellation-context` |
| POST | `/v2/raid-rooms/{room_id}/participation-cancellations` |
| GET | `/v2/me/raid-rooms/{room_id}/leadership-transfer-context` |
| POST | `/v2/raid-rooms/{room_id}/leadership-transfers` |
| GET | `/v2/me/raid-rooms/{room_id}/continuation-choices` |
