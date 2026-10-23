> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 모집 탐색 — 선택 주차 본인 실제 참가 방 제외 설계안1

현재 기준(2026-10-24): [검색 계약 보완](../contracts/ISSUE_24_SEARCH_CONTRACT.md)과 [#24 전체2번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6369761914)이 아래 설계안1의 검색 의미·head·커서 경계를 구체화한다. 기존 요청/응답 shape를 유지한다. 설계 완료·미구현이며 Flutter 자동 첫 페이지 회복은 후속이다.

최신 소비대조: [#24 전체1번째 Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6369170940). 기존요청/응답/SQL제외·커서표식은소비가능·blocking API변경요청없음. Backend검색의미/head·커서계약고정과Flutter stale커서첫페이지회복은후속이며현재자동재조회완료가아니다. 이번은정적검토이며구현/시험·개발반영승인이아니다. 아래설계안1을보완할근거로보존한다.

2026-10-24 / Backend / feat/raid-recruitment / **기획·설계 제안, 미구현**.

요구 원본은 [#13 전체135번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6366977367)다. 이미 참가한 모집을 탐색 결과에서 반복 노출하지 않고, 참가/기록 화면과 기존 회원 접근은 유지한다. 독립 완료조건으로 검색 후속에 추적하며 탈퇴/해산과 같은 작업 브랜치를 유지한다.

## 제품·계약 결정안

기존 POST `/v2/raid-rooms/search`를 재사용한다. 로그인한 호출자에게 **선택한 실제T(C 또는N)의 본인 실제 참가 방을 항상 제외**한다. 추가 flag·카드별 GET·모든 내참가 사전조회·응답 후 앱 필터는 두지 않는다. 비로그인 결과는 기존과 같고 별도 공개회원 식별을 요구하지 않는다.

입력/응답 DTO·상한/정렬/필터는 유지하지만 로그인 검색의 기본 결과 의미가 바뀐다. 구현 시 `openapi/two-cycle.openapi.yaml`의 해당 동작 설명/정책 메타데이터와 개발안내를 함께 갱신하고 객체 전체를 비교한다. 기본0023 앱/원본0.4.1·구 명령/원ACK·내참가/기록/그룹projection은 변경하지 않는다.

## 제외 판정의 정확한 범위

서버의 같은 READ ONLY/REPEATABLE READ 관측에서 RoomCycle의 room/cycle_key를 선택T로 먼저 한정한다. 본인 지속Membership의 user/room과 CM의 membership/user/cycle 관계가 일치해야 한다.

| 선택T의 실제 관계 | 탐색 제외 |
|---|---|
| 현양수generation CM=participating, 지속회원 활성 | 제외 |
| 현generation CM=review_required, 지속회원 활성 | 제외(불량 소유/활동 때문에 본인 참가 방을 다시 추천하지 않음) |
| RoomCycle/gen 모두 미확정이고 같은T 실제review CM인 명시 recovery-only | 제외 기준에 포함. 현재 검색은open/양수gen만 반환하므로 지금은 선행조건에서 이미 제외됨 |
| row는현양수gen인데 CM만null/옛gen | 같은현generation 참가로 간주하지 않음. 자료불일치 복구를 이번 검색변경으로 추정/수정하지 않음 |
| completed/stopped/cancelled/removed 또는 지속회원 종료 | 본인참가 사유로 제외하지 않음(방의 기존 수명/가시성 필터는 별도) |
| 단순 지속관계/legacy_intent/not_selected/미결신청만 | 제외하지 않음 |
| 본인은C만참가, 탐색은N(또는그반대) | 선택T 참가가 아니므로 제외하지 않음 |
| 비로그인 | 기존 탐색과 동일 |

**구현 위치:** `cycle_queries.search`의 기본 Room/RoomCycle SQL에 `NOT EXISTS`를 넣고 필터·정렬·offset/limit+1 이전에 적용한다. 실제 CM→지속Member를 join하여 user/membership/room 및 현재generation을 결합한다. 결과 카드를 만든 후 빼거나 본인 참가자를 기존 인원수 집계에서 빼지 않는다. 인원 정렬/잔여슬롯 집계는 실제 전체참가 근거 그대로다.

검색이 현재 open/양수gen만 노출하는 정책을 이 작업으로 넓히지 않는다. review/null 관계를 탐색 가능 방으로 만드는 작업도 아니다. 회원/환경/권한에 따라 보이는 관계를 공용 캐시에 섞지 않는다.

## 커서·가입/탈퇴 뒤 반영

기존 cursor는 user/session·선택T와 directory head/필터·그룹권한에 결합되어 있다. 신규 semantics는 digest에 고정표식 `own-target-participation-excluded-v1`을 추가해 변경 전 cursor를 `CURSOR_STALE409`로 재조회하게 한다. `app/game_accounts/support.py:cursor_decode`의 현재 CURSOR_STALE를 재사용하며 위조/scope혼합은 기존 INVALID_REQUEST400을 유지한다.

가입/취소·제거/복구 등 선택T의 실제참가 상태변화는 해당T directory head를 같은 쓰기트랜잭션에서 갱신해야 한다. 새 탈퇴/해산 후속도 이 조건을 따른다. 이전 페이지를 쓰면서 중간 결과를 조용히 건너뛰지 않고 기존 stale-cursor 동작으로 첫페이지를 다시 읽는다. 선택되지 않은T의 무관한 변경만으로 본인선택T 검색이 변경되지 않게 한다.

Flutter는 원래 탐색 요청/DTO를 사용하며 새 flag를 붙이지 않는다. 현재 사용자/환경/실제T의 기존 검색 캐시를 교체하고, 영향T의 가입·탈퇴 뒤에는 해당T 첫페이지를 갱신한다. 탈퇴한 방은 다른 기존 검색조건도 만족할 때 다시 보인다. 닫힌/보관/비공개 방을 재노출하지 않는다.

## 책임·검증·완료 조건

SQL 제외판정은 directory 서비스, 접근권한/정렬·페이지/커서는 기존 검색 경계, 앱의 선택T/지연응답·목록 갱신은 Flutter 책임이다. 기존 조회를 재사용하면 네트워크 증가나 별도 클라이언트 전체집합 없이 페이지 정합성을 유지할 수 있다. 성능 개선 수치는 측정 전 주장하지 않는다.

검증은 격리 PostgreSQL/HTTP에서 C/N 교차, 실제참가/review/지속관계·종료·신청·구gen, 비로그인/다른회원·group 가시성, 두 정렬방향/필터와 limit=1 이상 다중페이지, 가입/탈퇴 후 cursor·재노출, 내참가/기록/detail/plan/projection 보존을 표적으로 한다. 빈페이지를 만드는 앱후처리 대신 SQL limit 이전 제외를 실제 쿼리 결과로 확인한다. 필요할 때 합성 자료의 EXPLAIN으로 기존 CM/user/cycle·membership index 사용을 확인하고, 근거 없이 인덱스/캐시/집계체계를 신설하지 않는다.

완료는 구현/해당OpenAPI 의미갱신·표적검증→commit/push·원격확인→소비SHA/계약차이/개발반영·DB여부 인계→Flutter 기존탐색 소비/사용자 확인이다. 이번은 소스·계약 정적대조/문서검사뿐이며 신규 구현/시험·서버·DB/키/실행OpenAPI 변경은 없다. 다음 Flutter의 검토는 필터기본의미·기존 요청 재사용/캐시무효화에 소비차이가 있는지에 한정하고 같은 제품정책 수용이나 기존전체시험 반복을 요청하지 않는다.


협업 추적: [이 설계 Issue #24](https://github.com/heo0328/lostparty-backend/issues/24) / [관련 후속 #25](https://github.com/heo0328/lostparty-backend/issues/25) / [원본 #13](https://github.com/heo0328/lostparty-backend/issues/13). 검색/탈퇴·해산의 완료조건을 분리한 것이며 원본 요구의 폐기/완료나 별도 기능 브랜치 생성이 아니다.
