# 주차별 그룹 정책 개발환경 반영

2026-10-30 / feat/raid-group-policy. 사용자 반영 승인에 따라 기존 개발 서버의 같은 DB를0034→0035로 전진 이행했다. 구현/계약b212ad0과 실제 조회 보완 **b8542ef739593ffaad6da618215ff4f38fd87929**, 실행 이미지 **930c25f8**·DB **0035_cycle_group_policy**다. [공개 실행 집계](records/cycle-group-policy-rollout.json)·[변경 계약](../../features/groups/cycle-group-policy.md)·[DEV_LOG](../../project/DEV_LOG.md#cycle-group-policy-rollout)를 따른다.

기존 API/lifespan worker를 중지하고114업무표2,038행의 hash·열정의/시각·sequence·키 기준을 READ ONLY로 기록했다.0035 migration은1회만 실행했으며 기존 자료/sequence/키는 불변이다. 현재 explicit 세대36건을 정책표에 초기 반영했고 public/null 정규화·revision 불일치0, 과거 origin/참가/완료/명령 이력의 backfill은 없다. 기존 DB 컨테이너·이미지·볼륨·환경과 API의 환경·명령/사용자·보안/포트·로그·키mount·프로젝트 .env를 보존했다. 원문/키hash/행hash는 ignored backups의 제한 폴더에만 보관했다.

실제 조회에서 완료 주차의 null공대장 설정편집 권한 계산 오류를 발견해 API를 다시 중지했다. 해당 경계를 합성 DB로 재현하고 open/방활성·공대장 근거 검사를 보완했다. 신규/정상권한/profile 회귀3PASS 후 보완 소스로 교체했으며 실제 모든profile 조회가 통과했다. 이 과정에서 DB migration을 반복하거나 실자료를 바꾸지 않았다. 감사 도구 초기화·비교기준 재로딩·HTTP 경로의 기존 인증 기대값도 바로잡았으며 제품 오류와 도구 오류를 구분했다.

실제 이미지274파일/runtime31·두전체계약(기본123/140·two-cycle185/206) 일치, API/DB healthy, auth_cleanup/ownership_settlement/recruitment 성공·관찰 로그ERROR0/failed_items0을 확인했다. F01 코드도 이미지에 포함되며 반영 전 미처리 마스킹 대상0건, 수동 cleanup은 실행하지 않았다. 상세 실행값은 집계를 따른다.

실서비스 READ ONLY 검증은 기존 유효 세션2계정의 C/N 검색·목록·신청, 기본/application-display/membership-actions 상세 각13건·설정13건·일반전환 검토8건·그룹활성T3건이다. 일반전환 검토의 종료/공대장 권한 거절5건은 예상 결과다. 외부provider0, SQL은 SET/SELECT만 허용했다. 실제 loopback HTTP11PASS는 health/공개주차·검색metadata200, 보호된주차/설정/검토의 무인증·잘못된Bearer401/no-store/Bearer, 잘못된버전400을 구분한다. 인증된 실회원 쓰기/토큰발급·실제승계/원ACK대조·기기 인수로 확대하지 않는다.

다음은 Flutter의 새 계약 연결/시험·분석과 사용자 변경 경계 기기 확인이다. 기존 앱 쓰기는 새표시/검토 계약이 없으면 구 성공ACK 복구 외 CLIENT_UPGRADE_REQUIRED가 정상이다. DB0035 이후 구0034 API 단독롤백은 하지 않으며 문제 시 정책 원본 보존·전진 보완한다. dev/main 병합·AWS/release·자료초기화·복원리허설·부하·Issue종료는 수행하지 않았다.
