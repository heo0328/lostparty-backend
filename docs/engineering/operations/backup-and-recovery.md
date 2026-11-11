# 로컬·운영 백업 원장과 안내 기준

현재 준비 점검(2026-11-11 / Issue49): Native 새 release 서명키는 독립사본/접근·사본서명검증·서명 Secrets/CI 확인 완료 보고이며 신규 Android OAuth/운영 Web 원본 등록도 사용자 확인으로 인계됐다. Backend는 새 공개 client의 운영 azp 1항목 추가 준비만 필요하고 실제 실행/동결 설정에는 아직 미포함이다. Backend 서비스키4개·기존 배포 SSH Secret은 재사용하며 재발급하지 않는다. 최신 운영 DB/환경·복구 구성 사본 생성/PC전송은 아직 미수행으로 기존20261107 사본을 현재최신DB로 부르지 않는다. 실제 변경 직전 기존PC백업폴더에 새날짜 사본을 보관하고 변경 후 환경/동결구성·웹 배포 식별도 추가한다. [실측/인계 근거](records/web-handoff-2.1.0.json)·[Issue49 전체21](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6793947409).

현재 보관 기준(2026-11-10): #47 로컬 반영에서도 기존 환경/키 사본을 재사용했고 DB dump 제외 방침은 유지했다. 새 키/환경·운영 복구 구성을 만들지 않았다. 실행 현황은 [운영 안내](README.md), 당시 보존 비교는 [반영 기록](records/batch-completion-local-rollout.json)을 따른다. 기존 사본 보관/실제 복원 수준은 아래 원장과 같다.

로컬 구조 이행 당시(2026-11-08): 사용자 승인으로 #17 개발 DB0035→0036·API를 반영했다. [로컬 반영 집계](records/roster-participation-local-rollout.json) 기준 기존 자료/키·환경을 보존했고 로컬 DB dump 제외 결정은 유지했다. 신규 키/환경 생성·운영 변경은 없으며 기존 보관본을 재사용한다. ignored 감사 자료는 DB백업/복원 시험이 아니다. 아래0035는 복구 당시 기준이다.


