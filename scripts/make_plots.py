"""
Generate the engineering plots used in the README.

All inputs come from the project itself:
  * pulley / tendon geometry  -> CAD drawings (R = 20 mm groove radius, dL ~ 30 mm)
  * servo stroke              -> firmware (ANGOLO_APERTO = 180 deg, ANGOLO_CHIUSO = 70 deg)
  * LDR readings / thresholds -> Arduino serial-monitor logs recorded during the tests

Run:  python scripts/make_plots.py      (writes PNGs to docs/plots/)
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs" / "plots"
OUT.mkdir(parents=True, exist_ok=True)

# Validated categorical palette (slots 1-3) + neutral inks
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": INK2, "ytick.color": INK2, "legend.frameon": False,
    "savefig.dpi": 160, "savefig.bbox": "tight", "figure.facecolor": "white",
})

# ---------------------------------------------------------------------------
# 1) Pulley sizing: minimum groove radius vs. usable servo rotation
# ---------------------------------------------------------------------------
dL = 30.0                     # mm, tendon travel for full finger closure
R_design = 20.0               # mm, pulley groove radius (CAD)
theta_deg = np.linspace(60, 200, 400)
R_min = dL / np.deg2rad(theta_deg)

fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(theta_deg, R_min, color=BLUE, lw=2, label=r"$R_{min}(\theta)=\Delta L/\theta$")
ax.fill_between(theta_deg, R_min, 0, color=ORANGE, alpha=0.12, lw=0)
ax.axhline(R_design, color=INK2, lw=1.2, ls="--")
ax.text(198, R_design + 0.6, r"design radius $R = 20$ mm", color=INK2, fontsize=10, ha="right")
for th, lab, off in [(180, "full servo range 180°", (-12, 4.5)), (110, "firmware stroke\n180° → 70° = 110°", (6, 7))]:
    r = dL / np.deg2rad(th)
    ax.plot([th], [r], "o", ms=8, color=BLUE, mec="white", mew=2, zorder=5)
    ax.annotate(f"{lab}\n$R_{{min}}$ = {r:.1f} mm  (SF = {R_design / r:.1f})",
                xy=(th, r), xytext=(th + off[0], r + off[1]), fontsize=9.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(64, 1.5, "infeasible region: tendon stroke < ΔL", color=ORANGE, fontsize=9.5)
ax.set(xlabel=r"usable servo rotation $\theta$ [deg]", ylabel=r"minimum pulley radius [mm]",
       title="Pulley sizing for ΔL ≈ 30 mm of tendon travel", ylim=(0, 30), xlim=(60, 200))
ax.legend(loc="upper right")
fig.savefig(OUT / "pulley_sizing.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 2) Whiffletree vs. rigid single tendon: idealised quasi-static kinematics
#    Fingers modelled as linear springs (k_free) until contact, then a stiff
#    contact (k_contact).  Rigid coupling forces equal displacement on all
#    fingers; the whiffletree enforces equal tension (moment balance on the
#    triangular plate), so the input displacement is the mean of the three.
# ---------------------------------------------------------------------------
k_free, k_contact = 0.05, 2.0         # N/mm  (illustrative values)
contact = np.array([8.0, 16.0, 26.0])  # mm of tendon travel at which each finger touches the object

def finger_tension(d, c):
    d = np.asarray(d, dtype=float)
    return k_free * d + k_contact * np.clip(d - c, 0, None)

def finger_disp_from_tension(T, c):
    d = T / k_free
    over = d > c
    d[over] = c[over] + (T[over] - k_free * c[over]) / (k_free + k_contact)
    return d

u = np.linspace(0, 30, 300)                       # input (servo) tendon travel [mm]
# rigid coupling: every finger moves u
T_rigid = np.stack([finger_tension(u, c) for c in contact])
# whiffletree: find T such that mean(d_i(T)) = u
T_wt = np.zeros_like(u); D_wt = np.zeros((3, u.size))
for j, uj in enumerate(u):
    lo, hi = 0.0, 200.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if finger_disp_from_tension(np.full(3, mid), contact.copy()).mean() < uj: lo = mid
        else: hi = mid
    T_wt[j] = mid
    D_wt[:, j] = finger_disp_from_tension(np.full(3, mid), contact.copy())

fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
cols = [BLUE, ORANGE, AQUA]
for i in range(3):
    axs[0].plot(u, T_rigid[i], color=cols[i], lw=2, label=f"rigid tendon - finger {i+1}")
    axs[1].plot(u, D_wt[i], color=cols[i], lw=2, label=f"finger {i+1}")
axs[0].plot(u, T_wt, color=INK, lw=2, ls="--", label="whiffletree - all fingers (equal)")
axs[0].set(title="Per-finger tendon tension", xlabel="input tendon travel [mm]",
           ylabel="tension (normalised model units)")
axs[0].legend(loc="upper left", fontsize=9)
axs[1].set(title="Whiffletree: per-finger tendon travel", xlabel="input tendon travel [mm]",
           ylabel="finger tendon travel [mm]")
for c, col in zip(contact, cols):
    axs[1].axhline(c, color=col, lw=0.8, ls=":")
axs[1].text(0.5, 37, "dotted = contact point of each finger", fontsize=9, color=INK2)
axs[1].legend(loc="lower right", fontsize=9)
fig.suptitle("Idealised quasi-static under-actuation model (illustrative stiffness values)", color=INK2, fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(OUT / "whiffletree_model.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 3) LDR trigger: steady readings vs. calibrated threshold (serial logs)
# ---------------------------------------------------------------------------
conds = ["Dark room", "Indoor ambient", "Outdoor (sunny)"]
thr = np.array([11, 67, 336])                 # 'Soglia' printed by the firmware
ambient_cal = thr / 0.35                      # ADC value at calibration (soglia = 0.35 * ambient)
steady = np.array([22, 197, 965])             # typical steady reading after calibration (logs)

x = np.arange(3); w = 0.26
fig, ax = plt.subplots(figsize=(8, 4.4))
b1 = ax.bar(x - w - 0.01, ambient_cal, w, color=BLUE, label="ambient at calibration (= threshold / 0.35)")
b2 = ax.bar(x, steady, w, color=AQUA, label="steady reading during test")
b3 = ax.bar(x + w + 0.01, thr, w, color=ORANGE, label="trigger threshold (35 %)")
for bars in (b1, b2, b3):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() * 1.08, f"{r.get_height():.0f}",
                ha="center", va="bottom", fontsize=9, color=INK)
ax.set_yscale("log"); ax.set_ylim(5, 3000)
ax.set_xticks(x, conds)
ax.set(ylabel="10-bit ADC counts (log scale)", title="Photoresistor readings and adaptive threshold")
ax.legend(loc="upper left", fontsize=9.5)
fig.savefig(OUT / "ldr_thresholds.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 4) Trigger margin for different threshold ratios
# ---------------------------------------------------------------------------
k = np.linspace(0.1, 1.0, 200)
fig, ax = plt.subplots(figsize=(7.5, 4.0))
ax.plot(k * 100, (1 - k) * 100, color=BLUE, lw=2)
for kk, lab in [(0.35, "35 % (final)"), (0.70, "70 %"), (0.85, "85 %")]:
    ax.plot([kk * 100], [(1 - kk) * 100], "o", ms=8, color=ORANGE if kk == 0.35 else BLUE, mec="white", mew=2)
    ax.annotate(f"{lab}: {100 - kk*100:.0f} % shading needed", xy=(kk * 100, (1 - kk) * 100),
                xytext=(kk * 100 + 3, (1 - kk) * 100 + 8), fontsize=9.5)
ax.set(xlabel=r"threshold ratio $k$ [% of ambient]", ylabel="light reduction to trigger [%]",
       title="Sensitivity vs. robustness of the shadow trigger", ylim=(0, 100), xlim=(10, 100))
ax.text(12, 6, "← fewer false triggers (needs real occlusion)", fontsize=9, color=INK2)
ax.text(62, 88, "more sensitive, more false triggers →", fontsize=9, color=INK2)
fig.savefig(OUT / "threshold_tradeoff.png"); plt.close(fig)

print("plots written to", OUT)
