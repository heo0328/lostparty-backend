# Issue #13 W4-B — 현재주 완료·정정·명시 재개

2026-10-22 / `feat/raid-recruitment` / 시작 `ef25c38` / 구현·격리 검증 완료, 구현 `0d8b58111356b69d817b23b154a56efb64c974f9` commit/push·실제 원격 SHA 확인·[전체87번째 Backend · W4-B 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6319271776) 게시 완료.

기준은 [전체86번째 Backend · W4-A2](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6316089641), [계약4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md), 고정 전체 명세0.4.1/policy two-cycle-contract-4다. 사용한도 때문에 중단된 로컬 변경과 전용 검증 컨테이너를 보존한 채 이어서 진행했다. 재개 시 Issue 본문·전체86댓글을 다시 확인했고 새 요청/계약 변경은 없다.

## 구현 구간

| 후보 동작 | 처리 |
|---|---|
| GET `/v2/raid-rooms/{room_id}/command-context` | 실제 T 참가자의 완료/미완료 종료 영향·권한·120초 불투명 context |
| POST `/v2/raid-rounds/{round_id}/personal-completion` | 본인 item 완료·해당 Assignment 예약/lease만 해제, 남은 item 시각 보존 |
| POST `/v2/raid-rounds/{round_id}/completion` | 실제 T 공대장 권한·해당 Round 미완료 참가자 완료, 기존 개인 완료 보존 |
| POST `/v2/raid-rooms/{room_id}/weekly-incomplete-closures` | 함께하기 ON·실제 C 관계의 현재 미완료 round/assignment·남은 타임 종료 |
| POST `/v2/raid-rooms/{room_id}/weekly-resume-proposals` | 중단 source/revision·새 일정 의도 고정, 현재주 명시 재개 제안 |
| PUT `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion` | C 수요일10시 이후 본인 수동 완료/정정; party 완료와 현재 점유 보존 |

기존 POST `/v2/raid-schedule-proposals/{proposal_id}/responses`는 일반 일정 제안과 재개 제안을 정확한 내부 귀속으로 분기한다. 명시 재개는 N cancelled 세대의 reopen과 다르며, 같은 실제 C/RoomCycle 세대에서 중단 Round를 새 UUID/Round로 대체하고 새 Assignment/세션·동의 구간을 만든다. 옛 Round/Assignment·예약·제출/동의·투표 원천을 되살리지 않는다. 완료된 item과 개인 완료 이력은 재개 대상에서 제외하고 원래 round/자리를 formation_history에 남긴다.

완료·수동 체크/false 정정·재개는 T=C AND DB now≥수10시이며 N·06~10시를 거절한다. 완료 context는 실제 CM/리더·target/plan/members/room·Round/Assignment/원장/예약/세션·settings를 서명에 결합한다. 쓰기는 target CAS·현재 영향과 context 만료를 다시 확인하고 최종 DB 시각/원 ACK까지 한 transaction이다. 원 성공 ACK는 주차/권한·현재 자격 재검사보다 먼저 복구한다. GET는 REPEATABLE READ/READ ONLY이며 보존 원천을 만들거나 재개를 적용하지 않는다.

C의 마지막 개인 완료나 전체 미완료 종료로 persistent 관계·N을 종료/가입하지 않는다. completed/stopped 실제 관계의 조회·C 리더 위임·N 소스 특례를 유지하되 실제 자격을 검사한다. 재개는 N1 별도 명시 응답·N2=2/N3·4=2/N5·6=3/N7·8=4 정족수를 사용한다. 적용 시 모든 실제 대상의 현재 자격/완료·점유·좌석을 재검사하고, 수락자만 명시한 새 수동 일정에 새 동의/예약을 기록한다. 미동의자의 새 시간 예약은0/확인 대기다. 개인 제출표는 이전 source를 보존해 정리하고 자동 복원하지 않는다. 조율형은 새 명시 제출이 있어야 초기 조율을 진행한다. C 재개 일정에서 제외된 전역 완료 item은 N의 전체 묶음 복사 시 캡처한 설정 순서로 보완하며, 복사 자체로 N 확인/예약을 만들지 않는다.

