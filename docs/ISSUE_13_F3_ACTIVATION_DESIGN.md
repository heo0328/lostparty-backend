# F3 모집 API·개발환경 활성화 설계

[F3 설계·근거 답변 — #13 전체18번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263341047). 독립 F3-A 준비와 사용자 결정/실제 활성화·계약 고정을 구분하며 신규 시험 요청은 없다.

2026-10-19 / Backend / `feat/raid-recruitment` / 설계 기준61ca90b.

[상세 계약](ISSUE_13_R1_R2_CONTRACT_DRAFT.md)·[후보 HTTP](ISSUE_13_F2_HTTP.md)·[F2 설계](ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)를 재사용한다. #13은 [전체16번째 Flutter 접수](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260778487), #16은 [전체6번째 Backend G3 통합](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673)까지 확인했다. 설계 공유 중 [전체17번째 Flutter Q1~Q3 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263303080)가 추가된 것을 확인해 아래7~9절에 반영했다. 이 회신은 정책 승인이나 실서버 인수가 아니다. G3는 dev/ce3064f에 통합됐고 모집 브랜치에 이력을 merge했다. 모집 구현은 미push·서버/DB 미반영이다.

**이번 산출물은 설계다.** 아래 파일/설정/검증은 앞으로 구현할 계획이며 현재 동작으로 안내하지 않는다. 코드·원본 OpenAPI·migration·이미지/서버·DB·운영 자료를 이번에 변경하지 않는다.

## 1. 활성화 범위와 완료 조건

활성화 후보는 공개방·현재주차·유한 단일회차·최소전투력 미설정·leader_only/direct_join의 기존18동작이다. 전체17번째가 사용자 결정으로 분리한 최초 지원 범위를 확정하기 전 실제 서버 활성화나 최종 소비 계약 고정을 완료 처리하지 않는다. 본인관계/i·주간점유·완료는 별도 원본이다. Q1 종료불명/주차초과 일정, Q2 역할별 최소전투력 근거, Q3 그룹탈퇴 후 방관계는 해당 분기만 보류하며 영구 정책/요구 폐기로 해석하지 않는다.

F3 완료는 **최종 계약·실제 DB0018·사용량 원본·main 앱/router·실행 이미지가 일치하고 원격 게시·인계 근거가 있는 상태**다. Flutter 적용/실기기·전체 제품/운영 완료나 dev/main 병합은 포함하지 않는다. #16 조건부 해산은 실제 그룹방 원본이 필요하므로 공개방 활성화만으로 해제하지 않는다.

## 2. 실제 사용량 연결

현 `member_limits.service.snapshot()`은 모집 사용량을 항상 unavailable로 반환하며, 후보 명령은 `raid_rooms.core.room_count()`로 이미 실제 내부 집계를 쓴다. F3에서는 둘을 같은 읽기 원본으로 연결한다.

- 신규 `app/raid_rooms/usage.py`에 순수 집계를 둔다. models와 SQL만 의존하고 limits/service/core를 역참조하지 않아 순환 import를 피한다. core의 기존 room_count는 같은 함수를 재사용한다.
- count는 회원별 **종료되지 않은 membership + 종료되지 않은 room**의 수다. 캐릭터/원정대 수·활동 여부·주차·일정 종료·신청 pending으로 증감하지 않는다. 현재는 공개방만 생성하지만 집계 자체는 scope로 누락시키지 않는다. 다른 회원의 개인키·표시는 읽지 않는다.
- `/v1/me/usage-limits`의 필드/nullable/schema/policy_version은 유지한다. source 활성화 후 raid_rooms는 실제 used/remaining/state/can_increase로 응답하고 초과 시 MEMBER_RAID_LIMIT_EXCEEDED를 기존 issues에 추가한다. 미제공→실수치 전환을 계약 정책 설명·예시·인계에 명시한다.
- 미가입0은 정상 데이터다. 테이블/열/adapter 오류는 기존503이며 미연결/SQL 실패를0 또는 정상으로 덮지 않는다. 새 버전의 DB 준비 검사를 통과한 경우에만 이 원본을 사용한다. 요청별 자동 탐색/실패 시 조용한 fallback은 두지 않는다.
- 새 참가확정/탈퇴·마지막종료는 기존 transaction에서 MemberUsageHead를 갱신한다. replay·pending·이전은 사용량을 바꾸지 않는다. 한도변경은 limits_revision, 사용량변경은 usage_revision을 유지한다. source 전환을 이유로 모든 회원의 head/기본한도 행을 GET에서 생성하지 않는다.
- 개인방수 초과는 직접 참가한 공개/그룹방, 개인그룹수 초과는 직접 참가한 그룹방, 그룹정원 초과는 해당그룹 모든 그룹방이라는 기존 영향표를 유지한다. 정확한도는 기존 이용 정상/증가만 차단이며 모든 관련 원인이 해소돼야 진행을 재개한다.

## 3. main 앱·최종 계약

`app/main.py`에 후보 router를 연결하고, 기존 OpenAPI 가공에 raid-rooms 태그를 포함해 validation400/422 제거·no-store/401 Bearer·409 REQUEST_IN_PROGRESS Retry-After2를 일치시킨다. 단순 자동생성 덮어쓰기 대신 dev의 기존 path/components와 대조해 허용된 변경만 반영한다.

원본 `openapi/openapi.yaml`에는 기존18동작·DTO와 초기 지원/미지원표·사용량 source 전환 설명을 추가한다. 기존 API 경로/DTO/보안·정밀도는 유지하고 새 DTO 이름 충돌로 기존 schema가 바뀌지 않는지 확인한다. 예시의 실제 카탈로그 값은 저장된 버전과 대조하며 가짜 값은 예시로 표시한다.

기존 `/v2/me/account-bootstrap`은 usage-limits를 포함하지 않는다. 구조에 모집 목록·사용량을 새로 추가하지 않는다. 주간 participation 표시는 기존 WeeklyState로 자연스럽게 반영되며 별도 현재방 membership DTO를 주간 participation/완료에 섞지 않는다. 기존 manual 완료 가드·정정/readonly 기준을 회귀 검증한다.

## 4. 반영 준비와 복구 장치

### DB 준비 검사

실제 API lifespan에서 worker/서비스 시작 전에 읽기 전용으로 DB revision과 필수6표·application.build/필수 제약·공통시각 trigger 준비를 검사하는 방안을 구현한다. 이번 목표는0018_room_application_build이며 미래 후계 migration은 명시 호환 검토 대상으로 둔다. 잘못된 DB에 새 모집 경로만 노출하지 않는다. 기존 health 응답의 필드를 임의 추가하지 않는다.

마이그레이션은 신규 이미지의 Alembic으로 명시 실행한다. Dockerfile은 자동 migration entrypoint가 아니며 init-db.sh는 기존 DB에서 재실행하지 않는다. 실행 계정 lostparty_app의 실제 권한으로0017/0018 적용·조회/쓰기를 검증한다. superuser 테스트만 통과한 것을 개발권한 검증으로 확대하지 않는다.

### 신규 참가 일시정지

복구 시 데이터 조회/정리를 유지하기 위한 제안 설정은 `RAID_ROOM_ADMISSIONS_ENABLED`다. 원본 활성화와 분리하며 초기 미설정은 false, F3 활성화 시 명시 true로 시작한다. 전역 배포 설정이고 앱 회원/요청이 바꿀 수 없다. 적용은 환경 변경과 API 재기동 기준이며 실행 중 무중단 전환을 주장하지 않는다.

| 상태 | 동작 |
|---|---|
| true + DB 준비 완료 | 지원 범위의 생성/신청/즉시가입/승인 및 기존 조회·정리 |
| false + DB 준비 완료 | 기존 인증·공개범위 검사 후 유효한 새 생성/신청/즉시가입/승인503, 실제 사용량/기존 관계 조회와 권한 있는 거절·철회·탈퇴·이전·마지막종료 유지 |
| DB 준비 실패 | 서비스 준비 실패, 테이블 없음→0건/미제공으로 우회하지 않음 |

정지 검사는 멱등 reserve/replay의 **최초 실행 분기 안**에 넣어 기존 성공 ACK 복구를 막지 않는다. 실패한 신규 시도는 기존 retryable 규칙을 따른다. admission-context/permissions도 정지 사유를 반영하며, 거절/철회·이전/탈퇴의 현재 권한·주차·기한 검사를 완화하지 않는다. 정지를 한도 초과나 그룹정책 변경으로 표시하지 않는다. OpenAPI 구조는 true/false에 따라 달라지지 않는다.

이 설정은 F3 구현 대상 제안이며 아직 코드/Compose에 없다. 생성/가입 서비스의 명시 policy를 없애거나 기본 허용 callback으로 바꾸지 않는다.

## 5. 구현·검증·실제 반영 순서

1. **F3-A 계약/원본 연결:** 공유 usage 함수·한도 snapshot·main router/OpenAPI·DB 준비 검사·정지 설정을 구현한다. 후보 앱에만 의존하지 않고 실제 main 앱 경로/응답을 검증한다. 기존 unavailable 고정 시험은 실제0/초과 집계·조회실패503·정지 중에도 실수치 유지 시험으로 갱신하며, 기대값만0으로 바꾸지 않는다.
2. **F3-B 격리 검증:** 0016 상태의 합성 기존 자료에0017→0018을 적용하고 기존 행/제약 보존·실제 앱 권한·NULL/no backfill·trigger·실패 원자성을 확인한다. 모집/한도·그룹G1~G3·주간/manual·bootstrap·V2 영향 경계와 정확한 계약 비교를 필요한 범위로 묶는다. admissions true/false 모두 확인한다.
3. **F3-C 개발 전환 준비:** 기존 이미지 ID/기동 설정·DB revision/필요한 구조·기존표 검증 기준을 로컬 비공개 기록으로 확보한다. 필요 백업을 만들 경우 보호된 기존 로컬 저장 위치에 보관하고 원문/비밀을 Git·Issue에 올리지 않는다. 백업 생성과 복원시험을 구분한다. 신규 이미지만 build하고 아직 실제 서버를 교체하지 않는다.
4. **F3-D 개발 반영:** 짧은 API 중지 구간에서 worker/새 요청 쓰기를 멈추고 기존DB는 유지한다. 새 이미지의 일회성 실행으로0017→0018만 적용하고 앱 계정/기존자료 보존을 확인한 뒤 새 API를 명시 admissions=true로 시작한다. DB 볼륨 삭제/새환경/기존 데이터 import는 하지 않는다. 외부 DB 쓰기가 있으면 같은 시점의 단순 행수 비교를 보존 증거로 단정하지 않는다.
5. **F3-E 실행 확인·게시:** 최신 이미지의 health/DB 준비·인증 경계·모집 공개 GET과 사용량/기존 API 호환성·`scripts/check_openapi.py` 전체일치를 확인한다. 실제회원 참가/탈퇴 등의 시험은 자동 실행하지 않는다. 검증 구간을 commit/push·원격 SHA 확인 후 고정 계약/지원표·실행 반영 여부·미실행/다음 담당을 #13에 인계한다.

반영 전 실패는 기존 서버를 유지하고 해당 단계만 보완한다. migration0017/0018이 성공한 뒤에는 삭제 downgrade/0016 강제 stamp를 하지 않는다. **모집 업무 자료가 생성되기 전** 구버전 이미지로 복귀하려면 새 표를 남겨둔 채 기존 버전 호환과 모집/ACK 자료 부재를 확인한다. 새 자료가 생긴 뒤에는 기존 source·0018 해석·관계 정리를 유지하는 신버전에서 admissions=false로 막고 전진 수정한다. 원본을 숨기는 구버전 회귀나 승인 없는 데이터 복원/삭제는 기본 복구 절차가 아니다.

## 6. 검증 합격선과 남은 입력

- 실제 main 앱18동작과 canonical OpenAPI 전체일치, 기존 path/components의 허용 외 차이 없음.
- 사용량 생성/직접가입/승인/탈퇴/종료·replay/rollback·pending/이전·다원정대/주차 경계가 동일 원본/head를 유지하고 GET쓰기0. 실제 한도 변경과 방 진행/회복 정책이 일치.
- 정지 중에도 원 ACK/조회·정리를 보존하고 신규 증가만 막음. 부족한 DB/권한·사용량 실패를 정상0으로 처리하지 않음.
- #11 주간 원장과 현재방/i 분리·bootstrap 필드 불변, 기존 V2 worker의 active WeeklyState 기반 PARTY_IMPACT_REVIEW_REQUIRED 유지. 공개방 활성화를 V2 실제파티 adapter/보류해제 완료로 해석하지 않음.
- G3 기존3동작과 disband 미지원 유지. 그룹방·추방/대표변경/완료·반복·통계·WebSocket/운영을 추가하지 않음.

다음 담당은 Backend F3-A의 독립 가능한 원본/검증 준비와 아래 근거 답변이다. Flutter는 전체17번째에서 로그인 화면 재구성 수정을 별도 마감했고 이번은 계약 검토라고 정정했다. Q1~Q3의 제품 결정과 계약 고정/실제 활성화는 아래 구분을 따른다. 이번 설계는 새 구현·실행·Flutter 시험 요청이 아니며 기존101PASS를 F3 검증으로 재표시하지 않는다.

## 7. 전체17번째 회신 반영 — 결정과 독립 작업

Flutter는 uncertainSchedule/임의 기본시간 금지, 선택역할 snapshot 분리/P1 비검증, 그룹탈퇴 후 기존방 membership 유지·자동퇴장 금지를 확인했다. 새 조회/신청 권한 상실과 정리 방향을 근거로 방 전체 진행 정지·다른 사람 후보 공개까지 확정할 수는 없다.

| 사용자 결정 항목 | Backend 권고/후보 | 결정 전 경계 |
|---|---|---|
| 최초 지원 범위 | 공개방·현재주차 안 유한일정·단일회차부터 | Q1의 null/주차초과 표현을 없애지 않음. 독립 내부/격리검증은 진행하되 실제 활성화/최종 계약 고정 전 범위를 확인 |
| 전투력 입력·수치 의미 | 처음에는 문턱 없음. 단일 nullable 입력과 역할별 맵 중 최종 형태/의미는 별도 결정 | 현재 후보HTTP의 dealer/support 맵을 UI 확장 승인으로 보지 않음. 문턱 수치를 임의 매핑/검증하지 않음 |
| 그룹탈퇴 후 제한/최소정리 공개 | 기존 membership 유지, 본인 최소정리 우선 | 탈퇴자만/방 전체 진행 제한 및 후보 필드 범위를 확정 전 그룹 adapter 미활성 |

첫 지원 범위 결정은 실제 공개 API 활성화에 직접 필요하다. 전투력·그룹방의 세부 미결정은 해당 분기를 비활성으로 유지하면 공개방 내부 원자성/usage 준비를 막지 않는다. 다만 문턱 없음 입력을 어떻게 고정할지는 소비 계약에서 명시해야 한다. 이 설계 문서는 사용자 선택을 대신 확정하지 않는다.

## 8. Q2 최소 근거·예시 답변

현재 확보한 선택역할 자료는 CharacterRoleSummary의 `(user_id, character_id, ownership_revision, role)` 원본이다. `role`은 selected_role과 같아야 하고 P1의 `combat_power`/`combat_power_observed_at`, `source=flutter_analysis`, `analysis_rules_version`, `analyzed_at`, `observed_lifecycle_revision`, `catalog_version`, `integrity_status/issues` 및 서버 저장 `version/saved_at`을 함께 구분한다.

이 값은 클라이언트 분석 표시다. 서버 소유·수명/CAS 검사를 통과했다는 사실이 수치의 게임 서버 검증을 뜻하지 않는다. 일반 provider profile/power 캐시를 선택역할 수치로 연결하는 의미/신뢰 근거도 현재 확정하지 않았다. 따라서 server-verified role power라는 값을 새로 만들지 않고 문턱 판정은 미지원이다. 역할별 필드 의미·공급 근거/관측·검증 방법이 결정되면 그때 별도 adapter를 설계한다.

문턱 없음(null), 같은 역할 요약행 없음(missing), 관측값 null, 원본 revision/소유수명 등이 달라진 stale, 검증된 원본/문턱이 모두 존재할 때의 미달을 구분한다. 미달은 아직 활성화하지 않았다. 반대 역할의 현재값이나 표시 정수로 대체하지 않고, 없는 값을0으로 만들지 않으며 유효 decimal 비교가 필요해지면 원문 정밀도를 보존한다. 새로운 시간 TTL을 임의 추가하지 않는다.

자료 대조용 부분 예시(신규 API 응답/확정 게임수치가 아님):

```json
{
  "selected_role": "support",
  "stored_role": "support",
  "stored_version": 4,
  "source": "flutter_analysis",
  "combat_power": "12345.6789",
  "combat_power_observed_at": "2026-10-19T00:00:00Z",
  "server_verified_role_power": null,
  "threshold_decision": "deferred"
}
```

support 요약이 없다면 dealer에 위 값이 있어도 support의 missing을 유지한다. 원래 minCombatPower 단일 nullable 소비와 후보 역할별 맵의 형태 차이는 알고 있으며, 사용자 결정 전 UI/확정 계약으로 강제하지 않는다.

## 9. Q3 최소정리 제안과 별도 영향표

본인 최소정리 후보 DTO는 기존 RoomManagement의 본인 membership_id/revision/room_role, room/round/members revision 및 허용 정리만을 기본으로 한다. 타인 user UUID·그룹명단·방 전체명단·다른 사람 빌드를 붙이지 않는다. 그룹탈퇴자의 full 상세/새 신청 권한은 복원하지 않는다. 이 최소 응답과 후보 필드 자체도 아직 제안이다.

파티장이 남은 참가자에게 이전할 수 있도록 후보를 제공한다면 membership_id/revision만 우선 제안하고 display=null로 제한한다. 후보는 같은 방의 현재관계 + 활성 회원 + 현재 그룹자격을 서버에서 확인하고 최종 이전 transaction에서 다시 검사한다. 그룹장이란 이유로 후보/파티장 권한을 만들지 않는다. 예전 캐릭터 소유 실패를 본인 정리의 추가 조건으로 삼지 않는다.

유효 후보가 없으면 자동승격/자동추방·임의 방종료를 하지 않고 이전 불가를 표시한다. 비파티장은 본인 탈퇴, 파티장은 이전 선행, 마지막1인은 권한 있는 종료라는 정리 경로를 제안한다. 여러 명이 남고 이전 후보가 없을 때의 추가 회복 정책은 별도 결정 대상으로 둔다. 기존 group 관리 권한과 room 정리 권한은 서로 대체하지 않는다.

| 원인 | 확정된 영향/보존 | 미확정 또는 비전파 |
|---|---|---|
| GROUP_MEMBERSHIP_LOST | 탈퇴자의 새 그룹방 조회/신청 권한 상실·기존방 membership 유지/자동퇴장 금지 | 탈퇴자 본인 진행만/방 전체 진행 제한, 최소정리 응답·후보 공개 범위는 결정 필요 |
| MEMBER_RAID_LIMIT_EXCEEDED | 당사자 직접참가 공개/그룹방 제한·조회/정리 유지 | 미참가방/기존그룹 운영에 전파하지 않음 |
| MEMBER_GROUP_LIMIT_EXCEEDED | 당사자 직접참가 그룹방 제한·조회/정리 유지 | 공개방/미참가방에 전파하지 않음 |
| GROUP_CAPACITY_EXCEEDED | 해당그룹 모든 그룹방 제한·정리 유지 | 일반공개/다른그룹에 전파하지 않음 |

GROUP_MEMBERSHIP_LOST를 한도 초과 원인에 합치거나 하나의 제한이 사라졌다고 나머지 원인을 해제하지 않는다. 위 후보는 Q3 후속 입력이며 F3 공개방 활성화에 그룹 adapter를 포함시키지 않는다.
