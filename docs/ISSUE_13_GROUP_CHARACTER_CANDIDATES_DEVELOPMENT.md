# Issue #13 — 그룹 활동 캐릭터 후보 조회 구현·인계

2026-10-22 / feat/raid-recruitment. 기준은 [초안1](ISSUE_13_GROUP_CHARACTER_CANDIDATES_DRAFT.md)·[Flutter102 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339166701)·[보완2판/Backend103](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6339459589)이다. 아래 구현과 검증·서버 게시 상태를 구분한다. 실제 소비 SHA는 `0afd87932ab9b89a5d0976cf634daa5d6ef5a408`(commit/push·원격 SHA 일치)이며 [전체104번째 Backend · 구현/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6340348412)에 게시했다.

## 제공 경로·소비 순서

1. 현재 정상 로그인 세션으로 기존 GET `/v2/me/raid-room-filter-context`를 `group_ids=[선택group UUID]` JSON 배열 query로 호출한다.
2. GET `/v2/groups/{group_id}/raid-room-character-candidates?filter_context_token=...&limit=50`으로 첫 페이지를 읽는다. 다음 페이지는 동일 filter_context_token/limit과 next_cursor를 사용한다. 읽기 전용이며 멱등키/target_cycle_key/room_ids가 없다.
3. 선택은 context의 member_ref와 후보의 canonical character_id로 만든다. POST `/v2/raid-rooms/search`의 기존 body에 `group_character_candidates_token`을 추가해 candidate_token을 그대로 보낸다. 이 필드는 optional/non-null64hex이며 생략은 기존 소비, 명시null/잘못된 형식은400이다.
4. 후보가 변경되면 기존 선택을 보존하고 후보 첫 페이지의 새token으로 같은 선택 검색을 최대1회 자동 재시도한다. cursor=null로 첫 검색 페이지를 요청하며 다른UUID/character_ids=[]/token생략으로 우회하지 않는다. 서버가 전체 현재 후보에서 모든 선택을 검증하므로 후보2페이지의 선택도 검증할 수 있다. 200/items=[]는 선택유효/일치방0이며 후보 전체 로드/참가 확정이 아니다. 반복409/400/404는 선택보류·명시수정이다.

후보 응답은 최상위 group_id/filter_context_token/scope_digest/candidate_token/evaluated_at/groups/next_cursor를 제공한다. 회원별 groups 조각의 alias는 선택 그룹 membership과 연결하고, continues_from_previous/continues_on_next로 이전/다음 페이지 조각을 이어 붙인다. 회원UUID ASC·회원내 Decimal레벨 DESC/null LAST·캐릭터UUID ASC, 빈후보는characters=[] 한행이다. limit은회원수가아닌후보/empty marker 논리행수이며1..100/기본50, cursor1..2048, JSON UTF-8 응답1MiB 상한이다.

권한은 현재 같은 그룹 정상 회원끼리의 현재 인증소유·활동·confirmed/active/현재 NameClaim 유효 캐릭터로 제한한다. 원정대/등록/전체user ID·장비/분석원문·개인설정은 제공하지 않는다. 대표표시는 기존 그룹 snapshot/null, role_family=null이며 Flutter가 제공한2026.09.03.user.v1 직업 카탈로그로 역할가능성을 표시한다. 실제selected_role과구분한다.

역할별 dealer/support는 현재 소유/lifecycle과 일치하는 저장 RolePowerSuccess의 값/관찰시각/저장시각·client_submitted/integrity만 제공한다. 값없음은unavailable/null이며0/타역할로대체하지않는다. 최신 P1 head가 실패/null이어도 성공보존 원천을 유지하고 lifecycle/소유수명불일치 값은 공개하지않는다. 현재 별도 개인별 비공개설정은 없고 not_disclosed는 합의DTO의 구분값만 유지한다.

## 서버 구현과 계약 변경

