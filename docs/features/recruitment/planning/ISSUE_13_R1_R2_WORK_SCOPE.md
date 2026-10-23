# 모집 R1/R2 작업 구간

2026-10-19 / Backend / 구간 설정·구현 전 / [Issue13](https://github.com/heo0328/lostparty-backend/issues/13).

현재 작업 위치 정정: 모집 작업은 `feat/raid-recruitment`로 분리했다. G3 기준349fb79를 상속하되 기존 `feat/group-management`는 보존하며, 아래 준비 당시 브랜치 기록은 이력이다. 당시 미커밋 코드·문서를 그대로 이동했다. 이후 사용자 요청으로 F1 구현은9664fb4, 설계·진행 기록은 후행 문서 커밋으로 구분했으며 push/merge는 없다.

## 확인한 회신과 기준

| 출처·실제 전체 댓글 순서 | 작성 측·단계 | 반영 |
|---|---|---|
| [#13 전체10번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259125080) | Flutter·이관/후속범위 확인 | R1/R2 독립 진행에 추가 승인 요구 없음. membership/i·주간claim·종료이력 분리, 실제파티 adapter 전 review_required 유지 |
| [#13 전체1번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232280402) 및 전체2번째 Backend 수용 | Flutter·i 정책 정정 | i는 현재 방 관계. 과거 완료 source로 추정하지 않음. 완료 후 잔류/다음주 관계와 주간점유를 구분 |
| [#13 전체6번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232799560) | Flutter·한도 최종 정정 | 개인모집초과=직접참가 공개/그룹방, 개인그룹초과=직접참가 그룹방, 그룹정원초과=해당 그룹 모든 그룹방. 전체4번째의 광범위 상속안 미채택 |
| [#16 전체5번째](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6259125692) | Flutter·G3 계약 검토 | 332a8ab의 관리GET/최소ACK에 문서상 차단 충돌 없음. 연결/실기기 완료·merge승인은 아님 |
| [#12 전체17번째](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6259124455) | Flutter·G1/G2 인계 접수 | 기존 계약 재사용, 그룹 연결은 별도. 초기조회 추가/기초 재시험 요청 없음 |
| [#15 전체3번째](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6259074435) | Flutter D2·내부 연결 결과 | 174 고유 테스트/분석0 보고·미커밋/미push, 기존 UI는 V1. 다음 D3·추가Backend요청없음 |
| [#17 전체1번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6259126286) | Flutter·생명주기 검토범위 확인 | 소멸 근거/한계부터 검토, 옛UUID/자리/snapshot 보존. 삭제/보류해제 승인 아님 |
| [#18 전체1번째](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6259126990) | Flutter·활동정책 접수 | 최소 영속정책/DTO·동시성 초안이 다음. 기존자료 일괄활성화 금지 |
| [#19 전체1번째](https://github.com/heo0328/lostparty-backend/issues/19#issuecomment-6259127594) | Flutter·통계 제안 검토 | type 최초고정/함께집계·해산OFF/평균분모/그룹조회권한은 미확정. 실제 R1/R2 원천 보존을 막지 않음 |

위 번호는 본문 제외 실제 댓글 작성순서이며 Backend 작업 단계 번호가 아니다. Flutter 결과는 Issue 보고 기준으로 읽었으며 로컬 Flutter 소스는 접근하지 않았다.

후행 상태: [상세 계약 초안](../contracts/ISSUE_13_R1_R2_CONTRACT_DRAFT.md)을 [#13 전체12번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924)에 게시했다. 아래는 구간 설정 당시의 계획이며 최신 다음 실행은 NEXT_WORK의 F1 내부기반을 따른다.

## 바로 진행할 구간 — R1/R2 계약 설계

이번 단계는 상세 계약을 설계·게시하는 구간이다. API/DDL/구현 착수 또는 원격 게시 완료로 간주하지 않는다. 현 `feat/group-management`/HEAD349fb79에서 문서를 준비하며 G3 변경을 보존한다. 구간 설정을 이유로 branch 전환·merge·push를 하지 않는다.

1. **R1 방 원본·조회·생성**: 모집/회차/현재 회원 참가관계·슬롯·선택 캐릭터의 UUID와 revision, 카탈로그/난이도/주차 참조, 공개/그룹전용 권한, 목록·상세·내 신청/참가/종료이력의 조회 범위와 필터/cursor. 생성자 즉시참가와 주간 점유를 함께 설계한다. 실제 생성/종료되지 않은 상태에서 종료이력을 가짜로 만들지 않는다.
2. **R2 기본 참가 흐름**: 기본 승인형(현재 파티장 승인)·즉시가입의 지원표, 신청·승인·거절·본인철회, 확정 순간 슬롯/역할/직업·현재 소유/활동/usable·난이도 입장레벨/전투력·일정·주간 점유/완료·한도를 재검사한다. 그룹장 지위만으로 파티장 권한을 부여하지 않는다.
3. **직접 필요한 기존 계약 연결**: 개인 방수 실제집계와 사용량head, 그룹정원/현재membership guard, 동일회원 한방1자리·겹치는 일정·캐릭터/raid/cycle 난이도교차 차단, 최대8인/당별구성. 현재 방membership과 주간점유·완료근거의 단일 권위/원자성 경계를 명세한다. 현재 `/v1/me/usage-limits`의 모집 사용량 null을 실제 원본 없이0으로 바꾸지 않는다.
4. **최소 회복·생명주기 경계**: 모집을 생성·가입할 수 있게 할 때 본인 관계 정리가 막히지 않도록 기본 탈퇴·책임자이전·마지막1인 종료와 권한회복에 필요한 최소 동작의 계약/단계순서를 함께 정의한다. 이를 R3 전체나 추방·고급이동의 일괄 구현으로 확대하지 않는다. 그룹 탈퇴 시 실제방 접근/잔류/정리, 캐릭터 자격 상실의 기존자리 보존/새대상 검사, 주차경계 이후 stale 명령 거절을 정리한다. 회복 경계가 미정인 쓰기를 먼저 공개하지 않는다.

## 이번 단계 완료 조건

- 경로/DTO·요청/응답 예시·required/nullable·enum/시간/수치정밀도, UUID/참가 참조와 revision·권한별 공개범위·지원 동작표를 문서로 제시한다. 아직 실행 OpenAPI에는 미확정 경로를 추가하지 않는다.
- 생성/참가 확정 transaction, 역할/슬롯·주간점유·사용량head·멱등ACK의 전부성공/rollback, 기존 쓰기락/동시성·replay/응답유실·cursor stale를 설계한다. pending은 예약이 아니며 다른 pending의 지연종료가 두번째 확정을 허용하지 않는다.
- 15/5/10 원인별 영향/정확한도와 초과·제한중 회복표를 재사용한다. 공개 조회에서 타인전역UUID·그룹비공개명단/개인설정·키/외부상세 원문을 노출하지 않는다.
- 일정의 종료불명/중복판정, 역할/최소빌드 판단 근거, 그룹탈퇴와 실제방의 관계/정리, 주차전환 시 점유/기존membership 처리처럼 구현에 직접 필요한 정책만 좁혀 명시한다. 미정 의미를 자동 허용/기본시간으로 채우지 않는다.
- 기존 계정/그룹/카탈로그/개인주간 API와의 호환성 및 필요한 migration/원천을 제시하고, 격리 PostgreSQL·HTTP의 권한/경쟁/경계·rollback 표적 검증 계획을 붙인다.
- #13에 상세 계약과 미확정/다음담당을 게시한 뒤 독립 구현 가능한 단위를 확정한다. 구현→격리검증→기존API/실행계약검증→커밋/push·원격확인→인계의 후속순서를 유지한다. 이번 구간 설정만으로 Flutter 테스트를 요청하지 않는다.

## 후속·제외

- R3의 자리이동/캐릭터교체·추방 등 확장 관리, R4 전체완료/반복/공개전환은 별도 구간이다. 실제 방 원천은 후속을 연결할 수 있게 설계하되 모든 후속을 동시에 구현하지 않는다. 독립 범위가 커지면 착수 전에 별도 주제/완료조건으로 분리하고 #13에 링크한다.
- 전체완료 권한 충돌, 다중동의/quorum, 종료시각불명 일정의 명시확인·고급 스왑은 해당 동작만 보류한다. 미지원 동작을 정상허용 permissions로 노출하지 않는다.
- #16 조건부해산은 실제 활성 그룹방 검사와 동일 transaction 정책이 갖춰진 뒤. 원본 부재를0건으로 해석하지 않는다. G3해산을 위해 모집 기능 전체를 한 구간에 강제하지 않는다.
- V2의 실제파티 영향 adapter는 후속 연결/검증 전 `PARTY_IMPACT_REVIEW_REQUIRED`를 유지한다. 방 원본 도입만으로 기존 보류를 즉시 해제하지 않는다.
- #19에는 원천의 UUID/발생시각/가입·참가 유효구간/생성당시 공개범위·그룹과 도메인 revision을 남길 경계를 연결한다. 집계·마감worker·통계HTTP나 미확정4정책의 구현은 제외한다. 개인manual을 방 결과로 만들지 않는다.
- #17 증거/생명주기 검토와 #18 영속활동정책 초안은 독립 후순위다. 기존 L1/V2/수동선택을 재개발하지 않는다.
- Flutter #15 D3→D4 우선작업, #12/#16 그룹/모집 화면연결·실기기는 별도. 운영배포·DB/키/기기자료 삭제/초기화·환경이관·병합은 포함하지 않는다.
