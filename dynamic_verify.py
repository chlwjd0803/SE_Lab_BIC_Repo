import subprocess
import os
import shutil

# 1. 설정
cwd_path = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
candidate_file = "bic_candidates.txt"
config_file = ".defects4j.config"
config_path = os.path.join(cwd_path, config_file)
backup_config = "/tmp/.defects4j.config.bak"

if not os.path.exists(candidate_file):
    print(f"에러: {candidate_file} 파일이 없습니다.")
    exit(1)

# 중요한 설정 파일 미리 백업
if os.path.exists(config_path):
    shutil.copy2(config_path, backup_config)
    print(">> 중요 설정 파일을 백업했습니다.")

with open(candidate_file, "r") as f:
    candidates = [line.strip() for line in f if line.strip()]

final_bic = None

# 2. 검증 루프
for h in candidates:
    print(f"\n" + "="*40)
    print(f"--- 분석 중인 커밋: [{h}] ---")
    
    try:
        # A. 과거로 이동 (강제 이동)
        subprocess.run(f"git checkout -f {h}", shell=True, cwd=cwd_path, check=True, capture_output=True)
        
        # B. 설정 파일 복구 (이게 핵심!)
        if os.path.exists(backup_config):
            shutil.copy2(backup_config, config_path)
            print(">> 설정 파일을 복구했습니다.")

        # C. 컴파일 및 테스트
        print(f">> 빌드 및 테스트 시작...")
        subprocess.run("defects4j compile", shell=True, cwd=cwd_path, check=True, capture_output=True)
        
        # 테스트 명령어를 단순화하여 범용성을 높임
        test_cmd = "defects4j test" 
        test_result = subprocess.run(test_cmd, shell=True, cwd=cwd_path, text=True, capture_output=True)
        
        if "Failing tests: 0" in test_result.stdout:
            print(f">> 결과: [정상] 버그 없음")
        elif "Failing tests:" in test_result.stdout:
            print(f">> 결과: [발견!!] 테스트 실패 (버그 존재 시점)")
            final_bic = h
        else:
            print(f">> 주의: 결과를 알 수 없음. 로그 확인 필요.")

    except subprocess.CalledProcessError as e:
        print(f">> 에러 발생: {e.stderr.decode() if e.stderr else 'Unknown error'}")

# 원상 복구
subprocess.run("git checkout master", shell=True, cwd=cwd_path, capture_output=True)
if os.path.exists(backup_config):
    shutil.copy2(backup_config, config_path)

print("\n검증 프로세스가 종료되었습니다.")