2026-11-07 / Backend / [Issue46](https://github.com/heo0328/lostparty-backend/issues/46). 실제 파일·보관 상태와 다음 안내 시점의 원본이다. 상세 복구/시험 이력은 [DEV_LOG](../../project/DEV_LOG.md#development-recovery-20261107), 비민감 백업 집계는 [결과 JSON](records/backup-recovery-2026-11-07.json)을 따른다.

## 현재 완료와 구분

| 구분 | 상태·확인 수준 |
|---|---|
| 로컬 실행·인증 | 현재 two-cycle/DB0036. 2026-11-07 복구 당시DB0035·키4개 유효성·Google 허용값 반영과 실제 앱 로그인 성공 확인. 기존 로그인/키를 반복 생성·재시험할 대기가 아님 |
| 로컬 파일 보관 | 사용자 보고: `.env`·로컬 키4개, Google 콘솔 클라이언트 화면/다운로드 JSON, 시드니 기본 SSH 키를 개발용 내장 SSD의 백업 폴더에 보관. 사본을 모두 직접 검증한 것은 아님 |
| 로컬 DB | 사용자 지시로 dump 제외. 백업 실패/분실로 표시하지 않음 |
| 운영 기준본 | 2026-11-07 20:50경(KST), DB dump·운영 환경·기존 키4개·복구 구성을 생성하고 서버 밖 사용자 PC 내장 SSD 폴더로 전송·내용 비교 완료 |
| 복원 검증 | dump 목차·아카이브 읽기/내용·서버/PC SHA-256 일치 확인. 실제 DB/서비스 복원 시험은 미실행 |
| 외장 매체 | 사용자 직접 복사 대상. 현재 사본은 내장 SSD이며 외장하드 보관 완료로 표시하지 않음 |
| 정기 자동화 | 미구성·주기/보관기간 미확정. 현재 파일 안내·보관이나 개발 재개의 선행 조건이 아님 |
| 배포용 SSH 개인키 원본 | 기존 개발 환경에서 유실된 것으로 확정. 보유 여부를 반복 질문하지 않음. 정상인 GitHub Secret은 유지하며 지금 재발급/회수하지 않음 |

최초 운영 보류는 이후 사용자의 명시적인 온라인 백업 진행 지시로 이번 수동 기준본 범위에서 해제됐다. 다음 운영 작업·주기적 백업·키 교체의 포괄 승인이 아니다. [전체4번째 Native 범위 정정](https://github.com/heo0328/lostparty-backend/issues/46#issuecomment-6705693077)·[전체5번째 Backend 실행 결과](https://github.com/heo0328/lostparty-backend/issues/46#issuecomment-6706589300)를 따른다.

## 사용자가 보관할 물리 파일

로컬 루트는 프로젝트 폴더, 운영 루트는 `/home/ubuntu/lostparty-backend`다. 같은 파일명이어도 **로컬·운영 키는 서로 별개**다.

| 대상 | 원본 위치·보관 방법 | 복구 시 함께 필요한 것·현재 상태 |
|---|---|---|
| 로컬 환경 | 로컬 `.env`를 복사 | Google 클라이언트/허용 목록·DB 접속·키 ID 등 대응 설정. 사용자 보관 보고 |
| 로컬 JWT 서명 | 로컬 `.secrets/jwt.pem` | 같은 로컬 세션 환경. 사용자 보관 보고 |
| 로컬 세션 복구 | 로컬 `.secrets/recovery.key` | 대응 세션 갱신 복구 자료. 사용자 보관 보고 |
| 로컬 게임 API 암호화 | 로컬 `.secrets/lostark-credential.key` | 해당 키로 암호화한 DB 자료. 사용자 보관 보고 |
| 로컬 게임 API 식별 | 로컬 `.secrets/lostark-fingerprint.key` | 대응 암호화키·게임 API 키 DB 자료. 사용자 보관 보고 |
| 로컬 복사용 묶음 | 로컬 `backups/local-dev-files-20261107.tar` | `.env`·`.secrets`를 포함해 사용자가 생성·복사. DB 미포함. 원본 권한은 풀지 않음 |
| 운영 DB | 실행 PostgreSQL17에서 `pg_dump -Fc`로 생성 | 대응 키·환경·source/image·schema. 이번 기준본은 사용자 PC 저장·검증 완료 |
| 운영 환경 | 운영 `.env.lightsail` | DB 역할/비밀번호·OAuth·도메인 설정 및 실제 동결 구성. 기준본 포함 |
| 운영 키 | 운영 `.secrets/lightsail/`의 위4개 파일 | 해당 DB와 같은 키 묶음. 기준본 포함·원본 보존 |
| 운영 배포 상태 | `/var/lib/lostparty-deploy/`의 JSON 상태·현재/이전 동결 구성 | 현재 image digest·source·DB revision·복귀 기준. 기준본 포함, 민감한 환경값이 있을 수 있어 공개하지 않음 |
| 운영 복구 도구 | 운영 Compose, `docker/Caddyfile.lightsail`, `docker/init-db.sh`, `/usr/local/lib/lostparty-deploy/` 도구, 제한 sudo/공개키 등록 구성 | 기준본 포함. 관리자 SSH 개인키 자체는 서버에 있는 것으로 간주하지 않음 |
| 운영 이미지·인증서 볼륨 | Docker image 파일·Caddy 볼륨 자체는 이번 묶음에 미포함 | 복구 시 기록된 이미지 digest의 확보·HTTPS 재준비를 별도 확인. 이 묶음을 완전한 서버 디스크 이미지라고 부르지 않음 |

DB dump는 DB가 있는 상태의 별도 내보내기 파일이다. 코드 clone·환경파일·키 복사·실행 중인 DB 볼륨을 그대로 복사한 것과 구분한다. 단일 DB dump에는 클러스터 전역 역할이 모두 포함되지 않으므로, 복구 때 대응 환경과 `init-db.sh` 기준으로 역할·권한을 준비한다. 원본 운영DB 위에서 시험 복원하거나 누락 키를 새로 만들어 복구를 대신하지 않는다.

### 권한과 사용자 복사

키 디렉터리0700·파일0600 등 원래 접근 제한을 유지한다. 탐색기에서 Access denied이면 파일 부재로 판정하거나 API가 읽는 원본 소유자/권한을 무작정 바꾸지 않는다. 필요한 경우 승인된 범위에서 사용자 소유·제한 권한의 복사용 묶음만 만든다. 도구·권한 부족이 생기면 원인을 알리고 필요한 사용자 실행을 요청한다.

보관 위치·비밀번호 관리의 장기 협의, 새 암호화 도구·유료 저장소 도입을 사용자의 파일 복사 안내 앞에 붙이지 않는다. 이번 사본은 사용자 직접 보관용이며 파일 자체는 암호화하지 않았다. 실제 키·비밀번호·DB·복구 가능한 백업은 Git/Issue/채팅/공개 artifact·로그로 전송하지 않는다. 공개 기록에는 이름·상태·날짜·비민감 무결성 결과만 남긴다.

## 콘솔·초회 생성 자료

| 항목 | 보관/재발급 구분·담당 |
|---|---|
| GitHub CLI 로그인 | 현재 사용자 로그인·push 권한 정상. 이 목적만으로 새 PAT를 만들 필요 없음 |
| 직접 생성하는 GitHub PAT | 생성 때 표시되는 값을 그때 보관. 잃었으면 필요 시 재발급하며 사이트 비밀번호와 별개. 현재 발급 작업 없음 |
| GitHub production 배포 Secret | `LIGHTSAIL_DEPLOY_SSH_KEY`의 원본을 최초 생성 시 별도 보관. 이름 목록은 백업이 아니고 일반 Secret 조회로 원문 재다운로드 불가. 현재 원본 유실·Secret 정상 유지. 필요 시 별도 키 교체 구간에서 새 원본을 보관 |
| 배포 호스트 확인 | `LIGHTSAIL_SSH_KNOWN_HOSTS`와 대상 서버/공개 지문을 기록. 리전·서버 변경 시 새 서버에서 검증한 값으로 갱신하며 호스트 확인을 끄지 않음 |
| Lightsail 기본키 | 리전별 기본키는 콘솔에서 재다운로드 가능. 시드니 기본키는 사용자 다운로드·PC 보관 보고 및 접속 확인 완료 |
| Lightsail 사용자 지정키 | 생성 시 개인키 원본 별도 보관. 콘솔에서 개인키를 다시 받을 수 있다고 가정하지 않음 |
| Google OAuth | 프로젝트·Web/Android 클라이언트 ID·용도·패키지명·서명 SHA-1을 기록. 사용자 화면/다운로드 JSON 보관 보고. 현재 Backend ID-token 검증에는 client secret JSON을 추가하지 않음 |
| Native 서명자료 | Native 담당. #49 전체7·19·20에서 새 release 키 독립백업·접근/사본서명검증·Secrets/CI서명 확인 완료 보고. Backend 서비스키 교체와 구분하며 실제 기기/운영로그인은 별도 |

[GitHub PAT 안내](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)·[Actions Secrets API](https://docs.github.com/en/rest/actions/secrets)·[Lightsail 키 안내](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-managing-ssh-keys.html)·[Google OAuth 클라이언트 안내](https://support.google.com/cloud/answer/15549257?hl=en).

시드니 관리자 기본키를 추가하고 새 SSH/sudo 접속을 확인했으며 기존 ED25519 등록키와 별도 `lostparty-deploy` 계정의 키는 유지했다. 브라우저 SSH와 관리자/배포 키의 역할은 다르다. 서울 리전 이전은 차후 작업이며 새 접속키·호스트 확인과 기존 DB/서비스키 보존을 따로 다룬다.

## 이번 운영 기준본과 확인 범위

- 파일: `lostparty-production-20261107T115031Z-b4dad4.tar`와 대응 `.sha256`, `lostparty-production-20261107T115031Z-b4dad4-README.txt`.
- 서버 원본은 운영 루트의 `backups/lostparty-production-20261107T115031Z-b4dad4/`, PC 사본은 사용자가 지정한 내장 SSD 백업 폴더다. 개인 저장 경로는 공개 문서에서 복제하지 않는다.
- 묶음 내부 `database/database.dump`에 DB, `server/` 아래 원래 경로별 구성/키, `BACKUP-INFO.json`에 버전·원래 경로/권한·검증 범위를 기록했다. 내용을 채팅에 붙여넣지 않고 보관 파일로 관리한다.
- archive614,400bytes·33개 멤버·dump 목차842개 항목. 서버/PC SHA-256 및 멤버 내용 일치. 비민감 checksum은 [집계](records/backup-recovery-2026-11-07.json)에 보존한다.
- v2.0.0/source51b1cb3·imagef33f4c6c·DB0035. 실제 키 mount·여유공간·서비스 health 확인 후 배포 lock과 충돌하지 않게 온라인 dump했다. 테이블 lock 대기는5초로 제한했고 경고 없이 종료했다. 일반 조회/저장을 중지하지 않았지만 읽기·CPU·디스크 부하가0이었다는 뜻은 아니다.
- API/DB/Caddy 컨테이너·시작시각·재시작 횟수·이미지/mount, 원본 키/환경/복구 구성의 내용·권한·DB revision 보존 및 전송 후 공개health200/DB 정상 확인. 신규 배포·migration·키 교체·운영 복원 없음.
- 실제 복구 시험과 정기 자동화는 미실행. 실패 없는 복원이나 복구 시간을 보장하는 기록이 아니다.

## 언제 다시 안내하고 갱신하는가

| 시점 | 필요한 행동 |
|---|---|
| 로컬 키·환경을 처음 준비하거나 변경 | 파일명/실제 경로·복사 방법을 사용자에게 안내하고 보관 상태를 기록. 이번 복구 파일은 기존 보관 결과 재사용 |
| 새 서명키·접속키·토큰 생성 | 다시 받을 수 없는 원본과 alias/ID·필요 비밀번호를 그때 보관하도록 안내. 첫 사용/게시 전 해당 보관 상태 확인 |
| DB 구조/자료 변환·키/비밀번호·운영 접속/배포 구성 변경 전 | 변경 대상의 직전 상태와 필요한 최신DB·복구 구성을 확보할 범위를 판단·안내. 승인된 작업에서 사본 생성/전송. 변경 후 일치하는 키/설정 버전 참조를 갱신 |
| 일반 코드/앱 업데이트 | DB·키·설정 영향과 기존 사본 유효성부터 확인. 같은 키를 매번 재생성·재복사하거나 사용자에게 같은 자료를 반복 요구하지 않음 |
| 다음 운영 배포 준비 | 현재 백업 기준본 이후 필요한 최신DB/설정 사본만 확인. 배포 완료까지 백업을 미루지 않으며, 실제 서버 영향/권한·여유공간·동시 스키마 작업을 확인 |
| PC 교체·포맷 전 | 미게시 작업·ignored 설정/키와 사용자가 보존하려는 개발자료의 보관을 안내. 현재 사용자의 로컬DB 제외 결정을 자동 변경하지 않음 |
| 실제 서비스 복구·정기 자동화 | 별도 구간에서 대상/영향·필요 검증을 정함. 현재 개발 재개·이번 보관 마감의 필수 조건이 아님 |

유효 사본 재사용 조건은 **같은 원본/키 세대·용도·대응 환경**, 실제 보관 사실과 읽기 가능성에 반하는 새 증거 없음이다. DB는 계속 변경되므로 과거 dump를 최신 데이터로 부르지 않는다. 파일 안내·문서 검증·사용자 복사·무결성·실제 복원 단계를 각각 표시한다. 새 계약 영향이 없으면 Native의 동일 기준 재수용을 요구하지 않는다.

서버에서 dump·복사·다운로드하는 절차는 서비스 중 가능하지만, 기존 환경 보존과 실행 대상 확인이 필요하다. [PostgreSQL17 pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html)·[서버 운영 안내](lightsail-quick-ops.md)를 참고한다. 신규 백업 생성·원본 교체·자료 삭제를 단순 기록 정리 명령과 섞지 않는다.
