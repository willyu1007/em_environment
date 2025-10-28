"""Output helpers for writing raster grids and Top-3 diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from .grid import GridDefinition


def _grid_resolution(grid: GridDefinition) -> tuple[float, float]:
    lat_values = grid.latitudes[:, 0]
    lon_values = grid.longitudes[0, :]
    if len(lat_values) > 1:
        lat_res = float(abs(lat_values[1] - lat_values[0]))
    else:
        lat_res = float(grid.resolution_deg)
    if len(lon_values) > 1:
        lon_res = float(abs(lon_values[1] - lon_values[0]))
    else:
        lon_res = float(grid.resolution_deg)
    return lat_res, lon_res


def write_geotiff(path: Path, grid: GridDefinition, data: np.ndarray, nodata: float = np.nan) -> None:
    """Persist a single-band GeoTIFF using WGS84 geographic coordinates."""
    import rasterio
    from rasterio.transform import from_origin

    path.parent.mkdir(parents=True, exist_ok=True)

    lat_res, lon_res = _grid_resolution(grid)
    top_lat = float(np.max(grid.latitudes[:, 0]))
    left_lon = float(np.min(grid.longitudes[0, :]))
    transform = from_origin(left_lon, top_lat, lon_res, lat_res)

    data_to_write = np.flipud(data).astype(np.float32)
    if np.isnan(nodata):
        nan_mask = np.isnan(data_to_write)
        fill_value = np.float32(np.nan)
    else:
        fill_value = np.float32(nodata)
        nan_mask = np.isnan(data_to_write)
        data_to_write[nan_mask] = fill_value

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data_to_write.shape[0],
        width=data_to_write.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=float(fill_value),
    ) as dst:
        dst.write(data_to_write, 1)
        dst.write_mask(np.flipud(~nan_mask).astype(np.uint8) * 255)


def write_topk_parquet(
    path: Path,
    grid: GridDefinition,
    band_name: str,
    topk_indices: np.ndarray,
    topk_fraction: np.ndarray,
    topk_power_W_m2: np.ndarray,
    source_ids: Sequence[str],
) -> None:
    """Write Top-3 diagnostics into a columnar Parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)

    top_k = topk_indices.shape[0]
    mask_flat = grid.mask.ravel()
    if top_k == 0 or not np.any(mask_flat):
        table = pa.table(
            {
                "lat": pa.array([], type=pa.float64()),
                "lon": pa.array([], type=pa.float64()),
                "band": pa.array([], type=pa.string()),
                "rank": pa.array([], type=pa.int16()),
                "source_index": pa.array([], type=pa.int32()),
                "source_id": pa.array([], type=pa.string()),
                "fraction": pa.array([], type=pa.float32()),
                "power_W_m2": pa.array([], type=pa.float32()),
            }
        )
        pq.write_table(table, path)
        return

    lat_flat = grid.latitudes.ravel()[mask_flat]
    lon_flat = grid.longitudes.ravel()[mask_flat]

    topk_indices_flat = topk_indices.reshape(top_k, -1)[:, mask_flat].T  # (Npix, top_k)
    fraction_flat = topk_fraction.reshape(top_k, -1)[:, mask_flat].T
    power_flat = topk_power_W_m2.reshape(top_k, -1)[:, mask_flat].T

    num_pixels = lat_flat.shape[0]
    rank_column = np.tile(np.arange(top_k, dtype=np.int16), num_pixels)
    lat_column = np.repeat(lat_flat.astype(np.float64), top_k)
    lon_column = np.repeat(lon_flat.astype(np.float64), top_k)

    source_idx_column = topk_indices_flat.reshape(-1).astype(np.int32)
    valid_mask = source_idx_column >= 0
    source_idx_column = np.where(valid_mask, source_idx_column, -1)
    source_ids_array = np.array(source_ids, dtype=object)
    source_id_column = np.empty(source_idx_column.shape[0], dtype=object)
    source_id_column[valid_mask] = source_ids_array[source_idx_column[valid_mask]]
    source_id_column[~valid_mask] = None

    fraction_column = fraction_flat.reshape(-1).astype(np.float32)
    power_column = power_flat.reshape(-1).astype(np.float32)

    table = pa.Table.from_arrays(
        [
            pa.array(lat_column),
            pa.array(lon_column),
            pa.array(np.repeat(band_name, lat_column.shape[0])),
            pa.array(rank_column),
            pa.array(source_idx_column),
            pa.array(source_id_column, type=pa.string()),
            pa.array(fraction_column),
            pa.array(power_column),
        ],
        names=[
            "lat",
            "lon",
            "band",
            "rank",
            "source_index",
            "source_id",
            "fraction",
            "power_W_m2",
        ],
    )

    pq.write_table(table, path)
