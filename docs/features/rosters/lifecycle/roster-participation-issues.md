# 원정대 목록 누락과 기존 레이드 참가 유지 — Issue17

게시 최신: 사용자 지시로 구현 `caffaf3405a53be941250132a2b50779943b15f6`를 origin/feat/character-lifecycle에 push·원격 SHA 일치를 확인했다. [전체27번째 고정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722956197)·[DEV_LOG](../../../project/DEV_LOG.md) 기준이며 앱247파일은 실제 dev imagece59926c/DB0036과 일치한다. 아래 미커밋·미push/게시 대기는 당시 기록이다. 새 서버/DB 변경·폴더 이동/분류·merge/운영 배포는 하지 않았다.

현재 실행 최신: [Native 전체24번째 보완 수용](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722805010) 확인 후 사용자 지시로 로컬 API imagece59926c·DB0036에 보완을 반영했다. 실행247파일과 검증 소스/두 전체 계약 일치·DB117업무표99행/sequence·키/환경/포트/볼륨 보존·healthy를 확인했다. [실제 반영 집계](../../../engineering/operations/records/roster-participation-followup-local-rollout.json)가 현재 기준이며 아래 미반영·소비 대기는 당시 이력이다. 보완은 미커밋·미push이고 Native 신규 연결/기기·운영은 별도다. 폴더 분류/파일 이동은 하지 않았다.

현재 후속 완료: 사용자 확정 범위에 따라 active0의 완료P 자동 선택을 제거하고 기존 참가/관리 권한을 유지했다. 신규 개설·다음주 참가·재개설의 미선택 permission/409, 명시 선택 자격·stale/원ACK, 혼합 M/P 일정/실제 탈퇴·승계/rollback과 기존 N 누락 자리/noop 보존을 격리 검증했다. [잔여2항목 보완·인계](roster-participation-followup.md)·[검증 집계](roster-participation-verification.json)가 현재 기준이다. 보완은 미커밋·미push·실제 dev 미반영이며 기존 image4ac36fdb/DB0036은 유지한다. 아래 감사/진행 중·확인 대기는 당시 기록이다.


현재 감사 정정: [전체21번째 Backend](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721435909)에서 active0 이후 완료P의 다음주 source 자동 선택을 격리 재현했다. [Backend 잔여 감사](roster-participation-backend-audit.md) 기준 공통 source 경계 보완·혼합 M/P 후속 명령 직접 검증이 남아 있다. 기존 공개7PASS/게시·로컬0036 지원은 유지하나 **전체 Backend 후속까지 완료/Native 대기만 남음으로 표시하지 않는다.** 이번은 문서/감사이며 배포 소스/DB는 미변경이다.


최신: [전체19번째 Backend 게시 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721299358)로 구현 `4c37c2bebbb9eb8950770a240b6e20b7b468399c`·origin push/원격 일치를 확인했다. [전체18번째 로컬0036 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721249386)과 실행 소스247파일이 일치한다. [구현](roster-participation-implementation.md)·[로컬집계](../../../engineering/operations/records/roster-participation-local-rollout.json) 기준이며 운영/Native 신규 연결·기기는 미완료, 화면/Penpot·기기는 보류다. **아래 미구현/미게시/미반영 문장은 당시 이력이다.**


