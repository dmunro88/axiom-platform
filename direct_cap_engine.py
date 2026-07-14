"""
direct_cap_engine.py — Axiom Commercial Appraisal Platform
============================================================
Direct Capitalization calculation engine, ported from Excel to pure Python
per the Appraisal Institute's *General Appraiser Income Approach/Part 1*
course (PC403GCH-M) and its Solutions Booklet (PC403GSB-M), rather than
reverse-engineered from the platform's prior Excel formulas -- those
formulas had real, confirmed defects: an off-by-one row-shift in
income_summary pulling from the wrong expense_comp rows (driving NOI
negative), and cap_rates!E4:E7 computing NOI = rate x price -- backwards.

Every worked example in the source material agrees: the overall
capitalization rate is extracted from a comparable sale as
R_O = NOI / Sale Price, and applied to the subject as V_O = NOI / R_O.
The same extraction/application pattern (F = Price / Income; V = Income x F)
holds identically for every multiplier (PGIM, EGIM, GRM, NIM).

No function in this module reconciles multiple comps' indications into one
concluded rate or value -- that is an appraiser judgment call, not a
calculation, matching sca_engine.py's design.

Pure functions, no I/O, no persistence -- this module knows nothing about
the workbook, the DB, or the delivery pipeline.

Explicitly out of scope for this module (see project plan/HANDOFF.md):
time-value-of-money/annuity math (loan amortization, PV/FV, sinking
funds -- a separate foundational module), leasehold/leased-fee residual
(belongs with DCF/yield capitalization), and property-tax cap-rate
"loading" (no verified worked example exists yet).
"""

from dataclasses import dataclass


class DirectCapEngineError(Exception):
    """Raised on invalid input (e.g. a zero denominator that has no
    meaningful appraisal interpretation) -- mirrors sca_engine.py's
    SCAEngineError and adjustment_grid.py's AdjustmentGridError: fail
    loudly rather than silently miscompute or divide by zero."""


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EGIResult:
    total_pgi: float
    vacancy_and_collection_loss: float
    egi: float


@dataclass(frozen=True)
class NOIResult:
    total_operating_expenses: float
    noi: float
    operating_expense_ratio: float
    net_income_ratio: float


@dataclass(frozen=True)
class ResidualResult:
    known_component_income: float
    residual_income: float
    solved_value: float
    total_value: float


# ── PGI -> EGI -> NOI ────────────────────────────────────────────────────────


def compute_egi(pgi, vacancy_collection_loss_pct, reimbursements=0.0,
                 other_income=0.0, other_income_subject_to_vacancy=True):
    """Total PGI = PGI + reimbursements (reimbursements ADD to PGI, they are
    not netted against a specific expense line -- confirmed by the 9.11
    Problem worked example). Vacancy and collection loss is applied to
    total PGI (and to other_income too, if other_income_subject_to_vacancy).

    The returned `total_pgi` always means PGI + reimbursements only
    (matching the textbook's own "Total PGI" line item), regardless of
    other_income_subject_to_vacancy -- other_income is never folded into
    it, even internally, so a caller reading total_pgi gets consistent
    semantics no matter which vacancy-treatment branch was taken.
    """
    if reimbursements < 0:
        raise DirectCapEngineError("reimbursements cannot be negative")
    if not (0 <= vacancy_collection_loss_pct <= 1):
        raise DirectCapEngineError(
            "vacancy_collection_loss_pct must be between 0 and 1"
        )

    total_pgi = pgi + reimbursements
    if other_income_subject_to_vacancy:
        vacancy_basis = total_pgi + other_income
        vacancy_loss = vacancy_basis * vacancy_collection_loss_pct
        egi = vacancy_basis - vacancy_loss
    else:
        vacancy_loss = total_pgi * vacancy_collection_loss_pct
        egi = total_pgi - vacancy_loss + other_income

    return EGIResult(
        total_pgi=total_pgi,
        vacancy_and_collection_loss=vacancy_loss,
        egi=egi,
    )


