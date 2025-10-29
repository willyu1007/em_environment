"""Output helpers for writing raster grids and Top-K diagnostics.

提供 GeoTIFF（WGS84 坐标）与 Parquet 输出，便于在服务化部署后直接向对象存储或文件系统写入。
电场强度以 dBµV/m 输出，功率密度以 W/m² 表示，Top-K 数据用于分析主要贡献源。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from .grid import GridDefinition


def _grid_resolution(grid: GridDefinition) -> tuple[float, float]:
    """Return latitude/longitude step size (degree) for a grid.

    参数
    ----
    grid : GridDefinition
        目标网格。

    返回
    ----
    tuple[float, float]
        ``(lat_step_deg, lon_step_deg)``。
    """
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
    """Persist a single-band GeoTIFF using WGS84 geographic coordinates.

    参数
    ----
    path : Path
        输出文件路径。
    grid : GridDefinition
        网格定义（提供坐标与掩膜）。
    data : np.ndarray
        要写出的数据栅格，例如电场强度 (dBµV/m) 或功率密度。
    nodata : float, 默认 ``np.nan``
        空值填充值。默认为 NaN 以保持浮点精度。

    说明
    ----
    数据会按行翻转以符合 GeoTIFF 北向上的惯例。函数确保输出目录存在，
    方便在服务化场景中直接写入磁盘或挂载的对象存储。
    """
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
        dst.write_mask((~nan_mask).astype(np.uint8) * 255)


def write_topk_parquet(
    path: Path,
    grid: GridDefinition,
    band_name: str,
    topk_indices: np.ndarray,
    topk_fraction: np.ndarray,
    topk_power_W_m2: np.ndarray,
    source_ids: Sequence[str],
) -> None:
    """Write Top-K diagnostics into a columnar Parquet file.

    参数
    ----
    path : Path
        输出文件路径。
    grid : GridDefinition
        网格定义，用于展开经纬度。
    band_name : str
        频段名称。
    topk_indices : np.ndarray
        Top-K 源索引矩阵。
    topk_fraction : np.ndarray
        对应贡献比例 (0~1)。
    topk_power_W_m2 : np.ndarray
        功率密度 (W/m²)。
    source_ids : Sequence[str]
        与索引对应的源 ID 列表。

    返回
    ----
    None

    说明
    ----
    输出表包含经纬度、频段、排名、源索引/ID、贡献比例和功率，便于下游服务直接查询或
    可视化。即使没有有效数据也会生成空表，方便流水线处理。
    """
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
