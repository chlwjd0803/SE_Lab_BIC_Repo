import os

def run_simulation(target_hash):
    """
    ranking_results.txt 파일을 읽어 표준/가중 이분 탐색을 비교합니다.
    """
    if not os.path.exists("ranking_results.txt"):
        print("에러: ranking_results.txt 파일이 없습니다. rank_commits_4.py를 먼저 실행하세요.")
        return

    # 1. 파일에서 데이터 읽기
    ranked_commits = []
    with open("ranking_results.txt", "r") as f:
        for line in f:
            if ',' in line:
                h, s = line.strip().split(',')
                ranked_commits.append((h, float(s)))

    hashes = [c[0] for c in ranked_commits]
    scores = [c[1] for c in ranked_commits]
    
    # 2. 실제 BIC 인덱스 찾기
    target_idx = -1
    for i, h in enumerate(hashes):
        if h.startswith(target_hash):
            target_idx = i
            break

    if target_idx == -1:
        print(f"경고: 후보 리스트에서 타겟 BIC({target_hash})를 찾을 수 없습니다.")
        return

    def bisection_logic(is_weighted):
        bad = 0 # 최신 (실패)
        good = len(hashes) # 과거 (성공)
        steps = 0
        
        while good > bad + 1:
            steps += 1
            if is_weighted:
                # 가중 방식: 구간 내 점수 합의 균형점 찾기
                min_diff = float('inf')
                pivot = bad + 1
                for i in range(bad + 1, good):
                    left_sum = sum(scores[bad:i])
                    right_sum = sum(scores[i:good])
                    diff = abs(left_sum - right_sum)
                    if diff < min_diff:
                        min_diff = diff
                        pivot = i
            else:
                pivot = (bad + good) // 2

            # 시뮬레이션: 타겟보다 같거나 앞(최신)이면 Bad
            is_bad = pivot <= target_idx
            if is_bad:
                bad = pivot
            else:
                good = pivot
        return steps

    # 3. 결과 출력
    std = bisection_logic(is_weighted=False)
    weighted = bisection_logic(is_weighted=True)

    print(f"\n[실험 대상 BIC: {target_hash}]")
    print(f"- 후보 커밋 수: {len(hashes)}개")
    print(f"- 실제 BIC 위치: {target_idx + 1}위")
    print("-" * 30)
    print(f"표준 이분 탐색 횟수: {std}회")
    print(f"가중 이분 탐색 횟수: {weighted}회")
    print(f"절약된 횟수: {std - weighted}회")

if __name__ == "__main__":
    # Lang-13의 경우 '01ab63a' 입력
    target = input("찾으려는 실제 BIC 해시(앞 7자리)를 입력하세요: ")
    run_simulation(target)