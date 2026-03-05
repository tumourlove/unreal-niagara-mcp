"""Niagara curve generation tools -- pure Python math, no editor needed."""

from __future__ import annotations

import json
import math


from unreal_niagara_mcp.server import mcp


# ---------------------------------------------------------------------------
# Curve function implementations
# ---------------------------------------------------------------------------

def _linear(t: float) -> float:
    return t


def _ease_in(t: float) -> float:
    return t * t


def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) * (1.0 - t)


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def _sine(t: float, frequency: float = 1.0, phase: float = 0.0) -> float:
    return math.sin(t * frequency * 2.0 * math.pi + phase)


def _cosine(t: float, frequency: float = 1.0, phase: float = 0.0) -> float:
    return math.cos(t * frequency * 2.0 * math.pi + phase)


def _exponential(t: float) -> float:
    if t <= 0.0:
        return 0.0
    return math.pow(2.0, 10.0 * (t - 1.0))


def _logarithmic(t: float) -> float:
    if t <= 0.0:
        return 0.0
    return math.log(t + 1.0) / math.log(2.0)


def _bell_curve(t: float) -> float:
    x = (t - 0.5) * 4.0
    return math.exp(-x * x / 2.0)


def _sawtooth(t: float, frequency: float = 1.0) -> float:
    return (t * frequency) % 1.0


def _bounce(t: float) -> float:
    if t < 1.0 / 2.75:
        return 7.5625 * t * t
    elif t < 2.0 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


def _step(t: float) -> float:
    return 0.0 if t < 0.5 else 1.0


_FUNCTIONS = {
    "linear": _linear,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
    "sine": _sine,
    "cosine": _cosine,
    "exponential": _exponential,
    "logarithmic": _logarithmic,
    "bell_curve": _bell_curve,
    "sawtooth": _sawtooth,
    "bounce": _bounce,
    "step": _step,
}


def _evaluate_custom(expression: str, t: float) -> float:
    """Evaluate a simple math expression with 't' as the variable.

    Supports: +, -, *, /, **, sin, cos, sqrt, abs, pi, e, pow, exp, log.
    """
    safe_globals = {
        "__builtins__": {},
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "abs": abs,
        "pi": math.pi,
        "e": math.e,
        "pow": math.pow,
        "exp": math.exp,
        "log": math.log,
        "min": min,
        "max": max,
        "t": t,
    }
    try:
        return float(eval(expression, safe_globals))  # noqa: S307
    except Exception as exc:
        raise ValueError(f"Cannot evaluate expression '{expression}' at t={t}: {exc}") from exc


def _compute_tangent(values: list[float], times: list[float], idx: int) -> float:
    """Compute tangent at index via finite differences."""
    if len(values) < 2:
        return 0.0
    if idx == 0:
        dt = times[1] - times[0]
        return (values[1] - values[0]) / dt if dt != 0 else 0.0
    if idx == len(values) - 1:
        dt = times[-1] - times[-2]
        return (values[-1] - values[-2]) / dt if dt != 0 else 0.0
    dt = times[idx + 1] - times[idx - 1]
    return (values[idx + 1] - values[idx - 1]) / dt if dt != 0 else 0.0


def generate_curve_keys(
    function_type: str,
    domain_start: float = 0.0,
    domain_end: float = 1.0,
    num_keys: int = 10,
    amplitude: float = 1.0,
    frequency: float = 1.0,
    phase: float = 0.0,
    custom_expression: str | None = None,
) -> list[dict]:
    """Generate curve key data from a mathematical function.

    Returns a list of key dicts with: time, value, arrive_tangent, leave_tangent.
    """
    if num_keys < 2:
        num_keys = 2

    times: list[float] = []
    values: list[float] = []

    for i in range(num_keys):
        t_norm = i / (num_keys - 1)
        t = domain_start + t_norm * (domain_end - domain_start)
        times.append(t)

        if function_type == "custom":
            if custom_expression is None:
                raise ValueError("custom_expression is required for 'custom' function type")
            raw = _evaluate_custom(custom_expression, t_norm)
        elif function_type in ("sine", "cosine"):
            func = _FUNCTIONS[function_type]
            raw = func(t_norm, frequency=frequency, phase=phase)
        elif function_type == "sawtooth":
            raw = _sawtooth(t_norm, frequency=frequency)
        else:
            func = _FUNCTIONS.get(function_type)
            if func is None:
                available = ", ".join(sorted(list(_FUNCTIONS.keys()) + ["custom"]))
                raise ValueError(
                    f"Unknown function type '{function_type}'. Available: {available}"
                )
            raw = func(t_norm)

        values.append(raw * amplitude)

    # Compute tangents
    keys = []
    for i in range(num_keys):
        tangent = _compute_tangent(values, times, i)
        keys.append({
            "time": round(times[i], 6),
            "value": round(values[i], 6),
            "arrive_tangent": round(tangent, 6),
            "leave_tangent": round(tangent, 6),
        })

    return keys


@mcp.tool()
def generate_curve_from_function(
    function_type: str,
    domain_start: float = 0.0,
    domain_end: float = 1.0,
    num_keys: int = 10,
    amplitude: float = 1.0,
    frequency: float = 1.0,
    phase: float = 0.0,
    custom_expression: str = "",
) -> str:
    """Generate curve keys from a mathematical function for use with Niagara curves.

    Produces curve key data (time, value, tangents) that can be fed
    to the SetCurveValue C++ function to populate Niagara curve parameters.

    Pure math -- does not require the editor.

    Available function types: linear, ease_in, ease_out, ease_in_out,
    sine, cosine, exponential, logarithmic, bell_curve, sawtooth,
    bounce, step, custom.

    For 'custom', provide a math expression using 't' (0-1), e.g. 'sin(t*pi)*t'.

    function_type: Type of curve function
    domain_start: Start of the time domain (default 0.0)
    domain_end: End of the time domain (default 1.0)
    num_keys: Number of keys to generate (default 10, minimum 2)
    amplitude: Scale factor for values (default 1.0)
    frequency: For periodic functions (default 1.0)
    phase: Phase offset for periodic functions in radians (default 0.0)
    custom_expression: Math expression for 'custom' type, using 't' as variable
    """
    try:
        keys = generate_curve_keys(
            function_type=function_type,
            domain_start=domain_start,
            domain_end=domain_end,
            num_keys=int(num_keys),
            amplitude=amplitude,
            frequency=frequency,
            phase=phase,
            custom_expression=custom_expression or None,
        )
    except ValueError as e:
        return f"Error: {e}"

    lines = [
        f"Curve: {function_type}",
        f"  Domain: [{domain_start}, {domain_end}]",
        f"  Amplitude: {amplitude}",
    ]
    if function_type in ("sine", "cosine", "sawtooth"):
        lines.append(f"  Frequency: {frequency}")
        lines.append(f"  Phase: {phase}")
    if function_type == "custom":
        lines.append(f"  Expression: {custom_expression}")
    lines.append(f"  Keys: {len(keys)}")
    lines.append("")

    # Table
    lines.append("  Time      Value     ArriveTan  LeaveTan")
    lines.append("  ------    ------    ---------  --------")
    for k in keys:
        lines.append(
            f"  {k['time']:8.4f}  {k['value']:8.4f}  {k['arrive_tangent']:9.4f}  {k['leave_tangent']:8.4f}"
        )

    lines.append("")
    lines.append("--- JSON Keys ---")
    lines.append(json.dumps(keys, indent=2))

    return "\n".join(lines)
