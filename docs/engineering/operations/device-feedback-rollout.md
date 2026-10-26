# 문자 정책·모집 목록 오류 개발 서버 반영

2026-10-26 / 작업 구간 **문자/목록 보완 개발 반영·실행 확인·인계** / `feat/raid-recruitment`.

사용자가 승인한 계획으로 소스 `0fd43f90b46847a1de40650b3e1812e6ff473218`를 실제 개발 API에 적용했다. API 이미지 `sha256:5f7c5b6387591b923b327cc89f50033f4196646b5c52973f85bdd7a25ea005dc`, DB `0032_beta_recruitment`, 기본116경로/133 operation·two-cycle178/199다. wire2/profile1·문자 `hangul-printable-ascii-1`을 사용한다. [공개 실행 집계](records/device-feedback-rollout.json)·[전체165 Backend · 문자/목록 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410058244)를 따른다. 기존 [기기 조사/소스 보완](../../features/recruitment/weekly-cycles/device-feedback-investigation.md)과 실제 반영은 별도 구간이다.

## API 교체와 유지한 설정

0fd43f9 후보 이미지를 먼저 빌드하고 실행소스258개 파일hash·두 OpenAPI 전체객체·공식 runtime31 설치검사를 통과했다. 격리된 직접시험7건은 동일소스 결과를 재사용하고 pytest 전체회귀를 반복하지 않았다.

Docker Desktop의 기존 UNC 키mount source는 Windows Compose로 렌더링했다. 실제 실행 환경 전체와 command/포트를 대조하고 기존프로젝트에서 API만 --no-deps/--no-build로 교체했다. API만 잠시 재시작했으며 DB 컨테이너ID·이미지·영속볼륨·환경은 동일하다. API환경 전체/command·appuser/보안/tmpfs/포트/로그10m×5·키source/readonly와키hash·로컬.env hash 일치를 확인했다. 원문설정은 접근제한된 gitignore backups에만 보관하고 게시하지 않는다.

추가 migration·테이블변경·자료변환/삭제·dump/restore·전체자료hash재검사·실회원 명령·미확인 재전송은 실행하지 않았다. DB는0032를 유지한다. 이전 데이터934행은 당시 베타반영 기록이며 이번에 행수불변을 새로 주장하지 않는다. 기존 worker의 정상 업무는 계속 실행된다.

## 실제 확인과 한계

- 실행 API 소스258파일hash·runtime31·기본116/133 및현재178/199 생성OpenAPI 전체일치 PASS. 최신문자 표식 확인, join intent는 아직 미추가다.
- 기존 유효세션과 실제배포소스의 읽기전용 서비스조회12개(C/N×current/ended/all×기존/멤버관리reader) PASS. 이전 조사의 임시함수대체가 없으며 기록content=null/목록에비공개번호없음도 확인했다. 이는 정상회원HTTP/기기성공과 다르다.
- 실제HTTP6 PASS: health/공개주차200의2건, 문구GET·종료목록GET 무인증/invalidBearer의401 ACCESS_INVALID·details=null·no-store/Bearer4건. 새문자95개 허용·금지샘플5는 실행코드/저장DTO 검증이며 실제 회원 문구저장/신청을 호출하지 않았다.
- API/DB healthy. 실제허용JSON로그53줄·ERROR/CRITICAL0, auth_cleanup/ownership_settlement/recruitment 성공을 확인했다. 원문로그/개인자료/키/환경값은 게시하지 않는다.

소스 직접시험7·이번서비스12·HTTP6·문자코드확인은 서로 다른 근거이며 합산하지 않는다. 정상회원 새저장/기기·성능/메모리·운영 인수는 미실행이다.

## 복구와 다음 담당

직전이미지f458e6d5(d95e3827/DB0032 지원)와 실행설정을 확보했다. 실패/실제rollback은 없었다. 복구가 필요하면 기존0032와 문자저장자료의 구버전 허용범위 호환을 읽기전용으로 확인한 경우에만 직전이미지를 재시작한다. 새기호가 저장됐거나 호환성을 확인할 수 없으면 자료를 유지하고 전진수정한다. DB0031용 이미지366e868a를 사용하거나 백업으로 새자료를 덮지 않는다.

반영기록을 같은 목적브랜치의 한 구간으로 commit/push하고 원격확인 뒤 [전체165 Backend · 문자/목록 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410058244)에서 고정기록SHA/이미지와 다음담당을 인계한다. 다음Flutter의 확인대상은 **새기호 문구저장/재조회와 종료된 모집목록 열기** 두 변경이다. 한도/조율/기존전체시험을 일괄재요청하지 않는다. join 후보조회는 [전체164 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6409485714)의 소비 합의후 별도구현이다. 원ACK대상/null분기미확정과 전체기기인수·완료해체/두주차·dev/main/AWS는 미완료·Issue13 OPEN이다.
