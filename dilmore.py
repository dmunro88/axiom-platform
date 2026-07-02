"""
dilmore.py — Dilmore Size Adjustment Table
==========================================
Provides dilmore_factor(ratio, curve) → size factor scalar
and dilmore_adj_pct(ratio, curve) → adjustment percentage.

ratio  = A_c / A_s  (comparable GBA ÷ subject GBA)
curve  = one of: 80, 82.5, 85, 87.5, 90  (the elasticity curve %)

The size factor is interpolated linearly between the nearest
table entries. Ratios outside the table range are clamped to
the nearest edge value.

Adjustment % = (size_factor - 1) × 100
  Positive → comp is larger than subject → upward adjustment to comp
  Negative → comp is smaller than subject → downward adjustment to comp

Usage
-----
    from dilmore import dilmore_factor, dilmore_adj_pct

    factor = dilmore_factor(2.3, 85)      # → 1.22
    pct    = dilmore_adj_pct(2.3, 85)     # → +22.0%
"""

# ── Full Dilmore Size Adjustment Table ────────────────────────────────────────
# Key   = A_c/A_s ratio
# Value = [80%, 82.5%, 85%, 87.5%, 90%] size factors

_TABLE = {
    # Panel 1: 0.01 – 1.00
    0.01: [0.23, 0.28, 0.34, 0.41, 0.50],
    0.02: [0.28, 0.34, 0.40, 0.47, 0.55],
    0.03: [0.32, 0.38, 0.44, 0.51, 0.59],
    0.04: [0.35, 0.41, 0.47, 0.54, 0.61],
    0.05: [0.38, 0.44, 0.49, 0.56, 0.63],
    0.06: [0.40, 0.46, 0.52, 0.58, 0.65],
    0.07: [0.42, 0.48, 0.54, 0.60, 0.67],
    0.08: [0.44, 0.50, 0.55, 0.61, 0.68],
    0.09: [0.46, 0.51, 0.57, 0.63, 0.69],
    0.10: [0.48, 0.53, 0.58, 0.64, 0.70],
    0.11: [0.49, 0.54, 0.60, 0.65, 0.71],
    0.12: [0.51, 0.56, 0.61, 0.66, 0.72],
    0.13: [0.52, 0.57, 0.62, 0.68, 0.73],
    0.14: [0.53, 0.58, 0.63, 0.68, 0.74],
    0.15: [0.54, 0.59, 0.64, 0.69, 0.75],
    0.16: [0.55, 0.60, 0.65, 0.70, 0.76],
    0.17: [0.57, 0.61, 0.66, 0.71, 0.76],
    0.18: [0.58, 0.62, 0.67, 0.72, 0.77],
    0.19: [0.59, 0.63, 0.68, 0.73, 0.78],
    0.20: [0.60, 0.64, 0.69, 0.73, 0.78],
    0.25: [0.64, 0.68, 0.72, 0.77, 0.81],
    0.30: [0.68, 0.72, 0.75, 0.79, 0.83],
    0.35: [0.71, 0.75, 0.78, 0.82, 0.85],
    0.40: [0.74, 0.78, 0.81, 0.84, 0.87],
    0.45: [0.77, 0.80, 0.83, 0.86, 0.89],
    0.50: [0.80, 0.82, 0.85, 0.88, 0.90],
    0.55: [0.82, 0.85, 0.87, 0.89, 0.91],
    0.60: [0.85, 0.87, 0.89, 0.91, 0.93],
    0.65: [0.87, 0.89, 0.90, 0.92, 0.94],
    0.70: [0.89, 0.91, 0.92, 0.93, 0.95],
    0.75: [0.91, 0.92, 0.93, 0.95, 0.96],
    0.80: [0.93, 0.94, 0.95, 0.96, 0.97],
    0.85: [0.95, 0.96, 0.96, 0.97, 0.98],
    0.90: [0.97, 0.97, 0.98, 0.98, 0.98],
    0.95: [0.98, 0.99, 0.99, 0.99, 0.99],
    1.00: [1.00, 1.00, 1.00, 1.00, 1.00],
    # Panel 2: 1.1 – 5.0
    1.1:  [1.03, 1.03, 1.02, 1.02, 1.01],
    1.2:  [1.06, 1.05, 1.04, 1.04, 1.03],
    1.3:  [1.09, 1.08, 1.06, 1.05, 1.04],
    1.4:  [1.11, 1.10, 1.08, 1.07, 1.05],
    1.5:  [1.14, 1.12, 1.10, 1.08, 1.06],
    1.6:  [1.16, 1.14, 1.12, 1.09, 1.07],
    1.7:  [1.19, 1.16, 1.13, 1.11, 1.08],
    1.8:  [1.21, 1.18, 1.15, 1.12, 1.09],
    1.9:  [1.23, 1.19, 1.16, 1.13, 1.10],
    2.0:  [1.25, 1.21, 1.18, 1.14, 1.11],
    2.1:  [1.27, 1.23, 1.19, 1.15, 1.12],
    2.2:  [1.29, 1.24, 1.20, 1.16, 1.13],
    2.3:  [1.31, 1.26, 1.22, 1.17, 1.13],
    2.4:  [1.33, 1.28, 1.23, 1.18, 1.14],
    2.5:  [1.34, 1.29, 1.24, 1.19, 1.15],
    2.6:  [1.36, 1.30, 1.25, 1.20, 1.16],
    2.7:  [1.38, 1.32, 1.26, 1.21, 1.16],
    2.8:  [1.39, 1.33, 1.27, 1.22, 1.17],
    2.9:  [1.41, 1.34, 1.28, 1.23, 1.18],
    3.0:  [1.42, 1.36, 1.29, 1.24, 1.18],
    3.1:  [1.44, 1.37, 1.30, 1.24, 1.19],
    3.2:  [1.45, 1.38, 1.31, 1.25, 1.19],
    3.3:  [1.47, 1.39, 1.32, 1.26, 1.20],
    3.4:  [1.48, 1.40, 1.33, 1.27, 1.20],
    3.5:  [1.50, 1.42, 1.34, 1.27, 1.21],
    3.6:  [1.51, 1.43, 1.35, 1.28, 1.21],
    3.7:  [1.52, 1.44, 1.36, 1.29, 1.22],
    3.8:  [1.54, 1.45, 1.37, 1.29, 1.22],
    3.9:  [1.55, 1.46, 1.38, 1.30, 1.23],
    4.0:  [1.56, 1.47, 1.39, 1.31, 1.23],
    4.1:  [1.58, 1.48, 1.39, 1.31, 1.24],
    4.2:  [1.59, 1.49, 1.40, 1.32, 1.24],
    4.3:  [1.60, 1.50, 1.41, 1.32, 1.25],
    4.4:  [1.61, 1.51, 1.42, 1.33, 1.25],
    4.5:  [1.62, 1.52, 1.42, 1.34, 1.26],
    4.6:  [1.63, 1.53, 1.43, 1.34, 1.26],
    4.7:  [1.65, 1.54, 1.44, 1.35, 1.27],
    4.8:  [1.66, 1.55, 1.45, 1.35, 1.27],
    4.9:  [1.67, 1.55, 1.45, 1.36, 1.27],
    5.0:  [1.68, 1.56, 1.46, 1.36, 1.28],
    # Panel 3: 5.5 – 100
    5.5:  [1.73, 1.61, 1.49, 1.39, 1.30],
    6.0:  [1.78, 1.64, 1.52, 1.41, 1.31],
    6.5:  [1.83, 1.68, 1.55, 1.43, 1.33],
    7.0:  [1.87, 1.72, 1.58, 1.45, 1.34],
    7.5:  [1.91, 1.75, 1.61, 1.47, 1.36],
    8.0:  [1.95, 1.78, 1.63, 1.49, 1.37],
    8.5:  [1.99, 1.81, 1.65, 1.51, 1.38],
    9.0:  [2.03, 1.84, 1.68, 1.53, 1.40],
    9.5:  [2.06, 1.87, 1.70, 1.54, 1.41],
    10:   [2.10, 1.89, 1.72, 1.56, 1.42],
    11:   [2.16, 1.95, 1.76, 1.59, 1.44],
    12:   [2.23, 1.99, 1.79, 1.61, 1.46],
    13:   [2.28, 2.04, 1.83, 1.64, 1.48],
    14:   [2.34, 2.08, 1.86, 1.66, 1.49],
    15:   [2.39, 2.12, 1.89, 1.68, 1.51],
    16:   [2.44, 2.16, 1.92, 1.71, 1.52],
    17:   [2.49, 2.20, 1.95, 1.73, 1.54],
    18:   [2.54, 2.23, 1.97, 1.75, 1.55],
    19:   [2.58, 2.26, 2.00, 1.76, 1.56],
    20:   [2.62, 2.30, 2.02, 1.78, 1.58],
    25:   [2.82, 2.44, 2.13, 1.86, 1.63],
    30:   [2.99, 2.57, 2.22, 1.93, 1.68],
    35:   [3.14, 2.68, 2.31, 1.98, 1.72],
    40:   [3.28, 2.78, 2.38, 2.04, 1.75],
    45:   [3.41, 2.88, 2.45, 2.08, 1.78],
    50:   [3.52, 2.96, 2.51, 2.12, 1.81],
    55:   [3.63, 3.04, 2.56, 2.16, 1.84],
    60:   [3.74, 3.12, 2.62, 2.20, 1.86],
    65:   [3.83, 3.19, 2.67, 2.23, 1.89],
    70:   [3.93, 3.25, 2.71, 2.27, 1.91],
    75:   [4.02, 3.31, 2.76, 2.30, 1.93],
    80:   [4.10, 3.37, 2.80, 2.33, 1.95],
    85:   [4.18, 3.43, 2.84, 2.35, 1.96],
    90:   [4.26, 3.49, 2.88, 2.38, 1.98],
    95:   [4.33, 3.54, 2.92, 2.40, 2.00],
    100:  [4.41, 3.59, 2.95, 2.43, 2.01],
}

