# 서버 분석 개발환경 준비

2026-11-17 후행 Issue58: 로컬dev는 현재0038_analysis_candidates/API로 전환됐다. 기존자료·키/환경 보존 및 전체계약일치, [반영집계](../operations/records/analysis-candidates-local-rollout.json). 아래0037 준비/전환은 당시 이력이다.

2026-11-17 실제 개발 반영 완료: 사용자 토큰 파일 준비 확인 및 로컬 DB 삭제 명시 승인 후 lostparty DB만 초기화·0037 적용, 게시 구현 b95cff5 기준 image c2b4a320…a2dc로 개발 API 전환/healthy 확인. 기존 볼륨·DB 역할·환경/키와 운영은 보존했다. OpenAPI 전체 일치·health/공개 그룹200·미로그인 주차/개인 bootstrap401·회원0·서버 키 로딩 PASS. 실제 provider·회원 수집/저장·기기 인수는 아직 미검증이다. [전체15 Backend·개발 전환 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6921019988). 다음 Native I1 새 로그인·원정대 등록/서버 분석 연동, Backend는 결과 대응이다. 초기화는 이미 완료했으므로 반복하지 않는다. 아래 이전 준비/승인 대기 문구는 전환 전 이력이다. 최신 준비/반영 기록은 미커밋·미push다.


2026-11-16 / Issue55 / refactor/lostark-server-processing / 구현 b95cff5·게시 기록 e3ada17. 사용자 개발환경 준비 지시로 읽기 점검과 실행 후보 이미지 빌드를 완료했다. 실제 DB/환경/키/실행 API는 변경하지 않았다.

## 점검 결과

- 현재 API/DB 컨테이너 healthy, DB lostparty/0036_roster_presence. 업무표117개·총1,562행이며 회원3·세션13·게임 계정2·그룹1·모집실11건이다. 원문/비밀값 없이 집계만 읽었다.
- 0037 충돌 자료: 개인키2·역할 요약21·과거 정상 전투력21·소유권 proof3·모집 배정29·주차 신청2·옛 분석/키 명령425건. 현재 DB에 migration을 실행하지 않았다.
- 기존 JWT/recovery/fingerprint/과거 암호화 키 파일은 존재하고0600이다. lostark-api-token은 없다. 개인 회원키를 임의로 복호화해 서버키로 전용하지 않는다.
- 현재 API image add287075a37…f2, 후보 lostparty-backend:analysis-dev-prepared-e3ada17 / image c2b4a3202d5d…a2dc. 후보는 별도 태그이며 실행 서비스/기존 latest 태그는 교체하지 않았다. 후보 명세는 DB/외부 네트워크 없이 호스트 OpenAPI 전체 객체와 비교한다.

## 실제 전환 전 필요한 입력

AGENTS의 “DB 볼륨 삭제·초기화 … 대상과 영향이 명시된 별도 승인 없이 실행하지 않습니다”에 따라 다음 초기화는 아직 승인받지 않았다.

대상 제안은 **로컬 개발 PostgreSQL의 lostparty DB 전체**다. 기존 API를 중지하고 해당 DB만 새로 준비해0037까지 migration한 뒤 후보 API를 적용한다. 해당 DB의 회원/세션·게임 계정/등록·설정·그룹·모집·주간 기록/명령을 모두 제거하므로 재로그인·계정 재등록/그룹·모집 재생성이 필요하다. PostgreSQL 클러스터 역할·기존 postgres_data 볼륨 자체·.env·키 파일 및 운영/Firebase/기기 자료는 삭제 대상이 아니다. 부분 자료 승계/호환 코드를 만들지 않는다. 승인 시 실행 직전 집계/대상과 다른 연결 여부를 재확인한다.

[백업 원장](../operations/backup-and-recovery.md)의 기존 로컬 DB dump 제외 결정을 유지한다. 기존 환경/4키 보관본은 재사용하며, 초기화 후에는 옛 실행 이미지로 되돌리는 것만으로 옛 DB 자료를 복구할 수 없다. DB 보존을 원하면 초기화 대신 별도 보존 범위를 먼저 지정해야 한다.

서버 키는 사용자 본인이 `.secrets/lostark-api-token`에 안전하게 저장하고 기존 fingerprint 파일과 같은 소유자/0600 권한으로 제공한다. 값은 채팅/Issue/Git에 붙이지 않는다. 새 token 원본은 기존 개인 백업 폴더에 별도로 보관하고 기존 fingerprint.key·credential.key 복구 사본은 그대로 둔다. token 미설정에서도 저장/공개 읽기는 가능하지만 실제 수집 검증은503이므로 수집 완료로 인계하지 않는다.

## 승인·파일 준비 후 실행

1. 기존 환경/키 보관 기준과 대상 DB 집계를 재확인하고 로컬 API만 중지한다.
2. 승인된 lostparty DB만 초기화·기존 제한 app role 권한을 준비하고0037을 적용한다. 기존 볼륨 전체 삭제/역할 재생성은 하지 않는다.
3. 현재 후보 이미지로 로컬 API를 교체하고 health/DB0037·생성 OpenAPI 전체 비교·인증 거절/공개 읽기를 확인한다. 실제 token은 출력 없이 공급/읽기 권한을 검사한다.
4. 새 로그인 후 소유 캐릭터 분석·개인 profile/bootstrap 및 Native 통합은 실제 입력 준비 수준에 따라 구분한다. 실제 provider 호출/등록은 테스트 대상이 준비된 뒤 필요한 범위만 진행한다.

준비 기록은 미커밋·미push다. 준비만으로 초기화/운영 배포·병합/추가 게시 승인을 확대하지 않는다.
