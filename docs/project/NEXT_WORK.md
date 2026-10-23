# 다음 실행

2026-10-24 / **feat/raid-recruitment** / [#13](https://github.com/heo0328/lostparty-backend/issues/13), [#22](https://github.com/heo0328/lostparty-backend/issues/22), [#23](https://github.com/heo0328/lostparty-backend/issues/23) OPEN.

## 현재 — #24/#25 계약 보완 회신 완료, 기능 구현 전

- #24: [검색 계약](../ISSUE_24_SEARCH_CONTRACT.md)으로 기존 요청/응답 shape, 선택 실제T/현 generation의 SQL 페이지 전 제외, semantics 표식·영향 T head/커서 경계를 고정했다. [전체2번째 Backend · 검색 계약 보완](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6369761914)에 회신했다. Flutter 전체1번째의 blocking 변경 요청은 없으며 자동 첫 페이지 회복은 아직 앱 후속이다.
- #25: [계약 보완안2](../ISSUE_25_CONTRACT_REVIEW_V2.md)와 [closed schema](../design/issue25-membership-actions.contract.schema.json)·[합성 예시37개](../design/issue25-membership-actions.contract.examples.json)를 작성했다. 옵션별 접근 격리, planned 상태/revision의 유지·증가 증명, 명시 복구 reader, 종료 본인 기록/탈퇴·재가입 locator의 네 요청에 답했다. [전체2번째 Backend · 계약 보완](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6369762510), [전체3번째 Backend · 예시1/2](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6369763243), [전체4번째 Backend · 예시2/2](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6369763925) 전문 게시와 손실 없는 원격 대조를 완료했다.
- 다음 Flutter: 새 opt-in `reader_profile=membership-actions-1`/revision·기록 소비에 남는 구체 차이가 있으면 #25에 회신한다. 기존 제품 정책 재수용이나 기존 시험 반복 요청은 없다. 복구 UX는 별도 제품 승인 전 제안이다.
- 다음 Backend: 회신에 구체 차이가 있으면 계약을 보완하고, 구현 지시 후 검색 SQL/커서와 새 원자 명령·reader·audit/recovery 이행을 해당 범위로 진행한다. 현재 사용자 지시는 기획·설계이며 기능 구현/DB 이행/서버 반영·실기기 시험 요청은 하지 않았다.
- 검증: JSON Schema2020-12 정합성, 합성 wire37개·Impact→ACK9쌍·기존 reader 참조2건·거부 경계4건 정적 검증. 기존 실행 OpenAPI 두 파일은 HEAD와 바이트 동일하다. 합성 자료는 실제 서버 응답/동작 시험이 아니다. 문서 로컬 커밋·미push, 코드/서버/DB 변경 없음.

원본은 [#13 전체135번째 검색 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6366977367)·[전체136번째 사용자 확정 정책](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6367266418)이며 [전체137번째 Backend 설계/후속 이관](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6368822874)에서 독립 완료 조건으로 #24/#25를 연결했다. [설계안1 검색](../ISSUE_13_SEARCH_EXCLUSION_DESIGN.md)·[설계안1 탈퇴/해산](../ISSUE_13_MEMBERSHIP_ACTIONS_DESIGN.md)은 배경으로 보존하되 wire는 보완안2가 우선한다. 구 cancel/leave/end·D22/E23 pending/24h 원 ACK와 현행 174경로·DB0030은 보존한다. OPEN 이슈와 실제 인수 미완료는 기능 완료로 표시하지 않는다.

기존Flutter D22/E23/A/B는코드·관련자동경계완료보고/실기기전체인수미완료다. #13의전체135실기기와136최신정책원문·보고SHA/각시험수는 [수신정리](../ISSUE_13_OCT24_NATIVE_FEEDBACK.md)를따른다. 현Backend소비0eed67c/174·DB0030은유지한다. #13/#22/#23/#24/#25 OPEN·dev/main/운영/데이터삭제없음.

아래는 기존 Backend 인계 기준이다.

[개발 안내](../ISSUE_22_23_ATOMIC_MEMBER_ACTIONS_DEVELOPMENT.md), [OpenAPI174경로](../../openapi/two-cycle.openapi.yaml), [합성예시17그룹](../design/issue22-23-atomic-member-actions.examples.json)이 기준이다. [#22 전체2번째 Backend 표시 보완](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6361940655), [#23 전체2번째 Backend review 보완](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6361941083)을 구현했다. 같은 정책 수용을 다시 요청하지 않는다.

- #22: Context에 동일스냅샷의 character/raid/난이도·효과와 display_revision을 결합했다. 선택1개만 완료·잔여본인T취소·실제탈퇴/자동승계·후계없음 전체거절·마지막completed/incomplete/null리더, 다른T/지속회원/기존완료 보존이다. Flutter는 전용reader/ACK와 표시/영향 의미 비교·원본문 재송·성공후 member-only plan 미의존/상세이탈 연결 완료를 보고했다. 실회원·기기 인수는 남아 있다.
- #23: 실제CM/양수gen·관계/lease가 확정된 source review는 현재 자격있는 공대장의 current_only 정리를 지원한다. 불확정관계는 ROOM_REVIEW_REQUIRED, 반대review/미확정gen/actor없음은 정확한 status와target=null이다. 각T권한·option별token/current_only 반대불변·both 전체원자 ACK를 제공한다. Flutter는 기존 취소/현재만/함께 선택·mode별 의미 비교/무효화·전용ACK를 연결하며 자동fallback하지 않는다.
- 최종 고유39PASS(신규33/기존회귀6), 예시42개 게시schema/format검증·기본116/두주차174 실행계약일치·230소스 이미지일치. 실제 API92490ff3… healthy/DB0030, 교체 전후106표476행 내용·열정의·설정보존, 새4경로 인증거절8검사/health200. migration/DB재시작·실회원쓰기/키변경 없음. 임시시험환경정리 완료.
- 소비 `0eed67c453040b332653fd2071e6cd2e1eeed503` commit/push·GitHub 원격SHA 일치 확인 및 [#22 전체3번째 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6362447014), [#23 전체3번째 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6362447457)의 전문/실제순번 확인 완료. D22/E23 연결결과는 수신완료이며 실제 인수는 별도다. 다음 실행은 위 새 Backend 요청을 따른다. Backend는 재현 가능한 차이에 대응한다. 새 동작의 정상실회원 HTTP·실기기·성능·운영 인수는 미확인이며 같은 기존시험을 반복 요청하지 않는다.
- 당시 마지막1인해산/다인제외는 위136번째 정책으로 대체됐다. 구API/원ACK 효과는 보존하고 새행동은 별도계약으로 구현한다. #13 원본의 통합모집 인수·기존129 완료정정/보관 연결은 별도 유지하며 세 Issue를 이번 Backend 구현만으로 종료하지 않는다.

## 기존 인계·별도 후속

- 완료정정/보관 소비8bbcfc8: [Backend129](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618)·[개발안내](../ISSUE_13_COMPLETION_CORRECTION_DEVELOPMENT.md). 본인 manual/party 완료근거 정정과 실제 완료 기록/참가 복원은 구분한다. Flutter A/B 연결결과는133/134번째로 수신했고 실제인수는 별도이며 기존 pending/원ACK를 새명령에 강제 캐스팅하지 않는다.
- F6-C 소비2940824: [Backend121](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356827586), [Flutter122](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6357361150) 연결/mock 보고수신. F1~F6 전체 정상회원·기기 인수/성능과 모집관리 pending 앱종료 후 영속복구는 미완료다. 과거 시험/보고 상세는 [DEV_LOG](DEV_LOG.md)를 따른다.
- #19 통계, #17 생명주기, #18 활동정책 등 독립후속은 [추적표](ISSUE_TRACKER.md)를 따른다. 이번구간으로 범위를 확대하지 않는다.
- Issue21은 내용전달/문서정리로 종료했고 추가회신·수용대기가 없다. 승인된 후속에 [품질/UX 기준](../DEVELOPMENT_QUALITY_AND_UX_STANDARD.md)을 적용한다. 릴리즈/안정 확인 후 배포main/태그 기준의 별도 최적화 검토시점 안내는 남아 있다.
- 재기동은 compose.yaml+compose.two-cycle.yaml/two-cycle factory/DB0030이다. 기본0023앱·구worker 혼용, 과거snapshot 덮어쓰기/초기화, dev/main merge·운영배포는 이번 범위가 아니다.
