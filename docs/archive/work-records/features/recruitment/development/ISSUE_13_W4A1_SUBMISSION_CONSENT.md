> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [scheduling](../../../../../features/recruitment/scheduling/README.md) · [participation](../../../../../features/recruitment/participation/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #13 W4-A1 — target 제출표·명시 확인예약

2026-10-21 / `feat/raid-recruitment` / 구현 시작 `c619cef`.

기준은 [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083), [계약4판](../contracts/ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)·[공통 ACK 보완](../contracts/ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md)과 고정 전체 명세0.4.1/policy4다. 착수 시 Issue 본문·전체84댓글/Git을 재조회했고 계약 변경·신규 요청은 없었다. 다음 입력을 받기 위한 재계약 검토는 필요하지 않다.

## 완료 구간과 실행 경계

W4-A의 첫 구간인 **실제 T에 귀속한 제출표·본인 명시확인·새 예약 동의 구간**의 로컬 구현·격리 검증을 완료했다. 일정 조율/그룹 편집·후보/선택·제안/투표는 다음 W4-A2이며 W4-A 전체 완료로 보고하지 않는다. 완료/정정·공통관리·06 worker/v1 전환도 후속이다.

| 후보 경로 | 구현 |
|---|---|
| GET/PUT `/v2/me/raid-rooms/{room_id}/availability-submission` | actual T/generation/CycleMember의 제출표 조회·개인표 명시 snapshot 복사 |
| GET `/v2/me/raid-rooms/{room_id}/schedule-context` | 실제 T 참가자의 제출표/해당 주차 익명 busy, 지정 T session 제외 |
| GET `/v2/me/raid-schedule-overlaps` | 본인 실제 T의 활성 예약 겹침·표시 허용 정보·주차/세션 결합 cursor |
| POST `/v2/raid-sessions/{session_id}/participation-confirmations` | 실제 T/CM·일정/참가 CAS 재검사 뒤 본인 확인·새 예약/불변 동의 |

4경로/5동작 추가로 후보 합계31경로/34동작이다. plan의 본인 confirm 권한은 실제 같은 판정과 종료 시각을 사용한다. 이전 shadow head에서는 미준비로 남는다. 후보는 main에 미등록이며 실행 OpenAPI116경로/개발 서버·DB는 그대로다. source push를 API 공개·Flutter 인수·운영 완료로 해석하지 않는다.

## 저장·동의·보존

`0027_cycle_consents`는 불변 `recruitment_cycle_consents` 1표를 추가한다. room/cycle/generation/CM/회원/사용자와 실제 SessionParticipation/Session의 복합 FK, command/참가 revision 유일성을 검사한다. 동의에 당시 CM/참가/일정 revision·시각, 사용 Assignment의 캐릭터/역할·display/build·소유/생명주기·슬롯/시각, 제출표 snapshot과 새 예약 UUID/시간을 보존한다. 이전 기록을 새 동의로 backfill하지 않는다.

기존 `TimeReservation`의 전체 이력 `(participation_id, segment_id, schedule_revision)` UNIQUE는 제거한다. 같은 session/schedule revision에도 **이전 행을 해제 상태로 보존하고 새 UUID 행을 추가**할 수 있어야 하기 때문이다. 기존 활성 `(participation_id, segment_id)` partial UNIQUE와 정확한 소유 FK는 유지한다. DB trigger는 예약을 한 번 해제하는 변경만 허용하고 원천의 시간/귀속 변경·삭제·해제 취소를 거절한다. 불변 동의도 UPDATE/DELETE를 거절한다. 기존 모든 표의 행/열·기록시각은 이행 전후 지문으로 대조한다.

`source_models`의 전체 UNIQUE metadata는 구0023 runtime 요구로 남기며 readiness는 **0027에서만** 그 제약을 대체하고 활성 partial UNIQUE·새 이력 guard/동의 표를 검사한다. 구 API와 구 worker는0023만 활성 허용한다. 이 metadata 전환과 실제 서버 적용은 W4 후속 활성화 검증에 포함한다. 이행 downgrade로 기록을 삭제하지 않는다.

## 명령 의미

- GET은 한 RR/READ ONLY snapshot이며 없는 제출표·동의·예약·ACK를 생성하지 않는다. persistent 관계나 C 참가만으로 N 제출/시간정보를 조회할 수 없다. actual T의 참여/완료/중단 관계는 본인 제출표를 읽을 수 있고, 새 쓰기는 열린 T의 실제 참여 관계에 한정한다.
- PUT은 target/CM/제출/개인표 revision과 현재 C를 검사한다. 개인표가 없으면 거절하고 자동 개인표 생성/전 주차 복사는 하지 않는다. 성공 시 지정 T에만 복사하며 개인표 저장만으로 제출표/일정·예약을 바꾸지 않는다. 동일 개인표 source를 다시 제출하면 상태 revision을 변경하지 않는다. 제출표 갱신에 따른 초기 조율 계산은 W4-A2에서 연결한다.
- 확인은 경로 Session의 실제 T/generation과 본인 CM·활성 참여, 전체 bundle·현재 소유/활동/선택 자격·정확한 주간 lease·현재 일정/참가 revision을 검사한다. 명시확인 전 N 복사 일정·나중 참가자는 pending/예약0이다. 시각이 끝났으면 거절하며 최종 DB 시각에도 종료/06시 경계를 재검사한다.
- 시간 겹침·개인표 밖은 경고다. 경고를 배타적 예약 차단이나 자동 일정 변경으로 확대하지 않는다. 제출표가 없어도 유효한 본인 명시확인을 할 수 있다. 같은 일정에 이미 정확히 확인/예약되어 있으면 새 키도 noop이며 새 동의/예약을 만들지 않는다.
- 취소→동일 CM/Assignment/Session 재참가, 캐릭터 교체→동일 일정 재확인은 이전 예약을 덮거나 부활시키지 않는다. 새 확인은 새 UUID 예약과 새 동의 원천을 만든다. 원 동의의 캐릭터/빌드/제출표는 그대로다. W3 취소의 이전 제출표 head 정리·이벤트 보존을 유지하며 재참가 시 복원하지 않는다.
- 같은 키/불변본문의 원 성공은 현재 주차·CM 상태/일정 revision·시각 재검사 전에 복구한다. 취소 후 원 ACK 재시도는 재가입/예약 복원을 일으키지 않는다. 경합·부분 실패·마지막 마감 거절은 원자 rollback하며 새 키 자동 재시도는 하지 않는다.
- 시간 context의 타 방 정보는 시간 구간과 revision만 익명 제공한다. 본인 overlaps는 actual T/현재 세대·유효 관계/활성 예약으로 제한하며 반대 주차 자료를 섞지 않는다. cursor는 인증 세션/본인과 target·현재 C·limit·실제 예약에 결합해 변경 시 stale로 다시 조회한다.

## 검증

격리 `lostparty-w4-test` tmpfs PostgreSQL/제한 LOGIN·`lostparty-w4-runner`에서 현재 소스를 복사해 검증한다. 실제 개발 DB·API 이미지를 전환하지 않는다. 고정 명세53경로/56동작/204schema·84합성/CAS6쌍/endpoint흐름2개와 canonical hash 불변, 실제 FastAPI/원본116경로 전체일치·후보31경로34동작을 확인했다. 생성/검증 사용 DTO SHA256 `c5a1f9ef7d648ea0d7b49fc52895a3837b8fd455d987ead66997f3061498afc1` 일치다.

- 초기 핵심13PASS/114.92초. 확대 중 target가 바뀐 겹침 cursor를 기존 공용 decoder가400으로 거절하는 것을 확인해 target/현재 C를 revision에, 인증 세션을 scope에 결합하도록 보완했다. 13PASS/1FAIL/126.77초는 최종 결과에 합산하지 않는다. 테스트에서 잘못 타입을 바꾼 model_copy로 발생한 serializer warning도 정상 DTO 검증으로 교정했다.
- 서비스 최종16PASS를 확인했다. HTTP 검증은 격리 앱에 실제 main.no_store가 빠진 것을 수정한 뒤 신규 HTTP3+W3회귀30 총33PASS/253.13초다. 신규 고유19개와 W3회귀30개를 분리 실행으로 확인했으며 기존 BlockingPortal deprecation1건 외 실패/추가 경고는 없다. 추가 W2 생성/참가/조회·W1/주간 summary·v1 참가/일정/제출·계정 bootstrap/기록시각 회귀169PASS/469.02초다. 이번 고유 확인218개(신규19+회귀199)는 분리 실행의 합계이며 단일218개 실행으로 표시하지 않는다. 이전 실행은 중복이므로 합산하지 않는다. 기존 일정 생성/C 확인 fixture는 기존 구현을 사용한 준비이며 W4-A2 조율·제안/투표 구현 완료 증거가 아니다.

## 다음 Backend·게시

다음은 **W4-A2 일정 그룹 편집·후보/명시 선택·초기 조율·제안/투표**다. actual T/generation/리더·설정/기간 snapshot/제출 source·동의 구간을 함께 사용해야 한다. legacy `scheduling.reserve/evaluate_initial`의 current-week/persistent 가정을 새 v2 target 명령에 그대로 연결하지 않는다. 새 일정 revision이나 제안 수락에 따른 예약도 원 동의/해제 이력을 보존하도록 본 구간의 원천 모델과 원자 실행을 이어 쓴다.

이후 W4-B 완료/정정·현재주 재개, W4-C G1 공통·전역 관계, W4-D 06 worker/v1·legacy review·declined summary·활성화를 진행한다. 실제 서버/실회원/provider·기기/운영 성능·Flutter 적용은 미확인이다. 이번 구간은 사용자 지시에 따라 검증·문서와 함께 작업 브랜치에 commit/push·원격 확인하여 GitHub에 기록한다. merge/배포·자료 삭제는 수행 범위가 아니다.

## 게시 확인

구현 `6d2b301f8d6f5436026159b6585772aeb5df082b` / feat/raid-recruitment / push·원격 SHA 일치 확인 완료. [전체85번째 Backend · W4-A1 구현/검증 게시](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6314976554)에 결과/한계·다음 Backend W4-A2를 기록하고 Issue 상단도 같은 범위로 갱신했다. 실제 전체85댓글을 재조회해 순서와 게시 원문 일치를 확인했다. 이 게시 링크를 포함한 후속 문서 커밋도 같은 브랜치에 push한다.
