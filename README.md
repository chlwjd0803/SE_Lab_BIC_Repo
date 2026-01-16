# 🚀 LLM 기반 BIC(버그 유발 커밋) 식별 연구 가이드

이 가이드는 **Defects4J** 데이터셋과 **LLM(Ollama)**을 활용하여 버그의 원인이 된 과거 커밋(BIC)을 정교하게 식별하는 연구 환경 구축 및 분석 워크플로우를 다룹니다.

---

## 1. 시스템 필수 패키지 설치 (Root 권한 필요)
빈 서버(Ubuntu 기준)에서 가장 먼저 실행해야 하는 환경 설정입니다. Defects4J 운영에 필요한 Perl 및 Java 8, 기타 빌드 도구를 포함합니다.

```bash
# 1. 패키지 목록 업데이트 및 필수 빌드 도구 설치
sudo apt update

sudo apt install -y build-essential git curl wget unzip zip perl \
               libdbi-perl libdbd-csv-perl \
               python3 python3-pip cpanminus tree

# 가상환경일때 다음 명령어를 통해 안전한 경로임을 명시
git config --global --add safe.directory /workspace/SE_Lab_BIC_Repo

# 2. SDKMAN 설치 및 Java 설정
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# Java 11 (Temurin) 설치
sdk install java 11.0.22-tem
sdk use java 11.0.22-tem

# 설치 확인
java -version


# 혹시나 Java 8 버전과의 호환성이 우려될경우
sdk install java 8.0.402-tem
sdk use java 8.0.402-tem


# 시스템 기본값으로 고정 (터미널 다시 켜도 유지됨)
sdk default java 8.0.402-tem


# 자바 버전 토글

```

---

## 2. Defects4J & Ollama 환경 구축
```bash
# 1. 연구용 메인 디렉토리 생성 및 이동
mkdir -p ~/llmszz_v1
cd ~/llmszz_v1

# 2. Defects4J 저장소 클론 및 설치
git clone https://github.com/rjust/defects4j.git
cd defects4j
sudo cpanm --installdeps .
./init.sh

# 3. 환경 변수 등록 (~/.bashrc)
echo "export PATH=\$PATH:$(pwd)/framework/bin" >> ~/.bashrc
source ~/.bashrc

# 4. Ollama(LLM) 설치 및 모델 다운로드

# 아래 명령어로 GPU와 연결됨을 반드시 확인하기
nvidia-smi

# 하드웨어 연결용
apt update && apt install -y pciutils lshw

curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3:8b
ollama run llama3:8b
pip3 install ollama
```

---

## 3. 프로젝트 버전 관리 (Buggy vs Fixed)

BIC 탐지를 위해 버그가 있는 상태(`b`)와 고쳐진 상태(`f`)를 각각 체크아웃하여 비교하는 과정이 필수적입니다.

### 3.1 버전별 체크아웃 방법
```bash
cd ~/llmszz_v1
mkdir -p analysis/lang_1 && cd analysis/lang_1

# Lang 1번 버그의 Buggy 버전(1b) 가져오기: 버그 재현용
defects4j checkout -p Lang -v 1b -w ./lang_1_buggy

# Lang 1번 버그의 Fixed 버전(1f) 가져오기: 정답 비교용
defects4j checkout -p Lang -v 1f -w ./lang_1_fixed

# 컴파일 및 테스트
defects4j compile
defects4j test
```

### 3.2 버전 비교 요약
| 구분 | Buggy 버전 (`1b`) | Fixed 버전 (`1f`) |
| :--- | :--- | :--- |
| **상태** | 버그 포함 (테스트 실패) | 버그 수정됨 (테스트 통과) |
| **주요 용도** | `git blame` 실행 및 BIC 추적 | 수정 패치(정답) 확인 및 LLM 컨텍스트 |

---

## 4. 버그 분석 및 비교 방법 (추적의 핵심)

### 방법 1: `diff`를 이용한 코드 차이점 분석
```bash
# 두 폴더 사이의 소스 코드 변경 사항 직접 비교, 루트 디렉토리(프로젝트 디렉토리)에서 실행
diff -ur ./lang_1_buggy/src/main/java ./lang_1_fixed/src/main/java
diff -u -r lang_1_buggy/src/main/java lang_1_fixed/src/main/java

```

