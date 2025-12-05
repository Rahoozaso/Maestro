import os
import json
import argparse
import pandas as pd
import glob
import sys

def find_latest_run_dir(base_path="results/swe_outputs"):
    """가장 최근에 실행된 실험 폴더를 찾습니다."""
    if not os.path.exists(base_path):
        return None
    dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not dirs:
        return None
    return max(dirs, key=os.path.getmtime)

def load_data(run_dir):
    """결과 폴더를 순회하며 모든 final_report.json을 읽어옵니다."""
    data = []
    print(f"📂 분석 대상 폴더: {run_dir}")
    
    # 폴더 구조: run_dir / task_id / group / final_report.json
    report_files = glob.glob(os.path.join(run_dir, "*", "*", "final_report.json"))
    
    print(f"🔍 총 {len(report_files)}개의 리포트 파일을 찾았습니다.")

    for file_path in report_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            
            path_parts = file_path.split(os.sep)
            # 경로에서 정보 추출 (OS마다 구분자 다를 수 있음)
            group = path_parts[-2] # 폴더명이 그룹명 (B, C, D, E)
            task_id = path_parts[-3]
            
            # 데이터 추출
            nfr_score = report.get("quality_analysis", {}).get("total_score", 0)
            
            # 기능 성공 여부
            func_analysis = report.get("functional_analysis", {})
            is_success = func_analysis.get("success", False)
            
            # 비용
            cost = report.get("cost_analysis", {}).get("estimated_cost_usd", 0.0)
            
            # Maestro Score (기능 실패 시 0점)
            maestro_score = report.get("maestro_score", 0)
            if "maestro_score" not in report:
                # 구버전 호환성
                maestro_score = nfr_score if is_success else 0

            data.append({
                "Task": task_id,
                "Group": group,
                "Pass": 1 if is_success else 0,
                "NFR_Score": nfr_score,
                "Maestro_Score": maestro_score,
                "Cost($)": cost
            })
            
        except Exception as e:
            print(f"⚠️ 파일 읽기 오류 ({file_path}): {e}")

    return pd.DataFrame(data)

def print_summary(df):
    if df.empty:
        print("❌ 데이터가 없습니다.")
        return

    # 그룹 순서 정렬 (A는 없으므로 B, C, E, D 순)
    groups = ["B", "C", "E", "D"]
    
    print("\n" + "="*60)
    print(" 📊 MAESTRO 실험 결과 요약 (Summary Statistics)")
    print("="*60)

    # 1. 그룹별 평균 통계
    summary = df.groupby("Group").agg({
        "Pass": ["mean", "sum", "count"], # 성공률, 성공수, 전체수
        "NFR_Score": "mean",
        "Maestro_Score": "mean",
        "Cost($)": "mean"
    }).reindex(groups)
    
    # 컬럼명 정리
    summary.columns = ["Pass Rate", "Pass Count", "Total", "Avg NFR", "Avg Maestro", "Avg Cost"]
    summary["Pass Rate"] = summary["Pass Rate"] * 100 # 백분율 변환
    
    print(summary.round(2).to_string())
    print("-" * 60)

    # 2. 가설 검증 (Hypothesis Check)
    print("\n[🧪 가설 검증 데이터]")
    
    try:
        score_b = summary.loc["B", "Avg Maestro"]
        score_c = summary.loc["C", "Avg Maestro"]
        score_d = summary.loc["D", "Avg Maestro"]
        pass_b = summary.loc["B", "Pass Rate"]
        pass_d = summary.loc["D", "Pass Rate"]
        cost_b = summary.loc["B", "Avg Cost"]
        cost_d = summary.loc["D", "Avg Cost"]

        print(f"1. RQ1 (품질 향상): Group D vs B")
        print(f"   - Maestro Score: {score_d:.2f} vs {score_b:.2f} (Delta: {score_d - score_b:+.2f})")
        print(f"   - Pass Rate:     {pass_d:.1f}% vs {pass_b:.1f}% (Delta: {pass_d - pass_b:+.1f}%)")
        
        print(f"\n2. RQ3 (아키텍트 효과): Group D vs C")
        print(f"   - Maestro Score: {score_d:.2f} vs {score_c:.2f} (Delta: {score_d - score_c:+.2f})")
        print(f"   - 해석: {'D가 규칙 기반 C보다 우수함' if score_d > score_c else 'C가 더 높음 (가설 기각)'}")

        print(f"\n3. RQ2 (비용 효율성): Group D vs B")
        print(f"   - Cost: ${cost_d:.4f} vs ${cost_b:.4f} (Factor: {cost_d/cost_b:.1f}x)")
        print(f"   - 비용은 늘었지만 점수가 올랐는가? {'YES' if score_d > score_b else 'NO'}")

    except KeyError:
        print("⚠️ 일부 그룹 데이터가 부족하여 가설 검증을 수행할 수 없습니다.")

    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Analyze MAESTRO Experiment Results")
    parser.add_argument("--dir", type=str, help="Specific run directory to analyze (default: latest)")
    args = parser.parse_args()

    run_dir = args.dir if args.dir else find_latest_run_dir()
    
    if not run_dir:
        print("❌ 분석할 실험 결과 폴더를 찾을 수 없습니다.")
        return

    df = load_data(run_dir)
    print_summary(df)
    
    # CSV 저장
    output_csv = os.path.join(run_dir, "analysis_summary.csv")
    df.to_csv(output_csv, index=False)
    print(f"\n💾 상세 데이터 저장됨: {output_csv}")

if __name__ == "__main__":
    main()