# Sorted ratio list and array for interpolation
_RATIOS  = sorted(_TABLE.keys())
_CURVES  = [80, 82.5, 85, 87.5, 90]
_CURVE_IDX = {c: i for i, c in enumerate(_CURVES)}


def dilmore_factor(ratio: float, curve: float = 85) -> float:
    """
    Return the Dilmore size factor for the given A_c/A_s ratio and curve.

    Parameters
    ----------
    ratio : float
        A_c / A_s  (comparable GBA ÷ subject GBA)
    curve : float
        Elasticity curve: 80, 82.5, 85, 87.5, or 90.  Default 85.

    Returns
    -------
    float
        Size factor scalar (1.00 = no adjustment).
    """
    if curve not in _CURVE_IDX:
        valid = ", ".join(str(c) for c in _CURVES)
        raise ValueError(f"curve must be one of {valid}, got {curve}")

    col = _CURVE_IDX[curve]

    # Clamp to table bounds
    ratio = max(_RATIOS[0], min(_RATIOS[-1], ratio))

    # Find bracketing ratios for linear interpolation
    if ratio in _TABLE:
        return _TABLE[ratio][col]

    # Find the two surrounding keys
    lo = max(r for r in _RATIOS if r <= ratio)
    hi = min(r for r in _RATIOS if r >= ratio)

    if lo == hi:
        return _TABLE[lo][col]

    # Linear interpolation
    f_lo = _TABLE[lo][col]
    f_hi = _TABLE[hi][col]
    t = (ratio - lo) / (hi - lo)
    return round(f_lo + t * (f_hi - f_lo), 4)


