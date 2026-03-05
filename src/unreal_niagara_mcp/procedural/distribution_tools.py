"""Particle distribution generation tools -- pure Python math, no editor needed."""

from __future__ import annotations

import json
import math
import random

from unreal_niagara_mcp.server import mcp


# ---------------------------------------------------------------------------
# Distribution generators
# ---------------------------------------------------------------------------

def _fibonacci_sphere(count: int, radius: float) -> list[list[float]]:
    """Distribute points on a sphere using Fibonacci spiral."""
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
    points = []
    for i in range(count):
        theta = 2.0 * math.pi * i / golden_ratio
        phi = math.acos(1.0 - 2.0 * (i + 0.5) / count)
        x = radius * math.sin(phi) * math.cos(theta)
        y = radius * math.sin(phi) * math.sin(theta)
        z = radius * math.cos(phi)
        points.append([round(x, 4), round(y, 4), round(z, 4)])
    return points


def _phyllotaxis_disk(count: int, radius: float) -> list[list[float]]:
    """Distribute points on a disk using phyllotaxis (sunflower) pattern."""
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    points = []
    for i in range(count):
        r = radius * math.sqrt(i / count)
        theta = i * golden_angle
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        points.append([round(x, 4), round(y, 4), 0.0])
    return points


def _cube_surface(count: int, radius: float) -> list[list[float]]:
    """Distribute points on the surface of a cube."""
    half = radius
    points_per_face = max(1, count // 6)
    remainder = count - points_per_face * 6
    points = []

    faces = [
        (0, 1, 2, half),   # +X
        (0, 1, 2, -half),  # -X
        (1, 0, 2, half),   # +Y
        (1, 0, 2, -half),  # -Y
        (2, 0, 1, half),   # +Z
        (2, 0, 1, -half),  # -Z
    ]

    for face_idx, (fixed_axis, a1, a2, fixed_val) in enumerate(faces):
        n = points_per_face + (1 if face_idx < remainder else 0)
        side = max(1, int(math.ceil(math.sqrt(n))))
        generated = 0
        for row in range(side):
            if generated >= n:
                break
            for col in range(side):
                if generated >= n:
                    break
                pt = [0.0, 0.0, 0.0]
                pt[fixed_axis] = fixed_val
                pt[a1] = -half + (2.0 * half * row / max(1, side - 1))
                pt[a2] = -half + (2.0 * half * col / max(1, side - 1))
                points.append([round(pt[0], 4), round(pt[1], 4), round(pt[2], 4)])
                generated += 1

    return points[:count]


def _sphere_surface(count: int, radius: float) -> list[list[float]]:
    """Distribute points randomly on a sphere surface."""
    points = []
    for _ in range(count):
        u = random.random()
        v = random.random()
        theta = 2.0 * math.pi * u
        phi = math.acos(2.0 * v - 1.0)
        x = radius * math.sin(phi) * math.cos(theta)
        y = radius * math.sin(phi) * math.sin(theta)
        z = radius * math.cos(phi)
        points.append([round(x, 4), round(y, 4), round(z, 4)])
    return points


def _golden_spiral(count: int, radius: float) -> list[list[float]]:
    """Distribute points along a 3D golden spiral."""
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
    points = []
    for i in range(count):
        t = i / max(1, count - 1)
        r = radius * t
        theta = 2.0 * math.pi * golden_ratio * i
        phi = math.acos(1.0 - 2.0 * t)
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)
        points.append([round(x, 4), round(y, 4), round(z, 4)])
    return points


def _poisson_disk(count: int, radius: float) -> list[list[float]]:
    """Simple Poisson disk sampling in 2D (on XY plane).

    Uses dart-throwing with a maximum iteration limit.
    """
    min_dist = radius * 2.0 / math.sqrt(count) if count > 0 else radius
    points: list[list[float]] = []
    max_attempts = count * 30

    for _ in range(max_attempts):
        if len(points) >= count:
            break
        x = random.uniform(-radius, radius)
        y = random.uniform(-radius, radius)
        # Check if inside circle
        if x * x + y * y > radius * radius:
            continue
        # Check minimum distance
        too_close = False
        for p in points:
            dx = x - p[0]
            dy = y - p[1]
            if dx * dx + dy * dy < min_dist * min_dist:
                too_close = True
                break
        if not too_close:
            points.append([round(x, 4), round(y, 4), 0.0])

    return points


