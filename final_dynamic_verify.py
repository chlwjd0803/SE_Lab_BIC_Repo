import subprocess
import os
import shutil

# 1. 경로 및 설정 (질문자님의 환경에 맞춤)
cwd_path = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
candidate_file = "bic_candidates.txt"
config_name = ".defects4j.config"
# 설정 파일을 안전하게 보관할 외부 임시 경로
backup_path = "/tmp/d4j_working_config_bak"

def run_command(cmd, cwd):
    """명령어를 실행하고 결과를 반환하는 헬퍼 함수"""
    return subprocess.run(cmd, shell=True, cwd=cwd, text=True, 
                          stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

# --- 준비 단계 ---
# A. 후보 리스트 읽기
if not os.path.exists(candidate_file):
    print(f"❌ 에러: {candidate_file} 파일이 없습니다. auto_check.py를 먼저 실행하세요.")
    exit(1)

with open(candidate_file, "r") as f:
    candidates = [line.strip() for line in f if line.strip()]

# B. 현재 정상적인 설정 파일 백업
original_config = os.path.join(cwd_path, config_name)
if os.path.exists(original_config):
    shutil.copy2(original_config, backup_path)
    print(f"✅ 설정 파일 백업 완료: {backup_path}")
else:
    print("❌ 에러: .defects4j.config 파일을 찾을 수 없습니다. checkout 상태를 확인하세요.")
    exit(1)

results = []

# --- 검증 루프 시작 ---
for h in candidates:
    print(f"\n" + "="*60)
    print(f"🚀 분석 중인 커밋: [{h}]")
    
    # 1. 과거 커밋으로 이동 (이 과정에서 .defects4j.config가 삭제됨)
    print(">> Git Checkout 실행 중...")
    run_command(f"git checkout -f {h}", cwd_path)
    
    # 2. [핵심] 삭제된 설정 파일 즉시 복구
    shutil.copy2(backup_path, original_config)
    print(">> Defects4J 설정 파일 복구 완료.")

    # 3. 빌드(Compile) 시도
    print(">> 프로젝트 빌드 중 (defects4j compile)...")
    compile_res = run_command("defects4j compile", cwd_path)
    
    if "OK" not in compile_res.stdout:
        print(f"⚠️ [빌드 실패] 커밋 {h}는 현재 환경에서 빌드할 수 없습니다.")
        results.append(f"{h}: BUILD_FAILED")
        continue

    # 4. 테스트(Test) 실행
    print(">> 버그 재현 테스트 중 (defects4j test)...")
    # 특정 테스트 클래스만 지정하여 속도 향상
    test_cmd = "defects4j test -t org.apache.commons.lang3.math.NumberUtilsTest"
    test_res = run_command(test_cmd, cwd_path)
    
    # 5. 결과 분석
    if "Failing tests: 0" in test_res.stdout:
        print(f"✅ [CLEAN] 이 커밋 시점에는 버그가 없습니다.")
        results.append(f"{h}: CLEAN (PASS)")
    elif "Failing tests:" in test_res.stdout:
        # 실패한 테스트 케이스 이름 추출
        fail_line = [l for l in test_res.stdout.split('\n') if " - " in l]
        fail_info = fail_line[0].strip() if fail_line else "Unknown Test"
        print(f"🚨 [BUG FOUND] 버그가 발견되었습니다! BIC일 가능성이 매우 높습니다.")
        print(f"   ㄴ 상세: {fail_info}")
        results.append(f"{h}: BUG_DETECTED ({fail_info})")
    else:
        print("❓ [알 수 없음] 테스트 로그 분석에 실패했습니다.")
        results.append(f"{h}: UNKNOWN_ERROR")

# --- 마무리 단계 ---
print("\n" + "="*60)
print("🏁 모든 검증이 완료되었습니다. 원래 상태로 복구합니다.")
run_command("git checkout master", cwd_path)
shutil.copy2(backup_path, original_config)

# 최종 리포트 출력
print("\n[ 최종 검증 리포트 ]")
for res in results:
    print(f" - {res}")