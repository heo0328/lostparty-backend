# Issue #13 — 후보 선택 재검증 보완2판

> **구현/개발 반영 완료(2026-10-22):** [개발 안내](ISSUE_13_GROUP_CHARACTER_CANDIDATES_DEVELOPMENT.md)의 후보GET/검색token·검증/168경로 실행 상태가 현재 기준이다. 아래 미구현/미반영·다음구현 표기는 계약검토 당시 기록이다.

2026-10-22 / Backend / feat/raid-recruitment. [전체102번째 Flutter 소비 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339166701)에 대한 보완이다. [초안1](ISSUE_13_GROUP_CHARACTER_CANDIDATES_DRAFT.md)의 §5 재취득/선택 확인 설명을 이 문서로 구체화한다. 새 endpoint/필드/응답 schema를 추가하지 않는다. 기존 검토용 OpenAPI·6개 응답 예시는 그대로이며 실제 서버/기본 계약0.4.1/policy4/canonical SHA는 변경하지 않는다. **후보 API/검색 token 검증은 아직 미구현이다.**

## 수용 확인

- Flutter102가 수용한 공개 범위는 단일 선택 그룹의 현재 정상 회원끼리 현재 인증 소유/활동 캐릭터 허용필드 조회이며, 비회원/비활동·전체 roster/장비·분석 원문 공개로 확대하지 않는다. 별도 공개 설정/동의 UI를 이번 범위에 추가하지 않는다. preferences.visible/count/order는 본인 표시와 계속 분리한다.
- Backend role_family는 초안1대로null을 제공한다. Flutter는 자신이 제공한 ClassSynergyCatalog `2026.09.03.user.v1`의 supportedRoles/findClass로 표시하고 미상/null 직업은 계열 미상으로 처리한다. 출처는 Flutter 제공 [1249c5b 카탈로그](https://github.com/heo0328/LostParty_flutter/blob/1249c5b/lib/shared/game_catalog/data/catalogs/class_synergy_catalog.dart), 보고 SHA256 `fbf7e41dffcdb8fd46166a7780278fc6570e22d96564ef5013a078ecaa6a45e7`다. Backend에서 Flutter 소스를 읽거나 바이트/게임 최신성을 독립 검증한 것은 아니다.
- Flutter 보고의 바드/도화가/홀리나이트/발키리 dealer/support 양쪽, 나머지 등록26직업 dealer는 **그 카탈로그의 역할 가능성 표시**이며 실제 selected_role/개인 선호/실제 빌드 판단이 아니다. Backend에 분류표를 새로 구현하거나 자동 역할 선택하지 않는다. 별도 분석 카탈로그2026.09.12.2와 버전을 혼동하지 않는다.
- nullable/전투력 출처·회원별 정렬/페이지/empty marker·후보token 연결은 Flutter102 수용 기준으로 유지한다. 아래 재검증 규칙은 새 공개범위나 같은 정책 재채택을 요구하지 않는다.

## 재취득 뒤 선택 유효성 확인

Flutter102의 제안을 수용한다. **후보 페이지는 선택 목록을 제공하고, token을 포함한 검색은 전체 현재 후보 집합에서 기존 선택의 유효성을 판정한다.** 첫 페이지에 선택UUID가 없다는 이유만으로 삭제/소멸/비활동이라고 판정하지 않는다. 자동 전페이지 조회·별도 검증 endpoint는 필요하지 않다.

1. 후보 세대가 바뀌면 기존 `(단일 group_id, member_ref, character_ids)` 선택을 보존하고 `확인 대기`로 둔다. 이전 조회 결과는 새 세대의 확정 결과로 표시하지 않는다. 계정/세션/그룹 자체를 바꾼 경우에는 이 재검증 절차를 재사용하지 않고 기존 격리/폐기 규칙을 따른다.
2. 같은 그룹 접근/동일 context/ref가 유효하면 후보 **첫 페이지**만 새로 읽어 최신 candidate_token을 얻는다. 기존 context가 FILTER_CONTEXT_STALE이면 context부터 읽는다. 그 경우 기존 선택의 그룹 membership alias가 현재 context의 동일 membership으로 정확히 대응하는 경우에만 새ref로 연결하며, 이름/대표표시로 추정하거나 탈퇴·재가입의 새 membership으로 승계하지 않는다. 정확히 대응하지 않으면 선택을 보존한 채 보류하고 사용자 명시 수정을 기다린다.
3. 검증 가능한 context/ref와 새 candidate_token을 얻으면 동일한 character_ids·회원 조건·선택 실제T·필터/정렬을 유지한 읽기 POST `/v2/raid-rooms/search`를 **최대1회 자동 재시도**한다. `group_character_candidates_token`에 새 값을 넣고 기존 검색 cursor는 버리고 body의 `cursor`를null로 보낸다(기존 첫 검색 페이지 wire). 후보 token을 생략하거나 선택된 character_ids를[]로 바꾸어 우회하지 않는다. 읽기POST이므로 새 멱등 명령/쓰기·원ACK 복구를 만들지 않는다.
4. 서버는 해당 검색의 단일 READ ONLY snapshot에서 인증→현재 그룹 접근→context→현재 **전체 후보 집합**의 token 일치→각 member_ref와 그 회원의 모든 요청 character_id 소속/현재 후보 자격을 검사한다. 후보 GET에서 실제로 읽은 페이지/offset/limit, 화면이 받은 방/캐릭터 목록으로 검증 범위를 제한하지 않는다. 여러 회원·여러UUID가 있으면 모두 통과해야 한다. 그 후에 실제T 방 가시권한·회원AND/캐릭터OR·필터·정렬·검색 cursor/페이지를 평가한다.
5. 이 검증은 방 SQL 결과의 존재 여부/limit/빈방 목록과 독립이다. **200이면 모든 제출 선택이 현재 후보로 유효**하며 `items=[]`도 유효 선택+해당T/필터 일치 방0건이다. 200은 모든 후보 페이지를 읽었다거나 모든 후보 캐릭터 표시가 로드됐다는 뜻이 아니고, 참가 가능/선택 캐릭터의 실제 참가 확정도 아니다. UI는 `선택 유효`와 `후보 목록 일부 로드/더보기`를 별도로 유지한다. 성공하면 같은 선택을 그대로 보존하며 후속 후보 UI는 명시 더보기만 한다.
6. 새 token 취득 후 후보가 또 바뀌면409 GROUP_CHARACTER_CANDIDATES_STALE, 그룹 세대 변경이면409 FILTER_CONTEXT_STALE, 현재 접근 상실이면404 GROUP_NOT_FOUND다. token이 현재와 일치하지만 member_ref/UUID의 회원 결합/후보 소속이 틀리면400 INVALID_REQUEST다. 인증 실패는 기존401/403 처리다. **거절은 선택 삭제의 증거로 해석하지 않는다.** 자동재시도1회가 실패하면 선택·UUID를 보존한 확인 보류 상태로 멈추고 명시 재조회/선택 수정으로 처리한다. 반복 stale의 무한 재취득/재검색이나 자동 회원전체 검색으로 전환하지 않는다.

최대1회는 한 번의 읽기 실패/세대 변경을 복구하는 자동 흐름 전체 예산이다. metadata/context/후보 재취득 후 재검색이 또 실패해도 각 계층이 별도 횟수로 재시도하며 늘리지 않는다. 이후 사용자가 명시로 재조회하면 새 동작으로 처리할 수 있다. 손상·위조400이나 처음부터 접근 불가404를 새 자동 재시도 사유로 삼지 않는다. 계정/세션 변경 중 늦은 응답은 항상 폐기한다.

## 합성 판정 예시와 구현 검증 항목

| 상황 | 서버 판정 | 소비 결과 |
|---|---|---|
| X는 기존2페이지 선택, 다른 캐릭터 수치만 변경. 새 첫 페이지에 X 없음, 전체 후보에는 같은 회원X 존재 | 새token+동일 선택 검색200, 방 있으면items 존재 | X 유지/선택 유효. 후보 전페이지 자동조회 없음 |
| 위 상황에서 실제T 일치 방이 없음 | 전체 선택 검증 후200/items=[] | X 유지/선택 유효·일치 방0, 소멸 표시 금지 |
| X가 소유/활동을 잃은 뒤 새token 취득 | 새token 일치하나 X는 현재 후보가 아님→400 | X를 다른UUID/빈배열로 교체하지 않고 보류·명시 수정 |
| 새token 취득 뒤 또 활동/수치 변경 | 409 GROUP_CHARACTER_CANDIDATES_STALE | 자동 재시도 추가0, 확인 보류 |
| 조회자 그룹탈퇴 / 대상 탈퇴·재가입 | 접근404 / context409·alias 새 membership | 기존 선택·결과를 확정하지 않으며 이름으로 새회원 연결 금지 |

위 표는 **향후 구현의 판정 계약**이다. 실제 HTTP·PostgreSQL·HMAC/SQL/경합 결과가 아니다. 구현 시험에는 페이지 밖X 성공·200/0방에서도 잘못된 UUID 전체거절·토큰변경 후400/409 분리·여러UUID 중1실패·세션/탈퇴·재가입·기존 token생략 검색 회귀를 포함한다. 단순 schema/합성 예시 검사로 이 동작을 검증했다고 표시하지 않는다.

현재 기존 `cycle_queries.search`에는 이 신규 token/후보 사전검증이 없다. 향후 구현 때 방 SQL/페이지를 읽기 **전에** 전체 후보 검사 단계를 연결해야 한다. token생략 기존 검색의 의미는 초안1대로 유지한다.

## 다음 담당과 완료 경계

Flutter102의 공개범위·계열 소비·nullable/페이지·검색 token 수용과 이번 요청한 선택 재검증 설명을 구현 기준으로 기록한다. **다음 담당 Backend**는 후보API/검색 사전검증 구현→격리 권한/보존/성능/계약 검사→구간 commit/push·원격 확인→개발 실행 반영/소비SHA 인계다. 같은 계약 재채택/중복 시험 회신을 선행 대기로 다시 만들지 않는다. 새 충돌이 있으면 해당 경계만 같은 Issue에 남긴다.

Flutter의 후보 UI 연결은 실제 소비 가능한 계약/SHA 인계 뒤이며 현재 F1/F2·F3 독립 구현은 유지한다. F3 전체/실제 인증HTTP·실회원·기기/운영 인수는 미완료다. 이번 구간은 **보완 답변/문서만**이며 새 endpoint/서버/DB/자료·키 변경은 하지 않는다.
