# DB 돋보기 작업 스킬

## 목적

회원/온라인 쇼핑몰용 테이블 명세 관리 프로그램의 기능 수정, 샘플 DB 수정, 빌드 및 실행 검증을 안전하게 수행한다.

## 반드시 지킬 정책

1. 같은 MAJOR 버전 내의 `1.5 → 1.6` 변경은 로컬 개발/테스트용으로 관리한다.
2. GitHub 업로드 또는 릴리스는 `1.x → 2.x`처럼 MAJOR 버전이 올라갈 때만 한다.
3. 새 버전은 기존 `metadata.db`를 사용할 수 있어야 한다.
4. 배포 시 기존 DB와 첨부파일은 보존하고 `DB돋보기.exe`만 교체한다.
5. DB 변경은 백업 후 비파괴적·반복 가능한 마이그레이션으로 처리한다.
6. 수정이 끝나면 실행 중인 프로그램을 종료하고 재시작하여 변경 사항을 확인한다.
7. 정상 동작 중인 HWP/HWPX 내보내기 코드는 절대 수정하지 않는다.
8. `DB돋보기.spec`의 `collect_data_files('hwpx')` 설정을 반드시 보존한다.

## 테이블 명세 작업 순서

1. `metadata.db` 백업
2. `tables`에 테이블 기본 정보 추가/수정
3. `columns`에 컬럼 명세 추가/수정
4. `relations`에 관계 추가
5. 중복 및 참조 대상 확인
6. `PRAGMA integrity_check` 실행
7. 테이블/컬럼/관계 수 확인
8. 앱 종료 후 재시작
9. 화면에서 명세와 관계도 확인

## 배포 전 체크리스트

- [ ] 버전이 변경 목적에 맞게 올라갔는가?
- [ ] 같은 MAJOR 버전이면 GitHub에 업로드하지 않았는가?
- [ ] 기존 `metadata.db`로 앱이 실행되는가?
- [ ] EXE만 교체해도 기존 데이터가 보존되는가?
- [ ] DB 백업이 있는가?
- [ ] SQLite 무결성 검사가 통과했는가?
- [ ] 실행 중인 프로그램을 종료 후 재시작했는가?
- [ ] HWP/HWPX 관련 파일과 로직을 건드리지 않았는가?
- [ ] HWPX 내보내기 회귀 테스트가 통과했는가?
- [ ] GitHub push/release는 사용자의 명시적 요청이 있는가?

상세 규칙은 `.clinerules\project-rules.md`를 따른다.

## Hugging Face 이미지 생성 스킬

필요한 아이콘, 배너, 안내 이미지 등은 Hugging Face Inference API를 사용해 생성할 수 있다.

### 보안 규칙

- Hugging Face API 토큰을 소스 코드, `SKILL.md`, `.clinerules`, Git 저장소, 로그 또는 이미지 파일에 기록하지 않는다.
- 토큰은 반드시 `HF_TOKEN` 환경변수로 전달한다.
- 토큰이 채팅, 로그, 커밋 등에 노출되었으면 즉시 Hugging Face에서 해당 토큰을 폐기하고 새 토큰을 발급한다.
- 이미지 생성 요청은 필요한 경우에만 수행하며, 생성된 결과물에는 비밀정보나 개인정보를 포함하지 않는다.

### 환경변수 설정

PowerShell:

```powershell
$env:HF_TOKEN = "hf_발급받은_새_토큰"
```

영구 저장이 필요한 경우에는 운영체제의 사용자 환경변수에 등록하되, 프로젝트 파일에는 저장하지 않는다.

### 이미지 생성 기본 절차

1. 이미지의 용도, 크기, 투명 배경 여부, 스타일을 먼저 정한다.
2. Hugging Face에서 이미지 생성이 가능한 모델을 선택한다. 예: `stabilityai/stable-diffusion-xl-base-1.0`.
3. `HF_TOKEN` 환경변수를 읽어 Inference API에 인증 요청한다.
4. 생성 결과를 프로젝트 목적에 맞는 경로에 저장한다.
   - 앱 리소스: `assets\\generated\\`
   - 사용자 첨부파일: 기존 `attachments\\` 구조를 확인한 뒤 해당 위치에 저장
5. 파일 형식과 해상도를 확인하고, 프로그램에서 실제로 열리는지 검증한다.
6. 실패하면 토큰을 출력하지 말고 HTTP 상태 코드와 비밀정보를 제거한 오류 내용만 기록한다.

### PowerShell 호출 예시

```powershell
$model = "stabilityai/stable-diffusion-xl-base-1.0"
$prompt = "clean modern blue database application icon, white background, no text"
$headers = @{ Authorization = "Bearer $env:HF_TOKEN" }
$body = @{ inputs = $prompt } | ConvertTo-Json
$output = "assets\\generated\\db-icon.png"
New-Item -ItemType Directory -Force (Split-Path $output) | Out-Null

Invoke-WebRequest `
    -Uri "https://api-inference.huggingface.co/models/$model" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body `
    -OutFile $output
```

실제 작업에서는 대상 폴더를 먼저 만들고, API가 모델 로딩 중(`503`)이면 잠시 기다린 후 재시도한다. 생성 이미지를 프로그램에 포함하거나 배포할 때는 `DB돋보기.spec`의 데이터 수집 설정과 기존 HWP/HWPX 보호 규칙을 변경하지 않는다.
