# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 현재 — F6-C 재개 확인 Backend 구현·개발 반영 완료

[Backend118 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355880490)을 [Flutter120](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356264877)이 세방식 모두 수용해 구현했다. [개발 안내](../ISSUE_13_WEEKLY_RESUME_REVIEW_DEVELOPMENT.md)·[실행 OpenAPI](../../openapi/two-cycle.openapi.yaml)가 기준이다.

기존 POST의 읽기전용preview/Key분리, GETplan opt-in의재개제안별resume_review, 보호된생성/응답token과고정시각/설정/영향·현재권한/CAS를구현했다. null retained/[] 무일정·명시배열/순서·생성자표/1인별도응답·거절/미응답의참가재연결과시간동의구분·원Ack를보존한다. 새JSONB review_version=1과구형legacy_unverifiable를구분하며신규보호제안의token없는새응답은거절한다(Flutter120수용). 구형미결payload/원Ack·기본false응답을보존하고실패token fallback/과거행갱신/추가DDL은없다.

최종65PASS/763.70초+구형시각미정보완3PASS/41.43초(중복2제외고유66:신규30/기존회귀36)·두프로필OpenAPI전체일치·Python223소스/이미지바이트일치다. 실제API8000은168경로/DB0029·50928839…/healthy, 교체전후105표344행/전체내용지문·환경/키mount·보안/포트/command보존이다. 임시검증DB/runner/network정리완료, migration/초기화/실회원쓰기/키변경없음이다.

구간commit/push·원격SHA확인후같은Issue에새소비SHA/실행결과를인계한다. 다음담당은Flutter F6-C연결/결과회신, Backend는재현차이대응이다.

## 다음 Flutter — 새 게시/실행 SHA로 F6-C 연결

- POST weekly-resume-proposals?preview_only=true는명령writer/key/pending없이읽고깊이복사한기존Resume본문·CAS로확인한다. ready/permission/confirmation을함께검증하고같은본문+resume_context_token/새key·preview query제거로제출한다.
- GET 현재T plan?include_resume_display=true에서weekly_resume별DTO/고정일정·미정/영향·basis/display·권한/confirmation을확인한뒤기존응답본문+token을보낸다. 일반일정경로에token을보내지않는다. legacy/stale/token없음은새응답차단·명시새제안안내, 자동false읽기/재제안없음이다.
- recorded/applied·생성자accept와1인별도응답·참가재연결과수락자의시간동의를구분한다. 원Ack뒤현재T plan의새실제ID/본인상태를읽고preview/source ID와혼동하지않는다. 결과불명은원method/path/body/key/token재송이다.
- 사용SHA/연결결과를#13에회신한다. 기존정책/F5/F6-A/B동일mock을반복요청하지않는다. 새직접영향검증·정상로그인HTTP/실회원·기기·성능·F6최종/운영인수는별도로구분한다.

## 수신·후속 상태

- Flutter114 F5/1a909e7 push·단일106mock PASS/분석0, Flutter117 F6-A/660433d push·단일108mock PASS/분석0, [Flutter119 F6-B](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356041000) ea0c932f47094e70d324ec790c2892f8011b774f push/원격확인·단일156mock PASS/분석0 보고다. Flutter119는B별도사용자승인구현임을명시했다. Backend독립재현/실회원·기기인수는아니며서로합산하지않는다.
- 정정은manual근거해제만/완료Assignment·Round·party·참가·예약복원역명령없음이다. 모집관리pending은app소유메모리writer이며앱종료뒤영속복구완료로확대하지않는다. #19통계는독립후속이다.
- 기본0.4.1/policy4·canonical SHA·기본0023OpenAPI는유지한다. 재기동은compose.yaml+compose.two-cycle.yaml/two-cycle factory이며DB29에기본0023앱/구worker를혼용하지않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를따르고source23checkpoint재실행/과거snapshot overwrite없음. dev/main병합·운영배포·Issue종료는하지않았다.
