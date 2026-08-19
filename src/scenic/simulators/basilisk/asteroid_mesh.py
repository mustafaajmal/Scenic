"""Procedural asteroid meshes (Mars-rover-style terrain on a closed rock).

Scenic samples bumps / craters / ridges each ``generate()``; this module folds
them into an icosphere ellipsoid with optional multi-octave noise, then can
bake a grayscale albedo texture for Vizard.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np


@dataclass
class BumpSpec:
    """Positive Gaussian mound in asteroid-local coordinates (meters)."""

    center: Tuple[float, float, float]
    height: float
    spread: float


@dataclass
class CraterSpec:
    """Bowl + raised rim (negative Gaussian + annular ridge)."""

    center: Tuple[float, float, float]
    depth: float
    radius: float
    rim_height: float = 0.0


@dataclass
class RidgeSpec:
    """Elongated anisotropic ridge (Gaussian along a tangent axis)."""

    center: Tuple[float, float, float]
    direction: Tuple[float, float, float]
    height: float
    length: float
    width: float


def _icosphere_vertices(subdivisions: int = 2) -> np.ndarray:
    try:
        import trimesh

        mesh = trimesh.creation.icosphere(subdivisions=int(subdivisions), radius=1.0)
        return np.asarray(mesh.vertices, dtype=np.float64)
    except Exception:
        n = 20 * (4 ** max(subdivisions, 0))
        indices = np.arange(n, dtype=np.float64)
        phi = np.arccos(1.0 - 2.0 * (indices + 0.5) / n)
        theta = np.pi * (1.0 + 5.0**0.5) * indices
        x = np.sin(phi) * np.cos(theta)
        y = np.sin(phi) * np.sin(theta)
        z = np.cos(phi)
        return np.stack([x, y, z], axis=1)


def _icosphere_faces(subdivisions: int = 2) -> np.ndarray:
    try:
        import trimesh

        mesh = trimesh.creation.icosphere(subdivisions=int(subdivisions), radius=1.0)
        return np.asarray(mesh.faces, dtype=np.int64)
    except Exception:
        import trimesh

        v = _icosphere_vertices(subdivisions)
        hull = trimesh.Trimesh(vertices=v, process=True).convex_hull
        return np.asarray(hull.faces, dtype=np.int64)


def _project_to_ellipsoid(
    point: np.ndarray, radii: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Map a local point onto the ellipsoid surface; return (point, unit radial)."""
    r = np.asarray(radii, dtype=np.float64)
    p = np.asarray(point, dtype=np.float64)
    if float(np.linalg.norm(p)) < 1e-9:
        p = np.array([r[0], 0.0, 0.0])
    d = p / r
    d = d / (np.linalg.norm(d) + 1e-12)
    on_surface = d * r
    radial = on_surface / (np.linalg.norm(on_surface) + 1e-12)
    return on_surface, radial


def _hash_noise(x: np.ndarray, seed: int) -> np.ndarray:
    """Deterministic pseudo-noise in [-1, 1] from 3D points + seed."""
    # Cheap hash; good enough for rock roughness (not cryptographic).
    s = float(seed % 10007) + 0.5
    a = np.sin(x[:, 0] * 12.9898 + x[:, 1] * 78.233 + x[:, 2] * 37.719 + s) * 43758.5453
    return (a - np.floor(a)) * 2.0 - 1.0


def _fbm_noise(unit_dirs: np.ndarray, seed: int, octaves: int = 4) -> np.ndarray:
    """Multi-octave noise on unit directions."""
    amp = 1.0
    freq = 1.0
    total = np.zeros(len(unit_dirs), dtype=np.float64)
    norm = 0.0
    for o in range(max(int(octaves), 1)):
        total += amp * _hash_noise(unit_dirs * (freq * 3.1), seed + 17 * o)
        norm += amp
        amp *= 0.5
        freq *= 2.05
    return total / max(norm, 1e-9)


