#!/usr/bin/env python3
"""
zt_model.py - Isolation Forest anomaly detector (Phase 3, step 3E)

AnomalyDetector (Chapter 4 class diagram) wraps a StandardScaler and a
scikit-learn IsolationForest behind fit() and score().

  score = -IsolationForest.decision_function(x)   higher = more anomalous
  a window is flagged when score > threshold

Training is unsupervised: the model is given windows WITHOUT labels. Labels are
read only to evaluate the result afterwards.

Two training modes are compared in `evaluate`:
  normal-only  trained on normal traffic only (novelty detection)
  mixed        trained on unlabelled traffic in which attacks are rare (~9 %),
               the standard way Isolation Forest is used
The threshold is always tuned on a separate normal run: the 99th percentile of
its scores, i.e. about 1 % false alarms on normal traffic.

Evaluation is 5-fold leave-one-run-out: in fold k, run k of every attack type is
held out for testing and the model is trained on two other runs of each type,
so every run (including the weakest attacks) is tested by a model that never
saw it.

Usage:
  python zt_model.py evaluate        # metrics + charts -> results/
  python zt_model.py train           # final model -> models/zt_iforest.joblib
  python zt_model.py score data/dos_03.csv
"""
import argparse
import glob
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler

from zt_collector import FEATURES

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MODEL_PATH = os.path.join(HERE, "models", "zt_iforest.joblib")
RESULTS = os.path.join(HERE, "results")
ATTACKS = ["dos", "portscan", "bruteforce", "insider", "offhours"]
TRAIN_NORMAL, TUNE_NORMAL, TEST_NORMAL = ["normal_01", "normal_02"], ["normal_03"], ["normal_04"]
QUANTILE = 0.99
SEED = 42


class AnomalyDetector:
    """StandardScaler + IsolationForest with a tuned threshold."""

    def __init__(self, n_estimators=200, seed=SEED):
        self.scaler = StandardScaler()
        self.forest = IsolationForest(n_estimators=n_estimators, random_state=seed)
        self.threshold = 0.0
        self.features = list(FEATURES)

    def _x(self, rows):
        return rows[self.features].to_numpy(dtype=float)

    def fit(self, rows):
        self.forest.fit(self.scaler.fit_transform(self._x(rows)))
        return self

    def score(self, rows):
        return -self.forest.decision_function(self.scaler.transform(self._x(rows)))

    def tune(self, normal_rows, q=QUANTILE):
        self.threshold = float(np.quantile(self.score(normal_rows), q))
        return self.threshold

    def predict(self, rows):
        return self.score(rows) > self.threshold

    def save(self, path=MODEL_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path=MODEL_PATH):
        return joblib.load(path)


# ---------- data ----------
def load(runs):
    frames = []
    for r in runs:
        f = os.path.join(DATA, r + ".csv")
        frames.append(pd.read_csv(f).assign(run=r))
    return pd.concat(frames, ignore_index=True)


def attack_runs(k_list):
    return [f"{a}_0{k}" for a in ATTACKS for k in k_list]


def train_runs(mode, k_list):
    return TRAIN_NORMAL + (attack_runs(k_list) if mode == "mixed" else [])


def folds():
    """Fold k tests run k of every attack; trains on the next two runs (cyclic)."""
    for k in range(1, 6):
        yield k, [(k % 5) + 1, ((k + 1) % 5) + 1]


# ---------- metrics ----------
def metrics(y, flag, score):
    tn, fp, fn, tp = confusion_matrix(y, flag, labels=[0, 1]).ravel()
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": (tp + tn) / len(y), "precision": p, "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "roc_auc": roc_auc_score(y, score) if len(set(y)) == 2 else float("nan"),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def run_mode(mode):
    """5-fold leave-one-run-out. Returns all test rows with score/flag/fold."""
    out = []
    for k, train_k in folds():
        det = AnomalyDetector().fit(load(train_runs(mode, train_k)))
        det.tune(load(TUNE_NORMAL))
        test = load(TEST_NORMAL + attack_runs([k]))
        test["score"] = det.score(test)
        test["flag"] = test["score"] > det.threshold
        test["fold"], test["threshold"] = k, det.threshold
        out.append(test)
    return pd.concat(out, ignore_index=True)


def summarise(res):
    y, f, s = res["label"].astype(int), res["flag"].astype(int), res["score"]
    overall = metrics(y, f, s)
    per_type = {t: float(g["flag"].mean()) for t, g in res.groupby("attack_type")}
    per_run = {r: float(g[g.label == 1]["flag"].mean()) for r, g in res.groupby("run") if (g.label == 1).any()}
    return {"overall": overall, "detection_rate_by_type": per_type, "detection_rate_by_run": per_run,
            "mean_threshold": float(res.groupby("fold")["threshold"].first().mean())}