def compute_noi(egi, fixed_expenses, variable_expenses, replacement_allowance=0.0):
    """NOI = EGI - Total Operating Expenses, where Total Operating Expenses
    = Fixed + Variable + Replacement Allowance (Part 9 p.178)."""
    if egi == 0:
        raise DirectCapEngineError("compute_noi requires a nonzero EGI")

    total_expenses = fixed_expenses + variable_expenses + replacement_allowance
    noi = egi - total_expenses
    oer = total_expenses / egi
    nir = 1 - oer
    return NOIResult(
        total_operating_expenses=total_expenses,
        noi=noi,
        operating_expense_ratio=oer,
        net_income_ratio=nir,
    )


# ── Multipliers and overall capitalization rate ─────────────────────────────


def extract_overall_cap_rate(noi, sale_price):
    """R_O = NOI / Sale Price (Part 13 p.242-243, Part 21 p.412) -- the
    direction the platform's prior Excel formula had backwards."""
    if sale_price == 0:
        raise DirectCapEngineError("sale_price cannot be zero")
    return noi / sale_price


def apply_overall_cap_rate(noi, cap_rate):
    """V_O = NOI / R_O."""
    if cap_rate == 0:
        raise DirectCapEngineError("cap_rate cannot be zero")
    return noi / cap_rate


def extract_multiplier(sale_price, income):
    """F = Sale Price / Income -- the same extraction shape used for PGIM,
    EGIM, GRM, and NIM (Part 13 p.234-243); which multiplier this is
    depends only on which income figure the caller passes in."""
    if income == 0:
        raise DirectCapEngineError("income cannot be zero")
    return sale_price / income


def apply_multiplier(income, multiplier):
    """V = Income x Multiplier."""
    return income * multiplier


def cap_rate_from_nir_and_egim(nir, egim):
    """R_O = NIR / EGIM -- a cross-check relationship, confirmed exact in
    the 13.10 Problem worked example (both this and NOI/Price land on the
    identical rate)."""
    if egim == 0:
        raise DirectCapEngineError("egim cannot be zero")
    return nir / egim


# ── Band of investment ──────────────────────────────────────────────────────


def band_of_investment_mortgage_equity(loan_to_value_ratio, mortgage_rate, equity_rate):
    """R_O = M x R_M + (1 - M) x R_E (Part 15 p.279)."""
    return loan_to_value_ratio * mortgage_rate + (1 - loan_to_value_ratio) * equity_rate


def solve_equity_rate(overall_rate, loan_to_value_ratio, mortgage_rate):
    """R_E = (R_O - M x R_M) / (1 - M)."""
    equity_ratio = 1 - loan_to_value_ratio
    if equity_ratio == 0:
        raise DirectCapEngineError("loan_to_value_ratio cannot be 1 (no equity component)")
    return (overall_rate - loan_to_value_ratio * mortgage_rate) / equity_ratio


def band_of_investment_land_building(land_ratio, land_rate, building_rate):
    """R_O = L x R_L + B x R_B, where B = 1 - L (Part 15/19)."""
    return land_ratio * land_rate + (1 - land_ratio) * building_rate


def solve_land_rate(overall_rate, building_ratio, building_rate):
    """R_L = (R_O - B x R_B) / L, where L = 1 - B."""
    land_ratio = 1 - building_ratio
    if land_ratio == 0:
        raise DirectCapEngineError("building_ratio cannot be 1 (no land component)")
    return (overall_rate - building_ratio * building_rate) / land_ratio


def solve_building_rate(overall_rate, land_ratio, land_rate):
    """R_B = (R_O - L x R_L) / B, where B = 1 - L."""
    building_ratio = 1 - land_ratio
    if building_ratio == 0:
        raise DirectCapEngineError("land_ratio cannot be 1 (no building component)")
    return (overall_rate - land_ratio * land_rate) / building_ratio


def underwriters_method_cap_rate(loan_to_value_ratio, mortgage_rate, debt_coverage_ratio):
    """R_O = M x R_M x DCR (Part 14 p.261-265). A result that disagrees
    with a market-extracted R_O is not an error in the formula -- it
    signals the lender's quoted terms are not actually at market (confirmed
    by the 14.2 Problem worked example)."""
    return loan_to_value_ratio * mortgage_rate * debt_coverage_ratio


# ── Residual techniques ──────────────────────────────────────────────────────