def _displacement_field(
    verts: np.ndarray,
    *,
    radii: np.ndarray,
    bumps: Sequence[BumpSpec],
    craters: Sequence[CraterSpec],
    ridges: Sequence[RidgeSpec],
    noise_amp: float,
    noise_seed: int,
) -> np.ndarray:
    """Radial displacement (meters) at each vertex."""
    n_verts = len(verts)
    disp = np.zeros(n_verts, dtype=np.float64)
    norms = np.linalg.norm(verts, axis=1)
    safe = norms > 1e-9
    unit = np.zeros_like(verts)
    unit[safe] = verts[safe] / norms[safe, None]

    for b in bumps:
        c, _ = _project_to_ellipsoid(np.asarray(b.center, dtype=np.float64), radii)
        s = max(float(b.spread), 1e-3)
        d2 = np.sum((verts - c) ** 2, axis=1)
        disp += float(b.height) * np.exp(-0.5 * d2 / (s * s))

    for cr in craters:
        c, _ = _project_to_ellipsoid(np.asarray(cr.center, dtype=np.float64), radii)
        rad = max(float(cr.radius), 1e-3)
        d = np.sqrt(np.sum((verts - c) ** 2, axis=1))
        # Smooth bowl.
        bowl = np.exp(-0.5 * (d / (0.55 * rad)) ** 2)
        disp -= float(cr.depth) * bowl
        # Raised rim ring.
        rim_h = float(cr.rim_height) if cr.rim_height else 0.35 * float(cr.depth)
        rim_w = 0.22 * rad
        ring = np.exp(-0.5 * ((d - 0.85 * rad) / max(rim_w, 1e-3)) ** 2)
        disp += rim_h * ring

    for ridge in ridges:
        c, _ = _project_to_ellipsoid(np.asarray(ridge.center, dtype=np.float64), radii)
        direction = np.asarray(ridge.direction, dtype=np.float64)
        dn = float(np.linalg.norm(direction))
        if dn < 1e-9:
            direction = np.array([1.0, 0.0, 0.0])
        else:
            direction = direction / dn
        # Tangent basis at ridge center.
        radial = c / (np.linalg.norm(c) + 1e-12)
        axis = direction - radial * float(np.dot(direction, radial))
        an = float(np.linalg.norm(axis))
        axis = axis / an if an > 1e-9 else np.array([0.0, 1.0, 0.0])
        across = np.cross(radial, axis)
        across = across / (np.linalg.norm(across) + 1e-12)
        rel = verts - c
        along = rel @ axis
        side = rel @ across
        L = max(float(ridge.length), 1e-3)
        W = max(float(ridge.width), 1e-3)
        profile = np.exp(-0.5 * ((along / L) ** 2 + (side / W) ** 2))
        disp += float(ridge.height) * profile

    if noise_amp and abs(float(noise_amp)) > 1e-9:
        disp += float(noise_amp) * _fbm_noise(unit, int(noise_seed), octaves=5)

    return disp


def generate_asteroid_mesh(
    *,
    radii: Sequence[float] = (50.0, 40.0, 35.0),
    bumps: Iterable[BumpSpec] = (),
    craters: Iterable[CraterSpec] = (),
    ridges: Iterable[RidgeSpec] = (),
    subdivisions: int = 3,
    noise_amp: float = 1.8,
    noise_seed: int = 0,
) -> "trimesh.Trimesh":
    """Build a closed asteroid mesh with hills, craters, ridges, and noise."""
    import trimesh

    rx, ry, rz = [float(x) for x in radii]
    radii_arr = np.array([rx, ry, rz], dtype=np.float64)
    unit = _icosphere_vertices(subdivisions)
    faces = _icosphere_faces(subdivisions)
    verts = unit * radii_arr

    bump_list = list(bumps)
    crater_list = list(craters)
    ridge_list = list(ridges)
    disp = _displacement_field(
        verts,
        radii=radii_arr,
        bumps=bump_list,
        craters=crater_list,
        ridges=ridge_list,
        noise_amp=float(noise_amp),
        noise_seed=int(noise_seed),
    )
    norms = np.linalg.norm(verts, axis=1)
    safe = norms > 1e-9
    radial = np.zeros_like(verts)
    radial[safe] = verts[safe] / norms[safe, None]
    verts = verts + radial * disp[:, None]

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    mesh.remove_unreferenced_vertices()
    # Stash displacement for texture baking (aligned with processed verts best-effort).
    mesh.metadata["radial_disp"] = disp
    mesh.metadata["noise_seed"] = int(noise_seed)
    return mesh


def raycast_surface_distance(
    mesh,
    origin_local: Sequence[float],
    direction_local: Sequence[float],
    *,
    max_range: float = 2000.0,
) -> Optional[float]:
    """Nadir-style range to the mesh (asteroid-local frame).

    Args:
        mesh: Closed ``trimesh.Trimesh`` in asteroid-local coordinates.
        origin_local: Ray origin in asteroid-local meters.
        direction_local: Ray direction (will be normalized); typically toward COM.
        max_range: Clip distance, meters.

    Returns:
        Distance to first hit, or ``None`` if no hit within ``max_range``.
    """
    o = np.asarray(origin_local, dtype=np.float64).reshape(3)
    d = np.asarray(direction_local, dtype=np.float64).reshape(3)
    n = float(np.linalg.norm(d))
    if n < 1e-12:
        return None
    d = d / n
    try:
        locations, index_ray, _index_tri = mesh.ray.intersects_location(
            ray_origins=o.reshape(1, 3),
            ray_directions=d.reshape(1, 3),
        )
    except Exception:
        return None
    if locations is None or len(locations) == 0:
        return None
    dists = np.linalg.norm(locations - o.reshape(1, 3), axis=1)
    hit = float(np.min(dists))
    if hit > float(max_range) or not np.isfinite(hit):
        return None
    return hit


