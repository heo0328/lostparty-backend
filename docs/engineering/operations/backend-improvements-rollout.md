# Backend 개선 개발 서버 반영

2026-10-25 / 작업 구간: Backend 개선 실제 반영·통합 기록 정정 / 브랜치 `feat/raid-recruitment`.

사용자의 ‘개선 사항을 반영하고 모집 브랜치에 병합’ 요청을 코드 병합으로만 처리해 실제 서버 반영을 빠뜨렸다. 사용자 정정 지시에 따라 이번에 기존 개발 서버에 적용했다. 병합 이력은87c2a0e로 이미 보존됐으며 같은 소스를 실제 서버에도 맞췄다. [공개 검증 집계](records/backend-improvements-rollout.json)를 따른다.

## 실제 실행 기준

소스 `87c2a0e5e6f5b58f87ca8094324ec5a606b280ca`, API 이미지 `sha256:366e868aacb5937f47e54edecc028742338719286f83dd6f99d4ef7a8ebfc773`, two-cycle177경로/기본116·DB0031_membership_actions다. 새 격리 실행 경로는 작업 소스에 통합됐고, 서버는 고정된 runtime31개와 새 JSON 로깅을 사용한다. API/DB 모두 json-file10m×5 정책이며 healthy다. 실시간 로그 조회는 [로깅 안내](logging.md)를 따른다.

서버 API 이미지를 별도 태그로 먼저 빌드하고250개 소스/설정 파일hash·두 OpenAPI 전체 객체·고정 패키지를 확인했다. 사용자 데이터 쓰기 없이 후보와 기존 환경도 비교했다. PostgreSQL 이미지는 기존 것을 그대로 사용했다.

## 백업·보존·적용

API와 lifespan worker를 일시 중지한 뒤 비공개 DB custom dump·키 tar·실행 설정/감사 기준을 보관했다. dump archive catalog 읽기와 백업 중 불변을 확인했다. 백업 원문/키/환경값은 게시하지 않는다. 이번 restore 리허설은 미실행이다.

API의 새 이미지·CLI 로깅 설정을 반영했다. DB도 로그 보관 설정10m×5를 적용하도록 같은 PostgreSQL 이미지·기존 영속 볼륨으로 컨테이너만 재생성했다. 기존 데이터 디렉터리 초기화·볼륨 삭제·migration·DBbackfill·회원 자료/키/환경 수동 변경은 하지 않았다. DB·API 환경,포트/보안/재시작 정책과키mount source/readonly를 보존했다. API command에는 no-access-log/log-config만 추가했다.

전후108표993행의 전체 행hash·열정의·시퀀스·DBprofile·키hash 동일을 확인했다. 이는 이전 아이템레벨 반영 당시893행을 복원한 것이 아니라 **이번 반영 직전993행을 보존한 결과**다. DB의 의도적인 컨테이너 재생성과 데이터 볼륨 보존은 구분한다.

보존 확인 helper가 DB에 없는 선택 HostConfig.Tmpfs 키를 직접 참조해 한 번 중단됐다. 비교 보조 코드만 선택필드 처리로 정정해 통과했으며 서버 실패·데이터 수정·추가 교체가 발생한 것은 아니다.

## 실제 실행 확인

- health/공개주차200, 신청목록/상세·후보 두intent의 무인증/invalidBearer401 ACCESS_INVALID·no-store/Bearer경계8건, C/N 공개검색200/no-store2건으로 실제 HTTP12PASS.
- 실행 컨테이너에서 기본116/최신177 OpenAPI 객체 전체 일치와 runtime31개 정확 설치목록 검증PASS.
- 실제 API 최근64줄은 모두 허용 JSON 형식이었다. http_request20/api_rejected8/job_completed32/server_event4, 오류UUID와 요청 요약 연결 및 실제 주소/query/식별자 누락을 확인했다. auth_cleanup/ownership_settlement/recruitment의 성공tick을 모두 확인했다. 원문 로그는 게시하지 않고 집계만 남긴다.
- API/DB healthy·임시 reader 제거·기존 볼륨/키 유지 확인. 서버 부하/50MB 실제 rollover·정상회원 명령/기기/provider·운영 인수는 미실행이다. 기검증 격리78/18과 이번 HTTP12를 합산하지 않는다.

## 복구·후속

이전 API 이미지6d5857b3는 before-improvements 태그로, DB이미지도 같은버전 확인용 태그로 보존했다. API 복구가 필요하면 새 쓰기 호환을 확인하고 이전 이미지와 이전 command/log설정을 사용한다. 과거 백업으로 새 회원자료를 덮어쓰지 않는다.

이번은 기존 로컬 개발 서버 반영이다. AWS 운영 배포·dev/main 병합·전체 모집 인수·네이티브 새시험 요청/Issue 게시는 실행하지 않았다. 이후 사용자 승인으로 개선 병합·실제 반영 기록7d038cf를 원격 모집 브랜치에 push하고 SHA 일치를 확인했다. 소스는 이미 모집 브랜치에 통합돼 있고 현재 checkout도 해당 브랜치다. 네이티브 구체 차이 대기는 유지한다.
