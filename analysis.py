import argparse
import csv
import math
import os

import matplotlib
from cycler import cycler
matplotlib.use("Agg") #Trust me we need this, otherwise it looks really really bad - It's non interactive since we don't need to move around the graphs
import matplotlib.pyplot as plt
plt.rcParams['axes.prop_cycle'] = cycler(color=plt.colormaps['tab20'].colors) #This lets us add more colors than the base 10

def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_float(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def to_int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Lag-k bust probability analysis
# ---------------------------------------------------------------------------

def analyze_lag_k_bust(rows):
    """rows: draw_number_k, attempts, busts, bust_rate"""
    data = []
    for r in rows:
        k = to_int(r["draw_number_k"])
        attempts = to_int(r["attempts"])
        busts = to_int(r["busts"])
        rate = to_float(r["bust_rate"])
        data.append((k, attempts, busts, rate))
    data.sort()

    print("\n=== Lag-k Bust Probability ===")
    print(f"{'k':>3} {'attempts':>10} {'busts':>8} {'bust_rate':>10}")
    for k, attempts, busts, rate in data:
        print(f"{k:>3} {attempts:>10} {busts:>8} {rate:>10.4f}")

    # first-difference: how fast bust rate climbs per additional card
    diffs = []
    for i in range(1, len(data)):
        k = data[i][0]
        d = data[i][3] - data[i - 1][3]
        diffs.append((k, d))

    if diffs:
        avg_slope = sum(d for _, d in diffs) / len(diffs)
        print(f"\nAverage increase in bust rate per additional card drawn: {avg_slope:+.4f}")

    # k at which bust rate crosses common thresholds
    for target in (0.25, 0.5, 0.75):
        crossing = next((k for k, _, _, rate in data if rate is not None and rate >= target), None)
        print(f"First draw number where bust_rate >= {target:.2f}: "
              f"{crossing if crossing is not None else 'never observed'}")

    return data, diffs


def analyze_lag_k_value(rows):
    """rows: draw_number_k, samples, mean_running_value, std_running_value, marginal_gain_vs_prev_k"""
    data = []
    for r in rows:
        k = to_int(r["draw_number_k"])
        samples = to_int(r["samples"])
        mean_v = to_float(r["mean_running_value"])
        std_v = to_float(r["std_running_value"])
        marginal = to_float(r["marginal_gain_vs_prev_k"])
        data.append((k, samples, mean_v, std_v, marginal))
    data.sort()

    print("\n=== Lag-k Expected Value (running bankable score) ===")
    print(f"{'k':>3} {'samples':>10} {'mean_value':>11} {'std':>8} {'marginal_gain':>14}")
    for k, samples, mean_v, std_v, marginal in data:
        marg_str = f"{marginal:+.3f}" if marginal is not None else "     n/a"
        print(f"{k:>3} {samples:>10} {mean_v:>11.3f} {std_v:>8.3f} {marg_str:>14}")

    marginals = [m for _, _, _, _, m in data if m is not None]
    if marginals:
        print(f"\nAverage marginal EV gain per extra card: {sum(marginals)/len(marginals):+.3f}")
        # Diminishing returns check: is the marginal gain shrinking over k?
        if len(marginals) >= 2:
            slope_of_marginal = (marginals[-1] - marginals[0]) / (len(marginals) - 1)
            trend = "diminishing" if slope_of_marginal < 0 else "increasing"
            print(f"Marginal gain trend across draws: {trend} "
                  f"({slope_of_marginal:+.4f} per step)")

    # coefficient of variation per k (risk relative to reward)
    print("\nCoefficient of variation (std / mean) by draw number — higher = riskier relative payoff:")
    for k, samples, mean_v, std_v, marginal in data:
        if mean_v and mean_v != 0:
            cv = std_v / mean_v
            print(f"  k={k}: CV={cv:.3f}")

    return data


# ---------------------------------------------------------------------------
# Round length distribution
# ---------------------------------------------------------------------------

def analyze_round_length(rows):
    data = [(to_int(r["round_length_draws"]), to_int(r["count"]), to_float(r["proportion"]))
            for r in rows]
    data.sort()

    total = sum(c for _, c, _ in data)
    mean_len = sum(k * c for k, c, _ in data) / total if total else 0.0
    var_len = sum(c * (k - mean_len) ** 2 for k, c, _ in data) / total if total else 0.0
    std_len = math.sqrt(var_len)

    print("\n=== Round Length Distribution ===")
    print(f"Mean draws per round: {mean_len:.3f}")
    print(f"Std dev draws per round: {std_len:.3f}")
    mode_len = max(data, key=lambda x: x[1])[0] if data else None
    print(f"Most common round length: {mode_len} draws")

    return {"mean_length": mean_len, "std_length": std_len, "mode_length": mode_len}


# ---------------------------------------------------------------------------
# Card draw frequency (sanity check vs. deck composition)
# ---------------------------------------------------------------------------

def analyze_card_frequency(rows):
    data = [(r["card"], to_int(r["count"]), to_float(r["proportion"])) for r in rows]
    data.sort(key=lambda x: -x[1])

    print("\n=== Card Draw Frequency (top 10) ===")
    for card, count, prop in data[:10]:
        print(f"{card:>6}: {count:>8}  ({prop*100:5.2f}%)")

    return data


# ---------------------------------------------------------------------------
# Bust cause breakdown
# ---------------------------------------------------------------------------

def analyze_bust_causes(rows):
    data = [(r["duplicate_number"], to_int(r["bust_count"]), to_float(r["proportion_of_busts"]))
            for r in rows]
    data.sort(key=lambda x: -x[1])

    print("\n=== Bust Cause Breakdown ===")
    for number, count, prop in data:
        print(f"duplicate {number:>3}: {count:>7} busts  ({prop*100:5.2f}% of all busts)")

    if data:
        low_numbers = sum(c for n, c, _ in data if to_int(n) is not None and to_int(n) <= 4)
        high_numbers = sum(c for n, c, _ in data if to_int(n) is not None and to_int(n) >= 8)
        total = sum(c for _, c, _ in data)
        if total:
            print(f"\nLow numbers (0-4) cause {low_numbers/total*100:.2f}% of busts")
            print(f"High numbers (8-12) cause {high_numbers/total*100:.2f}% of busts")
            print("(Low numbers appear less often in the deck per-value but you're more "
                  "likely to be holding one by the time you bust; interpret with the "
                  "lag-k data above.)")

    return data


# ---------------------------------------------------------------------------
# Custom bot: win rate & score over lag (draw-by-draw progress within a round)
# ---------------------------------------------------------------------------

def analyze_custom_lag_performance(rows):
    """rows: draw_number_k, samples, win_rate, mean_running_value, std_running_value, bust_rate_at_k"""
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
    print(f"{'k':>3} {'samples':>9} {'win_rate':>9} {'mean_value':>11} {'bust_rate':>10}")
    for k, samples, win_rate, mean_v, std_v, bust_rate in data:
        print(f"{k:>3} {samples:>9} {win_rate:>9.4f} {mean_v:>11.3f} {bust_rate:>10.4f}")

    if len(data) >= 2:
        first_win = data[0][2]
        last_win = data[-1][2]
        print(f"\nWin rate moves from {first_win:.3f} (draw 1) to {last_win:.3f} "
              f"(draw {data[-1][0]}) as the round progresses.")

        # correlation-style check: does win rate track mean_value across k?
        ks = [k for k, *_ in data]
        win_rates = [w for _, _, w, _, _, _ in data]
        mean_vals = [m for _, _, _, m, _, _ in data]
        n = len(ks)
        mean_w = sum(win_rates) / n
        mean_m = sum(mean_vals) / n
        cov = sum((win_rates[i] - mean_w) * (mean_vals[i] - mean_m) for i in range(n)) / n
        std_w = (sum((w - mean_w) ** 2 for w in win_rates) / n) ** 0.5
        std_m = (sum((m - mean_m) ** 2 for m in mean_vals) / n) ** 0.5
        corr = cov / (std_w * std_m) if std_w and std_m else float("nan")
        print(f"Correlation between win rate and running value across draw numbers: {corr:.3f}")

    return data


def analyze_custom_final_stop_summary(rows):
    """rows: total_draws, samples, win_rate, mean_score, std_score, bust_rate, flip7_rate"""
    data = []
    for r in rows:
        total_draws = to_int(r["total_draws"])
        samples = to_int(r["samples"])
        win_rate = to_float(r["win_rate"])
        mean_s = to_float(r["mean_score"])
        std_s = to_float(r["std_score"])
        bust_rate = to_float(r["bust_rate"])
        flip7_rate = to_float(r["flip7_rate"])
        data.append((total_draws, samples, win_rate, mean_s, std_s, bust_rate, flip7_rate))
    data.sort()

    print("\n=== Custom Bot: Outcomes by Final Stop Length ===")
    print(f"{'draws':>5} {'samples':>9} {'win_rate':>9} {'mean_score':>11} {'bust_rate':>10} {'flip7_rate':>11}")
    for total_draws, samples, win_rate, mean_s, std_s, bust_rate, flip7_rate in data:
        print(f"{total_draws:>5} {samples:>9} {win_rate:>9.4f} {mean_s:>11.3f} "
              f"{bust_rate:>10.4f} {flip7_rate:>11.4f}")

    if data:
        best_by_win = max(data, key=lambda x: x[2])
        best_by_score = max(data, key=lambda x: x[3])
        print(f"\nHighest win rate ({best_by_win[2]:.3f}) occurs when stopping at {best_by_win[0]} draws "
              f"(n={best_by_win[1]})")
        print(f"Highest mean score ({best_by_score[3]:.3f}) occurs when stopping at {best_by_score[0]} draws "
              f"(n={best_by_score[1]})")
        print("Note: small-sample tails (very high draw counts) are noisy — check the "
              "sample size column before trusting an extreme value.")

    return data


# ---------------------------------------------------------------------------
# Final score summary — cross-player comparison
# ---------------------------------------------------------------------------

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
        print(f"{r['player']:>8} {r['threshold']:>8} {mean_s:>8.3f} {std_s:>8.3f} "
              f"{win_r*100:>6.2f}% {bust_r*100:>6.2f}% {flip7_r*100:>6.2f}% {avg_d:>9.3f}")

    # highlight the custom bot vs. the average of the fixed bots
    custom = next((r for r in rows if r["player"] == "Custom"), None)
    fixed = [r for r in rows if r["player"] != "Custom"]
    if custom and fixed:
        fixed_mean = sum(to_float(r["mean_score"]) for r in fixed) / len(fixed)
        custom_mean = to_float(custom["mean_score"])
        delta = custom_mean - fixed_mean
        pct = (delta / fixed_mean * 100) if fixed_mean else float("nan")
        print(f"\nCustom bot vs. average fixed bot: {delta:+.3f} points ({pct:+.2f}%)")

        # simple z-test style comparison using pooled std (rough, assumes ~independent)
        custom_std = to_float(custom["std_score"])
        custom_n = to_int(custom["games"])
        fixed_std = sum(to_float(r["std_score"]) for r in fixed) / len(fixed)
        fixed_n = sum(to_int(r["games"]) for r in fixed)
        se = math.sqrt((custom_std ** 2) / custom_n + (fixed_std ** 2) / (fixed_n / len(fixed)))
        z = delta / se if se else float("nan")
        print(f"Approx z-score for the difference: {z:.3f} "
              f"({'likely significant' if abs(z) > 1.96 else 'not clearly significant'} at p<0.05, rough approximation)")

    return parsed


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def make_multi_threshold_charts(all_results, out_dir):

    #
    # WIN RATE VS DRAW NUMBER
    #

    plt.figure(figsize=(9,6))

    for threshold, result in all_results.items():

        data = result["custom"]

        ks = [k for k, *_ in data]
        wins = [w for _,_,w,_,_,_ in data]

        plt.plot(
            ks,
            wins,
            marker='o',
            label=threshold.replace("threshold_","")
        )

    plt.xlabel("Draw Number")
    plt.ylabel("Win Rate")
    plt.title("Win Rate vs Draw Number")
    plt.legend(title="Threshold")
    plt.grid(True)

    plt.savefig(
        os.path.join(
            out_dir,
            "all_threshold_win_rate.png"
        ),
        dpi=200
    )

    plt.close()



    #
    # RUNNING VALUE
    #

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



    #
    # THRESHOLD VS MEAN SCORE
    #

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


# ---------------------------------------------------------------------------
# Consolidated output CSV
# ---------------------------------------------------------------------------

def write_consolidated_summary(lag_bust_data, lag_value_data, length_stats, final_score_rows,
                                custom_lag_data, out_path):
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["mean_round_length_draws", round(length_stats["mean_length"], 4)])
        writer.writerow(["std_round_length_draws", round(length_stats["std_length"], 4)])
        writer.writerow(["mode_round_length_draws", length_stats["mode_length"]])

        for k, attempts, busts, rate in lag_bust_data:
            writer.writerow([f"bust_rate_at_draw_{k}", rate])

        for k, samples, mean_v, std_v, marginal in lag_value_data:
            writer.writerow([f"mean_value_at_draw_{k}", round(mean_v, 4) if mean_v is not None else ""])
            writer.writerow([f"marginal_gain_at_draw_{k}",
                              round(marginal, 4) if marginal is not None else ""])

        for r in final_score_rows:
            writer.writerow([f"{r['player']}_mean_score", r["mean_score"]])
            writer.writerow([f"{r['player']}_win_rate", r["win_rate"]])
            writer.writerow([f"{r['player']}_bust_rate", r["bust_rate"]])

        for k, samples, win_rate, mean_v, std_v, bust_rate in custom_lag_data:
            writer.writerow([f"custom_win_rate_at_draw_{k}", round(win_rate, 4)])
            writer.writerow([f"custom_mean_value_at_draw_{k}", round(mean_v, 4)])

    print(f"\nConsolidated summary written to {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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