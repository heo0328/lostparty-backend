# 개인 완료 탈퇴 후 재신청 개발 반영

2026-10-27 / 작업 구간 **모집 재신청의 과거 기록·새 참가 판정 정합성 보완** / `fix/raid-recruitment-reapplication`.

[전체182 Flutter 갱신 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6435522815)·[184 Backend 설계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6435892485)와 사용자 승인에 따라 [구현·직접 검증](../../features/recruitment/participation/reapplication-history-fix-plan.md)을 완료하고 개발에 반영했다. 구현 `c1f86d8948601781e6c593341899c07ce83f1b68` push/원격 확인, 실행 이미지 `sha256:581a1a5ed2566061d4c1d23a83d622e36ed9f6da166666b74c1e76a28dfe13f2`, **DB0033_reapplication_history**다. 현재178/199·기본116/133·wire2/profile1·요청/응답/ACK/오류코드 유지. [공개 실행 집계](records/reapplication-history-rollout.json)를 따른다.

## 적용·보존 근거

후보262파일 해시·고정 runtime31·두 OpenAPI 전체 일치를 확인한 뒤 API/같은 worker를 중지하고 기존 DB에0033 DDL을 적용한 다음 새 API를 시작했다.0033은 Assignment 부분 유일 인덱스에서 completed를 제외하는 변경뿐이다. active/stopped의 현재 점유 제약은 유지하며 새 테이블/컬럼·자료 변환/삭제·과거 이벤트 backfill·dump/restore는 없다.

API 중지 상태에서 DDL 직전/직후 READ ONLY로 대조한112개 업무 테이블의1,883행 해시와 전체 sequence 값이 같다(alembic_version의 head 변경 제외). 기존 DB 컨테이너/이미지/볼륨/환경은 그대로며 API 환경값·실행 명령/사용자·포트·읽기 전용/보안/tmpfs/로그·키 mount source/읽기 전용·키 내용 해시·프로젝트 .env 해시도 같다. Docker의 환경 배열 순서만 달라 키/값 비교로 검증을 마무리했으며 배포/DDL 명령을 재실행하지 않았다. 원문 설정·credential·키 hash 상세·행 hash는 접근 제한된 ignored backups에만 보존했다.

기존420e057 API는0033 head를 지원하지 않는다. DDL 실패로0032에 원자 롤백됐을 때만 구 API 재시작이 가능하며,0033 커밋 이후에는 DB/자료를 유지한 전진 수정이다. 이번에는 rollback/구 API 재시작 없이 새 API가 healthy로 시작했다.

## 검증 범위와 제한

- 수정 전 합성 stale 실패를 재현했고 고유 격리20PASS(신규14/관련 기존6)를 확인했다. 같은 업무 소스의 성공 결과를 재사용했으며 전체 회귀·복원 리허설을 반복하지 않았다. 두 계약 전체·paths/components/닫힌 bundle·130완결 예시·원ACK32/음성3 보존이다.
- 실제 실행 이미지/소스 label·262파일 hash·runtime31·두 OpenAPI가 게시 소스와 같다. API/DB healthy·auth_cleanup/ownership_settlement/recruitment 성공, 확인 JSON 로그70줄/ERROR0이다. 오류 응답 검증에 따른 예상 api_rejected4는 서버 오류가 아니다.
- 실제 HTTP6PASS: health·공개주차200, 기존 문구와 join후보의 무인증/invalid Bearer401 ACCESS_INVALID/details=null/no-store/Bearer4. 정상회원 명령의 HTTP 성공으로 표시하지 않는다.
- 실자료 READ ONLY 서비스: 유효 세션2계정의 C/N 현재목록7건과 방 ID 합집합/공통한도 집계2쌍 일치, 역사목록66건, anchor기록34건·해제 구간22, 현재 종료 근거13건 정상 판정. 목록 페이지 상한50을 지켰고 GET/context의 쓰기나 실회원 생성·재신청·승인·원pending 재실행 없이 확인했다.
- 합성 PostgreSQL/인증 override HTTP와 실제 서버 읽기는 구분한다. 정상회원 재신청·기기 인수는 미확인이다. Native4833a164/111PASS 자체보고를 Backend 시험에 합산하지 않는다.

## 인계·다음 담당

[전체185번째 Backend · 개인 완료 탈퇴 후 재신청 수정/개발 반영·실행 확인](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6436334435)에 실제 소스·이미지·0033·검증/미확인을 회신했다. 이 반영 기록을 같은 브랜치에 묶어 commit/push·원격 확인한 후 같은 댓글에 고정 기록 링크와 직접 영향 확인 요청을 보완한다.

다음 Flutter는 제보한 **C개인 완료 탈퇴·N유지→다른 적격 캐릭터 후보/context/신청·승인→새 C 참가와 과거 완료 기록/N보존**만 실제 앱에서 확인하고 구체 차이를 회신한다. API shape나 화면 추가 구현은 필요 없다. 기존 정상 가입 전체·전체 성능/기기 인수를 반복 요청하지 않는다. Backend는 구체 차이에 대응한다. dev/main18830c2와 AWS는 변경하지 않았고 전체 인수·실제 원ACK 동일 키 대조·별도 기능 Issue는 OPEN/미완료로 유지한다.
