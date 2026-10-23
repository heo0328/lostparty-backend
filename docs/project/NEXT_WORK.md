# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 현재 — 본인 완료 정정·방 보관 계약 제안 / 다음 Flutter 소비 대조

[전체126번째 Backend · 완료 정정/방 보관 계약 제안1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358628814)에 [계약 제안1](../ISSUE_13_COMPLETION_CORRECTION_LIFECYCLE_DRAFT.md) 전문을 게시하고 실제 댓글 순번/작성측/전문 일치를 확인했다. Flutter124/125의 새 제품 요구에 대한 검토안이며 **새 계약 미합의·미구현**이다. 기존 Backend2940824/168경로/서버·DB·키는 유지한다.

- 다음 Flutter: 별도 context/완료정정 명령의 과거T·현재C 수06~10시 취소, 현재소유/CAS·새ACK/원ACK24시간·기존manual경로 보존과 current/ended/all·보관방 상세/쓰기차단/N보존·stopped재개 분리의 소비 가능 여부/구체 차이를 회신한다. 같은 기존 정책/시험 반복 요청 없음.
- Backend: 피드백 반영→합의 구간 구현→격리검증→구간commit/push·원격확인→정확한 실행 OpenAPI/SHA·개발반영 여부 인계. 현재는 5개 관련 소스 AST/기존168경로·새경로 미노출·멱등 실제code/24시간 대조와 diff검사만 수행했고 서버시험/DB변경은 없다.
- 정정은 본인 manual/party 투영만 해제하고 원본Outcome/완료Assignment/타인·N 보존, 좌석/참가/동의/예약 자동복원 없음이다. 별도 불변 정정 감사와 원자성·최종시각/CAS를 제안했다.
- 보관은 전raid 완료근거+열린 다음 실제주차 없음 조건이며 일부완료/0명/legacy를 전체완료로 추정하지 않는다. SQL pagination 전 current 실제참여필터와 기록조회/원ACK·개인정정 유지, N개방 경합/완료정정후방비복원도 검증대상이다.
- Flutter125 2ba24d95 push·단일190mock/분석0은 보고수신이며 독립재현/기기전체인수 아님. 레벨/최고난이도·생성실제T상세/새생성·변경캐릭터완료 정상확인 전달만 기록한다. 실회원/기기전체·성능/운영, pending영속복구·#19는 미완료/별도다.

## 현재 — F6-C 재개 확인 Backend 구현·개발 반영 완료

[Backend118 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355880490)을 [Flutter120](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356264877)이 세방식 모두 수용해 구현했다. [개발 안내](../ISSUE_13_WEEKLY_RESUME_REVIEW_DEVELOPMENT.md)·[실행 OpenAPI](../../openapi/two-cycle.openapi.yaml)가 기준이다.

기존 POST의 읽기전용preview/Key분리, GETplan opt-in의재개제안별resume_review, 보호된생성/응답token과고정시각/설정/영향·현재권한/CAS를구현했다. null retained/[] 무일정·명시배열/순서·생성자표/1인별도응답·거절/미응답의참가재연결과시간동의구분·원Ack를보존한다. 새JSONB review_version=1과구형legacy_unverifiable를구분하며신규보호제안의token없는새응답은거절한다(Flutter120수용). 구형미결payload/원Ack·기본false응답을보존하고실패token fallback/과거행갱신/추가DDL은없다.

최종65PASS/763.70초+구형시각미정보완3PASS/41.43초(중복2제외고유66:신규30/기존회귀36)·두프로필OpenAPI전체일치·Python223소스/이미지바이트일치다. 실제API8000은168경로/DB0029·50928839…/healthy, 교체전후105표344행/전체내용지문·환경/키mount·보안/포트/command보존이다. 임시검증DB/runner/network정리완료, migration/초기화/실회원쓰기/키변경없음이다.

소비구간 `29408243192ed3a37a347ade046db26ad2d918b9` commit/push·원격SHA확인 및 [전체121번째 Backend · F6-C 구현/개발 반영/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356827586) 게시·전문일치 확인을 완료했다. Flutter122의 F6-C 연결 결과를 수신했다. 다음 담당은 Flutter F1~F6 전체 실회원/사용자 기기 인수 준비·최종 연결/조건 체크리스트 대조이며 Backend는 재현 차이 대응이다.

## 이전 인계 — F1~F6 실회원·기기 인수 준비

[전체122번째 Flutter · F6-C 연결 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6357361150)에서 Backend2940824 소비·Flutter618f95e6/feature/raid-recruitment-scheduling commit/push·원격일치, 최종 단일153mock PASS·변경Dart7파일 분석0을 보고했다. Backend 독립재현이나 실회원/기기 인수 근거로 확대하지 않는다.

- F6-C 생성 전 preview/제안별 표시·확인/원명령 재송·원Ack/recorded·applied 구분 및 적용 후 현재T 자동조회 연결을 보고했다. 조회 실패에도 원Ack 확정·pending해제를 유지한다.
- 신규 계약 차이·추가 Backend 변경 요청은 없다. 중복 확인 댓글이나 동일 시험 요청은 작성하지 않는다.
- 정상인증회원 HTTP·실회원쓰기·새ID/참가/시간동의/예약·완료/N 보존·확인창/접근성/실기기/성능은 미확인이다. Backend DB/HMAC/권한/CAS/경합/원자성/정족수의 Flutter 독립재현도 미확인이며 Backend 기존 자동검증과 구분한다.
- Flutter는 F1~F6 전체 인수 준비·최종 조건 대조를 진행한다. Backend는 재현 가능한 차이 발생 시 해당 구간만 대응한다. 모집관리 pending 앱종료 후 영속복구는 별도 후속이다.

## 수신·후속 상태

- Flutter114 F5/1a909e7 push·단일106mock PASS/분석0, Flutter117 F6-A/660433d push·단일108mock PASS/분석0, [Flutter119 F6-B](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6356041000) ea0c932f47094e70d324ec790c2892f8011b774f push/원격확인·단일156mock PASS/분석0 보고다. Flutter119는B별도사용자승인구현임을명시했다. Backend독립재현/실회원·기기인수는아니며서로합산하지않는다.
- 정정은manual근거해제만/완료Assignment·Round·party·참가·예약복원역명령없음이다. 모집관리pending은app소유메모리writer이며앱종료뒤영속복구완료로확대하지않는다. #19통계는독립후속이다.
- 기본0.4.1/policy4·canonical SHA·기본0023OpenAPI는유지한다. 재기동은compose.yaml+compose.two-cycle.yaml/two-cycle factory이며DB29에기본0023앱/구worker를혼용하지않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를따르고source23checkpoint재실행/과거snapshot overwrite없음. dev/main병합·운영배포·Issue종료는하지않았다.
