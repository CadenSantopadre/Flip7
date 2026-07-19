import argparse
import csv
import math
import os

import matplotlib
from cycler import cycler
matplotlib.use("Agg") #Trust me we need this, otherwise it looks really really bad - It's non interactive since we don't need to move around the graphs
import matplotlib.pyplot as plt
plt.rcParams['axes.prop_cycle'] = cycler(color=plt.colormaps['tab20'].colors)


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_float(x, default=None): #We need these to convert strings to floats and ints
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def to_int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def analyze_custom_lag_performance(rows): #Look at win rate, bust rate, runnning value over k rounds
    data = []
    for r in rows:
        k = to_int(r["draw_number_k"])
        samples = to_int(r["samples"])
        win_rate = to_float(r["win_rate"])
        mean_v = to_float(r["mean_running_value"])
        std_v = to_float(r["std_running_value"])
        bust_rate = to_float(r["bust_rate_at_k"])
        data.append((k, samples, win_rate, mean_v, std_v, bust_rate))
    data.sort()

    print("\n=== Custom Bot: Win Rate & Value by Draw Number (lag-k) ===")
    print(f"{'k':>3} {'samples':>9} {'win_rate':>9} {'mean_value':>11} {'bust_rate':>10}") #:>3 means give 3 character spacing
    for k, samples, win_rate, mean_v, std_v, bust_rate in data:
        print(f"{k:>3} {samples:>9} {win_rate:>9} {mean_v:>11} {bust_rate:>10}")

    return data


def analyze_final_scores(rows):
    print("\n=== Final Score Summary (per player) ===")
    header = f"{'player':>8} {'thresh':>8} {'mean':>8} {'std':>8} {'win%':>7} {'bust%':>7} {'flip7%':>7} {'avgdraws':>9}"
    print(header)
    parsed = []
    for r in rows:
        mean_s = to_float(r["mean_score"])
        std_s = to_float(r["std_score"])
        win_r = to_float(r["win_rate"])
        bust_r = to_float(r["bust_rate"])
        flip7_r = to_float(r["flip7_rate"])
        avg_d = to_float(r["avg_draws_per_round"])
        parsed.append(r)
        print(f"{r['player']:>8} {r['threshold']:>8} {mean_s:>8} {std_s:>8} {win_r*100:>6}% {bust_r*100:>6}% {flip7_r*100:>6.2f}% {avg_d:>9}")

    custom = next((r for r in rows if r["player"] == "Custom"), None) #next() gets the next item from a list
    fixed = [r for r in rows if r["player"] != "Custom"]
    if custom and fixed:
        fixed_mean = sum(to_float(r["mean_score"]) for r in fixed) / len(fixed)
        custom_mean = to_float(custom["mean_score"])
        delta = custom_mean - fixed_mean
        pct = (delta / fixed_mean * 100) if fixed_mean else float("nan")
        print(f"\nCustom bot vs. average fixed bot: {delta} points ({pct}%)")

        #Z test
        custom_std = to_float(custom["std_score"])
        custom_n = to_int(custom["games"])
        fixed_std = sum(to_float(r["std_score"]) for r in fixed) / len(fixed)
        fixed_n = sum(to_int(r["games"]) for r in fixed)
        se = math.sqrt((custom_std ** 2) / custom_n + (fixed_std ** 2) / (fixed_n / len(fixed)))
        z = delta / se if se else float("nan")
        print(f"Approx z-score for the difference: {z} "
              f"({'likely significant' if abs(z) > 1.96 else 'not clearly significant'} at p<0.05, rough approximation)")

    return parsed


def make_multi_threshold_charts(all_results, out_dir):
    plt.figure(figsize=(9,6))

    for threshold, result in all_results.items():

        data = result["custom"]

        ks = [k for k, *_ in data]
        values = [m for _,_,_,m,_,_ in data]

        plt.plot(
            ks,
            values,
            marker='o',
            label=threshold.replace("threshold_","")
        )

    plt.xlabel("Draw Number")
    plt.ylabel("Mean Expected Value")
    plt.title("Expected Value by Draw Number")
    plt.legend(title="Threshold")
    plt.grid(True)

    plt.savefig(
        os.path.join(
            out_dir,
            "all_threshold_expected_value.png"
        ),
        dpi=200
    )

    plt.close()




    thresholds=[]
    mean_scores=[]
    win_rates=[]
    bust_rates=[]

    for threshold, result in all_results.items():

        summary=result["summary"]

        custom=next(
            r for r in summary
            if r["player"]=="Custom"
        )

        thresholds.append(
            float(threshold.replace("threshold_",""))
        )

        mean_scores.append(
            float(custom["mean_score"])
        )

        win_rates.append(
            float(custom["win_rate"])
        )

        bust_rates.append(
            float(custom["bust_rate"])
        )



    plt.figure(figsize=(8,5))
    plt.plot(thresholds,mean_scores,'o-')
    plt.xlabel("Threshold")
    plt.ylabel("Mean Score")
    plt.title("Threshold vs Mean Score")
    plt.grid(True)
    plt.savefig(os.path.join(out_dir,"threshold_vs_score.png"),dpi=200)
    plt.close()



    plt.figure(figsize=(8,5))
    plt.plot(thresholds,win_rates,'o-')
    plt.xlabel("Threshold")
    plt.ylabel("Win Rate")
    plt.title("Threshold vs Win Rate")
    plt.grid(True)
    plt.savefig(os.path.join(out_dir,"threshold_vs_winrate.png"),dpi=200)
    plt.close()



    plt.figure(figsize=(8,5))
    plt.plot(thresholds,bust_rates,'o-')
    plt.xlabel("Threshold")
    plt.ylabel("Bust Rate")
    plt.title("Threshold vs Bust Rate")
    plt.grid(True)
    plt.savefig(os.path.join(out_dir,"threshold_vs_bustrate.png"),dpi=200)
    plt.close()


threshold_dirs = sorted(
    d for d in os.listdir(".")
    if d.startswith("threshold_")
)

all_custom = {}

for folder in threshold_dirs:

    rows = load_csv(
        os.path.join(folder, "custom_lag_k_performance.csv")
    )

    all_custom[folder] = analyze_custom_lag_performance(rows)

def main():
    parser = argparse.ArgumentParser(description="Analyze Flip 7 simulation CSV output")
    parser.add_argument("--dir", default=".", help="Directory containing the CSV files")
    args = parser.parse_args()

    d = args.dir

    threshold_dirs = sorted(
    d for d in os.listdir(d)
    if d.startswith("threshold_")
)

    all_results = {}

    for folder in threshold_dirs:

        folder_path = os.path.join(d, folder)

        custom_lag_rows = load_csv(
            os.path.join(folder_path,
            "custom_lag_k_performance.csv")
        )

        final_score_rows = load_csv(
            os.path.join(folder_path,
            "final_score_summary.csv")
        )

        custom_data = analyze_custom_lag_performance(custom_lag_rows)
        final_data = analyze_final_scores(final_score_rows)

        all_results[folder] = {
            "custom": custom_data,
            "summary": final_data
        }

    make_multi_threshold_charts(all_results, d)


if __name__ == "__main__":
    main()