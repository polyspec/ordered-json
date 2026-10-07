<!-- doc-id: distribution -->
<!-- source-sha256: b11e69c15173732e60197bd85e0dc9c16efe77ea3a5e3272100c900e9acae85c -->
# 배포

[English](distribution.md)

<a id="state"></a>
## 확인된 상태

[distribution.json](../distribution.json)에 소스와 게시 관측을 기록합니다. 저장소는 다섯 [구현 패키지](../spec/repositories.ko.md#ownership)를 하나의 리비전에 담습니다. 기록된 관측에서 GitHub 릴리스와 버전 태그는 발견되지 않았습니다.

npm, crates.io, Packagist, Go, PHP 확장의 레지스트리 게시는 검증되지 않았습니다. 확인된 로컬 배포는 소스 체크아웃입니다. PIE 메타데이터와 성공한 PIE 빌드는 로컬 빌드 호환성을 확인하며 Packagist 게시 근거는 아닙니다. 확장 패키지는 `polyspec/ordered-json-extension`, PHP 라이브러리는 `polyspec/ordered-json`입니다.

소스 버전 문자열은 릴리스된 산출물의 근거가 아닙니다. 레지스트리 게시 워크플로는 설정되지 않았고, 호스팅 CI는 전체 suite와 push gate를 실행하며([호스팅 CI](validation.ko.md#ci)), tag의 push는 그 tag의 GitHub Release를 만듭니다([tag 릴리스](#tag-release)). LICENSE 파일은 없습니다.

<a id="source-publication"></a>
## 소스 게시

변경한 패키지의 필수 검사를 실행하고 공통 계약과 함께 커밋합니다. 모든 변경은 pull request와 merge queue를 거쳐 `main`에 들어갑니다([main 게시](validation.ko.md#publish)).

~~~sh
git push origin HEAD:refs/heads/<branch>
gh pr create --base main --head <branch> --fill
gh pr merge <branch> --auto --rebase
~~~

호스팅 CI가 pull request와 merge group에서 통합 검사와 PIE 검사를 실행하고, merge queue는 필수 검사를 통과한 commit으로 `main`을 옮깁니다. 깨끗한 복제가 게시된 리비전에서 모든 패키지를 빌드하는지 확인합니다. 공통 계약 변경은 검증기, fixture와 관련 패키지를 같은 리비전으로 게시합니다.

인증 정보는 시스템 인증 저장소에서 관리합니다. 게시 관측과 테스트 결과를 구분합니다.

<a id="tag-release"></a>
## Tag 릴리스

릴리스는 `main`의 commit에 붙인 tag입니다([릴리스 절차](../../AGENTS.ko.md#release)). `vX.Y.Z`는 `js/`의 npm 패키지와 `php/`, `php-extension/`의 Composer 패키지를 버전 X.Y.Z로 릴리스하고, `go/vX.Y.Z`는 Go 모듈 `github.com/polyspec/ordered-json/go`를 릴리스합니다. `rust/`의 Cargo 패키지는 archive로 릴리스하지 않고 git tag로 사용합니다. `cargo package`는 git 의존성을 해석되지 않는 crates.io 요구로 바꾸기 때문입니다. tag의 push는 `.github/workflows/release.yml`(`on: push: tags: ['v*', '**/v*']`, 권한 `contents: write`. tag filter에서 `*`는 `/`와 맞지 않으므로 `**/v*`가 어느 깊이의 Go 모듈 tag든 포함합니다)을 실행하며, 그 step은 다음 순서로 `scripts/release.py`를 실행하고 첫 실패에서 멈춥니다.

~~~sh
make release-verify
make release-versions
make release-assets
make release-publish
~~~

1. `make release-verify`는 tag된 commit이 `origin/main`의 조상이고(`git merge-base --is-ancestor`), 그 commit의 최신 check run `push-gate`와 `ci-passed`(`gh api repos/<repository>/commits/<sha>/check-runs`)가 결론 `success`로 완료되었는지 확인합니다. 없거나 실패한 check의 이름을 적으며 테스트를 다시 실행하지 않습니다.
2. `make release-versions`는 `package.json`, `js/package.json`, `rust/Cargo.toml`에 X.Y.Z가 있고(`version` field가 없는 `composer.json`은 Composer처럼 버전을 tag에서 받습니다) `CHANGELOG.md`에 section `## X.Y.Z`가 있는지 확인하며, 다른 파일마다 그 버전과 tag의 버전을 적습니다. `go/vX.Y.Z`에는 `go/go.mod`의 모듈 경로와 section을 확인합니다.
3. `make release-assets`는 `var/release/assets`를 만듭니다. `polyspec-ordered-json-X.Y.Z.tgz`(`js/`의 `npm pack`), `polyspec-ordered-json-X.Y.Z.zip`과 `polyspec-ordered-json-extension-X.Y.Z.zip`(tag된 commit의 `php/`와 `php-extension/`의 `git archive`)입니다. 릴리스 asset은 npm tarball과 Composer zip뿐입니다. archive 이름은 `<package name>-<version>.<ext>`이고 `@scope/`와 `vendor/`는 `scope-`와 `vendor-`로 씁니다. Go tag는 아무것도 만들거나 첨부하지 않습니다.
4. `make release-publish`는 archive와 함께 `gh release create <tag> --verify-tag --title <tag> --notes-file <notes>`를 실행합니다. GitHub는 125000자를 넘는 릴리스 본문을 거부하므로, notes는 `CHANGELOG.md`의 section `## X.Y.Z`가 125000자 이하이면 그 section이고, 그렇지 않으면 한 줄 `The changes of X.Y.Z are listed in [CHANGELOG.md](https://github.com/polyspec/ordered-json/blob/<tag>/CHANGELOG.md#<anchor>).`입니다. tag는 경로 segment별로 URL 인코딩되고, anchor는 section의 `<a id>` anchor이며 없으면 점을 뺀 버전입니다.

tag는 환경 변수 `TAG`로 step에 전달됩니다. `scripts/tests/test_release.py`는 `gh`, `npm`의 fake로 각 step을 실행하고, `scripts/tests/test_workflow_rules.py`는 trigger, 권한, step의 순서를 요구합니다.

<a id="releases"></a>
## 레지스트리와 릴리스 기록

확립되거나 검증된 레지스트리 게시는 없습니다. 릴리스를 기록하기 전에 패키지 이름, 버전, 포함 파일, 레지스트리, 산출물, 검사한 소스 개정본을 확인합니다. 산출물 URL과 게시 관측을 별도로 기록합니다. 확장 릴리스를 게시할 때는 `php-ext` Composer 메타데이터를 사용해 Packagist를 통해 PIE에 등록합니다.

게시 상태가 변경되면 영어·한국어 배포 문서, 기능 배포 상태, 변경 기록을 갱신합니다. 테스트, 버전 선언, 계획된 태그, 소스 푸시만으로 게시를 추정하지 않습니다.
