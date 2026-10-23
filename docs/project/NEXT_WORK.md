# 다음 실행

2026-10-23 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13), OPEN.

## 다음 Backend — F6 현재주 재개 제안의 일정 표시·binding 계약안

[전체115번째 Flutter · F6 설계 질문](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355333496)을 고정소비07c2b671의 구현/OpenAPI와 정적 대조하고 [전체116번째 Backend · 정정 범위 확답/재개 표시 보완 필요](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6355428620)에 회신했다. 현재는 계약 확인이며 새 API/코드·서버 반영 완료가 아니다.

1. 기존 권한 안에서 **제안별 불변 CycleResume.content의 일정 의도**를 읽는 최소 계약안을 작성한다. 현재 views/BResumeProposal은 원본 schedule_groups/시각/표시revision을 내보내지 않는다. 현재 plan.groups나 F5 prejoin display를 원본으로 대신하지 않는다. 기존 조회경로 확장/opt-in·닫힌 DTO·구 소비 호환·1MiB 등 정확한 wire는 다음 초안에서 확정하고 Flutter 대조 뒤 구현한다.
2. 실제 C/동일 cycle·generation/proposal revision·대상item/round·미생성 session/미정/후보/조율·적용 영향과 동의 경계를 정의한다. apply/make_session은 현재 target 설정 duration 등을 사용하고 대상/자격/정족수를 재계산하므로 제안 당시 고정 입력과 현재 검사를 구별한다. 시각/설정 근거 고정·변경거절/재확인·token/revision/응답 binding을 함께 검토한다.
3. **생성 전 확인 포함:** 2명 이상 create의 제안자 accept 기록, 1명 별도 본인 응답, schedule_groups=null의 retained 해석 원문 확인을 다룬다. 응답자 표시만 보완하지 않는다. 기존 미결 원본문/key/token·원ACK 우선과 호환을 보존한다. 현행 닫힌 POST에 임의 새 필드를 추가하지 않는다.
4. 최소 계약안 소비 대조→합의 구현/격리 검증→구간commit/push·원격확인→실행/소비SHA 인계 순서다. 개인표·다른방 공개/새권한·역명령/자동예약복구를 범위에 넣지 않는다.

## 다음 Flutter — 재개만 보완 대기·독립 F6 설계 진행

- 정정은 v2 manual-completion completed=false로 **본인 manual 완료 근거 해제**까지만 연결한다. party 원천/완료 Assignment·Round·참가·예약 복원은 지원하지 않는다. personal_completion이 남긴 manual 원천을 해제하더라도 완료 Assignment 복구가 아니다.
- 계정 새 수동명령 v2 전환/기존 v1 pending 원경로 보존·command-context 기반 complete_item/personal_completion/close_weekly 독립 설계는 진행 가능하다. 실제 C/수10시·권한/서버 impact·원ACK·N/다른item 보존을 유지한다.
- 현재주 재개 UI/응답만 Backend 표시 계약안 대기다. N opening/reopen과 구별하고 같은 cycle/generation의 새 round/assignment·완료이력 보존, recorded/applied 구분·정족수/동의/예약 서버 판정을 유지한다.

## 수신 완료 — Flutter F5 사전 표시 코드·자동검증

[Flutter113 소비 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6345378281) 뒤 [전체114번째 Flutter F5 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6345894901)는 feature/raid-recruitment-scheduling / **1a909e7 commit/push·최종 단일106mock PASS·분석0** 보고다. 기존 세GET opt-in/닫힌DTO·실제ID별 시각/명시선택·preview/none·변경거절/원ACK 연결의 코드/자동검증 구간 완료로 기록한다. Backend가 Flutter 소스/시험을 독립 재현한 결과는 아니다. 같은 정책 수용/기존시험을 반복 요청하지 않는다.

F6는 Flutter115의 e910231/F5 유지·설계 대조 단계다. 실제 정상로그인 회원HTTP·실회원쓰기/기기 가독성·스크롤/글자크기/성능·운영 인수는 미완료이며 앱종료 뒤 관리pending 영속복구도 이번 범위 밖이다.

## Backend 실행 기준 유지

- 구현소비 **07c2b671d67e5dfcef5f873ef55ffcb54f87b365** / 원격 문서HEAD00db6c8 기준. [표시 개발 안내](../ISSUE_13_PREJOIN_SESSION_DISPLAY_DEVELOPMENT.md)·[실행 OpenAPI](../../openapi/two-cycle.openapi.yaml). 이전 고유48PASS·실제API8000 168경로/DB0029·이미지404cf8c4…·전후105표345행/내용·설정보존 근거를 유지하며 이번에 재시험/합산하지 않았다.
- 이번은 정적 계약 대조·회신/문서 기록만 수행했고 앱/API·서버/DB/키 변경·시험 컨테이너 기동은 없다. 문서 구간은 로컬커밋·미push로 기록한다. dev/main 병합·운영배포·Issue 종료 없음.
- 재기동은 compose.yaml + compose.two-cycle.yaml/two-cycle image·factory를 함께 사용한다. 기본0023 앱/구worker를 DB29에 혼용하지 않는다. [전환/복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를 따른다. source23용checkpoint 도구를 DB29에 재실행/과거snapshot overwrite하지 않는다. #19 통계는 독립 후속이다.
