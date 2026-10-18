# 다음 실행

기준일2026-10-18. 기존 로컬 Docker API8000·PostgreSQL/DB0016·개발 자료와 키로 계속 개발한다. [PR14](https://github.com/heo0328/lostparty-backend/pull/14)로 현재 검증·인계 구간을 dev에 병합했고 main도 같은 위치로 맞춰 원격 확인했다. 코드 통합 merge SHA는 `a0e27995ad9d08fd46f7b593c4907f692cdd8226`이며 마감 문서를 포함한 dev/main 기준은 `77a1fe53875ddbe1a972361c90468106815c6f5b`다. 완료된 feat/raid-services는 로컬·원격에서 정리했다. [#8 전체152번째 Backend 통합결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249274152)를 기준으로 이어간다. 다음 목적 브랜치는 최신 dev 기반 `feat/group-management`다.

## 이슈 운영·현재 추적

사용자 지시로 **한 이슈 한 주제**를 적용한다. [이슈 추적표](ISSUE_TRACKER.md)가 현재 담당/완료·대기 기준이다. #10 카탈로그/주차와 #11 개인원장 구간은 완료 종료했고 #11 실제파티 후속은 #13에 이관했다. #8은 미완료 요구를 #17 생명주기/#18 활동정책/#15 V2연결/#13 실제파티로 옮겨 보관 종료했다. 기존 원문/댓글은 참고로만 보존하며 #8에 새 작업을 추가하지 않는다.

현재 열린 주제는 #12 Flutter G1/G2, #13 실제모집/파티, #15 Flutter V2, #16 Backend G3, #17 생명주기계약, #18 활동자동추가, #19 주간통계다. 그룹/모집에 통계를 묶거나 주제 이슈마다 브랜치를 만들지 않는다. 이번 문서 변경은 이슈정리 결과이며 G3/새 기능을 착수한 것이 아니다.

## 다음 Backend 작업

1. **G3 명세 준비가 우선이다.** [전용 Issue16](https://github.com/heo0328/lostparty-backend/issues/16)의 원본인 [Issue12 본문](https://github.com/heo0328/lostparty-backend/issues/12)의 그룹장 즉시 이전·일반 탈퇴 규칙을 현재 G1/G2와 대조해 명세를 작성하고 전용 #16에 게시한다. 기능 규칙은 전달됐지만 G3의 endpoint/DTO/오류/버전/동시성 계약은 아직 작성·합의되지 않았다. [전체13번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234990359)는 그룹 독립 설계를 계속할 수 있음을 확인했다. 화면 완성/Flutter 기존 기능 인수 전체를 선행 조건으로 두지 않는다.
2. 게시한 명세의 확정 구간부터 그룹장 이전·일반 탈퇴의 서버 처리/표적 검증을 진행한다. 그룹장은 수락/대기/쿨다운 없이 유효 멤버에게 이전하고 일반 멤버로 남는다. 그룹 대표는 유지한다. 그룹장 탈퇴는 이전/조건부 해산이 선행한다. 멤버 권한은 현재 회원 membership을 기준으로 하며 캐릭터 소유 상실로 본인 관계 정리를 막지 않는다. 추방/대표 변경 세부 정책·한도/회복·멱등/revision/cursor·권한 상실/replay를 명세에서 구분한다.
3. **조건부 해산은 독립시키며 활성 그룹 모집을 0건으로 가정하지 않는다.** 본인1인/pending 없음과 실제 활성 모집 원본을 같은 transaction 정책으로 검사해야 한다. 원본이 없으면 해산을 허용하지 않는 경계를 제안한다. G3를 이유로 모집 API 전체를 먼저 구현하지 않는다.
4. 다음 독립 후보는 [Issue13](https://github.com/heo0328/lostparty-backend/issues/13)의 R1/R2 기본 조회/생성·신청/그룹장 승인·즉시가입 명세와 기초다. 카탈로그/주간/회원 한도/그룹 권한을 재사용한다. 다중 동의·전체 완료 권한 충돌·불명확 일정·고급 이동은 해당 동작만 분리한다. [전용 통계19](https://github.com/heo0328/lostparty-backend/issues/19)의 원본인 [통계8번째 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232977464)은 귀속/조회 검토와 실제 방 원천이 먼저이며 원천 없는 집계를 만들지 않는다.

다음 작업 준비용 로컬 브랜치명은 통합된 최신 dev 기반 `feat/group-management`다. 아직 G3 구현/새 계약/DB 변경에는 착수하지 않았다. 관련 이슈는 #16이 주이며 #12의 기존 G1/G2와 #13 원본이 필요한 동작만 연계한다.

## 현재 마감 범위와 인계

| 영역 | Backend 기준 | 다음 담당/미확인 |
|---|---|---|
| #10 카탈로그/주차 | [개발 안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md)·공개2GET/서버KST수요일06시 | 게임 패치 자료 최신성/추가 Flutter 소비와 구분 |
| #11 개인 주간 원장 | [개발 안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md)·본인 배치GET/manual완료PUT·실제manual true 반영 보고 | 실제 room/자리·전체 완료/반복 연결은 #13 후속 |
| #12 G1/G2·한도 | [G1](../ISSUE_12_GROUP_G1_DEVELOPMENT.md)/[G2](../ISSUE_12_GROUP_G2_DEVELOPMENT.md), [전체15번째 G2 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235311908)·c06d3d2 | Backend 구현/로컬 반영/게시 완료, Flutter G1/G2 실연결은 별도. G3 미구현 |
| #8 소유권 분쟁 V2 | [개발 안내](../ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md)·7ba6297/[전체144번째 Backend](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245920315) | 최대3건·일괄방어·선성립24h worker 구현. Flutter 도전/방어/복원/앱내안내 별도후속. 실제파티영향 adapter 부재시 review_required |
| #8 첫 화면 일괄 조회 | [개발 안내](../ISSUE_8_ACCOUNT_BOOTSTRAP_DEVELOPMENT.md)·8d03e96/[전체146번째 Backend](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247620588) | 261PASS/158.21초·실행OpenAPI일치. 최대4000대상10,607,440bytes/20statements/0.902초는 격리측정 |
| DB 공통 날짜 | [기준](../DATABASE_RECORD_TIMESTAMPS.md)·업무48표 생성/최종수정 DB기록·0016 | 삭제 대상/기간 정책과 자동 삭제는 미추가. 미상 과거 NULL 유지 |

[#8 전체151번째 Flutter 마감](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248792000)은54bacd2021d60de6641bdf4fb9682368225ea341/feature/scoped-account-cache push·전체1662PASS/analyze0을 보고했다. 이전147~150의 미커밋 상태는 해소됐다. 기존8d03e96의 실회원 bootstrap1회 소비·Backend76→29요청/기본주간4661→2883ms의1회관찰과 현재개선수용은 확인됐으나 평균성능/첫paint/기기전체인수가 아니다. [전체153번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249286430)에서 dev/main deb2884d 원격동기화완료를보고했고 V2전용 feature/roster-ownership-dispute 분기/설계와 #15 이관을확인했다. V2 기능코드/시험/commit/push는아직없다는보고이며담당은Flutter D1이다. 현재 추가 Backend 변경 요청은 없고 V2 분쟁 소비는 별도다.

## 유지할 정책과 별도 후속

- 회원기본 그룹정원15/개인가입5/개인모집10은 서버 유효한도다. 정확히 한도는 기존 이용 정상/해당 증가만 차단한다. [#12 전체9번째 확정](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572): 개인모집초과는 직접참가 공개/그룹방, 개인그룹초과는 직접참가 그룹방, 그룹자체정원초과는 그그룹 모든 그룹전용방 제한. 조회·탈퇴·정리/이전 회복 경로와 기존 그룹운영은 보존하며 모든 관련 원인 해소 후 정상화한다. 실제 방 guard는 #13이다.
- 일반멤버 직접초대, 그룹장 코드관리, 공개ON 멤버조회/복사, 공개OFF는 화면숨김만/코드가입유효, 대문자+숫자6자/재생성10분/이전코드폐기는 확정이다.
- 수동 활동/대표는 현재소유/usable만 검사하고 레벨 하한 없음.1700은 최초 기본선택 기준이다. 신규/첫1700 자동추가·수동제외 영속은 #18(#8 122번째 출처) 후속 설계다. GET에서 선택을 저장하거나 과거 미선택을 일괄 활성화하지 않는다.
- 실제provider 정상목록·claim/lifecycle을 권위로 사용한다. 이름으로 개명/퇴역 ID를 이어 붙이지 않는다. #17 소멸 확정/운영자료 정리는 증거·계약 검토가 필요하며 자동퇴역/소유권 증거 보류를 임의 해제하지 않는다.
- 기존 로그인/키/최초장비인증·영문검색 성공을 다시 시작하지 않는다. 새환경/8001·Firebase이관/삭제·백업복원이관·DB초기화/운영배포는 없다. 사용자가 추가한 `compose.yaml`의 로컬 DB 접속 포트 `127.0.0.1:5432:5432`는 이슈 정리 문서와 함께 현재 작업 브랜치의 게시 범위에 포함한다.

완료/검증/장애·게시/통합 이력은 [DEV_LOG](DEV_LOG.md), 기능 지도는 [AI_CONTEXT](AI_CONTEXT.md)다. 설계·Backend완료·계약인계·Flutter적용·실기기·운영은 구분한다.
