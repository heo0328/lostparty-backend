# 다음 실행

2026-10-25

- **작업 구간명:** 신청자 아이템레벨 누락 보완(#26).
- **작업 내용:** 실제신청snapshot에item_level을저장하지않는누락을확인했다. 신규snapshot/기존누락 읽기보완의값·출처·시각계약을제안하고소비차이확인후구현한다. 기존프로필개발반영은완료상태다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 기능코드·문서·시험·인계를같은이력으로관리한다.
- **현재 실제 개발:** API source06ea4b214591f475d422f4599ca10260cda83d08/이미지d24d7cbd…·177경로/DB0031, 새 application-display-1 포함·API/DB healthy. [반영 근거](../engineering/operations/application-display-rollout.md)·[집계](../engineering/operations/records/application-display-rollout.json). 문서/예시보완source13ae0a5와API source를구분한다.

[#26 전체18번째 Backend · 표시 프로필 실제 개발 반영](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386031663) 게시·전문/실제전체순번 확인 완료. 반영근거 `6444c18bc3de8b341251169f84584cb622b69154` commit·push·원격일치 확인, 다음Flutter 정상로그인소수인수/Backend 직접차이대응이다.

[#26 전체20번째 Backend · 아이템레벨 출처/기존누락 보완 제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386261019) 게시·전문/실제전체순번 확인 완료. 제안source `b97eee2aa813a330d740318026617005dbac1c5e` commit·push·원격일치확인. 미합의/미구현·레벨미해결이며다음Flutter 최소소비차이확인후Backend 구현이다.

## 최신 전체19 · 아이템레벨 보완 계약 확인

[전체19 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761)에서 사용자표시1/2는아이템레벨‘확인필요’외정상보고를수신했다. clean문구‘세팅이상없음’/‘좌석미확정’삭제는Flutter58600023 commit/push/분석0 보고이며최종기기확인대기다. Backend실행06ea4b2의공용identity.display가3필드만저장하고목록이그대로반환하는누락을확인했다. 개발DB읽기집계7신청모두snapshot item_level없음·회원식별자/원본출력·자료수정없음이다.

[최소보완제안](../features/recruitment/participation/application-item-level-proposal.md)은기존display동적map3키(item_level/source/fetched_at)를정의한다. 새신청은모집Application에서만snapshot캡처, 기존누락은동일owner/revision·confirmed/active의현재저장값을current_saved로명시하여read-only보완한다. 과거snapshot은보존하고자료없음/소유변경은unavailable/null이며원본시각을만들지않는다. 공용identity/그룹/Assignment에확대하거나DBbackfill·provider·추가SQL을하지않는다.

현재제안·미합의/미구현이며API/OpenAPI·서버/DB미변경이다. 작성fragment9개정적검증은실행시험이아니다. 다음Flutter는동적map metadata와snapshot/current_saved의표시소비차이만확인하고Backend는합의후저장→실제HTTP목록까지직접구현·검증·게시인계한다. 정상1/2전체·413반복/파서완화/자격정책재수용은요청하지않는다.

## 기존 개발반영과 인수 경계

[전체16 Flutter 앱연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385536441) ac9fe621 push·413PASS/분석0은자체보고다. 연결/합성시험과새프로필실서버·실회원/기기를구분한다. 다음은 이미연결한앱에서사용자소수항목을확인하는것이다.

1. 공대장신청목록 카드의선택역할전투력·현재분석/미확인표시를확인한다. 오류/성공보존·미확인과전체승인가능판정을구분한다.
2. 본인pending방상세재진입시승인대기안내와신청버튼숨김을확인한다. 다른T·다른회원정보를섞지않는다.
3. 철회/만료·수락후기존흐름은그상태가발생할때확인한다. 시험을위해실회원자료를임의변조하지않는다. 기존가입3항목/413전체시험을이유없이반복요청하지않고변경·반대파티/C/N직접영향은계속추적한다.

차이가발생하면#26에개인정보를제거한상태/code·재현구간을회신한다. Backend는직접차이에대응한다. 일반오류원인은HTTP/code미확인관찰로남기며이번배포를원인수정완료로확대하지않는다. 목록진입/갱신·실시간/웹소켓/알림은이번범위에서바꾸지않았다.

## 검증·보존 경계

- 이번반영: 소스241파일·실제컨테이너177/기본116 OpenAPI 전체일치, HTTP12건 통과. API중지후백업/catalog읽기·DB불변확인→교체, 전후108표829행/열·시퀀스·DBprofile·키hash동일, DB컨테이너/볼륨·환경/명령/포트/보안·키mount/readonly보존·migration없음이다. 이전API fdd256ea는rollback태그로보존했고임시reader제거·기존API/DB만남았다.
- [전체14 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385227653)의격리28PASS와 [전체17 예시보완](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385820194)의추가12PASS/정상22·비정상23/원본8거절은별도근거다. Flutter413자체보고·기존시험과합산하지않는다.
- 정상로그인실회원조회200/기기인수는미확인이다. 실제회원session으로토큰을만들거나회원명령·provider/기기조작을수행하지않았다. 원pending/ACK/거절·철회·기존membership프로필/기록·IF-001을보존한다. 1~5는수동시험분량이지구현/필요회귀제외기준이아니다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

새표시프로필 개발반영은완료했다. 같은모집브랜치에서#26 정상로그인/소수기기인수 회신과직접차이에대응한다. dev/main/운영·DB자료/키수정은별도승인범위다.
