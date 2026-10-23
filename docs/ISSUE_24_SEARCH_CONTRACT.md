# Issue24 검색 계약 보완1 — 기존 shape/semantics·cursor/head

후속 구현 기준: [검색/일반 탈퇴·해산 개발 안내](ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md)와 실행 OpenAPI를 따른다. 아래는 합의 당시의 설계 자료/검증 경계를 보존한 것이다. 실제 개발 API/DB 반영 상태는 개발 안내·NEXT_WORK에서 구분한다.

2026-10-24 / 설계 계약 고정·미구현. [Flutter 전체1번째](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6369170940) 기존요청재사용 가능/차단API요청없음 회신을반영한다. [설계안1](ISSUE_13_SEARCH_EXCLUSION_DESIGN.md)의판정표·검증조건을유지한다.

## 고정 계약

- 기존 POST `/v2/raid-rooms/search`의본문/헤더/200/오류shape·상한/필터/정렬은그대로다. 신규flag/추가GET/선행내참가전체조회/응답후제외는없다.
- 원본소비 `0eed67c453040b332653fd2071e6cd2e1eeed503`의 request ref=`app__raid_rooms__cycle_schemas__Search`,200 ref=`OutputContract3PostV2RaidRoomsSearch`. 실제원본OpenAPI의$ref명과객체전체를대조하고바이트동일인새shape를가장해필드를추가하지않는다.
- 로그인선택T/현generation CM participating/review_required + 지속Member활성·room/user/membership일치에대한SQL NOT EXISTS를정렬/offset/limit+1 이전에적용한다. 현재검색자체는open/양수gen만대상이므로미확정review를새로노출하지않는다. 반대T참가/단순지속·legacy/not_selected·신청/종료·옛gen은제외근거가아니다. 비로그인/기존가시성·전체인원/잔여자리집계는유지한다.
- 달라지는것은**로그인모집탐색의기본결과의미**다. 구현시해당동작description과two-cycle 정책메타데이터에 `own-target-participation-excluded-v1`을고정한다. 기본0023/OpenAPI116 및고정0.4.1 원본·내참가/기록/detail/plan/projection은변경하지않는다.

## 정확한 커서/갱신 경계

기존scope(user/session/실제T)·정규화필터/그룹권한·대상T directory head를보존하며epoch digest에 위semantics표식을추가한다. 배포전cursor와가입/탈퇴·제거/해산/복구로대상T실제참가·가시성이바뀐cursor는기존CURSOR_STALE409다. 위조/다른scope cursor는기존INVALID_REQUEST400이며프런트가다른사용자/주차의첫페이지로자동전환하지않는다.

새명령의directory갱신은같은쓰기트랜잭션에서실제조회결과에영향이생긴T만수행한다. 다중T는각각,순수지속Member종료/effects=[]는실제선택T집합변경을만들지않고별도의관계/사용량head·앱알림을갱신한다. 그래도DB상불변근거와달리실제참가제외집합이바뀌었다면효과T와head를누락하면안된다. 다른회원/무관T표시만의변화로원래대상T집합을임의변경하지않는다.

Flutter의현재CURSOR_STALE처리는rows/cursor/cache폐기+failure표시이며**자동첫페이지재조회는아직없다**. 후속에서같은회원/환경/실제T/필터에대해최대1회회복또는기존명시갱신을사용한다. 반복루프/필터리셋/구페이지이어붙이기없음. 영향T가입/탈퇴/해산뒤기존mutation알림으로해당T검색/내목록·계정i를갱신하고정책변경전메모리페이지는유효refresh에서교체한다. 타기기실시간push전달을새로보장하지않는다.

## 완료/검증 경계

설계고정자료는 [기계가읽을snapshot](design/issue24-search-contract.json)에실제원본ref와schema해시·semantics/상태판정/cursor조건을보존한다. 해시는서버성능이나구현통과근거가아니라기존shape보존의정적대조근거다.

현재는API/SQL/실행OpenAPI·DB/서버를바꾸지않았다. 구현지시후SQL페이지전제외·C/N/다른회원/필터·가시성/다중페이지·탈퇴재노출/기존조회보존을직접검증하고정확SHA/push·개발API/DB여부를인계한다. 받은응답을다시제품정책수용이나기존전체시험요청으로바꾸지않는다.
