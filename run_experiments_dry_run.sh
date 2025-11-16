#!/bin/bash
#
# MAESTRO Dry Run 스크립트
# - HumanEval 벤치마크의 첫 번째 문제 하나만 실행합니다.
# - config.yml의 provider가 "mock"인지 확인하세요. (비용 0원)

# 오류 발생 시 즉시 스크립트 종료
set -e

# --- ⭐️ 수정된 부분: PYTHONPATH 설정 ---
# 'src' 폴더를 Python 검색 경로에 추가하여 'maestro' 모듈을 찾을 수 있도록 함
export PYTHONPATH="${PYTHONPATH}:."
# ------------------------------------

# --- 설정 변수 ---
BENCHMARK_BASE_DIR="./data/benchmark"
OUTPUT_BASE_DIR="./results/outputs"
CONFIG_FILE="config.yml"
MAESTRO_MAIN_SCRIPT="maestro.core.main_controller" 
GROUP_B_SCRIPT="scripts.run_group_b"         
# ---------------------------------------

# 사용할 SOTA 생성 프레임워크 (Dry Run에서는 이름만 사용됨)
SOTA_GENERATOR_NAME=${1:-"MetaGPT_DryRun"}

# --- 로그 및 출력 디렉토리 생성 ---
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_OUTPUT_DIR="${OUTPUT_BASE_DIR}/run_SINGLE_DRYRUN_${SOTA_GENERATOR_NAME}_${TIMESTAMP}" # Single Dry Run 표시 추가
mkdir -p "${RUN_OUTPUT_DIR}"
echo "Single Dry Run 결과를 다음 디렉토리에 저장합니다: ${RUN_OUTPUT_DIR}"

# Dry Run이므로 실제 config.yml을 복사하는 대신, 어떤 config를 사용했는지 기록
echo "Using config file: ${CONFIG_FILE}" > "${RUN_OUTPUT_DIR}/config_used.log"


# --- 벤치마크 목록 ---
# Dry Run을 위해 첫 번째 벤치마크만 사용 (HumanEval 우선)
BENCHMARKS=("HumanEval") # SWE-bench 제외
FIRST_BENCHMARK=${BENCHMARKS[0]} # 첫 번째 벤치마크 이름 가져오기

# --- 메인 실행 로직 ---
BENCHMARK_NAME=$FIRST_BENCHMARK
BENCHMARK_DIR="${BENCHMARK_BASE_DIR}/${BENCHMARK_NAME}"
echo "================================================="
echo "벤치마크 시작 (Single Dry Run): ${BENCHMARK_NAME}"
echo "================================================="

# --- 첫 번째 문제 폴더만 찾아서 처리 ---
FIRST_PROBLEM_DIR=$(find "${BENCHMARK_DIR}" -mindepth 1 -maxdepth 1 -type d | sort | head -n 1)

if [[ -z "${FIRST_PROBLEM_DIR}" ]]; then
    echo "[오류] ${BENCHMARK_NAME} 벤치마크에서 문제 폴더를 찾을 수 없습니다."
    echo "데이터 준비 3단계(prepare_humaneval.py 실행)가 완료되었는지 확인하세요."
    exit 1
fi

PROBLEM_DIR=$FIRST_PROBLEM_DIR
# ----------------------------------------------------
PROBLEM_ID=$(basename "${PROBLEM_DIR}")
PROBLEM_OUTPUT_DIR="${RUN_OUTPUT_DIR}/${BENCHMARK_NAME}/${PROBLEM_ID}"
mkdir -p "${PROBLEM_OUTPUT_DIR}"

echo "--- 문제 처리 시작 (Single Dry Run): ${BENCHMARK_NAME} / ${PROBLEM_ID} ---"

# --- 1단계: SOTA 프레임워크로 v_gen 생성 (Group A) ---
V_GEN_CODE_PATH="${PROBLEM_OUTPUT_DIR}/v_gen.py"
# Dry Run을 위해 HumanEval/0 문제의 실제 테스트 파일 경로를 사용
V_GEN_TEST_PATH="${PROBLEM_DIR}/test.py"

echo "  [Group A] v_gen 생성 중 (Placeholder)..."
# !!! 중요: 실제 Group A 실행 명령어를 채워넣어야 합니다 !!!
# Dry Run을 위해, HumanEval/0의 프롬프트 파일을 읽어 임시 v_gen.py 생성
if [[ -f "${PROBLEM_DIR}/prompt.txt" ]]; then
    cp "${PROBLEM_DIR}/prompt.txt" "${V_GEN_CODE_PATH}"
    echo "  [Group A] ${PROBLEM_DIR}/prompt.txt 를 임시 v_gen.py로 복사했습니다."
else
    echo "  [경고] ${PROBLEM_DIR}/prompt.txt 를 찾을 수 없습니다. 임시 파일을 생성합니다."
    echo "# Placeholder for ${SOTA_GENERATOR_NAME} execution" > "${V_GEN_CODE_PATH}"