# ---------- charts (palette: dataviz reference instance, light surface) ----------
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
TYPE_COLOUR = {"dos": BLUE, "portscan": ORANGE, "bruteforce": AQUA, "insider": YELLOW, "offhours": MAGENTA}
LABEL = {"dos": "DoS", "portscan": "Port scan", "bruteforce": "Brute force", "insider": "Insider",
         "offhours": "Off-hours", "normal": "Normal"}


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def charts(results, summaries):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": SURFACE})

    # 1. detection rate per attack type, both modes
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    _style(ax)
    types = ATTACKS
    xs = np.arange(len(types))
    for i, (mode, colour) in enumerate([("normal-only", INK2), ("mixed", BLUE)]):
        vals = [summaries[mode]["detection_rate_by_type"].get(t, 0) * 100 for t in types]
        bars = ax.bar(xs + (i - 0.5) * 0.36, vals, 0.34, color=colour, label=f"Trained on {mode} traffic",
                      edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=8, color=INK)
    fpr = {m: summaries[m]["overall"]["false_positive_rate"] * 100 for m in summaries}
    ax.set_xticks(xs, [LABEL[t] for t in types])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Attack windows detected (%)", color=INK2, fontsize=9)
    ax.set_title("Detection rate by attack type (5-fold, held-out runs)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.12), ncol=2)
    fig.text(0.99, 0.01, f"False-positive rate: normal-only {fpr['normal-only']:.1f}%, mixed {fpr['mixed']:.1f}%",
             ha="right", fontsize=8, color=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "detection_by_type.png"), dpi=200)
    plt.close(fig)

    # 2. score distribution, mixed mode, with threshold
    res = results["mixed"]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    _style(ax)
    order = ["normal"] + ATTACKS
    for i, t in enumerate(order):
        s = res[res.attack_type == t]["score"]
        jitter = np.random.default_rng(i).uniform(-0.28, 0.28, len(s))
        ax.scatter(np.full(len(s), i) + jitter, s, s=10, alpha=0.6,
                   color=INK2 if t == "normal" else TYPE_COLOUR[t], linewidths=0)
    thr = summaries["mixed"]["mean_threshold"]
    ax.axhline(thr, color="#d03b3b", linewidth=1.5, linestyle="--")
    ax.text(len(order) - 0.5, thr, f" threshold {thr:.3f}", va="bottom", ha="right", fontsize=8, color="#d03b3b")
    ax.set_xticks(range(len(order)), [LABEL[t] for t in order])
    ax.set_ylabel("Anomaly score", color=INK2, fontsize=9)
    ax.set_title("Anomaly score of every test window (mixed training)", color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "score_distribution.png"), dpi=200)
    plt.close(fig)

    # 3. confusion matrix, mixed mode
    o = summaries["mixed"]["overall"]
    cm = np.array([[o["tn"], o["fp"]], [o["fn"], o["tp"]]])
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.imshow(cm, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#cde2fb", "#184f95"]))
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center", fontsize=14,
                color="#ffffff" if v > cm.max() / 2 else INK)
    ax.set_xticks([0, 1], ["Normal", "Attack"])
    ax.set_yticks([0, 1], ["Normal", "Attack"])
    ax.set_xlabel("Predicted", color=INK2, fontsize=9)
    ax.set_ylabel("Actual", color=INK2, fontsize=9)
    ax.set_title("Confusion matrix (mixed training)", color=INK, fontsize=11, loc="left")
    ax.tick_params(colors=INK2, labelsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "confusion_matrix.png"), dpi=200)
    plt.close(fig)


def evaluate():
    os.makedirs(RESULTS, exist_ok=True)
    results = {m: run_mode(m) for m in ("normal-only", "mixed")}
    summaries = {m: summarise(r) for m, r in results.items()}
    for m, r in results.items():
        r.to_csv(os.path.join(RESULTS, f"scores_{m}.csv"), index=False)
    with open(os.path.join(RESULTS, "metrics.json"), "w") as f:
        json.dump(summaries, f, indent=2)
    charts(results, summaries)
    for m, s in summaries.items():
        o = s["overall"]
        print(f"\n== trained on {m} traffic (5 folds, {o['tp'] + o['fn']} attack and {o['tn'] + o['fp']} normal test windows)")
        print(f"   accuracy {o['accuracy']:.3f}  precision {o['precision']:.3f}  recall {o['recall']:.3f}  "
              f"F1 {o['f1']:.3f}  FPR {o['false_positive_rate']:.3f}  ROC-AUC {o['roc_auc']:.3f}")
        print("   detection by type:", {LABEL[t]: f"{v:.0%}" for t, v in s["detection_rate_by_type"].items()})
        weak = {r: f"{v:.0%}" for r, v in s["detection_rate_by_run"].items() if v < 1}
        print("   runs not fully detected:", weak or "none")
    print(f"\nresults/ : metrics.json, scores_*.csv, detection_by_type.png, score_distribution.png, confusion_matrix.png")


def train():
    """Final model for the live pipeline, trained exactly as evaluated: the normal training
    runs plus two runs of each attack (runs 2 and 4, a low and a high intensity), unlabelled,
    so attacks make up about 9 % of the training windows."""
    rows = load(train_runs("mixed", [2, 4]))
    det = AnomalyDetector().fit(rows)
    det.tune(load(TUNE_NORMAL))
    det.save()
    share = rows["label"].mean()
    print(f"trained on {len(rows)} windows ({share:.1%} attacks, labels not used); "
          f"threshold {det.threshold:.4f}; saved {os.path.relpath(MODEL_PATH, HERE)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["evaluate", "train", "score"])
    ap.add_argument("csv", nargs="?")
    a = ap.parse_args()
    if a.cmd == "evaluate":
        evaluate()
    elif a.cmd == "train":
        train()
    else:
        det = AnomalyDetector.load()
        rows = pd.read_csv(a.csv)
        rows["score"] = det.score(rows).round(4)
        rows["flag"] = rows["score"] > det.threshold
        print(rows[["window_start", "host_ip", "score", "flag", "label", "attack_type"]].to_string(index=False))
