#!/bin/bash
# 
# MAESTRO 연구 프로젝트 "총사령관" 마스터 스크립트
#
# 이 스크립트는 HumanEval 벤치마크 (50개)를 순차적으로 실행합니다.
#
# [실행 전제 조건]
# 1. 'config.yml'의 llm_provider가 'openai'로 설정되어 있어야 합니다.
# 2. 터미널에서 "필수 의식"이 먼저 수행되어야 합니다.
#
# [실행 방법 (Git Bash 또는 WSL)]
# $ ./run_experiment.sh

# --- 설정 ---

# 1. 스크립트가 오류를 만나면 즉시 중단
set -eu

# 2. 핵심 파일 및 고정 출력 폴더
CONFIG_FILE="config.yml"
RESULTS_BASE_DIR="results/outputs" # 고정된 '깔끔한' 출력 폴더

# 3. HumanEval 설정
HE_BENCHMARK_DIR="data/benchmark/HumanEval"
HE_TASKS_START=0
HE_TASKS_END=49 # 50개 (0번부터 49번까지)


echo "===== MAESTRO 마스터 스크립트 시작 ====="
echo "Config 파일: $CONFIG_FILE"
echo "결과물 저장 위치: $RESULTS_BASE_DIR"
echo "========================================"


# --- HumanEval 실험 루프 ---
echo ""
echo "===== HumanEval (Tasks ${HE_TASKS_START}-${HE_TASKS_END}) 시작 ====="

for i in $(seq ${HE_TASKS_START} ${HE_TASKS_END}); do
    
    PROBLEM_ID="HumanEval/${i}"
    echo ""
    echo "--- [HumanEval ${i}] 처리 시작 ---"

    # 입/출력 경로 정의
    INPUT_CODE_PATH="${HE_BENCHMARK_DIR}/${i}/prompt.txt"
    UNIT_TEST_PATH="${HE_BENCHMARK_DIR}/${i}/test.py"

    OUTPUT_B_DIR="${RESULTS_BASE_DIR}/HumanEval/${i}/B"
    OUTPUT_C_DIR="${RESULTS_BASE_DIR}/HumanEval/${i}/C"
    OUTPUT_D_DIR="${RESULTS_BASE_DIR}/HumanEval/${i}/D"
    OUTPUT_E_DIR="${RESULTS_BASE_DIR}/HumanEval/${i}/E"

    # 결과물 폴더 생성
    mkdir -p "$OUTPUT_B_DIR" "$OUTPUT_C_DIR" "$OUTPUT_D_DIR" "$OUTPUT_E_DIR"

    # Group B (Baseline) 실행
    echo "[HE ${i}] Group B 실행 중..."
    python experiment/baselines/run_group_b.py \
        --config "$CONFIG_FILE" \
        --input_code "$INPUT_CODE_PATH" \
        --output_dir "$OUTPUT_B_DIR"

    # Group C (RuleBased) 실행
    echo "[HE ${i}] Group C 실행 중..."
    python experiment/ablations/run_group_c.py \
        --config "$CONFIG_FILE" \
        --input_code "$INPUT_CODE_PATH" \
        --unit_tests "$UNIT_TEST_PATH" \
        --output_dir "$OUTPUT_C_DIR"
        
    # Group E (No Retrospection) 실행
    echo "[HE ${i}] Group E 실행 중..."
    python experiment/ablations/run_group_e.py \
        --config "$CONFIG_FILE" \
        --input_code "$INPUT_CODE_PATH" \
        --unit_tests "$UNIT_TEST_PATH" \
        --output_dir "$OUTPUT_E_DIR"

    # Group D (MAESTRO - Full) 실행
    echo "[HE ${i}] Group D 실행 중..."
    python experiment/ablations/run_group_d.py \
        --config "$CONFIG_FILE" \
        --input_code "$INPUT_CODE_PATH" \
        --unit_tests "$UNIT_TEST_PATH" \
        --output_dir "$OUTPUT_D_DIR"

    echo "--- [HumanEval ${i}] 처리 완료 ---"
    sleep 1 # API 호출 간 과부하 방지를 위한 1초 대기
done

echo "===== HumanEval 종료 ====="

echo ""
echo "===== 모든 HumanEval 문제가 처리되었습니다. ====="
echo "최종 결과물은 ${RESULTS_BASE_DIR}/HumanEval 폴더에 저장되었습니다."
echo "===== MAESTRO 마스터 스크립트 종료 ====="