def world_surface_altitude(
    mesh,
    *,
    craft_world: Sequence[float],
    asteroid_world: Sequence[float],
    fallback: Optional[float] = None,
) -> float:
    """Altitude = distance along craft→asteroid ray to the mesh surface.

    This is the PI-requested “radar straight down to the real surface” for an
    irregular rock (not a spherical shell or flat pad).
    """
    craft = np.asarray(craft_world, dtype=np.float64).reshape(3)
    ast = np.asarray(asteroid_world, dtype=np.float64).reshape(3)
    origin_local = craft - ast
    direction = ast - craft  # toward the body
    hit = raycast_surface_distance(mesh, origin_local, direction)
    if hit is None:
        if fallback is not None:
            return float(fallback)
        # Spherical-shell fallback from mesh extents.
        approx_r = 0.5 * float(np.mean(np.asarray(mesh.extents, dtype=np.float64)))
        return max(float(np.linalg.norm(origin_local)) - approx_r, 0.0)
    return float(hit)


def bake_heightmap_npz(
    mesh,
    *,
    asteroid_world: Sequence[float],
    res: float = 2.0,
    pad: float = 5.0,
) -> Tuple[np.ndarray, float, float, float]:
    """Bake top-down max-z heightmap in world frame for ``SurfaceMap``-style queries.

    Returns:
        ``(H, xmin, ymin, res)`` where ``H[iy, ix]`` is world ``z``.
    """
    ast = np.asarray(asteroid_world, dtype=np.float64).reshape(3)
    verts = np.asarray(mesh.vertices, dtype=np.float64) + ast.reshape(1, 3)
    xmin = float(verts[:, 0].min() - pad)
    xmax = float(verts[:, 0].max() + pad)
    ymin = float(verts[:, 1].min() - pad)
    ymax = float(verts[:, 1].max() + pad)
    res = max(float(res), 0.5)
    nx = int(np.ceil((xmax - xmin) / res)) + 1
    ny = int(np.ceil((ymax - ymin) / res)) + 1
    H = np.full((ny, nx), np.nan, dtype=np.float64)
    for v in verts:
        ix = int(round((float(v[0]) - xmin) / res))
        iy = int(round((float(v[1]) - ymin) / res))
        if 0 <= ix < nx and 0 <= iy < ny:
            cur = H[iy, ix]
            if not np.isfinite(cur) or float(v[2]) > cur:
                H[iy, ix] = float(v[2])
    # Fill NaNs with column-wise nearest finite (cheap).
    for iy in range(ny):
        row = H[iy]
        finite = np.isfinite(row)
        if not np.any(finite):
            continue
        idx = np.where(finite, np.arange(nx), 0)
        np.maximum.accumulate(idx, out=idx)
        row[~finite] = row[idx[~finite]]
        # back-fill leading NaNs
        first = int(np.argmax(np.isfinite(row)))
        row[:first] = row[first]
    return H, xmin, ymin, res


def write_obj(mesh, path: Path) -> Path:
    """Write mesh to Wavefront OBJ for MuJoCo ``<mesh file=...>``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(path), file_type="obj")
    return path


def write_albedo_texture(
    mesh,
    path: Path,
    *,
    size: int = 512,
    base_gray: float = 0.42,
) -> Path:
    """Bake a spherical grayscale albedo from surface roughness + seed noise.

    UVs are longitude/latitude so Vizard can wrap the JPG on the custom model.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        # Fallback: tiny solid gray JPG via numpy only is awkward; skip.
        return path

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) == 0:
        Image.fromarray(np.full((size, size), 110, dtype=np.uint8), mode="L").save(
            path, quality=90
        )
        return path

    center = verts.mean(axis=0)
    rel = verts - center
    norms = np.linalg.norm(rel, axis=1)
    unit = rel / (norms[:, None] + 1e-12)
    seed = int(mesh.metadata.get("noise_seed", 0))
    rough = 0.5 + 0.5 * _fbm_noise(unit, seed + 99, octaves=6)

    # Rasterize by projecting each vertex into lat/lon bins (scatter → fill).
    lon = np.arctan2(unit[:, 1], unit[:, 0])  # [-pi, pi]
    lat = np.arcsin(np.clip(unit[:, 2], -1.0, 1.0))  # [-pi/2, pi/2]
    u = ((lon + np.pi) / (2.0 * np.pi) * (size - 1)).astype(np.int32)
    v = ((0.5 - lat / np.pi) * (size - 1)).astype(np.int32)
    u = np.clip(u, 0, size - 1)
    v = np.clip(v, 0, size - 1)

    accum = np.zeros((size, size), dtype=np.float64)
    count = np.zeros((size, size), dtype=np.float64)
    for ui, vi, r in zip(u, v, rough):
        accum[vi, ui] += float(r)
        count[vi, ui] += 1.0

    # Fill empty bins with base + low-frequency noise.
    yy, xx = np.mgrid[0:size, 0:size]
    fill = base_gray + 0.12 * np.sin(xx * 0.07 + seed) * np.cos(yy * 0.05 + seed * 0.3)
    fill += 0.08 * np.sin(xx * 0.21 + yy * 0.17)
    img = np.where(count > 0, accum / np.maximum(count, 1.0), fill)
    # Emphasize crater-ish darker pits where roughness is low.
    img = base_gray + 0.55 * (img - 0.5)
    img = np.clip(img, 0.08, 0.92)
    pixels = (img * 255.0).astype(np.uint8)
    Image.fromarray(pixels, mode="L").save(path, quality=92)
    return path


