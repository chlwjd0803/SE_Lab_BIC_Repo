import subprocess
import os

def get_commit_order(project_path, candidate_hashes):
    """
    후보 커밋들의 최신순 정렬 순서를 가져옵니다.
    """
    cmd = ["git", "log", "--pretty=format:%H"]
    result = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True)
    all_commits = result.stdout.strip().split('\n')
    
    # 후보 커밋들만 필터링하여 최신순 유지
    ordered_candidates = [h for h in all_commits if h in candidate_hashes]
    return ordered_candidates

def calculate_stage3(ef_data, project_path, candidate_hashes):
    # 1. 커밋 순서 파악 (최신순)
    ordered_commits = get_commit_order(project_path, candidate_hashes)
    commit_to_rank = {h: i for i, h in enumerate(ordered_commits)}
    
    # 2. 라인별 수정 커밋 맵 생성 (Stage 1 결과 활용)
    # 실제로는 generate_cf 단계에서 이 매핑을 저장해두는 것이 좋습니다.
    line_to_commits = {}
    from generate_cf_2 import get_commit_hashes # 이전 단계 함수 재사용
    
    print("각 라인별 수정 이력 재분석 중...")
    for class_name, line_num in ef_data:
        hashes = get_commit_hashes(class_name, line_num, project_path)
        # 44개 후보군에 포함된 커밋만 남김
        valid_hashes = [h for h in hashes if h in candidate_hashes]
        line_to_commits[(class_name, line_num)] = sorted(valid_hashes, key=lambda x: commit_to_rank[x])

    # 3. 점수 계산 (Equal Vote + Decay lambda=0.1)
    decay_lambda = 0.1
    commit_scores = {h: 0.0 for h in candidate_hashes}
    
    for (cls, line), hashes in line_to_commits.items():
        for depth, h in enumerate(hashes):
            # 공식: score += 1 * (1 - lambda)^depth
            score = 1.0 * ((1 - decay_lambda) ** depth)
            commit_scores[h] += score

    # 4. 결과 정렬
    ranked_commits = sorted(commit_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_commits

if __name__ == "__main__":
    from extract_ef_1 import extract_failure_coverage
    
    PROJECT_DIR = "../lang_13_buggy"
    with open(PROJECT_DIR + "/cf_commits.txt", "r") as f:
        candidate_hashes = set(line.strip() for line in f if line.strip())
    
    ef_list = extract_failure_coverage(os.path.join(PROJECT_DIR, "coverage.xml"))
    final_ranking = calculate_stage3(ef_list, PROJECT_DIR, candidate_hashes)
    
    print("\n--- Stage 3: FONTE 최종 랭킹 결과 ---")
    for rank, (commit_hash, score) in enumerate(final_ranking[:10], 1):
        print(f"순위 {rank}: {commit_hash} (점수: {score:.4f})")


    with open("ranking_results.txt", "w") as f:
        for commit_hash, score in final_ranking:
            f.write(f"{commit_hash},{score}\n")
            
    print("\n--- Stage 3 결과가 ranking_results.txt에 저장되었습니다. ---")