# 즉시가입 후보조회 개발 서버 반영

2026-10-26 / 작업 구간 **join 후보 개발 반영·실행 확인·인계** / `feat/raid-recruitment`.

사용자승인계획과 [전체167 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410375489)에따라구현소스 `690f36f15880f7766526288ec515183b2b4d077a`를push/원격확인후개발API에반영했다. API이미지 `sha256:061dc5620d53b80d7f01f65b39d8ac75a667a3d96b1d5962d0646d6fe50b7e5d`, DB0032·178경로/199operation·wire2/profile1이다. [공개 실행 집계](records/join-candidates-rollout.json)·[전체170 Backend · join 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6411011928)를따른다.

## 범위·보존

기존admission-character-candidates의join intent만지원한다. direct_join/actor=null·공통자격/페이지·기존context/POST·원ACK를유지하며DBmigration/자료변환/삭제·새저장필드·회원명령/원pending재실행은없다. 한도/조율대기안내는 [전체169 소비제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410756326)·[제안원문](../../features/recruitment/weekly-cycles/active-room-and-wait-proposal.md)으로아직소비확인대기다. **실제서버한도는아직기존집계이고 10→활성3방은READONLY기대값**이며조율선택필드도실행계약에없다.

후보와실행258개소스hash·runtime31·두실행OpenAPI전체일치. 기본116/133불변·현재178/199유지, 기존AdmissionCandidateData의intent enum외원정의611불변과기존쓰기operation전체동일을확인했다. 이미통과한직접시험6개는동일소스결과재사용·전체pytest반복없음이다. 세부검증은 [join 구현기록](../../features/recruitment/participation/join-candidates-implementation.md)을따른다.

API만교체했다. 기존DB컨테이너ID/이미지/영속볼륨/환경·DB0032와API환경전체/command/포트/보안/tmpfs/로그·키mount source/readonly/키hash/.envhash동일을확인했다. 실제원문설정은비공개접근제한영역에보존하고게시하지않는다. dump/restore·과거자료정리·실회원쓰기없음이다.

## 실행 확인·미확인

- 실제배포소스/기존유효세션의READONLY서비스조회에서번호5 join intent/actor=null, 전체후보9·허용6·제보1704제외를확인했다. 제외는레벨1/완료1/기존참가1이었다. 대표예시는작성합성자료이며실자료원문은게시하지않는다.
- 기존목록C/N×current/ended/all×두reader12조회PASS·기록content=null/목록비공개번호부재. 함수대체없음. 후보1+목록12는서비스호출이며정상회원HTTP·가입명령성공으로표시하지않는다.
- 실제HTTP6PASS: health/공개주차2, 문구/join 후보 무인증·invalidBearer401 ACCESS_INVALID/details=null/no-store/Bearer4. API/DBhealthy·3종worker성공·허용JSON로그45줄/ERROR0확인. 이전문자95/금지5검사는실행코드검증이지회원저장이아니다.

직접시험6·서비스13·HTTP6·작성23/거절16·wire118은중첩/서로다른근거라합산하지않는다. 정상회원join HTTP/기기·성능/메모리인수는미실행이다. 기기에서일반join시트전용후보/페이지·역할/선택뒤최신확인을연결하고구체차이만회신한다.

## 복구·후속

직전0fd43f9/이미지5f7c5b63와실행설정을확보했다. 후보비교에서저장구조/쓰기operation/문자정책동일을확인했고실제rollback은없다. 문제시직전0032지원이미지의현재자료호환성을확인하고복구한다. 미확정호환/자료변경발생시전진수정하며과거DB를덮지않는다. 이전0031용이미지366e868a는사용하지않는다.

반영기록을같은목적브랜치에묶어commit/push·원격확인후 [전체170 Backend · join 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6411011928)에정확SHA/고정링크·일반join시트연결을인계한다. 다음Flutter는join연결과전체169한도상태표/선택조율DTO 소비확인, Backend는합의후나머지구현·직접검증·개발반영을이어간다. 현재구간마감이전체승인계획완료는아니다. 과거관계/원ACK키매칭·전체기기인수·dev/main/AWS는별도미완료·Issue13OPEN이다.
