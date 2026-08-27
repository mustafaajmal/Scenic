"""Generate writeup figures from Scenic / Gym evaluation CSVs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

SWEEP = ROOT / "outputs" / "scenic_policy_eval" / "sweep_dual.csv"
RECORDS = ROOT / "outputs" / "scenic_policy_eval" / "records"
GYM_V3 = (
    ROOT.parent
    / "asteroid-rl-demo"
    / "outputs"
    / "scenic_curriculum_v3"
    / "summary.csv"
)
GYM_MVP = (
    ROOT.parent
    / "asteroid-rl-demo"
    / "outputs"
    / "scenic_curriculum_mvp"
    / "summary.csv"
)

# Colorblind-friendly Okabe–Ito-ish palette
C = {
    "sphere": "#0072B2",
    "ellipsoid": "#E69F00",
    "bumpy": "#009E73",
    "scripted": "#0072B2",
    "ppo": "#D55E00",
    "reach": "#0072B2",
    "soft": "#CC79A7",
    "contact": "#999999",
}

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "figure.dpi": 140,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
    }
)


def load_record(stage: str, ep: int, seed: int) -> pd.DataFrame:
    return pd.read_csv(RECORDS / f"{stage}_ep{ep:02d}_seed{seed}.csv")


def fig_trajectories() -> None:
    series = [
        ("sphere", 0, 0, "Sphere (reach)"),
        ("ellipsoid", 0, 0, "Ellipsoid (reach)"),
        ("bumpy", 0, 0, "Bumpy (soft)"),
        ("bumpy", 1, 1, "Bumpy (fail)"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(6.2, 4.4), sharex=True)
    for stage, ep, seed, label in series:
        df = load_record(stage, ep, seed)
        color = C["bumpy"] if stage == "bumpy" else C[stage]
        ls = "--" if "fail" in label else "-"
        lw = 1.6 if "fail" in label else 1.8
        axes[0].plot(df["time_s"], df["altitude_m"], color=color, ls=ls, lw=lw, label=label)
        axes[1].plot(df["time_s"], df["speed_mps"], color=color, ls=ls, lw=lw, label=label)

    axes[0].axhspan(0.3, 8.0, color="#0072B2", alpha=0.08, zorder=0)
    axes[0].axhline(8.0, color="#555555", lw=0.7, ls=":")
    axes[0].set_ylabel("Mesh-radar altitude (m)")
    axes[0].set_ylim(0, 170)
    axes[0].legend(loc="upper right", frameon=False, ncol=2)
    axes[0].text(2, 10.5, "reach/soft altitude band", color="#444444", fontsize=8)

    axes[1].axhline(3.5, color="#0072B2", lw=0.9, ls="--", label="reach gate 3.5 m/s")
    axes[1].axhline(2.8, color="#CC79A7", lw=0.9, ls=":", label="soft gate 2.8 m/s")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Speed (m/s)")
    axes[1].set_ylim(0, 4.0)
    # Avoid duplicating trajectory labels; show only gates in second legend.
    h, lab = axes[1].get_legend_handles_labels()
    axes[1].legend(h[-2:], lab[-2:], loc="upper right", frameon=False)

    fig.tight_layout()
    fig.savefig(OUT / "trajectories.pdf")
    fig.savefig(OUT / "trajectories.png")
    plt.close(fig)


def fig_rates() -> None:
    df = pd.read_csv(SWEEP)
    stages = ["sphere", "ellipsoid", "bumpy"]
    metrics = [("contact_ok", "Contact"), ("reach_ok", "Reach (primary)"), ("soft_ok", "Soft")]
    x = np.arange(len(stages))
    width = 0.24
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    colors = [C["contact"], C["reach"], C["soft"]]
    for i, (col, name) in enumerate(metrics):
        rates = [100.0 * df.loc[df.stage == s, col].mean() for s in stages]
        ax.bar(
            x + (i - 1) * width,
            rates,
            width,
            label=name,
            color=colors[i],
            edgecolor="white",
            linewidth=0.4,
        )
        for xi, r in zip(x + (i - 1) * width, rates):
            ax.text(xi, r + 1.5, f"{r:.0f}%", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(["Sphere", "Ellipsoid", "Bumpy"])
    ax.set_ylabel("Rate over 12 episodes (%)")
    ax.set_ylim(0, 118)
    ax.legend(loc="upper right", frameon=False)
    ax.set_title("Fixed scripted policy vs. Scenic curriculum (Path A)")
    fig.tight_layout()
    fig.savefig(OUT / "rates_path_a.pdf")
    fig.savefig(OUT / "rates_path_a.png")
    plt.close(fig)


def fig_scatter() -> None:
    df = pd.read_csv(SWEEP)
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    markers = {"sphere": "o", "ellipsoid": "s", "bumpy": "^"}
    for stage in ["sphere", "ellipsoid", "bumpy"]:
        sub = df[df.stage == stage]
        ok = sub["reach_ok"].astype(bool)
        ax.scatter(
            sub.loc[ok, "final_speed_mps"],
            sub.loc[ok, "min_altitude_m"],
            c=C[stage],
            marker=markers[stage],
            s=42,
            label=f"{stage} reach",
            zorder=3,
        )
        ax.scatter(
            sub.loc[~ok, "final_speed_mps"],
            sub.loc[~ok, "min_altitude_m"],
            facecolors="none",
            edgecolors=C[stage],
            marker=markers[stage],
            s=48,
            linewidths=1.2,
            label=f"{stage} fail",
            zorder=3,
        )

    ax.axvline(3.5, color="#0072B2", lw=0.9, ls="--")
    ax.axvline(2.8, color="#CC79A7", lw=0.9, ls=":")
    ax.axhline(8.0, color="#555555", lw=0.7, ls=":")
    ax.axhline(0.3, color="#555555", lw=0.7, ls=":")
    ax.set_xlabel("Final speed (m/s)")
    ax.set_ylabel("Minimum mesh-radar altitude (m)")
    ax.set_xlim(0.5, 3.8)
    ax.set_ylim(0, 13)
    ax.text(3.52, 12.2, "reach", color="#0072B2", fontsize=8, rotation=90, va="top")
    ax.text(2.55, 12.2, "soft", color="#CC79A7", fontsize=8, rotation=90, va="top")
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=8)
    ax.set_title("Anytime-scored landings in (speed, altitude) space")
    fig.tight_layout()
    fig.savefig(OUT / "scatter_gates.pdf")
    fig.savefig(OUT / "scatter_gates.png")
    plt.close(fig)


def _gym_rates(path: Path) -> dict:
    df = pd.read_csv(path)
    out = {}
    for stage in ["sphere", "ellipsoid", "bumpy"]:
        out[stage] = {}
        for pol in ["scripted", "ppo"]:
            sub = df[(df.stage == stage) & (df.policy == pol)]
            out[stage][pol] = 100.0 * sub["safe_landing"].mean()
    return out


def fig_gym() -> None:
    v3 = _gym_rates(GYM_V3)
    mvp = _gym_rates(GYM_MVP)
    stages = ["sphere", "ellipsoid", "bumpy"]
    x = np.arange(len(stages))
    width = 0.18
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.85), sharey=True)

    panels = [
        (axes[0], v3, "Sphere-only PPO (5k steps)"),
        (axes[1], mvp, "Progressive PPO (4k/stage)"),
    ]
    for ax, data, title in panels:
        s = [data[st]["scripted"] for st in stages]
        p = [data[st]["ppo"] for st in stages]
        ax.bar(x - width / 2 - 0.02, s, width, color=C["scripted"], label="Scripted")
        ax.bar(x + width / 2 + 0.02, p, width, color=C["ppo"], label="PPO")
        ax.set_xticks(x)
        ax.set_xticklabels(["Sphere", "Ellipsoid", "Bumpy"])
        ax.set_title(title)
        ax.set_ylim(0, 110)
        for xi, val in zip(x - width / 2 - 0.02, s):
            ax.text(xi, val + 2, f"{val:.0f}", ha="center", fontsize=8)
        for xi, val in zip(x + width / 2 + 0.02, p):
            ax.text(xi, val + 2, f"{val:.0f}", ha="center", fontsize=8)

    axes[0].set_ylabel("Safe-landing rate (4 eps, %)")
    axes[1].legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "rates_path_b.pdf")
    fig.savefig(OUT / "rates_path_b.png")
    plt.close(fig)


def fig_speed_box() -> None:
    df = pd.read_csv(SWEEP)
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    data = [df.loc[df.stage == s, "final_speed_mps"].values for s in ["sphere", "ellipsoid", "bumpy"]]
    bp = ax.boxplot(
        data,
        tick_labels=["Sphere", "Ellipsoid", "Bumpy"],
        patch_artist=True,
        widths=0.55,
        medianprops={"color": "#111111", "linewidth": 1.4},
        whiskerprops={"linewidth": 1.0},
        capprops={"linewidth": 1.0},
        flierprops={"marker": "o", "markersize": 4},
    )
    for patch, stage in zip(bp["boxes"], ["sphere", "ellipsoid", "bumpy"]):
        patch.set_facecolor(C[stage])
        patch.set_alpha(0.55)
        patch.set_edgecolor("#333333")
    ax.axhline(3.5, color="#0072B2", lw=0.9, ls="--")
    ax.axhline(2.8, color="#CC79A7", lw=0.9, ls=":")
    ax.set_ylabel("Final speed (m/s)")
    ax.set_title("Terminal speed by curriculum stage")
    fig.tight_layout()
    fig.savefig(OUT / "speed_box.pdf")
    fig.savefig(OUT / "speed_box.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_trajectories()
    fig_rates()
    fig_scatter()
    fig_gym()
    fig_speed_box()
    print(f"Wrote figures to {OUT}")
