# 활성방 한도·자동조율 안내 개발 서버 반영

2026-10-26 / 작업 구간 **활성방 한도·조율 안내 개발 반영·실행 확인·인계** / `feat/raid-recruitment`.

[전체171 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6412692643)을 구현한 소스 `1800160dcb883a13b76bd8602bbdf5fcb8eb2986`를 push·원격 확인 후 개발 API에 반영했다. 이미지 `sha256:0a540425e334ce628eff4d1c013111374338bdfc4d05461d43af0dfa47f0ae69`, DB0032·현재178경로/199operation·기본116/133·wire2/profile1이다. [실행 집계](records/active-usage-wait-rollout.json)·[구현/직접검증](../../features/recruitment/weekly-cycles/active-usage-and-wait-implementation.md)을 따른다.

## 변경과 보존

현재 C/N의 실제 활성방 공통 SQL을 두 목록의 페이지 전 필터·한도·명령에 공유한다. 같은 방은1개·유효한 review_required 포함·과거/관계전용 제외다. 기존 지속관계 재참가도 실제 신규단위를 검사하며 영향회원 revision/동시 마지막자리/실패롤백/원ACK를 보존한다. `/v1/me/usage-limits`의0032 readiness 연계결함도 보완했다.

기존 베타 상세·plan GET에만 include_coordination_wait=true|false를 추가했다. true만 beta_schedule.coordination_wait를 제공하고 생략/false·기존reader/권한/null기록/쓰기ACK는 유지한다. waiting_members만 양수1~8, 다른 네 상태는null이다. 같은 조회 스냅샷의 자동조율 평가를 재사용하며 근거누락/명시unset/정상후보없음/DB오류를 구분한다. GET은 확정·저장하지 않는다. 수용된join후보·문자정책은 유지한다.

후보와실행259소스hash·runtime31·두OpenAPI전체일치, 기존쓰기operation동일을확인했다. 같은소스의직접고유18PASS(한도7/조율6/관련기존5)를재사용하고 전체회귀/복원리허설을반복하지않았다. 닫힌DTO/다섯추가대표예시를포함한123fixture·제안48/문자32·원ACK32·문서/diff도통과했다.

API만 교체했다. DB컨테이너ID/이미지/볼륨/환경·DB0032와 API환경/명령/포트/보안/tmpfs/로그·키mount source/readonly/내용hash/.envhash를 보존했다. 비공개 원문설정과직전이미지는접근제한영역에만보관한다. migration/자료변환/삭제·dump/restore·실회원시험명령·원pending재실행은없다.

## 실제 실행 확인과 한계

- 기존 유효세션의 READONLY 서비스 조회로 한도10/사용3, 현재 C2/N2와두목록합집합3의일치를확인했다. 과거7관계를삭제하거나강제종료하지않았다.
- 실제 배포소스의 상세/plan8조회조합에서 생략/false의필드부재와 true의안내를확인했다. 번호4는waiting_members/1, 번호5는no_earlier_candidate/null, 번호3/6은not_applicable/null이었다. 번호3은후보대조시와시간/상태가변했으며고정기대값으로강제하지않았다.
- 실제 HTTP6PASS: health/공개주차2, 기존문구/join후보 무인증·invalidBearer401 ACCESS_INVALID/details=null/no-store/Bearer4. API/DBhealthy·auth_cleanup/ownership_settlement/recruitment성공·확인한허용JSON로그32줄/ERROR0이다. 문자정책95/금지5는실행코드검증이다.

직접18·실자료서비스·HTTP·정적예시는 서로 다른 근거라 합산하지 않는다. 정상회원 인증 HTTP의 신규조율query·가입명령성공/기기·성능인수는미확인이다. 실자료서비스조회는기존세션을재사용했고JWT를만들거나회원자료를수정하지않았다.

## 복구와 다음 담당

직전690f36f/이미지061dc562와설정을확보했다. 새정책처리요청이없고DB0032호환이확인될때만직전이미지복구가가능하다. 교체시각이후완료모집명령이있거나자료호환이불명확하면이전집계로단순복귀하지않고자료를유지한전진수정이다. 실제rollback은없으며DB복원/초기화/키교체를하지않는다.

이번 Backend 완료 범위는 두기능 구현·직접검증·push·개발API반영·실행확인·인계다. 다음Flutter는 현재활성방한도와기존일정카드한줄안내의직접영향만연결/확인하고구체차이를회신한다. 원ACK동일키매칭·전체기기/성능·dev/main병합·AWS배포는별도미완료이며Issue13OPEN을유지한다.

[전체172번째 Backend · 한도·조율 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6414001866)에실행소스·이미지·검증경계·다음담당을인계한다. 반영기록구간을push/원격확인후고정링크와네이티브직접영향확인범위를같은댓글에보완한다.
