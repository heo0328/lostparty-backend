# 다음 실행

2026-10-25

- **작업 구간명:** 신청 표시 상세 예시 정합성 보완(#26).
- **작업 내용:** 작성상세8개 item/round참조정정·음성보존·검증도구/직접HTTP12PASS 완료. 소스게시·같은Issue회신후 별도개발반영 구간으로 이어간다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`. 문서·시험도동일이력으로관리한다.
- **API 기준:** 구현source06ea4b214591f475d422f4599ca10260cda83d08/검증후보d24d7cbd… 소스241파일일치·이번app/쓰기DTO/OpenAPI/migration변경없음. 실제개발fdd256ea…/source484ca17·177/DB0031은새프로필미반영·healthy. 경로수가같아도동일계약/배포완료가아니다.

## 최신 회신과 보완 결과

[#26 전체16 Flutter · 연결 결과/예시 참조 보완 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385536441) ac9fe621ed67aaafbcd8449fddfe17f2bce54c7e push·413PASS/분석0은자체보고다. 기존가입3항목성공·새앱연결/합성시험·새프로필실서버/실기기인수를구분한다. 전체15의2bdf9976은준비문서였고전체16에서연결완료를보고했다.

[표시계약/정정](../features/recruitment/participation/application-display-proposal.md)·[추가집계](../features/recruitment/participation/validation/application-display-reference-results.json). 정상22개중상세8개의room.items/game_items만정정·my_application과나머지자료유지. 원본Git이력/별도음성8개를보존했다. 정적검증22정상/23변이·8원본거절, 추가pytest12PASS=11HTTP사례22응답+과거round규칙1건(99.56초/기존경고1)이다. 기존28·Flutter413·작성자료를합산하지않는다.

참조검증은항목/현재라운드·Assignment/formation·공대장/본인을확인하고과거완료round를현재round로강제하지않는다. HTTP각사례에서기본/프로필공통부분일치·읽기DB불변을확인했으며실행응답에서같은결함은재현되지않았다. 합성principal override/FastAPI TestClient·격리PostgreSQL이며정상로그인회원/기기결과가아니다. 시험runner/tmpfsDB/internal network정리·기존API/DB만남음을확인했다.

## 다음 담당

- **Backend 현재 마감:** 보완자료/시험/문서commit·push·원격확인후#26에정확SHA와예시/실행확인결과를회신한다. 기존API source06ea4b2와이번자료보완SHA를구분한다.
- **Backend 다음 구간:** 별도개발서버반영승인시후보이미지/현재소스·DB0031·환경/키·백업/보존기준을재확인하고API/동일worker만교체·실행계약/HTTP·기존자료보존을검증해인계한다. 현재요청은예시보완이며실제서버교체를수행하지않았다.
- **Flutter:** 연결은완료보고상태다. 보완8개가필요한자료에반영됐는지만확인하고, 정확개발반영인계후카드값/분석·pending재진입·철회/만료/수락후흐름을소수항목으로인수한다. 기존413전체반복/정책재수용/파서완화는요청하지않는다.
- **보존:** 원pending/24hACK·거절/철회·회원/session·room/T/세대·기존membership프로필/기록·IF-001. 목록진입/갱신·실시간/웹소켓/알림과HTTP/code미확인일반오류원인수정은범위밖이다. 1~5는수동시험분량이지구현/회귀제외기준이아니다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

보완자료공식회신·실제개발새프로필미반영을구분한다. 같은모집브랜치에서새회신/직접차이를확인하고별도승인된개발반영구간을진행한다. dev/main/운영·DB자료/키수정은별도승인범위다.
