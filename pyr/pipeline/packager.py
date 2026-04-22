"""Game packager — bundles the runtime + game definition into a standalone Windows EXE."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


_LAUNCHER_TEMPLATE = '''"""Auto-generated game launcher — do not edit."""
import json, sys
from pathlib import Path

def main():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    game_json = base / "game.json"
    if not game_json.exists():
        print(f"ERROR: game.json not found at {{game_json}}")
        sys.exit(1)

    import json as _json
    from pyr.models.game import GameDefinition
    from pyr.runtime.engine import GameEngine

    data = _json.loads(game_json.read_text(encoding="utf-8"))
    game = GameDefinition.model_validate(data)
    assets = base / "assets"
    engine = GameEngine(game, assets_dir=assets if assets.exists() else None)
    engine.run()

if __name__ == "__main__":
    main()
'''

_SPEC_TEMPLATE = """# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['{launcher}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{game_json}', '.'),
        ('{assets_dir}', 'assets'),
    ],
    hiddenimports=['pyr', 'pyr.models', 'pyr.runtime', 'pygame'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='{icon}',
)
"""


class GamePackager:
    def __init__(self, game_dir: Path, output_dir: Path | None = None) -> None:
        self.game_dir = game_dir
        self.output_dir = output_dir or game_dir / "dist"
        self.build_dir = game_dir / "build"

    def package(self, progress_callback=None) -> Path:
        """Package the game into a standalone Windows EXE."""
        progress = progress_callback or print

        game_json = self.game_dir / "game.json"
        if not game_json.exists():
            raise FileNotFoundError(f"game.json not found in {self.game_dir}")

        import json
        from pyr.models.game import GameDefinition
        data = json.loads(game_json.read_text(encoding="utf-8"))
        game = GameDefinition.model_validate(data)
        game_name = _slugify(game.title)

        # Write launcher script
        launcher_path = self.build_dir / "launcher.py"
        launcher_path.parent.mkdir(parents=True, exist_ok=True)
        launcher_path.write_text(_LAUNCHER_TEMPLATE, encoding="utf-8")
        progress(f"Created launcher: {launcher_path}")

        assets_dir = self.game_dir / "assets"
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True)

        icon_path = self._find_icon()

        spec_content = _SPEC_TEMPLATE.format(
            launcher=str(launcher_path).replace("\\", "/"),
            game_json=str(game_json).replace("\\", "/"),
            assets_dir=str(assets_dir).replace("\\", "/"),
            name=game_name,
            icon=str(icon_path).replace("\\", "/") if icon_path else "",
        )
        spec_path = self.build_dir / f"{game_name}.spec"
        spec_path.write_text(spec_content, encoding="utf-8")
        progress(f"Created PyInstaller spec: {spec_path}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        progress("Running PyInstaller...")
        result = subprocess.run(
            [
                sys.executable, "-m", "PyInstaller",
                "--distpath", str(self.output_dir),
                "--workpath", str(self.build_dir / "pyinstaller_work"),
                "--noconfirm",
                str(spec_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"PyInstaller failed:\n{result.stderr}")

        exe_path = self.output_dir / f"{game_name}.exe"
        progress(f"Build complete: {exe_path}")
        return exe_path

    def _find_icon(self) -> Path | None:
        for candidate in [
            Path("pyr_icon.ico"),
            Path("pyr_icon.png"),
            self.game_dir / "icon.ico",
            self.game_dir / "icon.png",
        ]:
            if candidate.exists():
                return candidate
        return None


def _slugify(text: str) -> str:
    import re
    return re.sub(r"[^\w-]", "_", text.lower())[:40].strip("_")
