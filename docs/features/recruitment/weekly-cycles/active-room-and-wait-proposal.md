# 활성방 한도 공통판정·조율 대기 선택조회 제안

2026-10-26 / `feat/raid-recruitment` / 상태: **전체171 소비 수용·구현/직접검증 완료·실제반영 별도**.

요구는 [전체166 사용자 한도 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410274718), [전체167 join수용·분기대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410375489), [전체168 조율 한줄 승인](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410454752)이다. [전체169 Backend 상태표·선택조회 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410756326)에 아래 소비 확인을 요청했다. 이미 합의된 join 후보 구현은 이 대기로 중단하지 않는다. 아래는합의의기준이며 [전체171 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6412692643) 후 [구현/검증](active-usage-and-wait-implementation.md)에반영했다. DB필드추가는없고실제개발반영은별도기록을따른다.

## 한도 — active-target-rooms-1

서버시각 C/N의 현재목록과 동일한 SQL predicate를 두 현재목록의 페이지 전 필터·한도조회·명령의 새사용량증가/해제판정에서 공유한다. 방/지속회원이 미종료·비archive이고, 실제 선택T CM=participating/review_required·주차=open/review_required·현재세대 일치일 때만 포함한다. 기존import의 양쪽null 세대도 현재목록과 같은 비교로 처리한다. 검토상태를 일괄 제외하거나 캐릭터 자격/권한·한도 제한·조회오류로 count를 바꾸지 않는다.

같은 room C/N은1개다. 생성자/참가자 중복없음·C/N 한쪽유효1/양쪽종료0·과거관계/기록전용/실제현재CM없음0이다. READ ONLY 대조시 제보 계정은기존10→현재3방(C2/N2)이다. 과거7관계와원ACK/자료를 삭제·보정하지 않는다. 기본10/기존한도DTO·오류코드를 유지하고 새DB필드·migration을 추가하지 않는다.

신규가입/승인/개방에 기존persistent관계가 있어도 현재count집합에해당room이없으면 새1개를검사한다. 이미count되는room의 다른T는추가차감없고 pending은예약안함/승인시검사한다. 기존 game-mutations 잠금 안에서 최신집합/한도·주차를확인하고 실제변경의기존usage revision을갱신한다. 원ACK 재생은변경을반복하지않는다. 생성중중간상태를기존9→10의마지막자리실패나 C/N이중차감으로만들지않도록 명령전후집합과최종검사를검증한다.

## 조율 — include_coordination_wait

베타 `GET /v2/raid-rooms/{room_id}/detail` 및 `GET /v2/me/raid-rooms/{room_id}/plan`에만 `include_coordination_wait=true|false`를제안한다. 생략=false. 기존application-display/membership-actions reader와조합가능·기존profile없으면 새query는400 INVALID_REQUEST. true에서만 beta_schedule 객체안에 `coordination_wait`를추가한다. 미지정/false는기존본문·beta_schedule=null/기록content=null은그대로 유지한다. public검색/카드·쓰기ACK로확대하지않는다.

[닫힌 상태 DTO 제안](proposals/coordination-wait.schema.json)은 status/missing_members만 가진다.

| status | missing_members | 의미 |
|---|---|---|
| waiting_members | 양의정수 | 실제자동조율전원집합의추가필요인원 |
| no_earlier_candidate | null | 인원충족·정상판정완료·더이른유효후보없음 |
| pending | null | 후보가있으나아직미확정 또는기존기한처리대기 |
| unavailable | null | 복사표/참가근거 등 판정자료부족 |
| not_applicable | null | OFF/확정/종료/검토필요 등 안내대상아님 |

우선순위는확정/종료/검토/OFF→기한처리대기→판정근거확인/인원미달→충족후후보판정이다. 같은READ ONLY snapshot의기존시각·실제주차/세대·전원·표·타예약/진행시간/하한을사용한다. 부분그래프선택을사용하지않는다. 유효후보를GET에서확정하지않고pending으로반환한다. 실제DB/조회예외는기존오류를전달하며 no_earlier_candidate로삼키지않는다. 개인표명시unset은전시간가능, 복사누락/불량표는unavailable이다.

자동확정과기존candidate adapter가공유할내부평가결과를정리하되기존자동확정·30분기한·기본약속·개인표명시갱신은바꾸지않는다. 상세/plan의같은판정을중복계산하지않고조회수/계산량을직접영향시험에서확인한다. 새endpoint·polling·웹소켓은없다.

## 합의·검증·인계

한도상태표와새query/선택DTO의소비확인뒤구현·닫힌실행계약/예시를갱신한다. 제품정책재승인·같은정상시험반복은요청하지않는다. join은별도독립구현한다. 후보/한도/조율의직접시험·C/N경계/동시성/원ACK·선택조회구응답불변을검증하고구간별commit/push·정확소스/실제개발반영/기기인수를구분한다. 개발반영은사용자승인범위이며DB0032/키/환경을유지한다. dev/main/AWS·자료초기화는포함하지않는다.