def dilmore_adj_pct(ratio: float, curve: float = 85) -> float:
    """
    Return the size adjustment percentage for the given ratio and curve.

    Adjustment % = (size_factor - 1) × 100
      Positive → comp is larger than subject → upward adjustment
      Negative → comp is smaller than subject → downward adjustment

    Parameters
    ----------
    ratio : float   A_c / A_s
    curve : float   80 | 82.5 | 85 | 87.5 | 90

    Returns
    -------
    float  (e.g. +22.0, -15.0)
    """
    factor = dilmore_factor(ratio, curve)
    return round((factor - 1) * 100, 1)


def dilmore_summary(subject_gba: float, comp_gbas: list,
                    curve: float = 85) -> list:
    """
    Convenience function: given subject GBA and a list of comp GBAs,
    return a list of dicts with ratio, factor, and adjustment %.

    Parameters
    ----------
    subject_gba : float
    comp_gbas   : list of floats
    curve       : float

    Returns
    -------
    list of dicts:
        [{"comp": 1, "ratio": 2.3, "factor": 1.22, "adj_pct": +22.0}, ...]
    """
    results = []
    for i, comp_gba in enumerate(comp_gbas, 1):
        ratio   = comp_gba / subject_gba
        factor  = dilmore_factor(ratio, curve)
        adj_pct = dilmore_adj_pct(ratio, curve)
        results.append({
            "comp":    i,
            "comp_gba":    comp_gba,
            "ratio":       round(ratio, 4),
            "factor":      factor,
            "adj_pct":     adj_pct,
            "adj_pct_str": f"{adj_pct:+.1f}%",
        })
    return results


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Dilmore Size Adjustment Table — self-test\n")
    print(f"{'Ratio':>8}  {'Curve':>6}  {'Factor':>8}  {'Adj %':>8}")
    print("─" * 38)

    tests = [
        (0.50, 85),   # comp half the size of subject → negative adj
        (1.00, 85),   # same size → no adj
        (2.00, 85),   # comp double the size → positive adj
        (2.30, 85),   # interpolated
        (5.00, 85),
        (10.0, 85),
        (2.00, 80),   # same ratio, different curve
        (2.00, 90),
    ]
    for ratio, curve in tests:
        f   = dilmore_factor(ratio, curve)
        pct = dilmore_adj_pct(ratio, curve)
        print(f"  {ratio:6.2f}   {curve:5.1f}%   {f:7.4f}   {pct:+7.1f}%")

    print("\nSubject 22,668 SF vs comps:")
    subject = 22668
    comps   = [9780, 12144, 9554, 21166, 22088, 25272, 20000]
    for r in dilmore_summary(subject, comps, curve=85):
        print(f"  Comp {r['comp']}: {r['comp_gba']:>6.0f} SF  "
              f"ratio={r['ratio']:.3f}  factor={r['factor']:.4f}  "
              f"adj={r['adj_pct_str']}")
