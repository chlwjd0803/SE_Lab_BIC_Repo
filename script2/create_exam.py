import pandas as pd
import os
import subprocess

# 1. 경로 설정
BIC_CSV_PATH = "../fonte/data/Defects4J/BIC_dataset/combined.csv"
CORE_DATA_DIR = "../fonte/data/Defects4J/core/"

def create_prompt(project_name, bug_id):
    try:
        df = pd.read_csv(BIC_CSV_PATH)
        df['pid'] = df['pid'].str.strip()
        df['vid'] = df['vid'].astype(str).str.strip()
        target = df[(df['pid'].str.lower() == project_name.lower()) & (df['vid'] == str(bug_id))]
    except Exception as e:
        print(f"❌ CSV Error: {e}"); return

    if target.empty:
        print(f"❌ {project_name}-{bug_id} not found in CSV."); return
    
    true_bic = target.iloc[0]['commit']
    
    # 2. 로그를 가져올 폴더 확인
    folder_path = os.path.join(CORE_DATA_DIR, f"{project_name}-{bug_id}b")
    
    # 만약 폴더가 Git 저장소가 아니라면? (실험 환경 체크)
    if not os.path.exists(os.path.join(folder_path, ".git")):
        print(f"⚠️ Warning: {folder_path} is not a git repository.")
        print("Please run 'defects4j checkout' for this bug first.")
        commit_data = "[Error] This directory is not initialized as a git repo."
    else:
        # 정답 커밋을 포함한 주변 로그 20개 추출
        cmd = f"git log {true_bic} -n 20 --pretty=format:'%H : %s'"
        try:
            commit_data = subprocess.check_output(cmd, shell=True, cwd=folder_path, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as e:
            commit_data = f"[Git Error] {e.output.decode('utf-8')}"

    # 3. Llama 3 전용 영어 프롬프트
    prompt = f"""
==================== [BIC Detection Task] ====================
Role: Expert Software Engineer
Project: {project_name} (Bug ID: {bug_id})

[Task] Identify the Bug-Introducing Commit (BIC).
[Commit History]
{commit_data}

[Format]
BIC Hash: <hash>
Reason: <brief reasoning>
============================================================
"""

    file_name = f"exam_{project_name}_{bug_id}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(prompt)
        f.write(f"\n\n--- [GROUND TRUTH] ---\n{true_bic}\n")
    
    print(f"✅ Exam file updated: {file_name}")

if __name__ == "__main__":
    create_prompt("Lang", "55")