2026-11-08 / Backend / [Issue17](https://github.com/heo0328/lostparty-backend/issues/17). 사용자 확정 정책과 현재 구현·협업 경계를 관리한다. 원정대 소멸·개명 확정 계약과 혼동하지 않는다.

## 현재 협업 — Native 주도·서버 계약4항목 대조

[전체7번째 Native 사용자 표시 범위·양측 코드 재점검](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719797227)을 수신하고 [전체8번째 Backend 서버 계약4항목 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719925630)을 게시했다. **기획·UX·화면·Penpot 주체는 Native**이며 Backend는 서버 데이터·권한·계약·검증만 판단하고 필요한 협의를 Issue로 전달한다. Native 로컬 경로/소스를 Backend가 읽거나 수정하지 않는다. 현재 보류된 화면·Penpot·기기는 사용자/Native의 별도 진행 지시를 따르며 이번 서버 회신이 보류 해제는 아니다.

사용자 확정: 하단/레이드 현황의 주차 경고는 본인 미완료 참가, 방 상세의 각 주차 버튼은 **해당 실제 주차 참가자 전체의 문제**다. 두 주차 참가권한은 독립 검사한다. 전체6번째의 ‘방 주차 버튼 본인 문제만’ 초안은 이 확정으로 대체한다.

Backend가 사용자에게 호환 대안을 설명했고 **새 부분 완료 참가 구조를 이해하지 못하는 구버전은 영향 방·실제 주차만 업데이트 필요로 제한**하는 안을 직접 선택받았다. 다른 방·반대 실제 주차·일반 기능을 일괄 차단하지 않는다. 이 제품 결정은 해소됐고 서버 계약 표식/각 reader·명령의 세부 조합은 Native 기술 대조 후 고정한다.

정확한 제안 wire/필수 nullable·예시·오류·옵션 조합·M/P 교체·원본/반영·검증 책임의 원본은 전체8번째 댓글이다. 아직 공개 OpenAPI/서버 구현에 확정 반영된 명세가 아니다.

| Native 요청 | Backend 회신/남은 대조 |
|---|---|
| 경고 반환 | 본인 전역/주차·페이지 내 본인 방 경고와, detail/plan의 주차별 전체 참가자 요약·선택 주차 카드 경고를 구분. ready/정상0과 not_authorized/필수null, 미조회 상태를 구분. 본인 등록 ID만 본인에게 제공 |
| 실행 조합 | 기존 reader_profile/beta/group/opt-in의 기존 허용 범위를 보존하며 경고 opt-in·부분 완료 능력 표식을 별도 제안. 영향 대상의 구버전 거절·목록 항목 단위 복구 표시·원 ACK 우선 재생을 대조 |
| 부분 완료 교체 | 서버가 정확한 active 집합 M과 보존 이력 P를 분리해 actor/context/POST의 M 전체 일치를 유지. 완료 기록 불변, 현재 참가와 과거 표시 분리·일정/주차 전환/후속 명령·완료 경합을 함께 보완. 현재 미구현 |
| 표시·반영 | characters의 명시 관찰 상태 opt-in(present/missing/unknown) 제안. 공용 원본/캐시를 삭제하지 않고 Native 표시 projection에서 숨김. 기존 provider POST/저장 GET 구분·여러 방/두 주차 무효화·늦은 응답/원ACK를 보존 |

다음 Native는 위 필드·능력 표식·옵션·active/preserved actor 집합을 실제 DTO/엄격 검증/화면 경로와 대조해 수용/차이를 회신한다. Backend는 합의 후 공개 API/관찰 반환·공통 참가 해석·부분 완료 교체를 구현/격리 검증한다. 현재 Backend 내부23PASS는 이 새 공개 계약·부분 완료·Native 연결의 검증 근거가 아니다. 최종 문구/배치와 디자인 판단은 Native가 사용자와 진행한다.

## 최신 — Native 실제 UX 5항목 확인 수신·계약 보완 대기

[전체5번째 Native 실제 앱 대조·사용자 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719423066)을 확인하고 [전체6번째 Backend 수용·반환안](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719508031)으로 회신했다. Native 로컬 문서는 main의 미커밋·미push 자체보고이며 댓글이 원격 인계다. Backend가 Native 소스를 직접 읽거나 기기 확인한 근거로 사용하지 않는다.

- 확인된5항목: 첫 탭 좌측 상단 경고/우측 상단 기존 사용량 유지, 두 실제 주차 버튼별 발견성(선택 자동 전환/목록 재정렬 없음), 기존 내 캐릭터 변경 버튼/후보/확정 재사용, 활동 선택 저장 뒤 원래 방·실제 주차·교체 문맥 복귀/후보 재조회/명시 확정, 시작·복귀/진입/관련 명령 뒤 영향 범위 재조회·진행 요청 공유. 변경 없는 상세→목록 복귀마다 전체 재조회하거나 모든 복귀에 provider 수집을 붙이지 않는다.
- 안내 영역의 캐릭터 변경 버튼 중복 신설안은 철회한다. 기존 버튼을 재사용하고 정확한 안내 위치/최종 문구는 미확정이다. Native의 초기 provider 수집과 복귀 서버 GET은 별개다. 조회 실패로 기존 경고를 정상/0으로 덮지 않는다.
- 현재 내부 summary는 전역 bool/count·두 주차 key만 제공하므로 주차별 bool은 아직 미구현이다. 전역 요약에 현재주/다음주 각각 `target_cycle_key/has_issues/affected_room_count` 두 항목을 추가하고, detail/plan opt-in에 해당 방의 본인 두 실제 주차 요약을 별도 반환하는 안을 제안했다. 전역 주차 경고를 개별 방 버튼으로 합성하지 않는다. 방 UUID 기준 전체 count와 방×실제 주차 count를 구분한다.
- 타인 카드 경고는 요청 실제 주차의 기존 참가권한 안에서만 제공한다. 반대 주차 타인 상태/count를 노출하지 않는다. 주차 버튼 자체가 본인 문제만인지 같은 주차 타인 문제도 포함하는지는 Native에서 사용자 확인 범위를 대조해 회신해야 한다. Backend가 임의 결정하지 않는다.
- 일부 완료 후 남은 대상 교체는 현재 서버의 전부 active 전제와 다르며 미구현이다. 완료 기록/옛 캐릭터·일정 Snapshot을 보존하고 남은 active 대상만 교체 context/확정에 포함하는 제안을 Native와 대조한다. ACK 후 GET 실패는 성공 유지/GET만 재조회, ACK 미확정은 원 key/body 복구, 복수 방/주차 캐시 경계도 미완료다.

다음은 Native의 위 잔여 계약·의미 대조 회신과 Backend 합의 후 구현/검증이다. 5항목 확인을 공개 wire·전체 UX/앱 인수 완료로 확대하지 않는다. Penpot·Native 화면 구현·기기 시험 보류와 소스 미게시/실DB 미적용 상태는 그대로다. 아래 재기획 대기는 이 최신 수신 전 기록이다.

## 사용자 후속 정정 — Native 재기획·사용자 확인 필수

Backend 대화의 UX 협의를 Native가 실제 앱 기준으로 다시 기획·설계하고 사용자와 함께 확인해야 한다. [#17 전체4번째 Backend 협의 인계/재기획 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6718999630)에 사용자와 선택한 방향 전체를 전달했다. 기존 정책은 검토 출발점으로 보존하되 화면/배치·문구·초기 갱신·활동 선택 복귀·API 소비가 이미 Native에서 검토/확정됐다고 간주하지 않는다. 기존 Backend 내부 코드에 UX를 맞추도록 요구하지 않으며 차이는 사용자 확인 후 양측 계약/코드에 반영한다.

다음 Native는 실제 화면·수명/현재주·다음주 참가·상세/plan·캐시·초기 수집/활동 선택을 대조하고, 발견→원정대 갱신→복구/수동 교체→필요 시 활동 선택→방 복귀→경고 해소의 전 흐름을 재설계한다. 기존 협의 유지/보완/사용자 결정 필요를 구분해 Native 대화에서 사용자와 확인하고 같은 Issue에 결과·남은 결정·Backend 후속을 회신한다. API DTO만 접수하는 것으로 이 단계를 마감하지 않는다.

Penpot 연결/시안/검토 요청·Native 화면 구현·기기 시험은 별도 지시까지 계속 보류한다. 현재는 실제 앱 조사와 문서/동선 중심 기획 검토만 요청했다. Backend 내부 구현·고유23PASS는 보존하되 Native UX 타당성·화면 인수 근거가 아니며 공개 API·일부 완료 교체의 확정은 재기획 결과와 사용자 확인 뒤 이어간다.

## 사용자와 협의한 방향 — Native 실제 UX 재검토 대상

- 정상 본인 원정대 목록에서 기존 참가 캐릭터가 누락되면 즉시 확인 필요로 다룬다. 단순 실패·404·불량/빈 응답으로 상태를 바꾸지 않는다. 같은 UUID의 정상 재등장은 누락 경고를 해제하고 새 이름은 새 UUID다. 이름 점유/설정/참가를 자동 이전하거나 퇴역하지 않는다.
- 내 계정 일반 목록의 누락 캐릭터 숨김은 Native 표시 단계다. 원본 목록/페이지·서버 ID/설정/참가 Snapshot은 보존한다. 숨긴 UI 목록을 전체 원정대 관찰 증거로 서버에 보내지 않는다.
- 현재주·다음주 미완료 참가의 경고를 본인 요약/문제 방/카드에 사용한다. 완료·탈퇴 이력/미승인 신청은 조치 경고 대상이 아니다. 본인에게만 원정대 갱신 대상 등록을 제공하고 다른 실제 주차 참가자에게는 해당 참가 문제만 제공한다.
- 기존 자리·정원·예약·일정·투표/동의·공대장 관리 유지, 전체 완료는 기존 기록으로 허용한다. 새 참가/다음주 발급/교체 대상은 현재 자격 검증을 유지한다. 활동 자동 추가는 #18, 소유권 이전은 #15다.
- 원정대 갱신은 본인 해당 원정대의 기존 명령을 사용하고 요약·목록·상세를 재조회한다. 지속 누락이면 명시 교체, 활동 미선택은 기존 활동 선택을 거쳐 돌아온다. 웹소켓/polling은 구현하지 않으며 시작·복귀·진입·명령 후 재조회 경로만 준비한다.
- Penpot 연결/시안/검토 요청과 Native 화면 구현은 사용자 별도 지시 전까지 보류한다. 제안 배치(첫 탭/문제 방/캐릭터 카드 느낌표·본인 주차 선택 아래 안내)는 디자인 확정이 아니다.

## 현재 소비 계약 제안 — 미확정·공개 경로 미연결

[전체2번째 Backend 정책·계약 검토 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6718820434)에서 Native가 실제 소비 경계를 검토한다. DTO·조합이 합의되기 전 OpenAPI/공개 경로에 추가하지 않는다. 서버 내부 함수의 반환값은 현재 공개 wire 계약이 아니다.

| 제안 | 의미 |
|---|---|
| GET `/v2/me/raid-room-character-issues` | 현재주·다음주 본인 미완료 참가 전체의 `has_issues`, `affected_room_count`, `affected_target_count`, 두 실제 주차·`evaluated_at`·불투명 `issues_revision`. 페이지 밖 누락 방지 |
| memberships/detail/plan의 `include_character_issues=true` | 기존 응답/reader_profile 보존 opt-in. `ROSTER_CHARACTER_MISSING`, 기존 캐릭터 ID/표시명·실제 주차/참가/assignment·관찰 시각. 본인 등록 ID만 본인에게 제공 |
| 기존 원정대 갱신·캐릭터 교체 | 새 쓰기 API 없이 원 key/body/ACK·최신 권한/CAS 유지. GET에서 provider/쓰기 없음 |

Native 검토 항목: 실제 앱 기반 재기획·사용자 확인과 기존 프로필/조합의 strict DTO·표시 숨김·활동 선택 복귀·복수 주차/부분 완료 후 교체 경계. 화면 구현·기기 재시험 요청은 없다. 새 경로는 사용하거나 활성화하지 않는다.

## 내부 구현과 자료 보호

- `0036_roster_presence`는 새 `character_roster_transitions`·`roster_participation_recoveries`를 추가한다. 기존 테이블 backfill/퇴역/claim 해제/자료 삭제는 하지 않는다. 관찰·복구 증거는 DB에서 UPDATE/DELETE 금지다.
- 정상 소유 원정대 reconcile의 누락/재등장에 이전→현재 lifecycle revision과 당시 owner/ownership revision을 남긴다. 기존 불명확 suspect는 새 관찰로 경고할 수 있어도 과거 정상 참가의 연속성으로 간주하지 않는다.
- 기존 참가 유지 예외는 서버의 정확한 회원/실제 주차/세대/assignment, 활성 회원·등록·현재 owner/이름 점유와 누락/재등장만으로 이어진 연속 revision을 검증한다. 원인 불명 revision·소유권 변화·다른 원정대·퇴역은 면제하지 않는다. 기존 assignment의 revision이나 Snapshot은 바꾸지 않는다.
- 기존 검토 방 복구는 명시 원정대 갱신 트랜잭션에서만 수행한다. 원 immutable 오류 증거와 현재 assignment/참가자 revision이 일치하고 모든 참가자가 정상 또는 위 예외를 통과할 때만 해당 현재주/다음주를 복구한다. 근거 없음/혼합 원인/다른 세대/리더십 복구 중인 방은 유지한다. GET/worker는 일괄 복구하지 않는다.
- 새 DB 단계를 인식하는 기존 readiness/worker 기능 목록에는 호환 revision만 추가한다. 기존0023~0035 동작은 신규 관찰 테이블이 없으면 기존 기준을 유지한다.

## 적용·검증 상태

현재 소스는 `feat/character-lifecycle`의 로컬 미커밋·미push다. 이전 종료 기록의 미커밋 변경을 보존해 같은 checkout에서 이어갔다. 새 migration은 격리 PostgreSQL에서만 검증하며 실제 로컬/운영 DB에는 적용하지 않는다. 코드 준비와 실행 서버 지원·Native 적용·실회원/기기 인수는 구분한다.

실DB 반영 전 [백업 원장](../../../engineering/operations/backup-and-recovery.md)을 확인해 대상DB dump와 대응 환경/기존 키·source/schema를 함께 식별한다. 기존 유효 키 사본은 재사용하며 지금 키·환경을 생성/교체하거나 기존 로컬 DB dump 제외 결정을 변경하지 않는다. 실제 반영/복구·운영 배포·commit/push/merge·Issue 종료는 별도 지시다.

[전체3번째 Backend 구현/검증 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6718982612)를 게시했고 Issue 본문도 현재 단계로 갱신했다. 이후 사용자 정정으로 전체4번째의 Native 재기획·사용자 확인 요청을 추가했으며 해당 회신은 대기다.

관련 격리 검증은 고유23개 PASS(20·6·1 실행 중4개 중복), 두 전체 OpenAPI 객체 비교 PASS다. [검증 집계](roster-participation-verification.json)에 초기 실패·수정과 실행별 소스 경계를 보존한다. 신규 공개 API/부분 완료 후 교체는 미구현이며 기존 전체 미완료 대상의 교체만 검증했다.

시험 결과·실패/수정·남은 후속은 [DEV_LOG](../../../project/DEV_LOG.md), 현재 다음 실행은 [NEXT_WORK](../../../project/NEXT_WORK.md)에 기록한다. 계약 회신 후 공개 API/두 OpenAPI·부분 완료 교체를 포함한 소비 경계를 마무리한다.

## 외부 근거 재확인

2026-11-08 공식 [FAQ](https://developer-lostark.game.onstove.com/faq)의 데이터 동기화 지연 안내를 재확인했다. 이를 대기시간 경과 후 삭제 확정 보장으로 해석하지 않는다. 공개 Swagger는 이번 웹 도구에서 읽기 실패했으며 새 ID/삭제 사건 보장 확인으로 표시하지 않는다. 기존 [공급 API 증거 조사](../../../archive/work-records/features/ownership/ISSUE_8_PROVIDER_EVIDENCE_REVIEW.md)를 재사용하되 새 명시 보장은 확인되지 않은 상태다.
