# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 현재 — F6-C 현재주 재개 일정 확인 계약안 게시 / 다음 Flutter 소비 대조

[로컬 제안1](../ISSUE_13_WEEKLY_RESUME_REVIEW_DRAFT.md) 전문을 [전체118번째 Backend · F6 재개 일정 확인 계약 제안1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355880490)에 게시했다. 문서는 로컬/미push이며 **댓글 전문이 네이티브 검토 원본**이다. 미합의·미구현이고 새 실행 소비SHA 인계/테스트 요청이 아니다. 기본 구현은07c2b671/168경로/DB29로 유지한다.

다음 **Flutter**는 아래 세 소비 경계의 수용/구체적인 차이를 같은 Issue에 회신한다. 기존F5/F6-A시험·정책을 반복 요청하지 않는다.

1. 기존 POST weekly-resume-proposals?preview_only=true로 기존 Resume 본문을 읽기전용 미리보기하고, 확인 후 같은 본문+resume_context_token으로 제출하는 방식. preview는Key불필요/제출은Key필수, null retained/[] 무일정/명시배열을 구별한다.
2. 기존 GET 현재T plan?include_resume_display=true의 weekly_resume별 resume_review(display/confirmation) DTO·고정시각/미정/영향·제안자accept/1명별도응답·원ACK/결과불명·legacy/stale차단을 소비하는 방식.
3. 신규 review_version=1 제안은 응답token필수/구클라이언트 token없는 새응답거절, 구형 제안은 새Flutter에서공대장 명시재제안안내라는 **제한적 호환 경계**. 구형 미결본문/원ACK는보존하며 실패token을구경로로fallback하지않는다.

## 다음 Backend — 소비 피드백 반영 후 합의 구현

- 기존3경로 확장/DTO·120초/4096bytes confirmation·기존CAS·고정basis/display digest·현재영향/자격·생성/응답binding을 제안했다. 기본 queryfalse 응답 보존·새optional필드 생략/null 구별·구payload hash/원ACK 보존·전체응답1MiB/기존요청32KiB/오류/no-store를 포함한다.
- 새content JSONB 버전으로 일정·설정/duration/카탈로그/source확인근거를고정하며 추가DDL/과거불변행수정은계획하지않았다. 핵심근거변경은새제안, 현재target설정덮어쓰기/조용한끝시각변경없음. 현재적격자/정족수재평가정책은유지한다.
- 합의뒤 schema/구현·격리 권한/변경·ACK/호환/크기검증→구간commit/push·원격확인→개발실행/소비SHA를인계한다. 그뒤 Flutter가 F6-C 재개UI/응답을연결한다. 현재미합의API를실행OpenAPI에추가하거나서버를재기동하지않는다.

## Flutter 최신 수신 — F6-A 완료 보고 / F6-B 다음 범위

[전체117번째 Flutter F6-A](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355764602)는 **660433d commit/push·7파일 단일108mock PASS/분석0** 보고다. 새manual v2/기존v1 pending원경로·schema2 wire_version·원ACK/기존T·N캐시보존을연결했다. Backend 독립재현/실회원·기기/secure storage인수는아니다. 추가Backend구현/같은시험요청없음을확인해Backend118에수신기록을함께남겼다.

다음Flutter F6-B는방전체/본인item완료·미완료종료, F6-C는위재개계약대기다. **F6-A승인을B/C구현승인으로확대하지않는다.** 정정은manual근거해제뿐이며완료Assignment/Round·party·참가/예약복원역명령없음(Backend116).

F5사전표시는 Flutter114/1a909e7 push·단일106mock PASS/분석0 보고로코드/자동검증구간완료다. F5/F6-A목록을합산하거나실제정상로그인HTTP·회원쓰기/기기/성능·F6/운영인수완료로표시하지않는다.

## Backend 실행·검증 상태 유지

- 구현소비 **07c2b671d67e5dfcef5f873ef55ffcb54f87b365** / 원격문서HEAD00db6c8. [표시 개발안내](../ISSUE_13_PREJOIN_SESSION_DISPLAY_DEVELOPMENT.md)·[실행OpenAPI](../../openapi/two-cycle.openapi.yaml). 이전고유48PASS·개발API168경로/DB0029·이미지404cf8c4…·전후105표345행/내용·설정보존근거는유지하며이번에재실행/합산하지않는다.
- 이번은제안문서/댓글만변경했다. router AST/OpenAPI 기존3경로·기존본문필드/미구현상태·소비07c2b671바이트일치·KST날짜2예정적대조와diff검사통과, 실제HTTP/DB/token/동시성/크기시험은미실행이다. 앱/실행계약·서버/DB/키·컨테이너변경없음, 문서구간로컬커밋/미push다.
- 재기동은compose.yaml+compose.two-cycle.yaml/two-cycle factory. 기본0023앱/구worker를DB29에혼용하지않는다. [전환/복구](../ISSUE_13_W5_LIVE_CUTOVER.md) 기준으로기존checkpoint/source23도구재실행·과거snapshot overwrite없음. dev/main병합·운영배포·Issue종료없음, #19통계는독립후속이다.
