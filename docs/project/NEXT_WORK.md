# 다음 실행

2026-10-24 / **feat/raid-recruitment** / [#13](https://github.com/heo0328/lostparty-backend/issues/13), [#22](https://github.com/heo0328/lostparty-backend/issues/22), [#23](https://github.com/heo0328/lostparty-backend/issues/23) OPEN.

## 현재 — #24/#25 구현·격리 검증, 실제 개발 반영 전

사용자 구현 진행 지시와 [#24 전체3번째 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6370137482)·[#25 전체5번째 Flutter 네 차이 해소](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6370138718)를 확인했다. 네이티브의 계약 재수용을 기다리는 상태가 아니다. [개발 안내](../ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md)를 현재 구현 기준으로 사용한다.

- Backend 소스: 검색 SQL 페이지 전 본인 실제T 참가 제외·semantics cursor, 새 옵션별 Context/6필드 원자 명령·C→N ACK, 승계 불가 탈퇴/명시 복구, 방·지속관계·한도, opt-in reader/본인 종료 기록을 구현했다. 같은 지속회원의 재참가도 옛 CM/Assignment 식별자를 재사용하지 않도록 보강했다. 실행 후보 계약176경로·기본116/기존 component·구 명령/pending/24h 원 ACK 보존이다.
- DB 후보0031: 리더 복구/불변 감사2표와 현재 CM/Assignment partial unique를 추가한다. 기존 행 재작성/초기화 없이 임시 PostgreSQL·비관리자 역할에서 이행과 실제 ASGI 시작을 검증한다. 최종 고유38PASS(신규21/검색11/기존6), 합성 실행 응답7개 schema 대조·기본116/후보176 전체 계약·실제 후보 ASGI 시작/health·인증3건 검증 완료. 게시 SHA/결과는 DEV_LOG에 기록한다.
- 실제 개발 서버는 API92490ff3…/174경로·DB0030이고 두 컨테이너 healthy, 새2표 없음 확인. 구현 후보 이미지/합성 DB와 구분한다. 기존 개발 API·DB에 0031 이행/이미지 교체·실회원 쓰기를 실행하지 않았다.
- 다음 Flutter: 게시된 source/176계약으로 전용 DTO·원 명령/ACK → 메뉴/성공 화면/관계 종료 알림 → profile/기록 Router를 연결하고 직접 영향의 자동 검증 결과를 #24/#25에 회신한다. 실제 서버 연동·실회원/기기 인수는 개발 API/DB0031 반영 확인 뒤다. 기존 정책/전체 시험 재수용은 요청하지 않는다.
- 다음 Backend: 구현/자동 검증·게시 구간을 마감하고, 별도 개발 반영 구간에서 기존 자료 보존·0031 이행/API·worker 호환/실행 계약을 확인한다. 재현 가능한 소비 차이가 오면 해당 범위에서 대응한다. dev/main/운영·자료 삭제는 미진행이다.
- [IF-001](../INACTIVE_FEATURES.md): #13 전체139번째 사용자 최종 결정 전달에 따라 close_weekly/weekly_resume 앱 신규 진입을 비활성 보존으로 분리했다. endpoint·권한/자료·원 pending/ACK는 유지한다. 다음주 reopen/#25 recover_leadership과 구분하고 복구 UX는 제품 미승인 제안으로 유지한다.

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
