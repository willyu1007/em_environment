"""Command-line interface for offline compute runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..api_models import ComputeRequest
from ..service import ComputeService


def load_request(path: Path) -> ComputeRequest:
    """Load a compute request JSON file.

    参数
    ----
    path : Path
        JSON 文件路径，内容需符合 :class:`ComputeRequest` 结构，单位规范与 API 模型一致。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return ComputeRequest(**data)


def main() -> None:
    """Entry point for command-line batch runs.

    支持读取 JSON 请求、执行计算以及输出统计信息，可选写入 GeoTIFF/Parquet。
    该入口与服务化接口共享同一计算引擎，方便在 CI 或离线环境复用。
    """
    parser = argparse.ArgumentParser(description="EM environment compute CLI")
    parser.add_argument("input", type=Path, help="Path to JSON request file.")
    parser.add_argument("--band", type=str, help="Band name to summarize (defaults to first band).")
    parser.add_argument("--output-dir", type=Path, help="Directory to write GeoTIFF and Top-3 outputs.")
    args = parser.parse_args()

    request = load_request(args.input)
    service = ComputeService()
    result = service.run_compute(request, output_dir=args.output_dir)

    target_band = args.band or next(iter(result.band_results))
    band_res = result.band_results[target_band]

    mask = result.grid.mask
    field = np.ma.masked_array(band_res.field_strength_dbuv_per_m, mask=~mask)

    print(f"Computed bands: {', '.join(result.band_results.keys())}")
    print(f"Band: {band_res.name} (center {band_res.center_freq_MHz:.2f} MHz)")
    print(f"Field strength stats (dBμV/m): min={field.min():.2f}, max={field.max():.2f}, mean={field.mean():.2f}")
    if args.output_dir:
        print(f"Outputs written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
