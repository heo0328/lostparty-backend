# 활동 해제 후 기존 참가 유지

기준은 [Issue42](https://github.com/heo0328/lostparty-backend/issues/42)·[전체1번째 Backend 착수 계약](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6604762479)이다. 작업 브랜치는 `fix/raid-participation-continuity`다. 사용자 최종 결정은 [전체2번째 Backend 범위 변경](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6605446700)을 따르며, 실제 반영·고정 SHA 인계는 DEV_LOG의 완료 근거를 기준으로 한다.

## 검증 경계

활동 선택 해제는 소유권 상실·등록 삭제·회원 정지·퇴역과 다르다. 이미 참가한 C/N의 명단·편성·상세·일정·권한에 따른 관리·완료·탈퇴는 활동 해제만으로 제한하지 않는다. 배정 display/build·그룹 회원관계/대표 Snapshot·완료/탈퇴 자료는 삭제하거나 자동 교체하지 않는다.

| 동작 | 검증 |
|---|---|
| 기존 C/N 참가 유지 | 서버의 정확한 기존 참가 증명 + 기존 자격 검증; 활동 조건만 제외 |
| 생성·신청·가입·승인 배정 | 기존 활동 선택 검사 유지 |
| 기존 A→활동 B 교체 | 원천 A의 활동 여부는 제한하지 않고 대상 B는 신규 검증 |
| 비활동 A로 교체·재가입 | 거절 |
| 새 주차 발급·다음주 신규 참가 | 신규 검증 |

`selected_character`는 공통 소유/등록/생명주기/revision 검사 뒤 기존 활동 검사를 유지한다. 기존 참가 경로는 server room/cycle/현재 generation/CM/Member/CycleAssignment/Assignment의 연결에서 캐릭터·역할을 결정하고 공통 검증을 재사용한다. 클라이언트 isExisting나 임의ID로 면제하지 않는다. 다른 주차·과거 세대의 이력도 현재 권한이 아니다.

활동 조건 외 회원 상태·NameClaim·소유/수명 revision·전투력/아이템레벨·그룹·한도·점유 정책은 유지한다. 그룹 신규 활동 후보나 자동 전투력 갱신 범위를 확대하지 않는다. 공개 path/DTO/reader profile·오류 형식·권한·CAS·원키/원본문·원 ACK는 그대로다. 기본/two-cycle OpenAPI는 기존 paths/components를 보존하고 동작 정책 설명만 추가한다.

## 실제 호출 경로

| 경로 | 처리 |
|---|---|
| cycle_lifecycle.qualify | 서버 기존 참가 증명 후 활동 조건만 제외 |
| cycle_member_reads.detail → membership_readers | 현재 세대 증명으로 비교/build 표시; 활동 해제만으로 needs_review/stale 추가 없음 |
| cycle_worker.process_room | 활동 해제만으로 기존 주차 전체를 review로 바꾸지 않음 |
| cycle_times / cycle_schedule_service / cycle_planning / beta_schedule | 공통 qualify를 통해 기존 일정 조회·후보·제출·동의 경로에 적용 |
| cycle_leadership / cycle_management / cycle_common / membership_actions / atomic_members | 기존 참가 권한·승계/관리와 신규 선택 분리 |
| cycle_outcomes / weekly_summary | 기존 원장/완료 검증 유지, 잘못된 target review 전파 방지 |
| 생성/신청/가입/승인/교체 대상/새 주차 | 신규 selection 유지 |

## 최종 범위 — 예방 수정만 적용

사용자는 현재 문제가 dev에서 발견됐으며 운영 테스터 모집 전이라는 점을 근거로 **이미 막힌 기존 dev 방은 대응하지 않아도 된다**고 결정했다. 이번 작업은 앞으로 활동 해제만으로 기존 참가/주차가 새로 review 상태가 되는 현상을 방지하는 것으로 마감한다. 기존 review의 정상화는 구현하지 않으며 후속 필수 과제로 남기지 않는다.

따라서 복구 CLI·읽기 전용 복구 판정·감사 DB 확장·migration을 추가하지 않는다. 초기 설계/착수 댓글의 대상 지정 복구는 이 사용자 결정으로 제외됐다. 원본 LegacyCycleEvidence의 불변 trigger와 기존 자료는 그대로 보존한다. GET/일반 worker도 기존 review 자료를 자동으로 복구하지 않는다. 로컬 예방 코드 반영과 기존 자료 복구를 혼동하지 않는다.

운영 테스터 모집 전에 이 예방 수정을 운영에 반영하는 시점은 개발자가 별도 지시한다. Backend 완료·commit/push·로컬 확인을 운영 배포 승인으로 해석하지 않는다.

## 검증 구분

격리 PostgreSQL의 합성 자료로 참가 유지·신규 거절·권한/소유/수명/위조 방어·Snapshot/원장 보존과 관련 회귀를 확인한다. 현재 주차 종료를 넘던 공통 fixture의 +8시간 일정은 합성 간격만 남은 주차 안에 배치하도록 보완했다. 활동 해제를 부적격으로 보던 기존 회귀3개는 퇴역 거절 검증으로 유지하고 활동 해제 정상 흐름은 별도 검증한다.

합성 검증·실제 로컬 API 예방 수정 반영·기존 자료 복구·Flutter 연결·실기기 인수·운영은 각각 구분한다. 이번 작업은 merge·태그·운영 배포·자료 초기화·Issue 종료를 포함하지 않는다.
