# 다음 실행

2026-10-24 / **feat/raid-recruitment** / [#13](https://github.com/heo0328/lostparty-backend/issues/13), [#22](https://github.com/heo0328/lostparty-backend/issues/22), [#23](https://github.com/heo0328/lostparty-backend/issues/23) OPEN.

## 다음 담당 Backend — 선택T 참가 방 검색 제외·새 탈퇴/해산 계약

2026-10-24 최신 수신은 [정리 문서](../ISSUE_13_OCT24_NATIVE_FEEDBACK.md)를 따른다. [#13 전체135번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6366977367)의 검색제외와 [전체136번째 Flutter 사용자확정 전달](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6367266418)의 새 탈퇴/해산이 Backend 선행 작업이다. **136번째가 이전 사전위임/마지막1인 해산·다인해산 제외 제한을 대체**한다. 아직 새API/구현/개발반영은 없고 현174경로/DB0030과 구명령·pending/원ACK를 유지한다.

- 검색: 선택T/현generation의 본인 실제참가(필요review포함)를 SQL페이지전 제외. 반대T/단순지속·legacy/not_selected/취소는 구분, 비로그인/필터/정렬/커서·탈퇴후재노출/기존회원읽기는 보존한다.
- 선택T탈퇴는 C/N허용·사전위임없이 실제참가순 자동승계/빈T종료·반대T보존. 모두탈퇴는 본인양T/지속관계를 한명령으로정리·각T승계/빈T종료다. review/부적격후계도 탈퇴를막지않으면서 권한을확대하지않는 복구상태를설계한다.
- 해산은 본인이공대장인 모든C/N주차의 전원탈퇴/종료·다인허용. 비공대장T는보존, Context/확인/명령/ACK에대상집합고정. 모든유효T종료시Room/지속관계/한도정합성과 완료·감사·기록을보존한다. 구end/leave/cancel API의원효과/원명령·24hACK는새endpoint/version등으로호환보존한다.
- 다음Backend는현재구현대조→주제별추적·정확한계약/호환·권한/복구설계회신→합의범위구현/표적검증/게시·개발상태인계다. 다음Flutter는인계뒤버튼/새명령·영향T갱신/성공이탈정합화를진행한다. 이번확인만으로새정책을기존본문에적용하거나서버를바꾸지않았다.

Flutter D22/E23/A/B는 구현·자동경계완료 보고수신: #22 Flutter5 fece2003/133mock, [#23 Flutter5](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6363846643) b6720079/178mock, [#13 Flutter133 A](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6364089791) e9d2783d/94mock, [Flutter134 B](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6364976336)797c16b3/159mock·각분석0. 서로중복합산/Backend독립재현·전체실인수로확대하지않는다. N단독생성 앱수정407328ef/21mock 보고·수정본실행미확인이다. C단독/C+N생성·기존마지막1인해산은사용자정상보고, 다인승계등은추가회원부족으로미확인. 실회원/기기전체·성능/dev/main/운영·Issue종료는미완료다.

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