fi

# 실제 테스트 파일이 존재하는지 확인
if [[ ! -f "${V_GEN_TEST_PATH}" ]]; then
     echo "  [오류] 테스트 파일(${V_GEN_TEST_PATH})을 찾을 수 없습니다. 데이터 준비 3단계를 확인하세요."
     echo "Failed to find test file for ${PROBLEM_ID}" >> "${RUN_OUTPUT_DIR}/error_log.txt"
     exit 1 # Dry Run 실패로 종료
fi
echo "  [Group A] v_gen 생성 완료 (Placeholder): ${V_GEN_CODE_PATH}"


# --- Group B 실행 ---
GROUP_B_OUTPUT_DIR="${PROBLEM_OUTPUT_DIR}/GroupB_SimpleLLM"
mkdir -p "${GROUP_B_OUTPUT_DIR}"
echo "  [Group B] 단일 LLM 개선 실행 중..."
python -m ${GROUP_B_SCRIPT} \
    --config "${CONFIG_FILE}" \
    --input_code "${V_GEN_CODE_PATH}" \
    --output_dir "${GROUP_B_OUTPUT_DIR}" \
    > "${GROUP_B_OUTPUT_DIR}/run.log" 2>&1 || echo "  [경고] Group B 실행 중 오류 발생. 로그 확인: ${GROUP_B_OUTPUT_DIR}/run.log"
echo "  [Group B] 실행 완료."

# --- Group C 실행 ---
GROUP_C_OUTPUT_DIR="${PROBLEM_OUTPUT_DIR}/GroupC_RuleBased"
mkdir -p "${GROUP_C_OUTPUT_DIR}"
echo "  [Group C] 규칙 기반 MAESTRO 실행 중..."
python -m ${MAESTRO_MAIN_SCRIPT} \
    --config "${CONFIG_FILE}" \
    --input_code "${V_GEN_CODE_PATH}" \
    --unit_tests "${V_GEN_TEST_PATH}" \
    --output_dir "${GROUP_C_OUTPUT_DIR}" \
    --architect_mode "RuleBased" \
    > "${GROUP_C_OUTPUT_DIR}/run.log" 2>&1 || echo "  [경고] Group C 실행 중 오류 발생. 로그 확인: ${GROUP_C_OUTPUT_DIR}/run.log"
echo "  [Group C] 실행 완료."

# --- Group D 실행 (MAESTRO 기본 모드) ---
GROUP_D_OUTPUT_DIR="${PROBLEM_OUTPUT_DIR}/GroupD_MAESTRO_CoT"
mkdir -p "${GROUP_D_OUTPUT_DIR}"
echo "  [Group D] MAESTRO (CoT + 회고) 실행 중..."
python -m ${MAESTRO_MAIN_SCRIPT} \
    --config "${CONFIG_FILE}" \
    --input_code "${V_GEN_CODE_PATH}" \
    --unit_tests "${V_GEN_TEST_PATH}" \
    --output_dir "${GROUP_D_OUTPUT_DIR}" \
    --architect_mode "CoT" \
    --enable_retrospection \
    > "${GROUP_D_OUTPUT_DIR}/run.log" 2>&1 || echo "  [경고] Group D 실행 중 오류 발생. 로그 확인: ${GROUP_D_OUTPUT_DIR}/run.log"
echo "  [Group D] 실행 완료."

# --- Group E 실행 ---
GROUP_E_OUTPUT_DIR="${PROBLEM_OUTPUT_DIR}/GroupE_NoRetro"
mkdir -p "${GROUP_E_OUTPUT_DIR}"
echo "  [Group E] 자기 회고 없는 MAESTRO 실행 중..."
python -m ${MAESTRO_MAIN_SCRIPT} \
    --config "${CONFIG_FILE}" \
    --input_code "${V_GEN_CODE_PATH}" \
    --unit_tests "${V_GEN_TEST_PATH}" \
    --output_dir "${GROUP_E_OUTPUT_DIR}" \
    --architect_mode "CoT" \
    --disable_retrospection \
    > "${GROUP_E_OUTPUT_DIR}/run.log" 2>&1 || echo "  [경고] Group E 실행 중 오류 발생. 로그 확인: ${GROUP_E_OUTPUT_DIR}/run.log"
echo "  [Group E] 실행 완료."

echo "--- 문제 처리 완료 (Single Dry Run): ${BENCHMARK_NAME} / ${PROBLEM_ID} ---"
echo ""

echo "================================================="
echo "벤치마크 완료 (Single Dry Run): ${BENCHMARK_NAME}"
echo "================================================="
echo ""

echo "Single Dry Run이 완료되었습니다. 결과는 ${RUN_OUTPUT_DIR} 에서 확인하세요."