import subprocess
import os
import shutil

# 1. 경로 설정
cwd_path = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
candidate_file = "bic_candidates.txt"
config_name = ".defects4j.config"
backup_path = "/tmp/d4j_safe_config"

# 설정 파일 백업
if os.path.exists(os.path.join(cwd_path, config_name)):
    shutil.copy2(os.path.join(cwd_path, config_name), backup_path)

with open(candidate_file, "r") as f:
    candidates = [line.strip() for line in f if line.strip()]

for h in candidates:
    print(f"\n" + "="*50)
    print(f"--- 분석 중: [{h}] ---")
    
    # 과거 여행
    subprocess.run(f"git checkout -f {h}", shell=True, cwd=cwd_path, capture_output=True)
    shutil.copy2(backup_path, os.path.join(cwd_path, config_name))

    # [수정] 컴파일 단계부터 로그를 확인해봅니다. 컴파일이 안 되면 테스트도 안 돌거든요.
    print(">> 빌드 시도 중...")
    # stderr=subprocess.STDOUT 를 써서 에러 메시지도 일반 출력으로 합칩니다.
    compile_res = subprocess.run("defects4j compile", shell=True, cwd=cwd_path, 
                                 text=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    
    if "OK" not in compile_res.stdout:
        print(">> [경고] 빌드 실패! 에러 로그:")
        print(compile_res.stdout)
        continue # 빌드 실패하면 다음 커밋으로

    print(">> 테스트 실행 중...")
    test_cmd = "defects4j test -t org.apache.commons.lang3.math.NumberUtilsTest"
    test_res = subprocess.run(test_cmd, shell=True, cwd=cwd_path, 
                               text=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    
    # 결과가 무엇이든 일단 출력해봅니다.
    print("-" * 30)
    if "Failing tests: 0" in test_res.stdout:
        print(">> 결과: [PASS] 버그 없음")
    elif "Failing tests:" in test_res.stdout:
        print(">> 결과: [FAIL] 버그 발견!")
        print(test_res.stdout.strip().splitlines()[-1]) # 마지막 한 줄(결과 요약)
    else:
        print(">> [특이사항] 전체 로그 출력:")
        print(test_res.stdout if test_res.stdout else "로그가 정말로 비어있습니다.")
    print("-" * 30)

# 마무리
subprocess.run("git checkout master", shell=True, cwd=cwd_path, capture_output=True)
shutil.copy2(backup_path, os.path.join(cwd_path, config_name))