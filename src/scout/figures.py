"""Figures for the README.

    python -m scout.figures --zones 8   # reports/figures/shot_zones_k8.png
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Arc, Rectangle  # noqa: E402

from scout.features import (KEYS, PITCH_LENGTH, PITCH_WIDTH, PROCESSED, ZONE_X_EDGES,  # noqa: E402
                            ZONE_Y_EDGES, fit_shot_zones, shot_grids, shots_in)

FIGURES = Path("reports/figures")


def draw_half_pitch(ax) -> None:
    """Attacking half, goal at the top, seen from behind the attacker (their right is on
    the right). Coordinates: horizontal = metres from the attacker's left touchline."""
    kw = {"fill": False, "lw": 1, "color": "0.25"}
    w, half = PITCH_WIDTH, PITCH_LENGTH / 2
    ax.add_patch(Rectangle((0, half), w, half, **kw))
    ax.add_patch(Rectangle((w / 2 - 20.16, PITCH_LENGTH - 16.5), 40.32, 16.5, **kw))  # penalty area
    ax.add_patch(Rectangle((w / 2 - 9.16, PITCH_LENGTH - 5.5), 18.32, 5.5, **kw))     # six-yard box
    ax.add_patch(Rectangle((w / 2 - 3.66, PITCH_LENGTH), 7.32, 1.5, **kw))            # goal
    ax.add_patch(Arc((w / 2, PITCH_LENGTH - 11), 18.3, 18.3, theta1=233, theta2=307, **kw))
    ax.add_patch(Arc((w / 2, half), 18.3, 18.3, theta1=0, theta2=180, **kw))
    ax.plot(w / 2, PITCH_LENGTH - 11, ".", color="0.25", ms=3)
    ax.set_xlim(-1, w + 1)
    ax.set_ylim(half - 1, PITCH_LENGTH + 3)
    ax.set_aspect("equal")
    ax.axis("off")


def zone_label(component: np.ndarray) -> str:
    """Rough description from the component's centre of mass."""
    x_mid = (ZONE_X_EDGES[:-1] + ZONE_X_EDGES[1:]) / 2
    y_mid = (ZONE_Y_EDGES[:-1] + ZONE_Y_EDGES[1:]) / 2
    weights = component / component.sum()
    depth = PITCH_LENGTH - (weights.sum(axis=1) * x_mid).sum()
    lateral = PITCH_WIDTH / 2 - (weights.sum(axis=0) * y_mid).sum()  # > 0 = attacker's right
    side = "centre" if abs(lateral) < 4 else ("right" if lateral > 0 else "left")
    return f"{side}, ~{depth:.0f} m out"


def plot_shot_zones(components: np.ndarray, path: Path) -> None:
    """One half-pitch heatmap per NMF component."""
    nx, ny = len(ZONE_X_EDGES) - 1, len(ZONE_Y_EDGES) - 1
    k = len(components)
    cols = min(k, 4)
    rows = int(np.ceil(k / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.9 * rows))
    for i, ax in enumerate(np.atleast_1d(axes).ravel()):
        if i >= k:
            ax.axis("off")
            continue
        c = components[i].reshape(nx, ny)
        # Y = 0 is the attacker's right: plot against metres from the left touchline
        ax.pcolormesh(PITCH_WIDTH - ZONE_Y_EDGES, ZONE_X_EDGES, c, cmap="Reds", shading="flat",
                      vmin=0, vmax=c.max())
        draw_half_pitch(ax)
        ax.set_title(f"Zone {i + 1}: {zone_label(c)}", fontsize=9)
    fig.suptitle(f"Shot-location zones (NMF, k = {k}) · attacking right to the right", fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--zones", type=int, required=True, help="number of NMF components")
    args = p.parse_args()

    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    pool = pd.read_parquet(PROCESSED / "profiles.parquet").set_index(KEYS)
    # Same fit as build_profiles(zones=k): full-season grids of the pool players
    grids = shot_grids(shots_in(shots, apps.merge(pool.reset_index()[KEYS], on=KEYS))).reindex(pool.index)
    model = fit_shot_zones(grids, args.zones)
    path = FIGURES / f"shot_zones_k{args.zones}.png"
    plot_shot_zones(model.components_, path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