### 방법 2: Defects4J 제공 패치(Patch) 파일 확인 (권장)
이미 프레임워크 내에 저장된 정답 패치를 통해 수정된 라인을 즉시 파악할 수 있습니다.
```bash
# Lang 1번 버그의 공식 수정 패치 열람
cat ~/llmszz_v1/defects4j/framework/projects/Lang/patches/1.src.patch
```
> **Tip**: `-`로 시작하는 라인이 삭제/수정된 버그 지점이며, 이 라인번호가 `git blame`의 타겟이 됩니다.

### 방법 3: 수정된 파일 목록만 추출
```bash
cd ./lang_1_buggy
defects4j export -p modified_files
```

---

## 5. BIC 추적 실습 (SZZ + LLM)

### 5.1 Git Blame으로 후보군 추출
패치에서 확인한 '문제의 라인'을 마지막으로 수정한 커밋 해시들을 수집합니다.
```bash
# 예: NumberUtils.java의 464~485 라인을 수정한 과거 이력 확인, 버그 디렉토리에 들어가서 실행
git blame -L 464,485 src/main/java/org/apache/commons/lang3/math/NumberUtils.java

```

### 5.2 LLM 검증 및 식별
추출한 **버그 리포트**, **수정된 코드(Patch)**, **후보 커밋들의 Diff**를 LLM에게 전달하여 최종 BIC를 지목하게 합니다.

---

## 💡 연구 메모
- **Java 버전**: 버전 충돌 시 `sudo update-alternatives --config java`로 8버전 선택.
- **BIC 검증**: LLM이 지목한 커밋 해시로 `git checkout` 한 뒤 `defects4j test`를 돌려 버그가 재현되는지 확인.



# 🚀 영남대 SE Lab BIC 연구용 도커 관리 치트시트


### 1. 현재 상태 세이브 (Snapshot)
#### 작업이 잘 돌아갈 때 현재 컨테이너(예시 3fe6ad420493)를 이미지로 저장합니다.
docker commit 3fe6ad420493 my_research_env:backup_v1


### 2. 저장된 이미지로 새 컨테이너 생성 (Restore / Clone)
#### -v 옵션으로 호스트의 연구 폴더를 반드시 연결해야 파일이 보입니다.
docker run -it --name research_java8_test \
  --gpus all \
  -v /data/cj/SE_Lab_BIC_Repo:/workspace/SE_Lab_BIC_Repo \
  my_research_env:working_backup /bin/bash


### 3. 컨테이너 일상 관리 (Start / Stop / Enter)
# ------------------------------------------
#### 중지된 컨테이너 다시 깨우기
docker start research_java8_test

#### 실행 중인 컨테이너 안으로 들어가기 (진입)
docker exec -it research_java8_test /bin/bash

#### 컨테이너 잠시 멈추기
docker stop research_java8_test

#### 현재 컨테이너들 상태 확인 (Up인지 Exited인지 확인)
docker ps -a


### 4. 삭제 및 청소 (Cleanup)
### ------------------------------------------
#### (주의!) 컨테이너를 삭제해도 -v로 연결된 호스트의 .py 파일들은 안전합니다.
docker rm research_java8_test    # 컨테이너 삭제
docker rmi my_research_env:backup_v1 # 이미지 삭제


### 💡 팁: 컨테이너 안에서 나올 때 (Exit)
### - exit 입력: 컨테이너가 중지됨 (다시 start 해줘야 함)
### - Ctrl + P 누른 뒤 Ctrl + Q: 컨테이너를 끄지 않고 "연결만 끊고" 나옴



# 해당 소스코드만 들고오기. 해당 부분은 컴파일과 빌드가 정상적으로 진행되었음

### 1. 다시 깨끗하게 초기화
git restore src/

### 2. 메인과 테스트를 모두 '동일한' 과거 시점으로 복구
git restore --source=5c2471f8 src/main/
git restore --source=5c2471f8 src/test/

### 3. 만약 아까처럼 TypeUtilsTest에서 제네릭 에러가 난다면, 
#### 에러가 나는 그 파일만 '현재 성공하는 버전'으로 살짝 되돌립니다.
git restore src/test/java/org/apache/commons/lang3/reflect/TypeUtilsTest.java

### 4. 컴파일 시도
defects4j compile

### 5. 앞전에 발생했던 클래스 한정 테스트 시도
#### 특정 클래스의 특정 메서드만 골라서 테스트합니다.
#### 이 테스트가 '실패'해야 해당 커밋에 버그가 들어있다는 뜻입니다.
defects4j test -t org.apache.commons.lang3.math.NumberUtilsTest::TestLang747