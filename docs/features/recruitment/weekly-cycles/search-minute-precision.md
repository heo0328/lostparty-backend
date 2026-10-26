# 검색 분 단위 범위 구현·생성 시간 정책 검토

2026-10-27 / 작업 구간 **검색 분 단위 허용·직접검증·개발반영·인계** / `feat/raid-recruitment`.

[전체177번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6421096990)과 사용자 승인 계획에 따른다. 검색을 구현하고 생성·직접 지정은 검토만 한다. source a358a1a를push/원격확인후 [개발 반영·실행 확인](../../../engineering/operations/search-minute-rollout.md)을완료했다. 정확이미지/검증경계·고정기록은해당문서와Issue13인계를따른다.

## 검색의 변경과 소비 경계

검색 범위가 출발 시각의5분격자를 공유해18:03~20:17을400거절하던 문제를 검색 전용 minute_boundary로 분리했다. 베타 GET /v2/raid-rooms와 POST /v2/raid-rooms/search가 같은 beta_search.apply를 사용한다. UTC offset0·초/마이크로초0·양의구간/최대24시간·서버선택주차내부는 유지하며분단위경계를반올림하지않는다. 시작포함/끝제외·중복/인접구간병합·실제출발/확정시각·legacy대체조회·정렬/페이지전필터는기존그대로다.

커서는정규화한정확분단위조건에바인딩한다. 같은범위를다른순서/중첩구간으로표현한경우기존병합규칙을재사용하고1분이라도실제조건이바뀌면CURSOR_STALE이다. 경로/shape/오류코드·wire2/profile1·현재178/199/기본116/133유지. 공용time_policy.aligned/interval/TICK과일정생성·제안·예약동작은수정하지않았다. DB/회원명령변경없음이다.

실행OpenAPI에서는DepartureWindow의검색정밀도설명과beta정책의search_time만추가했다. 기본계약·경로operation객체·쓰기ACK는동일하다. 합의DTO/완결wire와GET·POST예시2개를추가해총125fixture를검증했다. 스키마의date-time설명과실제업무UTC/정수분/주차검사를구분한다.

## 직접 검증

격리PostgreSQL+합성HTTP 고유6PASS: 신규검색4, 기존필터/조율토글1·직접제안/수락1. GET/POST비5분·정확시작/끝·24시간허용·초/마이크로초/비UTC/naive/역전/동일/초과/주차밖거절,자정/C/N경계·확정effective시각·합집합/페이지전필터·커서/조건변경·검색전체표쓰기0을확인했다. 생성config·직접제안의비5분거절과기존5분흐름도검증했다.

처음5PASS/1FAIL은신규시험의필수nullable early_additional_members 누락이었다. 해당시험입력에null을명시하고그1건만재실행해PASS,통과5건은재실행하지않았다. 같은런타임소스결과를재사용한다. 기존Starlette/AnyIO경고1종유지·전체pytest/복원리허설미반복. 두OpenAPI전체객체·wire125/원ACK32/음성3·문서/diff PASS다. 정상회원HTTP·기기성공은별도미확인이다.

## 생성·직접 지정 검토 — 이번에는 미구현

**추천:** 베타의명시출발만UTC정수분으로허용하고자동조율/개인시간표/진행시간의5분격자는유지한다. 기존공용aligned를전역완화하지않고기본값5분인검사에명시출발경로만정수분정책을전달하는후속설계가필요하다.

| 경로 | 현재 확인 | 후속 변경 범위 |
|---|---|---|
| 생성·현재/다음주개방 | beta_schedule.config→time_policy.interval, install→scheduling.set_times 및개방최종검사가5분경계검사 | context·POST·설치·최종검사에서동일한명시분정밀도사용 |
| 직접제안·수락/재평가 | cycle_proposals.create/evaluate가공용interval을다시검사 | 제안작성/수락/재평가/검토복구경로의정밀도를맞추고CAS·동의·원ACK유지 |
| 자동조율 | ceil_tick/TICK=5분,복사표coverage·타예약중복제외·출발하한사용 | 5분후보그대로탐색,18:03기본출발보다이른유효5분후보만허용 |
| 기본기한·가입마감 | base/effective시각에서정확히30분차감,worker는실제timestamp와비교 | 18:03이면17:33기한유지,시각을5분으로반올림하지않고지연review우선순위보존 |
| 개인표·예약/진행시간 | 개인표Clock/DB대안start_minute·진행시간은5분규칙,session/segment/reservation은timestamptz | 개인표/진행시간/구대안격자는유지,예약에는명시분시각을그대로전파 |

개인표밖기본출발은현재config/install에서개인표coverage로거절하지않는다. 유효한개인표복사·소유/자격검사는유지되지만개인표가자동조율의가능시간근거라는점과직접출발선택은구분돼있다. 직접제안도create/evaluate에서개인표coverage를새로강제하지않는다. 이요구만을위한개인표제약해제기능은필요없다.

예약은정확timestamp구간으로저장되고자동탐색에서타예약을제외한다. 수동선택/동의경로의기존중복예약표시·소유범위·재확인과자동후보제외를혼동해새일괄거절정책을추가하지않는다. 분단위변경시에는타예약과18:03경계의겹침/인접판정과자기약속제외를직접시험해야한다.

이번검토에서session/segment/reservation의출발시각에5분DB CHECK는없고진행시간에5분CHECK가있음을확인했다. 베타명시출발정밀도만확장하는추천안은새필드·기존자료변환없이처리가능하다. 후속구현전구대안start_minute 경로와혼용되지않는지확인하며개발자료보존용backfill/이중운영통로는만들지않는다.

Native는일반시계UI로분단위를그대로UTC전달하고초/마이크로초0·현재미래/주차/점검/진행시간경계를유지해야한다. 생성/직접제안/기본기한·예약의분정밀도소비와자동조율/개인표5분유지를같이합의한뒤별도구현한다. 이번검색반영만으로생성18:03이성공한다고안내하지않는다.

[전체178번째 Backend · 검색 정수분 개발 반영/생성 정책 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6421669821)에결과를회신했고실제전체순번/전문을확인했다. 반영기록push/원격확인후같은댓글에고정문서/SHA와검색직접영향확인을보완한다.
