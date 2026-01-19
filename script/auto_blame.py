import subprocess

# 1. 실행할 명령어
command = "git blame -L 464,475 src/main/java/org/apache/commons/lang3/math/NumberUtils.java"
cwd_path = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"

# 2. 명령어 실행 및 결과 가져오기
result = subprocess.check_output(command, shell=True, text=True, cwd=cwd_path)

# 3. 결과 분석 (각 줄에서 첫 번째 단어인 '해시값'만 추출)
lines = result.strip().split('\n')
commit_hashes = set() # 중복을 없애기 위해 set을 사용합니다.

for line in lines:
    parts = line.split()
    if parts:
        commit_hashes.add(parts[0])

# 4. 결과 확인
unique_hashes = list(commit_hashes)
print("--- 찾아낸 범인 후보 리스트 ---")
print(unique_hashes)