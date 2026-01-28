import subprocess
import os

# 임시 파일을 저장할 디렉토리 생성
TEMP_DIR = "./temp_ast"
os.makedirs(TEMP_DIR, exist_ok=True)

def run_command(cmd, cwd="."):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def is_style_change(commit_hash, project_path):
    """
    해당 커밋이 스타일 변경만 포함하는지 GumTree로 검사합니다.
    """
    # 1. 커밋에서 수정된 자바 파일 목록 가져오기
    cmd_files = ["git", "show", "--name-only", "--pretty=format:", commit_hash]
    files = run_command(cmd_files, project_path).stdout.strip().split('\n')
    java_files = [f for f in files if f.endswith(".java")]

    if not java_files:
        return False # 자바 파일 수정이 없으면 일단 유지

    for file_path in java_files:
        prev_file = os.path.join(TEMP_DIR, "prev.java")
        curr_file = os.path.join(TEMP_DIR, "curr.java")

        # 2. 커밋 전/후 파일 추출
        try:
            with open(prev_file, "w") as f:
                f.write(run_command(["git", "show", f"{commit_hash}^:{file_path}"], project_path).stdout)
            with open(curr_file, "w") as f:
                f.write(run_command(["git", "show", f"{commit_hash}:{file_path}"], project_path).stdout)
        except:
            return False # 파일 추출 실패 시 안전하게 후보로 유지

        # 3. GumTree textdiff 실행 (AST Isomorphism Test)
        # 결과가 없으면(empty) 두 트리가 구조적으로 동일하다는 뜻입니다.
        gumtree_cmd = ["gumtree", "textdiff", prev_file, curr_file]
        result = run_command(gumtree_cmd).stdout.strip()

        if result != "": # 하나라도 구조적 차이가 있으면 스타일 변경이 아님
            return False

    return True # 모든 파일의 AST가 동일하면 스타일 변경임

def main():
    PROJECT_DIR = "../lang_13_buggy" # 실제 프로젝트 경로
    with open(PROJECT_DIR + "/cf_commits.txt", "r") as f:
        commits = [line.strip() for line in f if line.strip()]

    print(f"총 {len(commits)}개의 커밋에 대해 Stage 2 필터링 시작...")
    
    final_candidates = []
    style_changes_count = 0

    for i, h in enumerate(commits):
        if is_style_change(h, PROJECT_DIR):
            style_changes_count += 1
        else:
            final_candidates.append(h)
        
        if (i + 1) % 10 == 0:
            print(f"진행 중: {i+1}/{len(commits)} (필터링된 스타일 변경: {style_changes_count})")

    print(f"\n--- Stage 2 결과 ---")
    print(f"제거된 스타일 변경 커밋: {style_changes_count}개")
    print(f"최종 남은 BIC 후보 커밋: {len(final_candidates)}개")

    with open(PROJECT_DIR + "/final_bic_candidates.txt", "w") as f:
        for h in final_candidates:
            f.write(h + "\n")

if __name__ == "__main__":
    main()