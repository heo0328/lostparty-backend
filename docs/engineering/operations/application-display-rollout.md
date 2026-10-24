# 신청 표시 프로필 개발 서버 반영

2026-10-25 / 작업 구간명: 신청 표시·본인 승인 대기 프로필 개발 반영. 작업 내용: 검증 이미지 교체·자료 보존 감사·실행 계약/HTTP 확인·네이티브 인계. 브랜치: `feat/raid-recruitment`.

사용자 진행 지시에 따라 구현 source `06ea4b214591f475d422f4599ca10260cda83d08`, 이미지 `sha256:d24d7cbd3215ff3c6cf40aa86e3a111d84eef347d788c2b2d7d98820a44e4dfc`를 로컬 개발 API/동일 lifespan worker에 반영했다. `compose.yaml` + `compose.two-cycle.yaml`, `app.main:create_two_cycle_app --factory`를 유지하며 DB는0031_membership_actions다. 목록/일반상세의 `reader_profile=application-display-1`과 DB오류503 SERVICE_UNAVAILABLE 정정이 실제 서버에서 실행된다. 경로수177은 이전과 같고 두GET의입력/응답 계약이갱신됐다.

## 자료 보존·복구 기준

API/worker 정지 후 private DB custom dump·키/설정 백업·읽기 감사 기준을 확보했다. archive catalog 읽기와 백업 중 DB불변을 확인했다. 교체 전후108표/829행 전체의행hash·열정의·시퀀스·DB profile·인증키hash가동일하며 DB컨테이너/볼륨·API환경/명령/보안/포트·키원본mount/readonly를보존했다. migration·실회원자료수정·키생성/초기화를하지않았다. 비공개백업원본은게시하지않는다. 이번restore리허설은미실행이다.

기존이미지fdd256ea…를 `lostparty-backend-api:before-display26`로보존했다. 복구필요시현재새쓰기와호환성을먼저확인하고API이미지만되돌린다. 과거DB백업덮어쓰기/키·볼륨초기화로새자료를버리지않는다.

## 실제 확인 결과와 한계

[공개 집계](records/application-display-rollout.json): 소스/설정241파일바이트일치, 실제교체컨테이너177/기본116 OpenAPI 객체전체일치. 실제HTTP12건 통과: health/공개주차200, 새표시목록/상세 각각무인증·invalidBearer401 ACCESS_INVALID/challenge/no-store4건, 기존후보양intent같은인증거절4건, C/N공개검색200/no-store2건이다. API/DB healthy이고임시읽기컨테이너는제거했다.

정상로그인실회원의확장조회200·기기에서카드/버튼상태인수는아직미확인이다. 기존회원session으로토큰을만들거나회원명령·provider/기기조작을하지않았다. 격리28PASS·추가참조12PASS·Flutter413자체보고·작성예시정적검증과이번실행확인은합산하지않는다. 상세예시보완source13ae0a5와API구현source06ea4b2도구분한다. dev/main병합·AWS/운영배포는미실행이다.

## 다음 담당

Flutter가이미연결한앱에서정상로그인후소수항목으로인수한다. 공대장카드의역할별전투력/현재분석·미확인표시, 본인pending방재진입의승인대기안내/신청버튼숨김을먼저확인한다. 철회/만료·수락후기존흐름은해당상태가발생할때확인하며이를위해실회원상태를임의변조하지않는다. 기존가입3항목·413전체시험을이유없이반복요청하지않는다. 변경/반대파티/C/N직접영향은계속추적하고재현차이는#26에개인정보를제거한상태/code·구간으로회신한다. Backend는직접차이에대응하며Issue OPEN을유지한다.

공식 반영인계: [#26 전체18번째 Backend · 표시 프로필 실제 개발 반영](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386031663). 반영근거 `6444c18bc3de8b341251169f84584cb622b69154` commit·push·원격일치 확인후 게시·전문/실제전체순번 재조회 완료. Issue상단 최신반영상태/다음담당과OPEN을보존했다.
