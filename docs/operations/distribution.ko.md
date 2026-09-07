<!-- doc-id: distribution -->
<!-- source-sha256: 0a3750acddd942b11289f36a55978d125359dc6aa51dab0017bc352ab6b28d9b -->
# 배포

[English](distribution.md)

<a id="state"></a>
## 확인한 상태

게시 확인 결과의 정본은 [distribution.json](../distribution.json)입니다. 소스는 공개 [ordered-json 저장소](https://github.com/polyspec/ordered-json)의 `main`에서 제공됩니다. 기록된 확인 결과에는 GitHub 릴리스와 버전 태그가 없습니다.

npm, crates.io, Packagist, Go, PHP 확장의 레지스트리 게시는 검증되지 않았습니다. 확인된 배포 방식은 소스 체크아웃입니다. 소스 메타데이터의 버전 문자열은 릴리스된 산출물의 근거가 아닙니다. 저장소에는 레지스트리 게시 워크플로와 호스팅 CI 설정이 없습니다. LICENSE 파일도 없습니다.

<a id="source-publication"></a>
## 소스 게시

필수 검사 성공 후 승인된 소스 변경을 게시합니다.

~~~sh
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
~~~

로컬과 원격의 전체 커밋 ID를 비교합니다. 일치할 때만 소스 게시를 기록합니다. 인증 세부사항은 시스템 인증 저장소에서 관리하며 저장소 문서에 포함하지 않습니다.

<a id="releases"></a>
## 레지스트리 및 릴리스 기록

이 저장소에는 확정하거나 검증한 레지스트리 게시 명령이 없습니다. 릴리스를 기록하기 전에 정확한 패키지 이름, 버전, 포함 파일, 대상 레지스트리, 게시된 산출물, 검사한 소스와의 관계를 확인합니다. 산출물 URL과 확인 결과는 검증 결과와 별도로 기록합니다.

게시 상태가 바뀌면 영어 및 한국어 배포 문서, 기능 배포 상태, 변경 기록을 갱신합니다. 테스트 성공, 버전 선언, 태그 계획, 소스 파일 푸시만으로 게시를 판정하지 않습니다.
