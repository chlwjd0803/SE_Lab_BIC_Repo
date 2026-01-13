# LLM-based BIC Identification Study
> **목적**: Defects4J 데이터셋과 LLM(Ollama)을 활용하여 버그 유발 커밋(BIC)을 정교하게 식별하는 연구 환경 구축 가이드

---

## 1. 시스템 필수 패키지 설치 (Root 권한 필요)
빈 서버(Ubuntu 기준)에서 가장 먼저 실행해야 하는 환경 설정입니다. Defects4J 운영에 필요한 Perl 및 Java 8, 기타 빌드 도구를 포함합니다.

```bash
# 패키지 목록 업데이트
sudo apt update

# 필수 빌드 도구 및 라이브러리 설치
sudo apt install -y build-essential git curl wget unzip perl \
                       libdbi-perl libdbd-csv-perl \
                       python3 python3-pip

# SDKMAN 설치 스크립트 실행
curl -s "https://get.sdkman.io" | bash

# 현재 터미널에 적용
source "$HOME/.sdkman/bin/sdkman-init.sh"

# 설치 확인
sdk version


# Java 8 설치 (Defects4J 핵심 요구사항)
sudo apt install -y openjdk-8-jdk

# Java 11 (Temurin) 설치 -> 11버전이 더 나을듯
sdk install java 11.0.22-tem

# Java 버전 확인 (8, 11버전이어야 함)
java -version
```

---

## 2. Defects4J 설치 및 환경 변수 설정
```bash
# 1. 연구용 메인 디렉토리 생성
mkdir llmszz_v1
cd llmszz_v1

# 2. Defects4J 저장소 클론 및 설치
git clone [https://github.com/rjust/defects4j.git](https://github.com/rjust/defects4j.git)
cd defects4j
sudo cpanm --installdeps .
./init.sh

# 3. 환경 변수 등록 (~/.bashrc)
echo 'export PATH=$PATH:/home/cj/llmszz_v1/defects4j/framework/bin' >> ~/.bashrc
source ~/.bashrc
```

---

## 3. Ollama (LLM) 환경 구축
서버 로컬에서 LLM을 구동하기 위한 설정입니다.
```bash
# 1. Ollama 설치 스크립트 실행
curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh

# 2. 분석용 모델 다운로드
ollama run llama3:8b

# 3. 파이썬 연동 라이브러리 설치
pip3 install ollama
```

---

## 4. 버그 재현 및 분석 실습 (Lang 1 기준)
실제 연구를 진행하는 워크플로우입니다.

### 4.1 버그 체크아웃 및 환경 확인
```bash
cd ~/llmszz_v1
mkdir temp_lang_1 && cd temp_lang_1

# Lang 1번 버그의 Buggy 버전(1b) 가져오기
defects4j checkout -p Lang -v 1b -w .

# 컴파일 및 테스트 실패 재현 확인
defects4j compile
defects4j test
```

### 4.2 버그 수정 정보 추출 (Patch & Blame)
```bash
# 1. 버그 수정 내용 확인 (고쳐진 부분 파악)
cat /home/cj/llmszz_v1/defects4j/framework/projects/Lang/patches/1.src.patch

# 2. Git Blame으로 해당 라인을 수정한 커밋 추적
# (패치 파일에서 확인한 라인 번호를 -L 뒤에 입력)
git blame -L 464,485 src/main/java/org/apache/commons/lang3/math/NumberUtils.java
```

---

## 💡 연구 메모
- **Java 버전**: 만약 Java 버전이 꼬인다면 `sudo update-alternatives --config java` 명령어로 8버전을 선택하세요.
- **Perl 모듈**: Defects4J 실행 중 `DBI` 관련 에러가 나면 `libdbi-perl` 설치 여부를 다시 확인하세요.
- **BIC 확인**: LLM이 지목한 커밋 해시로 이동(`git checkout <hash>`)한 뒤 `defects4j test`를 돌려 실패 여부를 검증합니다.