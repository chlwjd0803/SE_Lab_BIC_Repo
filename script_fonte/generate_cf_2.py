import subprocess
import os

def get_commit_hashes(class_name, line_num, project_path):
    """
    특정 클래스의 특정 라인에 대한 수정 이력(커밋 해시)을 추출합니다.
    """
    # 클래스 이름을 파일 경로로 변환 (예: org.abc.Utils -> src/main/java/org/abc/Utils.java)
    # Lang 프로젝트의 기본 소스 경로는 src/main/java입니다.
    file_path = os.path.join("src/main/java", class_name.replace(".", "/") + ".java")
    
    # git log -L <line>,<line>:<file> --pretty=format:"%H" 명령어 구성
    # -L 옵션은 해당 라인의 변경 이력만 추적합니다. 
    cmd = [
        "git", "log", 
        "-L", f"{line_num},{line_num}:{file_path}", 
        "--pretty=format:%H", 
        "--no-patch" # 로그 메시지나 패치 내용은 생략하고 해시만 가져옵니다.
    ]
    
    try:
        # 해당 프로젝트 폴더 내에서 명령어 실행
        result = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, check=True)
        hashes = result.stdout.strip().split('\n')
        return [h for h in hashes if h] # 빈 문자열 제거
    except subprocess.CalledProcessError:
        # 간혹 삭제된 라인이나 경로 문제로 에러가 날 수 있으므로 예외 처리
        return []

def generate_cf(ef_data, project_path):
    cf_set = set()
    total = len(ef_data)
    
    print(f"총 {total}개의 라인에 대해 커밋 이력 추적 시작...")
    
    for i, (class_name, line_num) in enumerate(ef_data):
        hashes = get_commit_hashes(class_name, line_num, project_path)
        cf_set.update(hashes)
        
        if (i + 1) % 50 == 0:
            print(f"진행률: {i+1}/{total} (현재까지 수집된 고유 커밋: {len(cf_set)}개)")
            
    return cf_set

if __name__ == "__main__":
    # 앞서 만든 extract_ef.py의 로직을 사용해 데이터를 가져왔다고 가정합니다.
    from extract_ef_1 import extract_failure_coverage
    
    PROJECT_DIR = "../lang_13_buggy" # 실제 프로젝트 경로
    EF_FILE = os.path.join(PROJECT_DIR, "coverage.xml")
    
    ef_list = extract_failure_coverage(EF_FILE)
    cf_results = generate_cf(ef_list, PROJECT_DIR)
    
    print("\n--- Stage 1 결과 ---")
    print(f"추출된 실패 관련 커밋(Cf) 수: {len(cf_results)}개")
    
    # 결과를 파일로 저장
    with open(PROJECT_DIR + "/cf_commits.txt", "w") as f:
        for commit_hash in sorted(list(cf_results)):
            f.write(commit_hash + "\n")
    print("결과가 cf_commits.txt에 저장되었습니다.")