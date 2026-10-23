# Issue #13 — F6-C 현재주 재개 일정 확인 개발 안내

2026-10-23 / Backend / `feat/raid-recruitment`.

[Backend118 제안1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355880490)을 [전체120번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356264877)가 세 소비 방식 모두 수용했다. [합의 문서](../contracts/ISSUE_13_WEEKLY_RESUME_REVIEW_DRAFT.md)의 의미를 구현하고 정확한 닫힌 DTO/수치/nullable/응답은 [실행 OpenAPI](../../../../openapi/two-cycle.openapi.yaml)에 반영한다. 이전 기본0.4.1/policy4·고정 wire/기본 OpenAPI는 보존한다.

## 소비 흐름

| 기존 경로 | 새 소비 |
|---|---|
| POST `/v2/raid-rooms/{room_id}/weekly-resume-proposals?preview_only=true` | 기존 Resume 본문으로 읽기전용 미리보기. Idempotency-Key 불필요·제공시UUID4형식 검사. `kind=weekly_resume_preview`/`data.resume_review` 반환 |
| 위 POST의 query 생략/false | 새key 필수. 확인한 동일본문에 `resume_context_token`만 추가해 보호된 제안 생성. 기존 Ack/recorded 반환 |
| GET `/v2/me/raid-rooms/{room_id}/plan?include_resume_display=true&target_cycle_key=C` | 모든 weekly_resume 제안에 `resume_review` 포함, 일반 일정제안에는 없음 |
| POST `/v2/raid-schedule-proposals/{proposal_id}/responses` | 기존 Respond CAS·응답과 `resume_context_token`으로 보호된 제안에 수락/거절. Ack recorded/applied 구별 |

query는 문자열true/false·기본false다. 빈값/null/1/TRUE/다른값·중복은400. 생략/false의 plan에는 새필드가 없다. token 명시null은400이며 생략을 새null로 직렬화하지 않는다. 미리보기는 token필드를 받지 않는다. preview 성공이 기록/투표/적용을 뜻하지 않으며 command원장·제안·투표·새round/assignment/session·동의/예약을 만들지 않는다.

`resume_review={display,confirmation}`이며 confirmation은nullable `{context_token,issued_at,expires_at}`다. display status는ready/stale/legacy_unverifiable. ready도 실행권한/적용완료와 같지 않으며 pending·현재권한/근거가 유효한 경우만 confirmation을 발급한다. 생성 전 proposal ID/두revision과 모든 preview session_id는null이다. 현재C/동일cycle·generation이며 N 개방/reopen이 아니다.

schedule_groups=null은유지할의도해석, []는일정그룹없음, 명시배열은그대로검증한다. refs는opaque64hex이며groups/alternatives는ref순, item_ids는기존의미순서를보존한다. 실제C날짜·고정duration으로UTC시각을계산하며수요일00:00~05:55는해당주차끝날짜다. manual each/단일one_of는on_apply, 수동복수후보는after_group_selection, 조율은after_coordination, 미지정은not_scheduled다. 미입증legacy duration은현재설정으로채우지않고start_only/null로표시한다. 새수동일정에필요한duration/구간을입증할수없으면거절한다.

## 확인·저장·적용 경계

- actor/flow/room/C/cycle/gen·원본문hash(null/[]/순서구별)·source/설정/시각/영향·현재자격/집계/권한·기존CAS를digest로결합한다. 큰목록을token에싣지않아4096bytes이하이고최대120초/주종료전이다. display_revision은발급시각/token때문에매번바뀌지않는다.
- 새 content에 review_version=1·고정review_basis를보관한다. 기존JSONB에추가하며DDL/과거불변행수정없음. 현재설정/리더·source그룹/중단round·적격자의assignment핵심근거가달라지면stale/PROPOSAL_CONTEXT_CHANGED·confirmation=null, 새제안이필요하다. 현재설정으로끝시각을바꾸거나과거설정으로현재DB를덮지않는다. 적격자감소/현재정족수재평가정책은유지하고최신확인·CAS에결합한다.
- 실제투표대상인제안자는2명이상일때기존생성accept를기록한다. 제안자가이미완료돼중단투표대상이아니면자동수락으로표시하지않는다. 1인은별도본인응답이다. 생성Ack는recorded이며원응답의recorded/applied를구별한다.
- 적용때현재유효한중단참가관계를재연결하므로거절/미응답이자동탈퇴를뜻하지않는다. 수락자의실제대상수동세션만새시간동의/예약이가능하고나머지는확인대기다. 완료/N·과거round/assignment/투표/동의/예약은보존한다. 적용후현재T plan에서새실제ID/본인동의상태를읽는다.
- 원성공Ack는현재token만료·현재제안상태·주차/자격재검사보다먼저복구하되현재인증은유지한다. 결과불명은원method/path/body/key/token재송이다. 확정된거절후에만재조회/재확인·새key로새명령을발급한다.

