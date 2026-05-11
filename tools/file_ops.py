# JARVIS Tool — File Operations
"""File management tools — create, delete, move, copy, rename, search, open."""

import os
import shutil
import platform
from pathlib import Path
from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("create_file")
class CreateFileTool(BaseTool):
    tool_id = "create_file"
    name = "Create File/Folder"
    description = "Create a new file or folder"
    permission_tier = "confirm"
    parameters = [ToolParam(name="name", description="Name/path to create")]

    def execute(self, params: dict) -> ToolResult:
        name = params.get("name", "").strip()
        if not name:
            return ToolResult(content="No name provided", success=False)
        target = Path(name).expanduser()
        try:
            if not target.suffix:
                target.mkdir(parents=True, exist_ok=True)
                return ToolResult(content=f"Created folder: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            return ToolResult(content=f"Created file: {target}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("delete_file")
class DeleteFileTool(BaseTool):
    tool_id = "delete_file"
    name = "Delete File/Folder"
    description = "Delete a file or folder (DESTRUCTIVE)"
    permission_tier = "admin"
    parameters = [ToolParam(name="target", description="Path to delete")]
    PROTECTED = {"C:\\Windows", "C:\\Program Files", "/", "/usr", "/bin"}

    def execute(self, params: dict) -> ToolResult:
        target = params.get("target", "").strip()
        if not target:
            return ToolResult(content="No target", success=False)
        path = Path(target).expanduser().resolve()
        if str(path) in self.PROTECTED:
            return ToolResult(content=f"BLOCKED: protected path", success=False)
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            else:
                return ToolResult(content=f"Not found: {path}", success=False)
            return ToolResult(content=f"Deleted {path}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("move_file")
class MoveFileTool(BaseTool):
    tool_id = "move_file"
    name = "Move File"
    description = "Move a file or folder to a new location"
    permission_tier = "confirm"
    parameters = [
        ToolParam(name="source", description="Source path"),
        ToolParam(name="destination", description="Destination path"),
    ]

    def execute(self, params: dict) -> ToolResult:
        src, dst = params.get("source", ""), params.get("destination", "")
        if not src or not dst:
            return ToolResult(content="Source and destination required", success=False)
        try:
            shutil.move(src, dst)
            return ToolResult(content=f"Moved {src} → {dst}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("copy_file")
class CopyFileTool(BaseTool):
    tool_id = "copy_file"
    name = "Copy File"
    description = "Copy a file or folder"
    permission_tier = "confirm"
    parameters = [
        ToolParam(name="source", description="Source path"),
        ToolParam(name="destination", description="Destination path"),
    ]

    def execute(self, params: dict) -> ToolResult:
        src, dst = params.get("source", ""), params.get("destination", "")
        if not src or not dst:
            return ToolResult(content="Source and destination required", success=False)
        try:
            if Path(src).is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return ToolResult(content=f"Copied {src} → {dst}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("rename_file")
class RenameFileTool(BaseTool):
    tool_id = "rename_file"
    name = "Rename File"
    description = "Rename a file or folder"
    permission_tier = "confirm"
    parameters = [
        ToolParam(name="source", description="Current name"),
        ToolParam(name="destination", description="New name"),
    ]

    def execute(self, params: dict) -> ToolResult:
        src, dst = params.get("source", ""), params.get("destination", "")
        try:
            Path(src).rename(dst)
            return ToolResult(content=f"Renamed {src} → {dst}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("open_file")
class OpenFileTool(BaseTool):
    tool_id = "open_file"
    name = "Open File"
    description = "Open a file with the default application"
    permission_tier = "auto"
    parameters = [ToolParam(name="target", description="File path to open")]

    def execute(self, params: dict) -> ToolResult:
        target = params.get("target", "").strip()
        if not target:
            return ToolResult(content="No file specified", success=False)
        try:
            if platform.system() == "Windows":
                os.startfile(target)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", target])
            return ToolResult(content=f"Opened {target}")
        except Exception as e:
            return ToolResult(content=f"Failed: {e}", success=False)


@ToolRegistry.register("search_file")
class SearchFileTool(BaseTool):
    tool_id = "search_file"
    name = "Search Files"
    description = "Search for files by name in common directories"
    permission_tier = "auto"
    parameters = [ToolParam(name="query", description="Filename pattern to search")]

    def execute(self, params: dict) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(content="No query", success=False)
        results = []
        for d in [Path.home()/"Desktop", Path.home()/"Documents", Path.home()/"Downloads"]:
            if not d.exists():
                continue
            try:
                for m in d.glob(f"*{query}*"):
                    results.append(str(m))
                for m in d.glob(f"*/*{query}*"):
                    results.append(str(m))
            except PermissionError:
                continue
            if len(results) >= 10:
                break
        if results:
            unique = list(dict.fromkeys(results))[:10]
            return ToolResult(content="Found:\n" + "\n".join(unique))
        return ToolResult(content=f"No files matching '{query}'", success=False)
