# 활성방 한도·자동조율 대기 안내 구현

2026-10-26 / 작업 구간 **활성방 한도·조율 선택조회 구현·직접검증·인계** / `feat/raid-recruitment`.

[전체171 Flutter 확정 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6412692643)과 [합의 상태표/선택 DTO](active-room-and-wait-proposal.md)를 구현했다. join 후보690f36f는 유지한다. 소스 구현과 실제개발반영은 구분하며 정확 source/이미지·push/반영기록은Issue13의최종인계를따른다.

## 활성방 공통 판정

active_usage의같은 SQL predicate를 두 현재목록의페이지전필터·개인한도조회·명령의신규단위판정에서재사용한다. 서버시각C/N, 미종료방/지속관계·비archive, 현재세대/실제CM의participating/review_required·open/review_required를포함한다. 양쪽null세대도현재목록기준대로처리한다. 같은room C/N중복제거·과거/기록/관계전용/종료만남은방제외이며일시자격/권한/조회실패를집계제외로바꾸지않는다.

기존persistent관계로신규한도검사를건너뛰던조건을현재활성집합의room존재여부로바꿨다. pending미차감·승인시검사, 기존집계방의반대T참가는추가차감없음이다. 명령의같은game-mutations잠금/고정서버시각에서변경전후의영향회원집합을비교해실제증가를최종검사하고기존usage head를필요시갱신한다. 같은명령의기존갱신을중복하지않고원ACK조회/재생은새검사/변경보다먼저돌려준다. 삭제/해산의다른회원도대상이며주차가도중바뀌면기존CYCLE_CHANGED로롤백한다.

한도숫자/DTO·오류코드·DB0032/자료는그대로다. 새사용량저장값/보정·migration은없다. 정책반영만을위해개발계정usage head를임의수정하지않고이후실제명령의집합변화에갱신한다. 시간C/N에따른파생값이므로조회는기존evaluated_at과함께읽는다. 구0023/전환전시험환경은기존비주차집계경로를유지한다.

실자료후보대조중 `/v1/me/usage-limits`의구0023전용readiness가0032에서503을내는직접연계결함을발견해프로필별기존readiness로분기했다. 현재two-cycle은전체실행준비검사를사용하고0023기본앱은종전검사를유지한다. 제보계정의최종후보READONLY대조는한도10/사용3, 현재C2/N2·두reader합집합3이일치했다. 과거7관계종료/삭제나실제회원명령은없다.

## 조율 선택조회와 공통 평가

베타상세/plan GET에만include_coordination_wait=true|false(기본false)를지원한다. 기존reader와조합하며true일때만기존beta_schedule 안에 [CoordinationWait](proposals/coordination-wait.schema.json)를제공한다. 생략/false·기존beta_schedule=null/기록content=null·일반검색/목록/쓰기ACK는유지한다. 잘못된위치/값·profile없는새query는400이고기존권한/no-store를유지한다.

현재CM과실제참가근거를대조해누락회원을분모에서조용히제외하지않는다. 실제전원/세대·복사표/진행시간·예약·출발하한을기존자동조율과같은내부평가로계산한다. read-only snapshot에서만해당row/revision/시각평가를재사용하고명령/다른조회에는캐시하지않는다. 기존candidate adapter의ready/no_candidate와시각필드는보존한다. 개인표명시unset은전시간가능, 복사누락/불일치/불량표·자격근거부족은unavailable, DB예외는기존오류로전달한다. GET은자동확정/저장하지않는다.

| status | missing_members | 의미 |
|---|---|---|
| waiting_members | 양수1~8 | 실제참가인원미달 |
| no_earlier_candidate | null | 정상판정완료/더이른후보없음 |
| pending | null | 유효후보미확정 또는기한처리대기 |
| unavailable | null | 정상판정근거부족 |
| not_applicable | null | OFF/확정/종료/검토필요 |

확정/종료/검토/OFF→기한처리대기→판정자료/인원→후보의합의된우선순위를사용한다. 부분그래프비교는실제분모에반영하지않는다. 후보판정이완료돼도임계미달이면인원안내를, 정상충족후후보없음일때만기본유지안내를제공한다. 안내문장은네이티브가표시한다.

## 계약·검증·인계 경계

기본116경로/133operation·현재178/199유지. 기존실행schema에서는BetaScheduleView의선택속성만추가하고CoordinationWait를신설했다. query는기존두GET에만추가하며모든쓰기operation/원ACK는변경하지않는다. 실행OpenAPI·합의closed DTO·기존123개완결예시(기존118+다섯상태5)를대조한다.

직접고유18개PASS(한도7·조율6·관련기존5). 9→10/11거절·C/N생성/합류·기존관계우회방지·동시생성/승인·상대회원해산/원ACK/실패롤백·과거/검토/주차·기존한도조회, 다섯상태/기존reader·query/권한/null/평가1회·DB실패503·GET쓰기0·기존자동확정/예약을검증했다. 합성fixture의FK삽입순서와기록anchored식별자를수정후해당실패만재검증했다. 첫후보실자료503은readiness보완뒤직접2시험과READONLY재대조를통과했다. 마지막oneOf추가는schema명시이며DTO정상5/오류6으로검증했다. 두OpenAPI전체일치·정적12/lock·제안48/문자32·wire123/원ACK32·문서/diff PASS다. 기존Starlette/AnyIO경고유지·전체pytest미반복.

위후보/합성검증은실제API교체/정상회원HTTP/기기성공이아니다. 다음같은목적브랜치에서묶어commit/push→후보runtime소스/계약/패키지검증→사용자승인된API만교체/실행확인→고정소스/이미지/대표예시인계다. DB/키/환경·원ACK를유지한다. 원ACK동일키매칭·전체기기/성능·dev/main/AWS는별도미완료이며자료변환·삭제/복원은없다.
