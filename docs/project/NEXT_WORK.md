# 다음 실행

문서 운영 #29는 공통 원본·양측 참조 반영 및 [상호 대조](https://github.com/heo0328/lostparty-backend/issues/29#issuecomment-6520322169) 완료로 추가 수정 대기를 해소했다. Issue 종료는 별도이며 상세 근거는 [DEV_LOG](DEV_LOG.md)에 보존한다. 기존 그룹 기기 인수와 기술 진단 후속은 별도다.

## 현재 상태 — 최초 그룹 연결·목록 표시 개발반영·실행검증 완료

checkout `feat/group-management`, main/dev `1b6f57b` 유지. #16 전체22 사용자승인계획과 #12 전체35/36 요청을같은브랜치에서구현·격리검증·고정계약인계한다. 사용자서버반영지시로**source2602e45/이미지5bd8dde6·DB0034 유지**로개발API를교체했다. migration·병합·운영배포·자료변경실행은없다. [계약/경계](../features/groups/raid-link-contract.md)·[합성표시예시](../features/groups/raid-link-examples.json)를따른다.

- 기존 common-context의 target_group_id로검토하고기존 common-settings 한명령에서 null→현재내그룹+scope=group을원자처리한다. G1/C/N·토큰/CAS/한도·rollback/원ACK·기존참가/신청/예약/완료원장을보존한다. A→B/해제는거절하고같은A public↔group은유지한다.
- 목록4경로의include_group_state=true는root.group_states와현재페이지room_groups를일괄제공한다. 내신청origin/과거content를현재그룹으로덮지않고기본DTO/기존cursor는유지한다. 이름/연결변경은opt-in cursor stale로회복한다.
- 상세배지는기본/application-display-1의data.members, membership-actions-1의data.content.data.members를사용한다. 그룹원/비그룹원조회자·옵션조합12개에서같은참가자bool을확인했고Backend누락은재현되지않았다. null/content없음을false로합성하지않는다. Flutter는실제진입/표시조건을이예시와대조한다.
- 검증: 신규/기존그룹레이드·공통관리47PASS, 최종추가경계4PASS·토큰1PASS(반복합산없음·선택49시나리오). 두전체OpenAPI일치/기본객체불변·기존schema값변경0·5경로/새11schema. [실행집계](../features/groups/raid-link-verification-2026-10-30.json).
- 다음Flutter는고정DTO/context소비를연결하고실제진입/배지조건의구체차이를회신한다. Backend는차이에대응한다. 실제개발반영은완료했고Flutter신규계약연결/변경경계기기인수는미완료다.

구현/고정계약 source `6dac5ab2cc67e197979e7188a9c97ce2c27fb548`를commit/push·원격일치확인후 [#12 전체38번째 Backend · 목록/소속표시 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503052363)·[#16 전체24번째 Backend · 최초연결 명령 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503052848)를게시했다. 실제전체순번/작성측/단계확인·당시 양본문상단에 개발미반영/다음담당을 갱신했다. 이후 서버반영 완료로 현재 상태를 갱신하며 OPEN을 유지한다.

## 유지할 기존 완료·실제 실행 기준

- [#12 전체36 Flutter 사용자기기인수](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6502226347)·[#16 전체21](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502226876)의안내된기존그룹잔여시험전체통과를수용한다. 생성/조회·신청/승인/취소·대소문자/역할별표시/정렬·활동·차단/코드·이전/탈퇴/조건부해산·필터/기존참가보존·카드배치의보고범위다. 새최초연결/목록그룹명/소속표시결함해결인수로확대하지않고반복정상시험을요청하지않는다.
- [#16 전체22 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502336731)의9d1baa39는생성그룹선택/해제기본값과기존API1회연결·29PASS자체보고다. Backend시험/기기인수와합산하지않고Flutter로컬소스는읽지않는다.
- 실제개발반영기록은source2602e45/이미지5bd8dde6·DB0034(기본123/140·two-cycle185/206)이며 [실행집계](../engineering/operations/records/raid-group-link-rollout.json)를따른다. 기존114업무표2,015행/sequence·설정/키·DB볼륨보존, 274소스/runtime31/두전체계약·HTTP12/READONLY목록·프로필·worker/healthy확인. 실제context샘플은G1/방상태거절로최초연결성공write미확인이고신규UI/기기에서확인한다.
- G-RECOVERY·활동자동추가미정/로컬89a3248보존·main/dev병합/운영배포·자료삭제없음. 그룹원동등개설·실제T공대장관리/그룹장전용레이드명령없음을유지한다.

반영 기록 `ad095c30e32e41d9ac90a4a34e50ba87dc062a9c` commit/push·원격 일치 후 [#12 전체39번째 Backend · 표시 기능 서버 반영](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503318325)·[#16 전체25번째 Backend · 최초 연결 서버 반영](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503318794)를 게시하고 실제 전체 순번·작성 측·단계를 확인했다. 양 Issue 본문 상단은 개발반영 완료/Flutter 신규 계약 연결·새 경계 기기 인수 대기로 갱신했으며 OPEN을 유지한다. 실제 실행은 source2602e45/이미지5bd8dde6·DB0034이며 후행 기록 커밋은 실행 소스를 바꾸지 않는다.

## 다른 미완료 주제

모집1차인수/Issue13종료는유지하고차후정밀도/알럿/UX/소켓은 [보완대장](../features/recruitment/follow-up-backlog.md)을따른다. 다른Issue상태는 [추적표](ISSUE_TRACKER.md), 완료/결정/검증·장애는 [DEV_LOG](DEV_LOG.md)에보존한다. IF-001/002/003 비활성·원자료/pending/ACK·별도성능/실회원원ACK 검증경계는유지한다.
