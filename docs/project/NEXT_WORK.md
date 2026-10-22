# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 현재 — 사전 참가 표시 메타 Backend 구현·개발 서버 반영 완료

[개발 안내](../ISSUE_13_PREJOIN_SESSION_DISPLAY_DEVELOPMENT.md)·[실행 OpenAPI](../../openapi/two-cycle.openapi.yaml) 기준이다. [Flutter110 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6344221859)/[Backend111 경로 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6344566106)을 구현했다. 기존 세GET에서 include_session_display=true만 data.session_display를 제공하고 생략/false의 응답·token 계산/쓰기본문·원ACK를 보존한다.

actual 세션/미생성 opening_preview/none·실제T/새generation·표시binding·전체1MiB 초과413을 구현했다. 최종47PASS/410.22초+DB29연계1PASS/15.82초, 고유48PASS다. 기본/두주차 OpenAPI 전체일치·기본0.4.1/policy4/canonical SHA 불변이다. 실제 API8000은168경로/DB0029·이미지404cf8c4…/healthy, 교체전후105표345행/전체내용지문·환경/키mount·보안/포트/command 보존이다. migration/초기화/키변경 없음·임시검증DB/컨테이너/network 정리완료다.

구간 `07c2b671d67e5dfcef5f873ef55ffcb54f87b365` commit/push·실제 원격SHA 일치 확인·[전체112번째 Backend · F5 사전 참가 표시 구현/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6345290060) 게시 완료다. 다음 담당은 Flutter 새 표시·선택 연결이며 Backend는 차이 대응이다. 구현/자동검증·개발실행 반영과 Flutter 적용·실회원/기기 인수를 구별한다.

## 다음 Flutter — F5 사전 참가 표시·선택 연결

- 게시된 소비SHA와 위 실행계약으로 admission `/v2/raid-rooms/{room_id}/admission-context`, continuation `/v2/me/raid-rooms/{room_id}/continuation-context`, opening `/v2/me/raid-rooms/{room_id}/opening-context`의 opt-in DTO를 연결한다.
- actual ID/시각/미정·변경거절/재조회·기존 target_session_ids 선택, 미생성 preview는 session_id=null/POST 제외·개방원ACK뒤현재T plan의 실제ID조회, none/noop를 구별하고 적용 결과/사용SHA를 #13에 회신한다. 같은 계약 수용/이미 보고한 mock을 반복 선행 요청하지 않는다.
- F4는 Flutter106/0c850294·93mock PASS 마감 보고, F5 독립 연결은 Flutter107/f2e09c9d·고유130mock PASS 보고를 유지한다. Backend가 Flutter 소스/시험을 독립 재현한 결과는 아니다. 새 사전표시 연결/F6·정상로그인 실제HTTP·실회원/기기/운영인수는 미완료다.

## 다음 Backend — 재현 차이 보완·현재 실행 유지

- Flutter의 재현 가능한 표시/선택·계약/실행 차이가 오면 같은 브랜치에서 보완·검증·commit/push 후 회신한다. 이전 수용/같은 시험을 다시 요청하지 않는다. #19 통계는 독립 후속이다.
- 재기동은 compose.yaml + compose.two-cycle.yaml/two-cycle image·factory를 함께 사용한다. 기본0023 앱/구worker를 DB29에 혼용하지 않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를 따른다. 코드 게시와 dev/main 병합·운영배포는 별도다.
- 지난주7관계의 현재C/N 검색 제외는 정상이며 원본/persistent관계·한도 자동해제 없음. 기존 비공개checkpoint는 보존하고 source23용도구를 DB29에 재실행/이전snapshot overwrite하지 않는다.
