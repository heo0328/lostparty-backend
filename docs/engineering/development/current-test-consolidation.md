# 현재 앱 시험 기준 통일

2026-11-16 / Issue55 사용자 승인 구현. 코드 상태는 [구현 기록](../../features/rosters/power-and-profiles/server-processing-implementation.md), 다음 실행은 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다.

현재 실행은 create_app/DB0037 하나다. 지원을 끝낸 DB0023 앱에서 새 명령을 실행하는 시험을 통과시키기 위해 버전 분기·writer 우회·가짜 schema revision을 추가하지 않는다. 당시 명세·migration·Git 원문은 보존한다. 테스트 개수의 이전 결과 계승을 완료 조건으로 삼지 않는 사용자 기준을 적용하며 실제 현행 기능의 검증은 현재 API로 이어간다.

## 폐기한 실행 시험과 현재 검증 위치

아래 DB0023 전용 v1 신규 명령/worker 시험8개 모듈은 제거했다. 당시 자료는 [원본 source cda4db3](https://github.com/heo0328/lostparty-backend/tree/cda4db352c9ac922f269b9ec2794f0d888d4dca6/tests/raid_rooms)에 있다. 현재 앱이 의도적으로 CLIENT_UPGRADE_REQUIRED로 막는 경로를 새 쓰기로 실행하지 않는다. 기존 v1 읽기/원ACK 경계의 현행 계약 시험은 유지한다.

| 제거한 시험 모듈(경로는 tests/raid_rooms 기준) | 현재 기능·검증 위치 |
|---|---|
| admissions/test_recruitment_admission.py | 모집 생성/참가/신청/승인·권한/CAS: [현재 HTTP](../../../tests/raid_rooms/admissions/test_recruitment_cycle_http.py), [명령](../../../tests/raid_rooms/admissions/test_recruitment_cycle_commands.py), [구성](../../../tests/raid_rooms/admissions/test_application_composition.py) |
| common/test_recruitment_continuation.py | 자동 구 worker 실행을 종료. 실제 현재/다음 주 개방: [생성](../../../tests/raid_rooms/admissions/test_recruitment_cycle_creation.py), [명시 개방](../../../tests/raid_rooms/admissions/test_beta_recruitment.py) |
| outcomes/test_recruitment_completion.py | [현재 완료/기록](../../../tests/raid_rooms/outcomes/test_recruitment_cycle_outcomes.py), [묶음 완료](../../../tests/raid_rooms/outcomes/test_batch_completion.py), [실제 계약](../../../tests/raid_rooms/outcomes/test_completion_profile_contract.py) |
| schedules/test_recruitment_scheduling.py | [현재 일정](../../../tests/raid_rooms/schedules/test_recruitment_cycle_times.py), [계획](../../../tests/raid_rooms/schedules/test_recruitment_cycle_planning.py), [베타 약속](../../../tests/raid_rooms/admissions/test_beta_recruitment.py) |
| participation/test_recruitment_member_reads.py | [현재 조회](../../../tests/raid_rooms/reads/test_recruitment_cycle_queries.py), [관계/기록](../../../tests/raid_rooms/participation/test_membership_actions.py) |
| participation/test_recruitment_management.py | [현재 관리](../../../tests/raid_rooms/participation/test_recruitment_cycle_management.py), [현재 그룹 권한](../../../tests/raid_rooms/group_links/test_cycle_group_policy.py) |
| schedules/test_recruitment_availability.py | [현재 시간표 HTTP](../../../tests/raid_rooms/schedules/test_recruitment_cycle_times_http.py), [개인 예약](../../../tests/raid_rooms/schedules/test_personal_reservations.py) |
| reads/test_recruitment_search.py | [현재 조회](../../../tests/raid_rooms/reads/test_recruitment_cycle_queries.py), [공개 탐색](../../../tests/raid_rooms/reads/test_discovery.py) |

0034의 모집실 공통 최초 연결 시험 `group_links/test_group_room_connection.py`도 종료했다. 현재0035 이후 정책은 대상 주차·generation별이며 공통 target_group_id 편집을 의도적으로 거절한다. [현재 그룹 정책 시험](../../../tests/raid_rooms/group_links/test_cycle_group_policy.py)의 대상별 변경/권한·동시성·rollback·ACK·공개/비공개·상세 badge·pending 보존·HTTP marker 검증으로 대응한다. 방 전체 연결 및 public+group_id 잔존을 현재 정답으로 되살리지 않는다. 0035의 현재 generation만 이관/구 pending 명령 차단은 고정 SQL migration 시험으로 유지한다.

W1 shadow 앱을 활성화해 시험하던 공통 fixture/시험과 W5 비어 있지 않은 옛 runtime 체인도 제거했다. 같은 파일의 실제 주차 경계 함수와 역사 SQL 자료 helper, 실제 JWT/current 앱 통합 시험은 유지한다. 전체 이전 기능 요구를 폐기했다는 의미가 아니며 현행 검증 위치와 실제 실행 결과를 구분한다.

개인키·클라이언트 summary 생산자 시험(`test_lostark_keys`·`test_lostark_retry_restore`·`test_role_power_success`·`test_startup_batches`)은 제거한 API/저장소를 활성화하지 않는다. 신규 수집·항목별 명령/응답유실·CAS·키/공유 제한은 [분석 시험](../../../tests/game_accounts/analysis/test_analysis_http.py)·[서버 키](../../../tests/game_accounts/analysis/test_server_credentials.py)·[공유 제한](../../../tests/game_accounts/analysis/test_provider_limits.py)에서 검증한다. 유지하는 개인 프로필 배치 GET은 [현재 reader 시험](../../../tests/game_accounts/test_personal_profile_batch_reads.py)에 권한·단일 GET 일치·쿼리 수·동일 snapshot·무부수효과를 분리해 보존했다.

## 보존·재작성한 검증

- 0017/0018/0019/0020 이력 검증은 고정 SQL 자료로 준비하며 최신 ORM의 분석 상세를 옛 DB에 억지로 추가하지 않는다. 0033의 completed 이력/현재 중복 index는 실제 SQL 자료로 전진 migration 전후를 검사한다.
- 0037의 호환 빈 DB 적용/제한 LOGIN·비호환 행이 있으면 DDL 전에 거절하는 검증을 유지한다. 실제 개발/운영 자료는 초기화하지 않는다.
- 계정/그룹/모집의 현재 기능 fixture는 head부터 한 번 준비한다. 현재 DB에 예전 revision으로 upgrade를 반복하던 무효 단계와 전체 표 hash 반복을 제거했다. 실제 consent/예약·현재 계획 보존 검증은 그대로 실행하며 migration 검증이라고 표시하지 않는다. bootstrap 요약과 상세 GET, 최신 null/저수치·무결성 오류, 자동 대상/소유/수명·현재 명령 정합성을 검사한다.
- API 검증은 현재 OpenAPI와 실제 응답을 대조한다. 과거 제안 Schema를 새 reader의 정답으로 재사용하지 않으며 동결 예시 파일은 변경하지 않는다.
- 병렬 서비스 시험은 호출한 시험의 명시적 ContextVar를 별도 사본으로 전달한다. 인증/권한을 우회하거나 생산 코드에 호환 플래그를 추가하지 않는다. 실제 HTTP 인증·query/profile 검증은 current 앱 통합 시험에서 별도로 확인한다.

이 문서는 시험 범위/대응표다. 현행 전체 통과나 Native 기기 인수를 선언하지 않으며 남은 실패와 실제 통과 수치는 구현 기록/DEV_LOG에 누적한다.
