# 검색 정수분 범위 개발 서버 반영

2026-10-27 / 작업 구간 **검색 정수분 개발 반영·실행 확인·정책 검토 인계** / `feat/raid-recruitment`.

[전체177 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6421096990)과사용자승인계획에따라 source `a358a1a13ea0b0852612eef4b7c8d8b5bf008a23`를push/원격확인후API에반영했다. 이미지 `sha256:1307ac36cf630ea0200a1270e2857cb3d64d68b36ca817febdd81352ca8e0df7`, DB0032·현재178/199·기본116/133·wire2/profile1이다. [공개실행집계](records/search-minute-rollout.json)·[구현/직접검증/생성정책검토](../../features/recruitment/weekly-cycles/search-minute-precision.md)를따른다.

## 반영과 보존

베타검색GET/POST의departure_windows만UTC정수분을허용한다. 초/마이크로초0·양의구간/최대24시간·선택주차내부·시작포함/끝제외·정확범위/페이지전필터·커서를유지하고반올림하지않는다. 생성/개방·직접제안·예약·공용5분/자동탐색·개인표·진행시간은변경하지않았다. 생성정수분추천은검토/후속소비협의이며미구현이다.

후보와실행259소스hash/runtime31/두OpenAPI전체일치,기존경로operation객체/쓰기ACK동일·DepartureWindow설명/search_time정책추가만확인했다. 같은런타임소스의고유직접6PASS를재사용·전체회귀/복원리허설미반복,완결125예시/원ACK32/음성3·문서/diff통과다.

API만교체했다. 기존DB컨테이너ID/이미지/볼륨/환경·DB0032와API환경/command/포트/보안/tmpfs/로그·키mount source/readonly/키내용hash/.envhash를유지했다. 비공개원문설정과직전이미지는접근제한영역에만보관했다. migration/자료변환/삭제·dump/restore·실회원시험명령/원pending재실행없음이다.

## 실제 실행 확인과 한계

- 실제현재공개방을실행소스+READONLY DB의공개검색서비스로조회해비5분범위포함/끝시각정확제외를확인했다. 서비스호출이며정상회원HTTP/기기성공이아니다. 대표대상번호16의결과1건·페이지1,회원식별/토큰생성/자료수정없음이다.
- 실제HTTP9PASS: health/공개주차2,기존문구/join후보무인증·invalidBearer401 ACCESS_INVALID/details=null/no-store/Bearer4,새검색GET/POST200동일결과/no-store·초입력400의3건. 실제GET/POST검색은18:03~20:17범위UTC변환값을사용했다. 부하/정상회원쓰기시험은미실행이다.
- API/DBhealthy·auth_cleanup/ownership_settlement/recruitment성공·허용JSON로그37줄/ERROR0확인. 기존문자95/금지5는실행코드검증이지새저장시험이아니다. 직접6·실제서비스·HTTP·작성예시를합산하지않는다.

## 복구·다음 담당

직전1800160/이미지0a540425와설정을보존했고실제rollback은없다. 검색만변경/모든쓰기와DB동일을확인했으며장애시현재0032호환을확인해직전이미지로복구할수있다. 자동복구는더보수적으로교체시각이후완료모집명령이없음까지확인한다. 상태/호환이불명확하면자료를유지한전진수정이며DB복원/키교체를하지않는다.

반영기록구간을같은목적브랜치에묶어commit/push·원격확인후Issue13같은결과댓글에고정SHA/문서를보완한다. Native에는비5분검색의직접영향만확인요청하고생성/직접지정은추천검토에대해소비의견을회신받는다. 전체174~176기기통과보고는기존수신범위로보존하며전체반복시험은요청하지않는다. 원ACK동일키매칭·전체기기/성능·dev/main/AWS는별도이며Issue13OPEN유지다.

[전체178번째 Backend · 검색 정수분 개발 반영/생성 정책 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6421669821)에결과를회신했고실제전체순번/전문을확인했다. 반영기록push/원격확인후같은댓글에고정문서/SHA와검색직접영향확인을보완한다.