## 구 소비·크기

구token없는Resume는구형제안을생성하고구형미결응답/원Ack를보존한다. 기존 proposals.permissions는구경로의기존값이며, 새확인흐름의가능여부는resume_review의status/permission/confirmation을함께판정한다. 구형제안은당시설정/duration을입증할수없어신규opt-in에서legacy_unverifiable/confirmation=null로표시하며새Flutter는새응답을막고공대장명시재제안을안내한다. 자동재제안/과거행삭제·갱신없음.

**review_version=1 신규보호제안은token없는새응답을400 CONTEXT_INVALID로거절한다.** 구클라이언트가이제안에새응답을계속보낼수없다는소비제약은Flutter120에서수용했다. 구형제안/일반일정제안에새token을붙이거나actor/flow/제안을교환해도400이며실패token을구경로로내리지않는다.

입력은token포함전체32KiB·초과413 REQUEST_TOO_LARGE, opt-in 전체plan/preview UTF-8 JSON은1MiB·초과413 RESPONSE_TOO_LARGE다. 일부후보절단/false자동재조회없음·no-store다. 새preview배열개수제한은추가하지않았다.

## 검증·실행·인계

최종 관련 묶음 **65PASS/763.70초**와구형수동시각미정경계보완후**3PASS/41.43초**(재실행2제외고유**66PASS**, 신규30·기존회귀36), 실패0/기존anyio deprecation warning1종이다. 구형manual의starts_local=null도undetermined/confirmation=null로읽으며보호된생성/HTTP회귀2개를함께재확인했다. 탐색3PASS·21PASS·추가6PASS는최종과중복이므로합산하지않는다. 새기능은모두격리DB0029·합성계정으로검증했다.

preview 쓰기0/두200응답·Key모드/엄격flag·null/[]/순서·수동each/단일/복수·조율/주차전체/미지정·legacy와구명령/원Ack·핵심설정/round/assignment/group 변경stale·actor/flow/변조·토큰만료/최종만료rollback·동시동일명령·수락/거절/참가재연결과동의·적격자감소·완료된제안자의자동표없음·N보존/C수10시/KST수요일00:05를확인했다. 실제합성Bearer성공·무인증/오류/폐기세션/타인권한·32KiB요청/응답정확경계·5,001개저장후보가있는전체plan의실1MiB초과413도확인했다. 무관전체시험/성능SLA시험은아니다.

실행변경은기존plan/create의query/응답과Resume/Respond의optional non-null token/관련schemas뿐이다. 경로168개 유지·기본116경로OpenAPI와two-cycle168경로OpenAPI를각각전체객체비교했다. core wire/기본OpenAPI·고정53경로56동작204schema/84fixture·canonical SHA fb4c7d…는불변이다.

검증이미지 `sha256:50928839b92c6d44089449f2f76b7d8c17ca3e2b14481b7a0afd04ce17f345f4`의app/alembic Python223파일이작업트리와바이트일치했다. 해당이미지로개발API8000만two-cycle factory로교체해healthy/DB0029다. 교체전후105표344행의전체내용지문·환경/인증키mount·보안/포트/command 일치, DDL/초기화/실회원쓰기/키변경없음이다. 직전실행이미지404cf8c4…는`lostparty-backend-api:pre-resume-review`로보존했다. 실제내부health200·3경로의무인증/잘못된Bearer401/no-store/WWW-Authenticate 6검사·호스트health200과실제두프로필OpenAPI일치를확인했다. 이번tmpfs검증DB/runner/network만정리하고기존API/DB두컨테이너만healthy다.

소비 SHA `29408243192ed3a37a347ade046db26ad2d918b9`를 `feat/raid-recruitment`에 commit/push·원격확인하고 [전체121번째 Backend · F6-C 구현/개발 반영/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356827586)로 회신했다. 게시 전문과 본문 제외 전체 댓글 순번을 재조회했다. 실제정상로그인회원HTTP·실회원쓰기·기기·성능/운영인수는미확인이다. 합성DB/Bearer·자동검증과 실제회원HTTP/기기·운영인수는 구별한다. 다음 Flutter는 게시·실행확인된 새 소비SHA의 DTO/두200응답·확인창/원명령writer/원Ack·현재T조회에 F6-C를 연결하고 결과·사용SHA를 #13에 회신한다. F6-A/B 기존mock 반복이나 같은정책수용은 다시 요청하지 않는다.
