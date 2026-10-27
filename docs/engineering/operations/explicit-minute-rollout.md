# 베타 명시 출발 정수분 개발 반영

2026-10-27 / 작업 구간 **명시 출발 정수분 개발 반영·실행 확인·인계** / `feat/raid-recruitment`.

[전체179 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6422070028)과사용자승인계획의구현소스 `420e0570feb0c7f4be82dca8ee132e30000540f0`를push·원격확인후API에반영했다. 이미지 `sha256:cd581ac04aa8bb5d429af25bf5553d26bd117d4f382244216416eddc024bfa39`, DB0032·현재178/199·기본116/133·wire2/profile1이다. [구현/직접검증](../../features/recruitment/weekly-cycles/explicit-minute-departures.md)·[공개실행집계](records/explicit-minute-rollout.json)를따른다.

## 변경·보존

베타생성/CN개방·실제베타세션직접제안/수락/재평가/needs_review복구만UTC정수분을사용한다. 기본5분검사·자동후보/개인표/진행시간/구대안·정확30분/주차/점검·동의/예약/원ACK는유지한다. 생성/개방의같은config/install과명시옵션을사용해원분이설치/조회/예약까지보존되며프로필만으로구일정을완화하지않는다. 18:03기한은17:33,자동후보는기존5분격자다.

후보/실행259소스hash/runtime31/두OpenAPI전체일치·기존모든경로operation/본문/ACK동일·BetaScheduleConfig설명/explicit_departure정책추가만확인했다. 고유17직접시험(신규11/검색4/기존2)은같은업무소스결과재사용·전체회귀/복원리허설미반복이며130완결예시/원ACK32/음성3·문서/diff통과다.

API만교체했다. 기존DB컨테이너ID/이미지/볼륨/환경·DB0032와API환경/command/포트/보안/tmpfs/로그·키mount source/readonly/키내용hash/.envhash가같다. 비공개설정원문은접근제한영역에만보존한다. migration/자료변환/삭제·dump/restore·실회원시험명령/원pending재실행없음이다.

## 실행 확인·한계

- 배포소스의순수validator를합성시각으로실행해정수분config·18:03→17:33·정확마감·기본5분거절/자동TICK5분을확인했다. 이검사는DB/회원명령을실행하지않으며정상회원생성/제안/수락HTTP성공은아니다.
- 실자료READONLY공개검색서비스에서현재공개방번호16의비5분범위포함/정확끝제외를확인했다. 결과1건/페이지1·회원식별/토큰생성없음이며생성context/POST성공으로확대하지않는다.
- 실제HTTP9PASS: health/공개주차2,기존문구/join후보무인증·invalidBearer401 ACCESS_INVALID/details=null/no-store/Bearer4,비5분검색GET/POST200동일결과/no-store·초400의3건. 기존문자95/금지5는실행코드검사다.
- API/DBhealthy·auth_cleanup/ownership_settlement/recruitment성공·허용JSON로그34줄/ERROR0. 합성17/순수검사/서비스/HTTP/작성예시를합산하지않는다. 정상회원쓰기/기기/부하·성능인수는미확인이다.

## 복구·다음 담당

직전a358a1a/이미지1307ac36와설정을보존했고실제rollback은없다. 복구전교체시각이후완료모집명령과분단위기본시각·pending제안이없는지읽기전용으로확인한다. 새분자료/처리명령이있거나호환확인이불명확하면이전5분코드로단순복귀하지않고자료를유지한전진수정이다. DB복원/키교체는하지않는다.

반영기록을같은모집브랜치에묶어commit/push·원격확인후Issue13결과댓글에고정문서/SHA를보완한다. 다음Flutter는분단위생성/개방·직접제안/수락의직접영향만확인·구체차이회신,Backend는차이대응이다. 전체기기/성능·원ACK동일키매칭·dev/main/AWS는별도이며Issue13OPEN유지다.

[전체180번째 Backend · 명시 출발 정수분 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6422693611)게시/실제전체순번·본문확인. 반영기록push·원격확인후같은댓글에고정문서/기록SHA와Native직접영향확인을보완한다.
