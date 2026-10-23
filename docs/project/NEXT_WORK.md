# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 공통 기준 — Issue21 전달/문서 정리 완료·종료

[Issue21](https://github.com/heo0328/lostparty-backend/issues/21)의 [공통 원문62240fe](https://github.com/heo0328/LostParty_flutter/blob/62240fe25711d26c478c295590c80114ebf69a6a/docs/architecture/DEVELOPMENT_QUALITY_AND_UX_STANDARD.md)을 읽고 [Backend 최소 지침](../DEVELOPMENT_QUALITY_AND_UX_STANDARD.md)을 AGENTS/개발·협업 규칙에 연결했다. 기존 규칙 충돌 없음, 승인된 후속 기능부터 사용자문제/책임/선택·소비영향/필요검증에 적용한다. API/DB/배포/전면감사·최적화 착수 없음이다. 릴리즈 배포·안정 확인 후 종료보고에서 배포main/태그 기준 목적별 최적화 검토시점을 안내하되 지금 브랜치/자동작업을 만들지 않는다. [전체1번째 Backend · 품질/UX 지침 반영 결과](https://github.com/heo0328/lostparty-backend/issues/21#issuecomment-6360604622)에 적용기준/실제순번·전문일치 확인, 사용자의 문서 commit/push 지시에 따라 지침afb0a0c·전달/종료기록02a8ce2와 게시상태 기록을 feat/raid-recruitment에 함께 게시한다. 사용자 지시로 내용전달 전용 이슈는 추가댓글 없이 종료한다. 별도회신/수용대기는 없고 양측은 이후승인작업부터 적용한다. Issue13 후속은 아래 상태를 유지한다.

## 현재 — 완료 정정·방 보관 게시/개발반영/소비인계 완료

[Flutter127 수용/최종 wire 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358680312)을 기준으로 [개발 안내](../ISSUE_13_COMPLETION_CORRECTION_DEVELOPMENT.md)·[예시8개](../design/issue13-completion-correction.examples.json)·[실행 OpenAPI](../../openapi/two-cycle.openapi.yaml)의 새2경로/총170경로를 구현했다. 기존168경로/기존schema·manual/summary·원ACK 의미는 유지한다. 복구용 room=null/gen=null 실관계와 양수gen review, 보관회원 detail/plan의 permission/access·실제UUID/리더십, 새context/ACK·주차경계·오류 순서를 닫았다.

관련 고유42PASS(신규26/회귀16). 초기42묶음41PASS/구계약 기대1실패 뒤 새current/all 계약으로 시험기대 수정·5PASS(4중복) 재확인, 탐색24와 합산없음이다. 예시8개의 closed OpenAPI 검증·기본116/두주차170 실행계약 전체일치·app/alembic228파일 바이트 일치다. 실제 API8000/이미지13291847… healthy·DB0030: 기존104업무표430행/전체내용·열정의·설정보존, 새 감사표0행·총106표431행(version포함). DB재시작/기존행삭제·수정/키교체·실회원 쓰기 없음, 실제ready/health/인증거절4검사·임시환경정리 완료다.

소비 `8bbcfc8cb89e69eb1f9747a0fcf2e919e41c3b76` commit/push·원격SHA일치 및 [전체129번째 Backend · 완료정정/보관 구현·개발반영·소비인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618) 전문/실제순번 확인을 완료했다. 다음Flutter는 새reader/정정writer·원pending schema호환/권한/ACK·목록/기록 직접차이 연결·결과회신이다. 같은 계약 수용/기존 mock 반복 요청은 하지 않는다. 실제 정상회원HTTP·실기기전체/성능·운영 인수, 과거·은퇴UI 확대/pending영속복구/#19는 별도다. 아래는 이전 구간 기록이다.

## 다음 Backend — 개인 완료후 선택T 탈퇴 / 양T 동일회원 추방 계약 검토

[전체131번째 Flutter · 개인 완료후 선택T 탈퇴 계약 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360708926)이 추가됐다. 사용자 의도는 “나혼자 완료처리이후 탈퇴”: 선택raid 본인완료 + 같은실제T의 나머지 본인참가 취소/예약정리 + 공대장자동승계/마지막1인종료를 한명령으로 처리하고 다른T는 보존하는 것이다. 현재 personal_completion은 선택round 본인Assignment만 완료·남은active없으면CycleMember.completed이며 명시탈퇴/자동승계를 하지 않는다. global leave/end로 대체할 수 없음을 코드에서 확인했다.

- 다음 Backend: 정확한 context/impact·permission과 선택raid완료/다중raid잔여취소·후계자권한/자격/마지막1인·소유/CAS/세대·원ACK/재송·예약/주간근거·N보존을 최소계약으로 검토한다. 새계약 미합의·미구현이며 기존 item완료/원pending을 바꾸거나 두명령자동연속으로 대체하지 않는다. 사용자확인중인 양T강제해산을 확정범위로 포함하지 않는다.
- 별도 기존 요청 [전체128번째 Flutter · 양주차 동일회원 함께 내보내기](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360210574)는 현재카드 대상/실제T 고정·반대C/N 같은 user_id의 실제참가·각T리더십/권한·CAS·current-only/양T원자처리·단일ACK/원재송/양T무효화 계약 검토 대기다. 미합의·미구현이며 현재T공대장의 권한을 임의확대하지 않는다.
- [전체130번째 Flutter · 상세행동/카드단일T추방 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360353809)는1d6c0c1a commit/push·최종단일144mock PASS/전체분석0 보고다. 기존소비2940824·한T writer 유지/양T추방미구현이며 Backend 독립재현/실회원·기기인수와 구분한다.
- 기존 완료정정/보관 Backend129·소비8bbcfc8 인계는 완료 상태를 유지한다. Flutter131은 새소스와 정적대조했으나 새 정정/보관의 구현연결 완료회신은 아직 없다. 다음Flutter는 해당 인계의 직접연결/결과회신, 다음Backend는 위 두 별도계약 검토다. 같은기존시험·정책재수용 요청은 없다.

## 이전 — F6-C 재개 확인 Backend 구현·개발 반영 완료

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
