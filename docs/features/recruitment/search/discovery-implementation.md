# 모집 탐색 discovery-1 구현·로컬 인계

2026-11-12 KST / Issue50 / `feat/recruitment-discovery`. 작업 구간은 기존 검색 API 개선·단계 전환이다. [Native 전체4 수용](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820418957)으로 기본 제안과 카드 보완 계약을 고정했다. [제안/수용 전 원문](discovery-api-proposal.md), 정확한 공개 타입/상한/nullable은 [현재 OpenAPI](../../../../openapi/openapi.yaml)를 따른다.

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

**업무/계약 고정 SHA는 `558ee6da4299dea49729ebaca5825ce9a235a42e`이며 사용자 직접 지시로 commit/push·원격 tip 일치를 확인했다.** 기반 b03595a와 구분한다. [전체7 Backend 고정계약 인계](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6821559025)로 Native전체6의 실제파일위치 요청에 [고정 OpenAPI](https://github.com/heo0328/lostparty-backend/blob/558ee6da4299dea49729ebaca5825ce9a235a42e/openapi/two-cycle.openapi.yaml)와 정적원본 다운로드 링크/hash를 회신했다. 후행게시결과기록은같은목적브랜치에보존한다. dev/main미통합이며운영배포는별도다.

전체5 당시 미커밋/미push 기록은 당시 상태다. commit/push가 업무 소스·계약 bytes나 실행 image87a918db…5c0bd/DB0036을 바꾸지 않으므로 로컬 API 재반영/동일 시험을 반복하지 않았다. 공개 OpenAPI 파일의 GitHub blob도 로컬과 같은 e25f771885d50105c928059d89c1c06caf238378이다. 파일 SHA256은 3fdc06616d64e19aa7abf35b548cf1156fa7fbee6bcfb02c1dccf4ce9a9d7052다.

## 최종 소비 확인·미진행 점검

[Native 전체12](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826309269)는 Flutter 최종 dev83a550204dd442ec2ce54a01c79c2c485106b472 게시와 discovery-1 소비/화면·캐시 연결·담당자보고2927PASS/analyze0·사용자 필터 성공 보고/Penpot02 통합을 인계했다. 목록 전체/일반/그룹·인원정렬은마지막적용조건으로즉시검색하고 상세필터초안은분리한다. 고정계약/Backend변경요청·충돌은없다.

[전체13 Backend 최종점검](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826448910)으로 합의 기능 구현·Native 적용/보고된 사용자 확인 완료와 추가 협업 요청 없음을 회신했다. 미진행 기능이나 Native 대기는 없다. Native검증/사용자보고를Backend대리시험/전수기기·신청·성능인수로확대하지않는다. 현재 코드/시험/계약hash가기존검증기준과같아재검증·재반영을반복하지않았다.

## 사용자 승인 Git 통합·마감

사용자명시지시로최종확인문서011375bf를커밋하고업무558ee6da와함께dev `0dc381ae646fba062f008d26c58b20e653a6de67`에이력보존병합·push/원격일치·작업tip포함/동일tree를확인했다. Issue50은2026-11-12T14:52:57Z(KST23:52:57) completed종료. [전체14 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036) 게시·실제순번확인, 현재checkout은dev이며feat/recruitment-discovery를로컬/원격에서정리했다. 다른작업브랜치는보존한다.

마감결과기록은dev의후행문서커밋으로보존한다. 업무/계약·로컬실행은기존검증기준과같으며이번마감으로main/운영·DB/키·기기인수를변경하지않았다. 추가협업대기는없다.
