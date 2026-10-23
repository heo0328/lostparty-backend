# 주차별 조회·명령과 데이터 경계

## 계약 원본

[실행 OpenAPI](../../../../openapi/two-cycle.openapi.yaml)가 현재 요청·응답·상태 코드·필수/nullable 필드의 원본이다. `two-cycle`은 실행 구성 이름이며 DB 마이그레이션 번호가 아니다. 당시 0.4.1 설계 스냅샷은 합의·재현용 기준 자료이며 이후 확장된 실행 계약 전체를 대신하지 않는다.

| 목적 | 경로 |
|---|---|
| C/N 메타·시간 정책 | GET `/v2/raid-cycles` |
| 생성 전 확인·선택 생성 | GET `/v2/me/raid-room-creation-context`, POST `/v2/raid-rooms` |
| 다음주 개방 | GET `/v2/me/raid-rooms/{room_id}/opening-context`, POST `/v2/raid-rooms/{room_id}/recruitment-openings` |
| 다음주 함께하기·불참 | GET `/v2/me/raid-rooms/{room_id}/continuation-context`, POST `/v2/raid-rooms/{room_id}/continuation-participations`, POST `continuation-declines` |
| 선택 주차 참가 취소 | GET `/v2/me/raid-rooms/{room_id}/participation-cancellation-context`, POST `/v2/raid-rooms/{room_id}/participation-cancellations` |
| 공대장 위임 | GET `/v2/me/raid-rooms/{room_id}/leadership-transfer-context`, POST `/v2/raid-rooms/{room_id}/leadership-transfers` |

## 읽기와 권한

서버 세션이 actor를 결정한다. 지속 관계·실제 주차 참가·현재 소유·그룹 공개 권한은 각각 검사한다. 날짜나 membership 이름으로 다른 참가자의 ID·자격을 만들어내지 않는다. GET은 참가·개방·예약·재개 제안을 생성하지 않는다.

context는 읽기 시점의 설명과 선택 근거다. 실제 쓰기는 현재 C/N·세대·revision·권한·활동 캐릭터·주간 점유·구성을 다시 확인한다. 주차 전환 뒤의 낡은 context를 새로운 주차의 승인으로 사용하지 않는다. 과거 ACK는 원 명령의 성공이며 현재 권한이 아니다.

## 쓰기와 원자성

C/N 생성, 선택 주차 참가·취소·위임은 최신 자격 검증과 데이터 변경·예약/점유·감사·멱등 결과 저장을 같은 업무 트랜잭션 안에서 완료하거나 전부 실패한다. 외부 HTTP를 DB 잠금 안에서 수행하지 않는다. 동일 key/body의 응답 유실 복구는 원 명령을 재전송하며, 새 사용자 결정에는 새 key를 사용한다.

명령 성공 뒤의 조회 실패를 쓰기 실패로 바꾸지 않는다. 완료된 명령을 재실행해 현재 상태를 맞추지 않고 현재 GET을 별도로 읽는다. revision/세대 충돌은 최신 context 재취득과 사용자 결정의 재확인이 필요하다. 구 명령의 body·namespace·원 효과·보관 기한을 새 명령과 섞지 않는다.

## 데이터 보존

주차별 참가·순번·공대장·예약·완료는 실제 T와 세대에 귀속된다. 주차 전환은 날짜의 의미를 바꾸는 것이며 이전 완료 기록을 새 주차에 복사하지 않는다. 취소로 현재 권한을 정리해도 과거 완료 snapshot·감사와 다른 T의 자료는 보존한다. 재참가에서 옛 기록 식별자가 새 쓰기 권한이 되지 않도록 현재 관계와 종료 관계를 분리한다.

과거 단계의 추가 migration·shadow 후보·서버 미반영 여부는 현재 실행 방법이 아니다. 실행 환경·이행·복구 경계는 공통 개발·운영의 최신 안내가 담당한다.

## 오류 처리와 소비

잘못된 엄격 입력은400, 앱 인증 실패는401, 권한 부족은403, 자원 접근 불가는 해당 API의404, revision·현재 세대·멱등 충돌은 해당409를 구분한다. 모든409를 자동 재시도로 취급하지 않는다. 정확한 오류 code와 헤더·원 ACK 기한은 실행 OpenAPI와 공통 명령 처리 기준을 따른다.

[기능 설명](README.md) · [결정 근거](decisions.md)
