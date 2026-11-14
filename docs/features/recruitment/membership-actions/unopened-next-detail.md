# Issue53 BUG-036 — 미개방 다음 주 모집 상세 500

2026-11-14 / fix/recruitment-detail. [Native 전체39 조사 요청](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6874697856)·[전체40 대기](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6874741537)와 사용자 정정을 기준으로 **다음 주 함께하기 미개방 방의 모집 상세에서 다음 주 탭 진입**을 조사했다.

## 확인 원인

로컬 안전 로그에서 GET /v2/raid-rooms/{room_id}/detail의 HTTP500/internal을 확인했다. 로그는 query/회원·대상을 저장하지 않으므로 과거 개별 요청을 특정 회원이나 방에 연결하지 않았다. 예외 traceback/민감 원문 로깅은 추가하지 않았다.

임시 PostgreSQL의 이번 주만 생성한 방에서 다음 요청을 HTTP로 재현했다:

`GET /v2/raid-rooms/{room_id}/detail?target_cycle_key=N&reader_profile=membership-actions-1&contract_profile=beta-recruitment-1&group_policy_version=cycle-group-policy-1&include_coordination_wait=true&include_group_state=true`

membership reader는 N의 RoomCycle이 없는 경우에도 기존 관계 조회 계약에 따라 relation_only/content=null 응답을 정상 작성한다. 뒤의 group_link_display.get이 없는 N의 row를 metadata에 넘겼고 cycle_group_policy.metadata_value의 row.room_id 참조에서 AttributeError가 발생했다. 동일 요청의 include_group_state 없는 경우200, 있는 경우 예외로 **수정 전1PASS/1FAIL**을 확인했다. 이 예외는 정상 GameError가 아니므로 HTTP500이며 클라이언트에서 INVALID_RESPONSE로 보일 수 있다.

## 최소 수정·보존 계약

주차별 그룹 정책이 활성화된 group_link_display에서 resolve 결과 row가 None이면 이미 권한 검사를 마친 기존 응답에 group_state=null을 붙여 반환한다. 현재 주차의 그룹이나 가짜 다음 주 정책을 대신 넣지 않는다. API/DTO/OpenAPI/권한·주차 생성/활성화 명령은 변경하지 않는다.

미개방 N의 membership 상세는200·viewer.mode=relation_only·content=null·view_detail.allowed=true다. 일반 상세는 기존409 TARGET_NOT_OPEN, 비회원 membership 상세는403을 유지한다. 서버가 다음 주를 자동 개방하거나 참가 권한을 부여하는 수정이 아니다.

## 검증·실행

[시험](../../../../tests/raid_rooms/group_links/test_cycle_group_policy.py)의 test_unopened_next_detail_membership_http는 group_state false/true × character_issues/participation profile false/true의4조합(DB0035/0036)에서 HTTP/권한·일반 상세 오류·이번 주 정상·미개방 N 행 미생성을 검증한다. 기존 실제 주차 그룹 변경/다른 주차·참가 보존 시험1건을 포함해 **5PASS/73.40초**다. 생성 현재/legacy 명세 전체 객체 동일·문서/diff 검사를 확인했다.

로컬 API만 image add28707…1f71f2로 교체했고 app296파일이 현재 소스와 일치하며 health200이다. DB 컨테이너/0036·118테이블/키/환경·포트/mount는 유지했다. 전후 live DB 자료 집계는1327→1326행으로 달라 전체 자료 동일성은 확인하지 못했다. 원인은 추정하지 않으며 migration·초기화·합성 회원 쓰기·자료 복원은 실행하지 않았다. [비민감 반영 기록](../../../engineering/operations/records/unopened-next-detail-local-rollout.json)을 따른다. 인증 상세 성공은 임시 DB의 HTTP 검증이며 실제 회원/Native 화면 인수와 구분한다.

코드/시험/기록은 미커밋·미push이며 기존 게시dev89e0196에는 포함되지 않는다. 로컬 dev의 실행 응답은 수정됐고 API 계약이 그대로라 Native 앱에 새 DTO가 필요하지 않다. 운영 배포·merge·Issue 종료는 하지 않았다. 전체43 Native가 사용자 정상 표시와 기존 응답 소비를 수용해 해당 대기는 해소됐다. 원격 소스 게시가 필요하면 사용자 commit/push 직접 지시 기준을 따른다.

## 사용자 확인

사용자가 미개방 다음 주 모집 상세에서 “참가 데이터 없음” 정상 표시를 확인했다. [전체42 Backend 사용자 확인 기록](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875077805). BUG-036 화면 인수 대기는 해소됐으며 반복 시험 요청은 없다. 코드 미커밋·미push/로컬dev 반영 상태를 유지하고 운영·dev 병합·Issue 종료는 별도다.

## 문서 최신화·게시 승인

[전체43 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875080366)의 수용으로 상세500 복구를 확인했다. 사용자 지시로 수정·시험·조사/실행 기록을 커밋하고 dev에 병합·push한다. 실행 코드는 기존5PASS/로컬 반영 그대로이며 문서·Git 상태 검사를 수행한다. 게시 SHA/병합과 최종 인계는 후행 기록을 따른다. 운영·Issue 종료는 별도다.

## 게시·dev 통합 완료

BUG-036 수정/기록 9a61d0ea55d92b8389021048ec97ab058ec2b387를 게시하고 dev4be81dc21547807e0b8339ded6f3100582dd9977에 이력 보존 병합·push/원격 일치를 확인했다. [전체44 Backend 고정 인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6875171401). 작업 tip과 dev의 app/tests/openapi 및 로컬 실행 수정 소스가 동일하다. 기존 격리5PASS·사용자 정상 표시·전체43 Native 수용 근거를 재사용하고 문서/diff 검사를 통과했다. 완료 작업 브랜치는 정리했고 현재 checkout은 dev다. 이 오류의 추가 Backend 수정/반복시험 대기는 없다. 운영·main 변경·DB초기화·Issue 종료는 하지 않았다. 미게시·게시 승인 대기 문구와 원장의 publication은 당시 기록이며 현재 소비 기준은 이 절의 고정 SHA다.
