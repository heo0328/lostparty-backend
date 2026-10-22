# Issue #13 W4-C — 주차별 관리·공통 설정·전역 정리

2026-10-22 / `feat/raid-recruitment` / 시작 `88dcb3b` / 구현·격리 검증 완료, 구현 `babb25b8599fb3564fec59bae13a690e2f53d5b6` commit/push·실제 원격 SHA 확인·[전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057) 게시 완료.

기준은 [전체87번째 Backend · W4-B 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6319271776), [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[공통 ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), 고정 명세0.4.1/policy two-cycle-contract-4다. 착수 시 Issue 본문·전체87댓글과 Git을 조회했으며 추가 요구/계약 변경·원격 충돌·사용자 미커밋 변경은 없었다.

## 구현 범위

| 동작 | 권한·효과 |
|---|---|
| GET `/v2/me/raid-rooms/{room_id}/settings` | 명시 actual T의 설정·리더·권한, persistent 관계 기반 읽기 전용 |
| PUT `/v2/raid-rooms/{room_id}/settings` | 해당 T open·실제 리더/현재 자격·target/room/settings/leadership CAS, T 설정 snapshot만 변경 |
| PUT `/v2/raid-rooms/{room_id}/formation` | 해당 T의 활성 Assignment 전체 자리와 CM revision 검증; 원자 자리 교환, 완료 이력/예약 시각·다른 T 보존 |
| POST `/v2/raid-rooms/{room_id}/removals` | 실제 T 리더·대상 CM 귀속/수정 CAS; 본인/리더 제외 거절; 해당 T만 정리하고 persistent/다른 T 보존 |
| GET `/v2/me/raid-rooms/{room_id}/common-context` | target query 없는 GlobalScope·persistent CAS·120초 불투명 context·실제 영향0~2 |
| PUT `/v2/raid-rooms/{room_id}/common-settings` | G1+room/연결그룹 CAS·전체 영향 context; title/scope만 변경; no-op 영향[]·room revision 유지 |
| POST `/v2/raid-rooms/{room_id}/leave` | 열린 T의 리더 위임 미해결이면 거절; 확인한 C/N 실제 참가와 persistent 관계·한도1room 원자 정리 |
| POST `/v2/raid-rooms/{room_id}/end` | G1·전체 persistent 마지막1인·다른 T 실제 참가자 없음; 허용한 현재/미래 정리·완료 보존 |

T 제외는 원 Assignment/제출·동의/예약 근거를 ParticipationEvent에 보존하고 CM을 removed로 기록한다. 과거 완료 Assignment의 원장/자리/source는 수정하지 않는다. 남은 실제 참가자의 일정 제안 정족수/새 확인 구간을 재평가하며 미동의자의 예약을 되살리지 않는다. 편성 중 immediate 자리 index를 해제하는 임시 left 상태는 같은 transaction 안에서만 존재하고 weekly lease를 해제하지 않는다.

공통 권한 G1은 C 행이 없을 때만 N을 사용한다. closed/completed C는 현재 자격이 유효하면 해당 실제 리더의 관리 권한을 유지하고, review C나 현재 권한 부재를 N 리더로 메우지 않는다. GlobalScope에는 target/세대/CAS를 꾸며 넣지 않는다. 전역 탈퇴의 영향0은 합법적이며, 취소된 N의 과거 행이나 완료 C를 탈퇴 효과로 재작성하지 않는다. 다른 참가자의 전역 탈퇴 후 완료 C 리더가 남으면 completed 세대/리더 근거를 보존한다.

context는 명령/actor·room·persistent·실제 C/N의 target/members/plan/leadership·현재 CM/회원 상태·Assignment/원장/lease·참여/예약/신청·연결그룹·관리 자격을 결합한다. GET는 REPEATABLE READ/READ ONLY다. 명령은 현재 영향/권한·만료를 재검사하고 전체 효과·원 ACK를 한 transaction으로 저장하며, 최종 주차/만료·새 일정 시각도 확인한다. 원 성공 ACK는 새 주차/권한/context 재검사보다 먼저 복구한다. 공통 no-op/설정·편성 no-op은 관계/원장/예약을 쓰지 않는다.

## 저장·실행 경계

신규 DDL 없이 shadow0029의 기존 복합 FK/불변 ParticipationEvent·원 ACK 저장소를 사용한다. 원본 실행 OpenAPI116경로·main 미등록 경계와 기존 v1/worker의0023 활성 guard를 유지한다. 후보는50경로/53동작이며 남은 고정 동작은 W4-D legacy continuation-choices GET1개다. main의 주차/summary2동작과 합쳐 전체56동작을 추적한다. 고정 명세53경로/56동작/204schema와 canonical SHA `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`을 변경하지 않는다.

## 검증·다음 담당

전용 `lostparty-w4c-test` tmpfs PostgreSQL/제한 LOGIN·격리 앱·합성 자료의 최종 관련6파일은 **고유98PASS(25+26+47 분리 실행, 마지막47PASS/374.96초)**(신규 W4-C27개 포함), 수정 후 실행의 종료 코드0을 확인했다. 주차별 권한/CAS·부분 완료/재개 후 자리/제외·N/persistent 보존·정족수 재평가, C 부재/closed/review의 G1, 영향0·quota 회복, 연결그룹 CAS·권한403, 두 T 처리 실패/최종 주차·만료 rollback·중복 동시요청/원 ACK, 8개 HTTP 경로의 고정 요청/응답 schema·엄격 입력/no-store를 검증했다. 앞선9PASS·16PASS는 최종 통계와 합산하지 않는다. 초기 common 조회의 모델 참조 누락을 수정했고, N-only 테스트 입력을 체크박스 context와 일치하도록 고쳤다. 마지막 연결그룹 시험은 준비 자료의 그룹 회원 부재로 실패해 실제 그룹 생성 명령을 사용하도록 fixture를 수정했다. 이어 nullable Version 값 객체를 정수와 직접 비교하던 정상 그룹 CAS 오류를 찾아 직렬화된 정수 값 비교로 수정했다. non-null 그룹 revision 수정에 영향 없는 앞선25PASS·수정 후26PASS와 남은 회귀를 분리 실행했으며 전체 단일 실행 PASS로 표현하지 않는다. 기존 BlockingPortal deprecation 외 최종 미해결 실패 없음.

고정84합성/CAS6쌍/공통ACK2흐름·canonical SHA 불변과 실행 main FastAPI/원본116경로 전체 일치, 후보50경로/53동작 미등록을 확인했다. datamodel-code-generator0.86.0 재생성/사용 DTO 바이트 일치·SHA256 `125056d7ba0ace6fe769d5a2c46fcf4093a659c999fe6851228b849d1af18f7c`다. 전용 시험 컨테이너/임시 tmpfs DB는 완료 후 정리했다. 실제 개발 DB/API 이미지·서버/provider·실회원·기기·Flutter 적용/운영 성능은 이번 구간에서 변경·검증하지 않는다.

다음 Backend는 **W4-D**: legacy 함께하기 조회 보존 projection·06worker/v1 adapter·legacy review/declined summary·활성화 검증이다. 이후 W5 전체 실행 계약·통합/성능·소비 가능 구간의 실제 인계가 남는다. 신규 후보 소스 게시만으로 Flutter 새 서버 시험을 요청하지 않는다. 원본 RoomSettings를 target 설정으로 읽는 옛 adapter는 전환 검증 전까지 실행하지 않는다.
