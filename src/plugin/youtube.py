from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path, PureWindowsPath
from subprocess import Popen
from urllib.parse import quote_plus
from typing import Any, Dict, List, Optional, Tuple

from pyflowlauncher import FlowLauncherV2, Plugin, Result, api
from pyflowlauncher.models.result import PreviewInfo
from requests import RequestException
from youtube_search import YoutubeSearch

PLUGIN_DIR = Path(__file__).resolve().parent
ICON = str(PLUGIN_DIR.parent / "icon.png")
BASE_URL = "https://www.youtube.com"
THUMBNAIL_URL = "https://i.ytimg.com/vi/{id}/default.jpg"
DEFAULT_SEARCH_LIMIT = 10
MAX_CACHE_AGE = 600
SEARCH_ATTEMPTS = 3
REQUEST_TIMEOUT = 10

plugin = Plugin(launcher=FlowLauncherV2())


def load_codes(file_name: str) -> Dict[str, Optional[str]]:
    return json.loads((PLUGIN_DIR / file_name).read_text(encoding="utf-8"))


LANGUAGES = load_codes("languages.json")
REGIONS = load_codes("regions.json")

class NoResultsPage(Exception):
    pass


class VideoSearch(YoutubeSearch):
    def _search(self) -> List[dict]:
        url = f"https://youtube.com/results?search_query={quote_plus(self.search_terms)}"
        for _ in range(SEARCH_ATTEMPTS):
            page = self.session.get(url, timeout=REQUEST_TIMEOUT).text
            if "ytInitialData" in page:
                return self._parse_html(page)[: self.max_results]
        raise NoResultsPage("YouTube answered without search results. Try again in a moment.")


_cache: Dict[Tuple[Any, ...], Tuple[float, List[dict]]] = {}


def as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return default


def search_limit() -> int:
    try:
        return int(plugin.settings.get("max_search_results") or DEFAULT_SEARCH_LIMIT)
    except (TypeError, ValueError):
        return DEFAULT_SEARCH_LIMIT


def language() -> Optional[str]:
    return LANGUAGES.get(plugin.settings.get("language") or "Default")


def region() -> Optional[str]:
    return REGIONS.get(plugin.settings.get("region") or "Default")


def search_videos(query: str, limit: int, lang: Optional[str], reg: Optional[str]) -> List[dict]:
    now = time.monotonic()
    for key in [key for key, (stored, _) in _cache.items() if now - stored >= MAX_CACHE_AGE]:
        del _cache[key]
    key = (query, limit, lang, reg)
    if key not in _cache:
        videos = VideoSearch(query, max_results=limit, language=lang, region=reg).to_dict()
        _cache[key] = (now, videos)
    return _cache[key][1]


def preview(image: str, description: str) -> PreviewInfo:
    return PreviewInfo(PreviewImagePath=image, Description=description, IsMedia=image != ICON)


def flow_icon(name: str) -> str:
    return getattr(plugin.launcher.icons, name) or ICON


def menu_item(title: str, subtitle: str, icon: str) -> Result:
    return Result(title=title, subtitle=subtitle, icon=icon, preview=preview(ICON, subtitle))


def video_url(video: dict) -> str:
    return f"{BASE_URL}/watch?v={video['id']}"


def video_subtitle(video: dict) -> str:
    subtitle = " - ".join(str(part) for part in (video["publish_time"], video["channel"]) if part)
    if video["duration"]:
        subtitle += f" (Length: {video['duration']})"
    return subtitle


def video_result(video: dict) -> Result:
    url = video_url(video)
    subtitle = video_subtitle(video)
    icon = ICON
    if as_bool(plugin.settings.get("download_thumbs"), True):
        icon = THUMBNAIL_URL.format(id=video["id"])
    return Result(
        title=video["title"],
        subtitle=subtitle,
        icon=icon,
        copy_text=url,
        context_data=[url],
        preview=preview(icon, subtitle),
    ).add_action(api.open_url(url))


@plugin.on_method
async def query(query: str) -> List[Result]:
    if not query:
        return []
    loop = asyncio.get_running_loop()
    videos = await loop.run_in_executor(None, search_videos, query, search_limit(), language(), region())
    return [video_result(video) for video in videos]


@plugin.on_except(RequestException)
def connection_error(error: RequestException) -> Result:
    return menu_item("Unable to reach YouTube", str(error), ICON)


@plugin.on_except(NoResultsPage)
def no_results_page(error: NoResultsPage) -> Result:
    return menu_item("No results from YouTube", str(error), ICON)


@plugin.on_method
def context_menu(data: List[str]) -> List[Result]:
    url = data[0]
    results = [menu_item("Open in browser", "", flow_icon("Browser")).add_action(api.open_url(url))]
    program_path = plugin.settings.get("program_path")
    if program_path:
        args = (plugin.settings.get("program_args") or "{url}").format(url=url)
        results.append(
            menu_item(f"Open with: {PureWindowsPath(program_path).name}", args, program_path)
            .add_action(open_in_program, [program_path, args])
        )
    results.append(menu_item("Copy to clipboard", url, flow_icon("copy")).add_action(api.copy_to_clipboard(url)))
    return results


@plugin.on_method
def open_in_program(program_path: str, args: str) -> None:
    Popen(f'"{program_path}" {args}')
