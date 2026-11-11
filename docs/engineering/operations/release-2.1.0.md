# Backend 2.1.0 공동 릴리즈

2026-11-11 / Issue49 / 사용자 승인 6단계 실행 원본. 현재 상태는 [NEXT_WORK](../../project/NEXT_WORK.md), 실행별 근거는 [DEV_LOG](../../project/DEV_LOG.md)에 기록한다.

## 기준과 책임

- 운영 v2.0.0/source51b1cb3/imagef33f4c6c/DB0035, 후보는 DB0036·기본125/142·two-cycle192/213. Backend 버전2.1.0/full 검증, 과거 reuse 예외는 재사용하지 않는다.
- [합의/실물 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6793794562)와 [독립 수령](records/web-handoff-2.1.0.json)을 기준으로 Native는 웹 build/manifest·APK·서명/기기 인수, Backend는 산출물 검증/서버배치·API/DB·백업/동결구성을 담당한다. 최종 공개는 함께 진행한다.
- 웹 원3파일은 ignored backups/web-handoff/artifact-13849320316에 보존했다. 수령 검증/로컬비활성만 완료, AWS전송/활성화·실브라우저/운영기기 인수는 미완료다. 재빌드/재압축/다른artifact 묵시대체 금지.
- 서비스키4개·관리자/제한배포SSH는 재사용한다. 새Android client 1개를 기존azp2개에 추가하되 Web audience·서명/nonce 검증을 유지한다. Native 백업을 Backend의 새 선행작업으로 만들지 않는다.

## 단계와 완료 조건

| 단계 | 작업·완료 조건 |
|---|---|
| 1 현재변경 정리 | CORS·W3/W4·백업 근거와 이 설계를 기록하고 CORS/두계약/문서/JSON/diff 확인. 미완료를 구분 |
| 2 첫 통합 | 최신원격확인→현재변경커밋→dev 이력보존병합→main 동일SHA→두원격push/일치→release/2.1.0 생성. 태그/운영변경 없음 |
| 3 로컬 준비 | 웹수령/안전검증/inactive/활성화·Caddy·동결구성·maintenance 전환·OAuth변경안·복귀를 구현/격리검증 |
| 4 후보 고정 | VERSION2.1.0/full 계획·Backend소스/image/계약/DB/설정·웹/APK 식별 고정→회귀/전체계약/도구검증→dev/main 재통합/push→CI·불변이미지 확보 |
| 5 운영 적용 | 최신DB/환경·키/동결구성·복구도구를 기존PC폴더 새날짜 사본으로 보관/무결성확인→잠금/점검/쓰기중지→0036 migration→환경/Backend/웹구성→정상확인 |
| 6 공동 공개 | 점검접근으로 Backend/Native 담당별 인수→조정된 점검해제/Native Release 공개→Issue 결과/미확인/실제공개 기록. 종료는 별도판단 |

## 배포 구현 계약

일반 릴리즈의 기존 자동 검증/이미지게시/API교체 경로를 유지한다. 이번 릴리즈는 명시적인 maintenance 계획으로 자동 API교체를 보류하고 불변이미지 확보 후 관리자가 승인된 전환도구를 실행한다. 제한SSH의 DB/인프라 보호나 shell 제한을 완화하지 않는다. DB revision/설정이 다른 상태에서 일반배포를 강행하지 않는다.

웹수령은 고정 run/artifact ID/name/만료/fullsource/ZIP SHA256과 root3파일·내외manifest바이트·filehash·POSIX안전경로/중복/링크거절을 검증한다. 검증된 site만 고정parent/releases 아래 readonly 제공, 상대 current로 교체한다. manifest/zip/checksum은 공개root 밖에 보존한다. 실패시 기존current를 유지한다.

Caddy는 /v1·/v2·/health 정확경로/하위를 API에 우선 전달한다. 화면만 index fallback, 누락자산404, wasm MIME과 실행/bootstrap 캐시재검증을 검증한다. 점검상태는 API와웹의 공개요청을503으로 제한하되 내부검증 경로를 남긴다. 인증서volume/네트워크/DBvolume 보존. 새탭/재접속 인수이며 구탭 무중단/미전송작업 자동이전은 지원하지 않는다.

환경/Compose/Caddy와 실제 current/previous의 동결구성/configuration revision을 함께 정렬하고 다음 API배포에서도 웹mount와환경을 보존한다. 동일릴리즈 조합에 Backend/image/계약hash/DB/configrevision·웹source/hash·APKsource/hash·인수결과를 기록한다.

## 검증·운영·복귀

- 로컬: 원구프로필/단건GET·POST/원query·원ACK와 신규/pending 차이, capability/group_policy 업그레이드거절·CONTEXT_INVALID, 신규4묶음경로·캐릭터문제 경로·두전체계약을 확인한다. 실패를 skip/과거PASS로 대체하지 않는다.
- 도구: 위조zip/hash·탈출/중복/링크·source불일치/만료/묵시대체거절, 원3파일보존·활성화실패시기존current·웹복귀·실정적HTTP/SPA/404/cache/MIME 검증.
- 운영직전: 기존백업준비는 재사용하되 최신dump/변경대상설정만 갱신한다. 실제PC폴더 접근을 확인하고 사본검증 후 쓰기를 중지한다. 이미지사전확보·배포잠금·DB/키/설정 보존비교를 준비한다.
- DB0036 전 실패는 기존구성복귀. 적용후 구0035전용이미지/DB downgrade 자동복귀 금지, 점검을 유지하고 전진수정한다. 백업복원은 자료영향이 있는 별도 결정이다.
- 정상Backend+웹실패는 웹만 이전/current없음(API-only)으로 복귀한다. 공개전 실패는 점검유지, 자동공개하지 않는다. API/DB/전체계약/정적HTTP는Backend, 로그인·보호조회·모집생성/재조회/재로드/로그아웃·새APK로그인은Native/사용자가 확인한다.

기존 배포·백업 기준은 [배포 안내](backend-release.md)와 [백업 원장](backup-and-recovery.md)을 따른다. 현재 설계의 작성/통합은 도구구현·운영검증 완료를 뜻하지 않는다.