- character_candidates는 단일 READ ONLY/REPEATABLE READ에서 현재 그룹/context와 전체 후보를 배치조회한다. 쿼리 수가 캐릭터당 증가하는N+1 방식이 아니다. 전체 집합·현재근거·허용표시/전투력을HMAC에결합하고 actor/session/group/limit 범위cursor를서명한다. raw회원/원정대 매핑을token/cursor본문에노출하지않는다.
- 검색token이 있으면 그룹1개/동일context→현재후보token→각ref/UUID 전체현재후보 소속을 검사한뒤 기존실제T 방SQL/필터/정렬/페이지를수행한다. 잘못된선택이 방0건으로정상200이되는shortcut이없다. 변경token409 GROUP_CHARACTER_CANDIDATES_STALE, 현재token의잘못된회원/캐릭터조합400, 그룹문맥변경409 FILTER_CONTEXT_STALE/접근상실404 GROUP_NOT_FOUND, 후보cursor세대변경409 CURSOR_STALE다.
- 두주차 실행 [OpenAPI](../openapi/two-cycle.openapi.yaml)에 후보GET1경로/6schema와 기존 Search의optional token1필드만 추가했다. 기존167경로정의와나머지기존schema 불변·총168경로다. 기본0023 앱/원본openapi.yaml은불변이다. 고정0.4.1/policy4/canonical SHA는기존두주차기본계약이며 후보보완은이추가경로/필드로별도추적한다. 원래고정53경로fixture/코드생성wire를임의변경하지않는다.
- 실행 오류 스키마는 기존 v2 cycle의 Error/Error1이며 `error.details`(nullable)를 포함한다. 검토용 초안의 GameErrorOut에는 이 필드가 빠져 있었으므로 후보 GET의 오류 parser도 실제 실행 OpenAPI의 기존 cycle envelope를 기준으로 소비한다. 새 경로에서 details는null이며, 기존 검색 오류 계약/처리에는 변경이 없다.
- DDL/이행/데이터backfill·원천갱신·provider호출/새권한설정쓰기없음. 정상권한검사를제외한새쓰기·참가/예약/자동정리없음. 현재DB29/환경/volume/인증키로사용한다.

## 검증·성능·실행 상태

최종 신규 후보/검색/HTTP 회귀 **28PASS/222.33초** 후 실제 JWT 정지/회수 및 token 동반 C/N 일치 검색을 **2PASS/21.14초** 보강했다. 중복1건을 제외한 **고유29PASS**이며29건 단일 실행으로 보고하지 않는다. 예비22PASS/173.37초는 중복 합산하지 않는다. 기존 BlockingPortal deprecation1건 외 최종 실패 없음. 초기 runner의 누락jsonschema/소스 동기화 중 설정import 실패와 요청fixture의 생략필드null 변환을 수정했으며 실패 실행은 통과수에 합산하지 않는다.

시험은 별도internal network의 tmpfs PostgreSQL/제한LOGIN에서 수행했다. 합성 JWT 실제HTTP·회원/그룹권한·페이지/검색·READ ONLY/전체표지문 보존과 합의된 검토schema 대조를 확인했다. 실제Google/provider·실회원쓰기·사용자기기 인수가 아니다. 전용 runner/DB/network는 최종종료 후 정리했다.

[합성 측정 집계](design/issue13-group-character-candidates.performance.json)는 회원2명의 활동후보400/10,000개에서 페이지100개를 각각1회 측정했다. SQL은두경우모두10 SELECT, 반환SQL행410/10,010, 응답69,962/70,016bytes, 첫페이지74.730/1467.014ms다. 전체scope 지문 계산 비용을 숨기지 않으며 제품전체상한/실서버SLO/p95로 확대하지 않는다.

개발 API만 검증이미지 `sha256:66e695454abc741406fe3f3b30ab12042686f9ba2a90833b39094125b6afce76`로 교체했다. 이미지의app/alembic Python219파일이 작업트리와 일치한다. 이전이미지ccc787cb9ccb…는 `lostparty-backend-api:pre-character-candidates`로 보존했다. DB이행/초기화없음. DB0029·전체105표449행/내용지문이 전후동일이고 환경/키mount·보안·포트·command 설정지문도 동일하다. Compose는같은two-cycle factory/worker설정이며 DB/volume은유지한다.

실행 API의 two-cycle168경로/기본116경로 각각 OpenAPI 전체객체 일치, 내부health200·신규경로 무인증/잘못된Bearer401 ACCESS_INVALID/no-store의3 HTTP검사와 호스트8000 health200을 확인했다. 실제정상로그인 후보조회성공/실회원쓰기·기기는별도미확인이다. 이를위해기존실회원토큰을발급하지않았다.

구간commit/push·원격확인 및 위104번째 인계를 완료했다. 다음은 Flutter가 그룹원2열 후보/정렬·선택/stale 재검증을 연결하는 것이다. 기존 F1/F2·F3 독립구현은 유지하며 F3전체·실기기/운영완료로 확대하지 않는다.
