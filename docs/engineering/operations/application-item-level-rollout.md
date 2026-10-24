# 신청자 아이템레벨 보완 개발 서버 반영

2026-10-25 / 작업 구간명: 신청자 아이템레벨 보완 개발 반영. 작업 내용: Flutter 호환 회신 확인·검증 이미지 교체·자료 보존 및 실행 확인·인계. 브랜치: `feat/raid-recruitment`.

사용자가 네이티브 회신 확인 후 서버 반영을 승인했다. [#26 전체23번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386758343)에서 출처별 표시 연결(source13fb5848, push 확인·158PASS 자체보고) 및 추가 소비 차이 없음을 확인했다. 새 앱은 필수3키가 없는 기존 서버의 비어 있지 않은 신청목록을 오류로 처리하므로 호환 연결 후 반영했다. Backend가 Flutter 시험을 독립 재현한 것은 아니다.

## 반영 소스·범위

구현 source `f471e3133ad60befcad77d7123e1107ba7501bb4`, 이미지 `sha256:6d5857b38b91c6cb1f5ec2f61a047cf4bfd3a31a4b10b6b6efbd299710f4f242`를 기존 개발 API와 동일 lifespan worker에 반영했다. compose.yaml + compose.two-cycle.yaml, two-cycle factory·177경로·DB0031_membership_actions를 유지한다. 신규 신청은 실제 레벨 snapshot/원본시각을 저장하며, application-display-1 목록의 기존 누락은 합의한 current_saved/unavailable 출처로 읽기 보완한다. 기존 신청 DB backfill·provider 호출·migration은 없다. [합의·구현 계약](../../features/recruitment/participation/application-item-level-proposal.md)을 따른다.

## 보존·실행 확인

[실행 집계](records/application-item-level-rollout.json): API/worker를 중지하고 비공개 DB custom dump·키/실행 설정 및 읽기 감사 기준을 확보했다. archive catalog 읽기·백업 중 DB 불변을 확인했다. 교체 전후108표893행의 전체 행hash·열정의·시퀀스·DB profile·키hash가 동일하다. DB 컨테이너/볼륨·API 환경/명령/포트/보안·키 원본mount/readonly를 보존했다. 백업 원본은 게시하지 않으며 이번 restore 리허설은 미실행이다.

실제 컨테이너 소스/설정241파일 바이트 일치,177/기본116 OpenAPI 객체 전체 일치, HTTP12건 통과다. health/공개주차200, 표시목록/상세의 무인증·invalidBearer401 ACCESS_INVALID/no-store/challenge4건, 기존 후보 양intent 동일 인증경계4건, C/N 공개검색200/no-store2건이다. API/DB healthy·임시reader 제거를 확인했다. 이전 이미지d24d7cbd…는 `lostparty-backend-api:before-item-level26`에 보존했다. 복구가 필요하면 새 쓰기 호환을 확인해 API만 되돌리며 과거 DB 백업으로 새 자료를 덮어쓰지 않는다.

격리 Backend35PASS·Flutter158 자체보고와 이번 실행12건을 합산하지 않는다. 정상로그인 실회원 확장목록200·새신청 저장/기기 표시 인수는 미확인이다. 실제회원 session으로 JWT를 만들거나 회원 명령·provider·기기를 조작하지 않았다. 키/회원자료 수동수정·dev/main 병합·AWS/운영배포는 없다.

## 다음 담당

Flutter는 반영된 서버와 source13fb5848 이후 앱에서 정상로그인으로 신청카드의 레벨/출처 문구만 소수 확인한다. snapshot은 ‘아이템 레벨 1700’, 현재정보는 ‘아이템 레벨 1750 · 현재 저장 정보’, unavailable은 ‘아이템 레벨 조회 불가’다. 시험만을 위해 실회원 자료를 변조하지 않는다. 기존 정상1/2 전체·전체413 시험을 반복 요청하지 않는다. 차이는 개인정보를 제거한 상태/code·재현구간으로 #26에 회신하며 Backend가 직접 대응한다. Issue OPEN·기존 IF-001 및 독립 미완료 범위를 유지한다.

공식 인계: [#26 전체24번째 Backend · 아이템레벨 실제개발 반영](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386808894) 게시·댓글전문/실제순번 확인. 반영근거 `6be5c6fee12272858acc5493b06278340096521f` commit·push·원격일치 후 인계했고 Issue 상단/OPEN·원본이력을 보존했다. 다음Flutter 레벨/출처문구 소수기기인수·Backend직접차이대응이다.
