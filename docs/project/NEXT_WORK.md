# 다음 실행

2026-10-22 / **feat/raid-recruitment** / Issue [#13](https://github.com/heo0328/lostparty-backend/issues/13).

## 최신 수신·다음 Backend — 그룹 캐릭터 필터 후보 계약

[94번째 Flutter F1](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6335276652)·[95번째 F2](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6335852339)·[97번째 F3 독립 구간](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6337065372)의 commit/push·mocked HTTP 검증 보고를 수신했다. F3 전체/정상 인증 HTTP·실회원·기기 인수는 미완료다. [96번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6336402066)의 그룹원 전체 활동 캐릭터 후보 출처는 현재 계약/구현에 없음을 확인하고 [전체98번째 Backend · 후보 출처 점검](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6337703638)에 회신했다.

다음 담당 **Backend**: 단일 선택 그룹의 후보 조회 계약을 작성한다. 기존 R0 기술경계4판 §3.1의 타인 전체 roster 비공개와 달라지는 공개 범위를 명시하고, 소유/활동·대표표시/캐릭터/역할별 전투력 nullable/출처·context/ref 결합·회원별 묶음/레벨 정렬/안정 cursor·권한/소유/활동 변경 무효화를 정의해 Flutter와 대조한다. 합의 전 새 API/권한을 구현하지 않는다. 기존 방 projection·본인 캐릭터 API는 전체 후보 대안이 아니며 페이지 후 로컬 필터로 대체하지 않는다. Flutter는 후보 부분만 계약 대기, 독립 구현 결과 유지다. 새 소비 SHA/경로는 아직 없고 현재 계약/서버는 유지한다. 아래 정상 로그인/기기 확인은 별도 남은 인수이며 이번에 반복 요청하지 않았다. 아래 인계 당시 차이 대응 순서보다 이 후보 계약 보완을 우선한다.

[개발 DB/API 실제 전환](../ISSUE_13_W5_LIVE_CUTOVER.md) 완료: 구 API/모든 내부 worker 정지·다른 DB 연결0 확인 후 새 checkpoint, 제한 app LOGIN의0023→0029·82업무표413행/기록시각·키4개/시퀀스 보존, API8000 factory167경로/새 worker 기동·호스트 health200. 두 프로필 OpenAPI 전체 객체 일치·공개/인증 거절 HTTP8검사·기존2회원 서비스 읽기·기동 후 전체 테이블 불변 확인. 신규 DTO/계약/DDL 변경 없음. 지난주7건의 현재 C/N 검색 제외는 사용자 확인한 정상 동작이며 원본/관계는 유지한다.

착수/인계 시 AGENTS → 협업 → 이 문서 → AI_CONTEXT → 계약3판/4판/ACK와 Issue 본문/최신 댓글·Git을 확인한다. 계약0.4.1/policy4·canonical SHA `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1` 유지. 구간 `3c26cdb6fd8a17c0bf0d7afaa3bbd93d1f4f3176` commit/push·실제 원격 SHA 일치 확인·[전체92번째 Backend · W5 실제 전환/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6332478347) 게시 완료. 다음 담당은 Flutter 메타/summary·주차 선택/계정 캐시 격리·정상 로그인 확인이며 Backend는 차이 대응이다.

## 다음 Flutter — 주차 메타·summary/선택기 소비

- 정상 로그인으로 GET `/v2/raid-cycles`·POST `/v2/me/raid-weekly-summary` 성공과 C/N 선택/target 본인 목록을 연결한다. 현재 로컬 개발 서버는167경로/DB29이며 기존 개발 연결 경로를 사용한다. 실제 기기 연결/로그인 성공은 Backend 공개 HTTP·서비스 읽기 검증과 별도 미확인이다.
- 계정 전환/로그아웃 시 summary·선택 주차 캐시를 회원/환경별로 격리한다. 사용 계약 SHA·확인/실패/미확인을 같은 #13에 회신한다. 과거7건은 C/N 밖이므로 현재 공개 검색에 없는 것이 정상이며 persistent 관계/한도는 자동 해제하지 않았다.
- v1 위험 방 쓰기는 원 ACK 우선/409 CLIENT_UPGRADE_REQUIRED이고 본인 수동 C10시/개인표는 유지한다. 새 쓰기/실회원·기기 전체 인수는 이 읽기 구간과 구분한다.

## 다음 Backend — 인계 회신 대응·현재 실행 유지

1. [전체92번째 Backend · W5 실제 전환/Flutter 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6332478347)의 Flutter 회신을 확인한다. 정상 로그인/읽기 성공·사용SHA·캐시 격리 결과를 구별하며 새 계약 재채택 요청은 하지 않는다.
2. Flutter의 재현 가능한 차이/실패가 있으면 기존 브랜치에서 필요한 구간만 보완·검증·게시 후 회신한다. Flutter 적용을 추정해 완료 처리하거나 새 기능 범위를 추가하지 않는다. #19 통계는 독립 후속이다.
3. 개발 재기동은 `compose.yaml` + `compose.two-cycle.yaml`/two-cycle 이미지·factory를 함께 사용한다. 실제 DB29에0023 기본 앱/구 worker를 혼용하지 않는다. [재기동 명령과 복구 경계](../ISSUE_13_W5_LIVE_CUTOVER.md)를 따른다.
4. 비공개 checkpoint는 `backups/lostparty-preflight-f2b2a14f7162`에0700/0600·Git/Docker 제외로 보관한다. source23 전용 checkpoint 도구를 현재29 source에 재실행하지 않는다. 새 쓰기 이후 snapshot overwrite로 자료를 버리지 않으며 실제 복구/운영변경/merge는 범위를 별도 확인한다.

추가 제품 입력 대기는 없다. 실제 인증 HTTP 성공/provider·Flutter 적용·실회원 쓰기/기기·운영 인수는 미완료다. 테스트 토큰 발급/저장은 자동 승인 검토 거절로 실행하지 않았고 정상 로그인 검증을 Flutter 인계 범위로 남긴다. 이전 W5 합성304/백업 보호7은 기존 근거이며 이번 실제 확인과 합산하지 않는다.
