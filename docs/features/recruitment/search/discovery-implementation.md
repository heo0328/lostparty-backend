# 모집 탐색 discovery-1 구현·로컬 인계

2026-11-12 KST / Issue50 / `feat/recruitment-discovery`. 작업 구간은 기존 검색 API 개선·단계 전환이다. [Native 전체4 수용](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820418957)으로 기본 제안과 카드 보완 계약을 고정했다. [제안/수용 전 원문](discovery-api-proposal.md), 정확한 공개 타입/상한/nullable은 [two-cycle OpenAPI](../../../../openapi/two-cycle.openapi.yaml)를 따른다.

[전체5번째 Backend 결과 회신](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6821288801) 게시·순번/본문 재확인 완료. 다음 Native 적용과 원격 게시 대기를 구분한다.

## 구현과 소비

새 endpoint는 없다. POST `/v2/raid-rooms/search`에 `response_profile=discovery-1`을 지정한다. 생략 시 기존 응답을 유지한다. 권고 조합은 `contract_profile=beta-recruitment-1&group_policy_version=cycle-group-policy-1&include_group_state=true`이며 response_profile을 context/candidate/상세/GET 목록에 보내지 않는다. Native의 limit/행 검증20개를50개로 바꾸되 상세·신청/권한은 기존 API를 쓴다.

기존 조건 정규화·권한·실제T/세대·그룹/캐릭터/정수분 필터·본인 참가 제외 SQL을 공통으로 사용한다. 같은 REPEATABLE READ/READ ONLY 트랜잭션에서 전체 filtered distinct room count와 정렬된 limit+1행을 읽는다. 목록 전체를 앱 메모리에 올리거나 카드별 상세를 선조회하지 않는다. 인원·항목/일정·대표·베타 일정/그룹정책은 페이지 단위로 일괄 조회한다. 기존 rich 카드와 full beta_schedule을 생성한 뒤 버리지 않는다. 일정 시각/상태 판정은 기존 상세와 순수 projection 함수를 공유하고 기존 상세용 시간 후보 계산은 검색에서 실행하지 않는다.

scope는 유지하고 data에 items/total_count/directory_revision/filter_scope_digest/result_revision/next_cursor/evaluated_at을 반환한다. closed DiscoveryCard는 합의된 최소 카드와 schedule/coordination_progress·view_detail_permission을 담는다. include_group_state=true이면 최상위 group_states/cycle_groups 필수 배열, false/생략이면 부재다. 옛 room_groups로 fallback하지 않는다. CoordinationProgress의 status/정수|null 관계는 Python validator와 OpenAPI oneOf 양쪽에 명시했다.

새 cursor namespace는 회원·세션·실제T·profile·정규화조건/limit·권한/context·directory/clock 세대와 결합하고 total_count도 result_revision에 결합한다. 같은 세대의 변경은409, 다른 scope/위조는400이다. 기존 cursor와 교차 소비하지 않는다. 추가 페이지 stale 시 첫 페이지/count/cursor를 전부 교체한다. 60초는 첫 수신부터이며 추가 페이지가 연장하지 않는다. 조건부 조회·count/검증 endpoint·polling을 추가하지 않았다.

## 검증과 측정 범위

[검증/로컬 보존 집계](discovery-verification.json)와 [합성 성능 원본](discovery-performance.json)을 따른다. 신규 시험은0/1/20/50/102개·50/50/2 페이지 집합·인원/자리·본인 실제 참가 제외·기존 strict 응답·profile/위조/주차·clock stale·그룹 매핑/조율·열람권한·중간 동시 쓰기·candidate/context 오류 선검증이다. 기존 그룹정책/후보·분검색·조율 시험을 함께 확인한다. 초기 시험 보조 코드의 중복 keyword·그룹생성 시점/생략 필드 변형 오류는 수정 후 관련 신규 시험을 재실행했으며 업무 실패를 숨기기 위해 정책을 바꾸지 않았다.

합성 자료는102개 공개 target(베타1/최소 legacy101), 활성 assignment lease1개다. 단계별 warmup1회+반복10회 ASGI TestClient의 전체/SQL/count/projection/render·bytes를 분리 측정했다. 실제 사용자 환경·운영망·캐시 cold 상태·50개 베타/밀집 그룹 조합·운영 크기의 깊은 offset은 미측정이다. 개선 수치는 이 합성 조건에 한정한다. count 단독 EXPLAIN ANALYZE/BUFFERS 수치도 별도 원본에 있다.

## 로컬 실행·게시 경계

로컬 Docker가 꺼져 있어 기동한 뒤 기존 API/DB healthy를 확인했다. 검증 이미지의 앱 파일 전체가 현재 소스와 같음을 확인하고 로컬 API만 교체했다. DB0036·컨테이너/기존 테이블·환경/키4개·API 포트/명령을 보존했고 migration·자료삭제·키 생성·운영 변경은 없다. 첫 교체는 환경 배열 순서까지 비교하는 검사 때문에 자동복귀했으며 실제 값 동일성을 확인한 뒤 정렬을 정규화해 재반영/보존 검사를 통과했다. 기존 사본 재사용과 로컬 DB dump 제외 방침을 유지한다. 보존 해시는 DB백업/복원 시험이 아니다.

실행 이미지/앱 manifest 식별과 두 전체 계약 hash는 집계에 기록한다. 실제 로컬 공개 검색의 새/기존 DTO·401/400·no-store와 두 전체 생성계약을 확인했다. 실회원 명령/기기 인수는 수행하지 않았다. 개발 DB의 반영 시점 행 수를 이후 고정값으로 보지 않는다.

**새 구현 commit SHA는 아직 없다.** HEAD b03595a는 기반 커밋이며 업무 구현 SHA가 아니다. 코드/계약/문서는 로컬 미커밋·미push, dev/main 미통합이다. 실제 로컬 API 연결 가능과 원격 고정 소스/계약 게시 가능 상태는 구분한다. 사용자 직접 게시 지시 전 새 SHA/원격 계약 소비 완료로 인계하지 않는다. 운영 배포는 별도다.

다음 Native는 합의된 discovery DTO/캐시/화면 연결을 진행하고 원격 고정계약 게시 전에는 이슈의 계약과 로컬 API 준비 상태를 구분한다. 구현/검증 결과를 같은 Issue에 회신하며 실제 기기 인수와 Backend 자동/로컬 시험을 구분한다. Backend의 다음 게시/통합은 사용자 지시 범위다.