## 저장·기존 호환 경계

shadow `0029_cycle_outcomes`는 불변 CycleOutcome·CycleResume2표를 추가한다. 기존 모든 행/열·기록시각을 이행 전후 지문으로 대조한다. 재개 source는 기존 CycleProposal/CM revision별 CycleVote 소유 FK와 결합하며 제안/원 source·적용 전 세대 상태/시각·적용 투표 집합·이전 제출표를 보존한다. 내부 current Round link만 교체하고 이전 Round/Assignment 행을 재활성화하거나 시간을 덮지 않는다.

개인 부분 완료 뒤에도 남은 활성 Assignment의 세션 확인/제안·정족수/예약을 계산한다. 완료 item 때문에 남은 타임을 앞당기지 않으며, 다른 사람/다른 item/다른 T 예약과 기존 수동/party 완료 원천을 지우지 않는다. 기존 0023 API·worker 활성 guard는 그대로 유지하고 shadow0029와 혼용하지 않는다. 신규 후보는 전체42경로/45동작이며 main 미등록이다. 실행 OpenAPI116경로·실제 개발 DB/API 이미지·서버는 유지한다.

## 검증 기록

전용 `lostparty-w4b-test` tmpfs PostgreSQL/제한 LOGIN과 cached 검증 이미지의 `lostparty-w4b-runner`에서 합성 자료로만 검증한다. 최종 관련 10개 파일은 **132PASS/1081.82초**다. 신규 W4-B26사례를 포함하며 예비 실행과 중복 합산하지 않는다. 이전 UI 종료로 최종 출력이 유실되어 동일 묶음을 다시 실행했고, 이번 최종 로그/종료 코드를 확인했다. 전용 검증 컨테이너와 tmpfs 시험 DB는 완료 후 정리했다.

고정53경로/56동작/204schema·84합성/CAS6쌍/endpoint흐름2개 검증을 통과했다. canonical SHA256 `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`은 불변이다. 생성 DTO/검증 사용본 SHA256 `7abfb96a98258ab3ca2eda340f5458dbe1fd44fa3a9499f58e68e5071a0ff3a6` 바이트 일치, 현재 실행 FastAPI/원본116경로 전체 일치·후보 미등록도 확인했다. 캐시 이미지의 구 계약 파일 때문에 최초 대조가 실패해 저장소 원본을 동기화하고 재확인했으며 원본 계약을 임의 변경하지 않았다.

초기 검증 중 표시용 server_time을 상태 보존 비교에서 제외했고, DB에 없는 session state completed를 기존 finished/cancelled로 보완했다. 부분 개인 완료 후 재개 때 완료 Assignment까지 입장시키던 경로는 중단된 본인 item만 사용하도록 교정했다. DB 제약이나 완료/모집 조건을 완화하지 않았다. 예비12PASS 등 중복 실행은 최종 고유 통계에 합산하지 않는다.

실제 서버/provider·실회원·기기/운영 성능·Flutter 적용/인수는 미검증이다. 이번은 후보 소스 구간이며 새 Flutter 서버 시험·merge·배포·실제 DB 이행을 요청하지 않는다.

## 다음 담당

다음 Backend는 **W4-C T 설정/편성/제외와 G1 공통 설정·GlobalScope/원 ACK·전역 leave/end**다. 고정 명세의 T settings GET/PUT·formation PUT·removals POST4동작과 G1 common-context GET/common-settings PUT/leave·end POST4동작을 연결한다. legacy continuation-choices GET은 W4-D의 보존 projection과 함께 처리한다. 기존 C가 closed/review여도 N 리더로 G1 권한을 메우지 않고, context의 전체 실제 영향·persistent CAS에 맞춰 원자 정리한다. 이후 W4-D 06worker/v1·legacy review·declined summary·활성화 검증과 W5 통합/성능·실제 인계가 남는다. 같은 계약의 재검토나 추가 제품 입력 대기는 없다.