def building_residual(noi, land_value, land_rate, building_rate):
    """Building Residual: land value is known, solve for building value
    (Part 16 p.309-311)."""
    if building_rate == 0:
        raise DirectCapEngineError("building_rate cannot be zero")
    land_income = land_rate * land_value
    residual_income = noi - land_income
    building_value = residual_income / building_rate
    return ResidualResult(
        known_component_income=land_income,
        residual_income=residual_income,
        solved_value=building_value,
        total_value=land_value + building_value,
    )


def land_residual(noi, building_value, building_rate, land_rate):
    """Land Residual: building value is known, solve for land value (Part
    16 p.309-311). A negative residual_income/solved_value is a valid,
    meaningful result -- it signals the tested use is not financially
    feasible (confirmed by the 16.8 four-scenario highest-and-best-use
    worked example); this function does not raise on it."""
    if land_rate == 0:
        raise DirectCapEngineError("land_rate cannot be zero")
    building_income = building_rate * building_value
    residual_income = noi - building_income
    land_value = residual_income / land_rate
    return ResidualResult(
        known_component_income=building_income,
        residual_income=residual_income,
        solved_value=land_value,
        total_value=building_value + land_value,
    )


def extract_building_rate_via_residual(noi, land_value, land_rate, building_value):
    """Extracts (rather than applies) the building capitalization rate via
    the residual technique, when total NOI, land value, land rate, and
    building value are all known (16.5 Problem, Part 16 p.309-311) -- the
    inverse of building_residual: there, building_rate is given and
    building_value is solved for; here, building_value is given and
    building_rate is solved for."""
    if building_value == 0:
        raise DirectCapEngineError("building_value cannot be zero")
    land_income = land_rate * land_value
    building_income = noi - land_income
    return building_income / building_value


def mortgage_equity_residual(noi, mortgage_value, mortgage_rate, equity_rate):
    """Mortgage/Equity Residual: mortgage value is known (given directly,
    not derived from loan amortization -- see module docstring), solve for
    equity value (Part 17 p.331-333)."""
    if equity_rate == 0:
        raise DirectCapEngineError("equity_rate cannot be zero")
    mortgage_income = mortgage_rate * mortgage_value
    residual_income = noi - mortgage_income
    equity_value = residual_income / equity_rate
    return ResidualResult(
        known_component_income=mortgage_income,
        residual_income=residual_income,
        solved_value=equity_value,
        total_value=mortgage_value + equity_value,
    )


# ── Reversion via terminal capitalization rate ──────────────────────────────


def forecast_income(year1_income, growth_rate, target_year):
    """Year_N income = Year_1 income x (1 + growth_rate) ** (N - 1)
    (confirmed exact in the 14.4 Problem worked example)."""
    if target_year < 1:
        raise DirectCapEngineError("target_year must be >= 1")
    return year1_income * (1 + growth_rate) ** (target_year - 1)


def terminal_cap_rate(going_in_rate, load):
    """R_N = R_O (going-in) + load (a basis-point addition reflecting a
    building aging into a weaker competitive position over the holding
    period -- Part 14 p.267-269)."""
    return going_in_rate + load


def reversion_value(forecasted_income, terminal_rate):
    """Reversion value = Year_N income / R_N."""
    if terminal_rate == 0:
        raise DirectCapEngineError("terminal_rate cannot be zero")
    return forecasted_income / terminal_rate


# ── NOI adjustment between comps ────────────────────────────────────────────


def noi_adjustment_factor(subject_noi_psf, comp_noi_psf):
    """NOI Adjustment Factor = Subject NOI/SF / Comp NOI/SF.

    Confirmed with Derek 2026-07-13: this exact grid (GBA / Sale $/SF /
    NOI/SF Comp / NOI/SF Subject / NOI Adj. Factor / Adj. Indicated $/SF)
    does not appear as a named technique in either source document -- it is
    a standard-practice extension of the textbook's own rate-extraction
    principle (Part 13/21), not a page-cited textbook formula. Re-expresses
    a comparable's price per SF in terms of the subject's own income per
    SF, implicitly applying that comp's own market-derived rate to the
    subject's income level."""
    if comp_noi_psf == 0:
        raise DirectCapEngineError("comp_noi_psf cannot be zero")
    return subject_noi_psf / comp_noi_psf


def apply_noi_adjustment(comp_price_psf, factor):
    """Adjusted Indicated $/SF = Comp $/SF x NOI Adjustment Factor."""
    return comp_price_psf * factor