def write_landing_xml(
    *,
    xml_path: Path,
    mesh_filename: str,
    asteroid_pos: Sequence[float],
    mesh_scale: float = 1.0,
    collision_mesh_filename: Optional[str] = None,
) -> Path:
    """Write a sat_ast_landing-like MuJoCo XML with a positioned asteroid mesh.

    Visual mesh is non-colliding; a (usually convex-hull) collision mesh provides
    a hard surface with stiff contacts so the lander does not ghost through.
    """
    ax, ay, az = [float(x) for x in asteroid_pos]
    s = float(mesh_scale)
    col_file = collision_mesh_filename or mesh_filename
    xml = f"""<mujoco>
  <option gravity="0 0 0" timestep="0.01" cone="elliptic" solver="Newton" iterations="50"/>
  <compiler meshdir="."/>

  <default class="main">
    <geom contype="1" conaffinity="1" condim="3" friction="1.5 0.1 0.001"
          solref="0.02 2.5" solimp="0.999 0.999 0.001"/>
    <default class="panel">
      <geom type="box" pos="0 0 2" size="1.1 0.05 2" rgba="0 1 0 1"/>
    </default>
    <default class="leg">
      <geom type="capsule" size="0.12" fromto="0 0 0 0 0 1.25" rgba="1 0 1 1"/>
    </default>
  </default>

  <asset>
    <mesh name="asteroid_visual" file="{mesh_filename}" scale="{s} {s} {s}"/>
    <mesh name="asteroid_collision" file="{col_file}" scale="{s} {s} {s}"/>
  </asset>

  <worldbody>
    <body name="hub">
      <freejoint name="hub"/>
      <site name="hub_origin"/>
      <camera name="navcam" pos="0 1.5 -0.8" xyaxes="1 0 0 0 1 0" fovy="60"/>
      <geom name="hub_box" type="box" size="1 1 1" rgba="1 0 0 0.5" density="200"/>
      <body name="panel_1" childclass="panel" pos="1 0 0" xyaxes="0 1 0 0 1 1">
        <geom name="panel_1_box"/>
      </body>
      <body name="panel_2" childclass="panel" pos="-1 0 0" xyaxes="0 -1 0 0 1 1">
        <geom name="panel_2_box"/>
      </body>
      <body name="leg_1" pos="0.6 0.6 -1" zaxis="0.6 0.6 -2">
        <geom name="leg_1" class="leg"/>
      </body>
      <body name="leg_2" pos="-0.6 0.6 -1" zaxis="-0.6 0.6 -2">
        <geom name="leg_2" class="leg"/>
      </body>
      <body name="leg_3" pos="-0.6 -0.6 -1" zaxis="-0.6 -0.6 -2">
        <geom name="leg_3" class="leg"/>
      </body>
      <body name="leg_4" pos="0.6 -0.6 -1" zaxis="0.6 -0.6 -2">
        <geom name="leg_4" class="leg"/>
      </body>
    </body>

    <body name="asteroid" pos="{ax} {ay} {az}">
      <geom name="asteroid_visual" type="mesh" mesh="asteroid_visual"
            contype="0" conaffinity="0" rgba="0.55 0.45 0.35 1"/>
      <geom name="asteroid_collision" type="mesh" mesh="asteroid_collision"
            contype="1" conaffinity="1" condim="3"
            solref="0.02 2.5" solimp="0.999 0.999 0.001"
            friction="1.8 0.1 0.001" rgba="0.55 0.45 0.35 0"/>
    </body>
  </worldbody>

  <actuator>
    <motor name="thrust" site="hub_origin" gear="0 0 1 0 0 0"/>
  </actuator>
</mujoco>
"""
    xml_path = Path(xml_path)
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml, encoding="utf-8")
    return xml_path
