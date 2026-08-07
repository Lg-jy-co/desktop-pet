"""桌面宠物入口。

用法：
    python main.py                 # 默认启动
    python main.py --no-click-through   # 关闭点击穿透
    python main.py --config data/config.json
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pet.app import PetApp
from pet.config import PetConfig, _from_raw, load_config


def _apply_file(cfg: PetConfig, path: Path) -> PetConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _from_raw(cfg, raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="桌面宠物")
    parser.add_argument("--no-click-through", action="store_true", help="禁用点击穿透")
    parser.add_argument("--config", default=None, help="额外配置文件路径")
    args = parser.parse_args()

    cfg = load_config()
    if args.config:
        cfg = _apply_file(cfg, Path(args.config))
    if args.no_click_through:
        cfg.click_through = False

    PetApp(cfg).run()


if __name__ == "__main__":
    main()