def _attractor(count: int, radius: float, params: dict | None = None) -> list[list[float]]:
    """Generate points from a strange attractor (Lorenz by default).

    params can override: sigma, rho, beta, dt, steps_per_point.
    """
    params = params or {}
    sigma = float(params.get("sigma", 10.0))
    rho = float(params.get("rho", 28.0))
    beta = float(params.get("beta", 8.0 / 3.0))
    dt = float(params.get("dt", 0.005))
    steps_per_point = int(params.get("steps_per_point", 10))

    x, y, z = 1.0, 1.0, 1.0
    points = []
    scale = radius / 30.0  # Lorenz attractor roughly spans +-30

    for i in range(count):
        for _ in range(steps_per_point):
            dx = sigma * (y - x)
            dy = x * (rho - z) - y
            dz = x * y - beta * z
            x += dx * dt
            y += dy * dt
            z += dz * dt
        points.append([
            round(x * scale, 4),
            round(y * scale, 4),
            round(z * scale, 4),
        ])

    return points


_DISTRIBUTIONS = {
    "fibonacci_sphere": _fibonacci_sphere,
    "phyllotaxis_disk": _phyllotaxis_disk,
    "cube_surface": _cube_surface,
    "sphere_surface": _sphere_surface,
    "golden_spiral": _golden_spiral,
    "poisson_disk": _poisson_disk,
}


@mcp.tool()
def create_particle_distribution(
    distribution_type: str,
    count: int = 100,
    radius: float = 100.0,
    params: str = "",
) -> str:
    """Generate particle position distributions using mathematical patterns.

    Pure math -- does not require the editor.
    Returns position arrays as JSON suitable for feeding into Niagara spawn modules.

    Available types: fibonacci_sphere, phyllotaxis_disk, cube_surface,
    sphere_surface, golden_spiral, poisson_disk, attractor.

    distribution_type: Type of distribution pattern
    count: Number of positions to generate (default 100)
    radius: Radius/scale of the distribution (default 100.0)
    params: Optional JSON object with type-specific parameters (e.g. for attractor: '{"sigma":10}')
    """
    extra_params = {}
    if params:
        try:
            extra_params = json.loads(params)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON for params: {params[:200]}"

    count = max(1, int(count))
    radius = float(radius)

    if distribution_type == "attractor":
        positions = _attractor(count, radius, extra_params)
    else:
        func = _DISTRIBUTIONS.get(distribution_type)
        if func is None:
            available = ", ".join(sorted(list(_DISTRIBUTIONS.keys()) + ["attractor"]))
            return f"Unknown distribution type '{distribution_type}'. Available: {available}"
        positions = func(count, radius)

    # Compute bounding box
    if positions:
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        zs = [p[2] for p in positions]
        bbox = {
            "min": [round(min(xs), 2), round(min(ys), 2), round(min(zs), 2)],
            "max": [round(max(xs), 2), round(max(ys), 2), round(max(zs), 2)],
        }
    else:
        bbox = {"min": [0, 0, 0], "max": [0, 0, 0]}

    lines = [
        f"Particle Distribution: {distribution_type}",
        f"  Count: {len(positions)} (requested {count})",
        f"  Radius: {radius}",
        f"  Bounding Box: [{bbox['min'][0]}, {bbox['min'][1]}, {bbox['min'][2]}] to "
        f"[{bbox['max'][0]}, {bbox['max'][1]}, {bbox['max'][2]}]",
    ]
    if extra_params:
        lines.append(f"  Extra Params: {json.dumps(extra_params)}")
    lines.append("")

    # Show first few points as preview
    preview_count = min(5, len(positions))
    lines.append(f"Preview (first {preview_count}):")
    for i in range(preview_count):
        p = positions[i]
        lines.append(f"  [{i}] ({p[0]}, {p[1]}, {p[2]})")
    if len(positions) > preview_count:
        lines.append(f"  ... and {len(positions) - preview_count} more")

    lines.append("")
    lines.append("--- JSON Positions ---")
    lines.append(json.dumps(positions))

    return "\n".join(lines)
