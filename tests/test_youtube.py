import asyncio
import json
from pathlib import Path

import pytest
import requests

import youtube

ROOT = Path(__file__).resolve().parents[1]


def run(method, *params):
    response = asyncio.run(youtube.plugin._event_handler.trigger_event(method, *params))
    return response["Result"]


def titles(results):
    return [result["Title"] for result in results]


def test_empty_query_does_not_search(search):
    assert run("query", "") == []
    assert search.calls == []


def test_results_keep_youtube_order_and_open_the_video(search):
    results = run("query", "sourdough")
    assert titles(results) == ["Sourdough for beginners", "Shaping a boule"]
    first = results[0]
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert first["SubTitle"] == "2 years ago - Bread Club (Length: 12:04)"
    assert first["IcoPath"] == "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg"
    assert first["CopyText"] == url
    assert first["ContextData"] == [url]
    assert first["JsonRPCAction"]["Method"] == "Flow.Launcher.OpenUrl"
    assert first["JsonRPCAction"]["Parameters"][0] == url
    assert first["Preview"]["PreviewImagePath"] == first["IcoPath"]


def test_mix_results_open_the_video_without_the_playlist(search):
    mix = run("query", "sourdough")[1]
    url = "https://www.youtube.com/watch?v=a1b2c3d4e5f"
    assert mix["CopyText"] == url
    assert mix["ContextData"] == [url]
    assert mix["JsonRPCAction"]["Parameters"][0] == url


@pytest.mark.parametrize("value", [False, "false", "False"])
def test_thumbnails_can_be_turned_off(search, settings, value):
    settings["download_thumbs"] = value
    result = run("query", "sourdough")[0]
    assert result["IcoPath"] == youtube.ICON
    assert result["Preview"]["IsMedia"] is False


def test_default_settings_are_passed_to_the_search(search):
    run("query", "sourdough")
    assert search.calls == [("sourdough", 10, None, None)]


def test_settings_are_passed_to_the_search(search, settings):
    settings.update({"max_search_results": "25", "language": "Deutsch", "region": "Germany"})
    run("query", "sourdough")
    assert search.calls == [("sourdough", 25, "de", "DE")]


def test_unknown_setting_values_fall_back_to_defaults(search, settings):
    settings.update({"max_search_results": "lots", "language": "Klingon", "region": None})
    run("query", "sourdough")
    assert search.calls == [("sourdough", 10, None, None)]


def test_repeated_queries_are_cached_for_ten_minutes(search, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(youtube.time, "monotonic", lambda: clock[0])
    run("query", "sourdough")
    clock[0] += 599
    run("query", "sourdough")
    assert len(search.calls) == 1
    clock[0] += 1
    run("query", "sourdough")
    assert len(search.calls) == 2


def test_query_with_a_url_does_not_crash(search):
    assert titles(run("query", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")) == [
        "Sourdough for beginners",
        "Shaping a boule",
    ]


def test_network_errors_are_shown_as_a_result(search):
    search.error = requests.exceptions.SSLError("certificate verify failed")
    (result,) = run("query", "sourdough")
    assert result["Title"] == "Unable to reach YouTube"
    assert result["SubTitle"] == "certificate verify failed"
    assert result["Preview"] is not None


def test_context_menu_without_custom_program(settings):
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    results = run("context_menu", [url])
    assert titles(results) == ["Open in browser", "Copy to clipboard"]
    assert results[0]["JsonRPCAction"]["Method"] == "Flow.Launcher.OpenUrl"
    assert results[0]["JsonRPCAction"]["Parameters"][0] == url
    assert results[1]["SubTitle"] == url
    assert results[1]["JsonRPCAction"]["Method"] == "Flow.Launcher.CopyToClipboard"
    assert results[1]["JsonRPCAction"]["Parameters"][0] == url


def test_context_menu_opens_custom_program(settings):
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    settings.update({
        "program_path": r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
        "program_args": "{url}",
    })
    results = run("context_menu", [url])
    assert titles(results) == ["Open in browser", "Open with: PotPlayerMini64.exe", "Copy to clipboard"]
    assert results[1]["SubTitle"] == url
    assert results[1]["IcoPath"] == settings["program_path"]
    assert results[1]["JsonRPCAction"] == {
        "Method": "open_in_program",
        "Parameters": [settings["program_path"], url],
        "DontHideAfterAction": False,
    }


def test_open_in_program_starts_the_program(monkeypatch):
    started = []
    monkeypatch.setattr(youtube, "Popen", started.append)
    asyncio.run(youtube.plugin._event_handler.trigger_event("open_in_program", "mpv.exe", "https://youtu.be/x"))
    assert started == [["mpv.exe", "https://youtu.be/x"]]


def test_manifest_keeps_plugin_identity():
    manifest = json.loads((ROOT / "data" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["ID"] == "42DE0794627A48B2847E6FDF29DD5561"
    assert manifest["ActionKeyword"] == "yt"
    assert manifest["Language"] == "python_v2"
    assert manifest["ExecuteFileName"] == "run.py"


def setting_options(name):
    template = (ROOT / "data" / "SettingsTemplate.yaml").read_text(encoding="utf-8")
    block = template.split(f"name: {name}\n", 1)[1].split("- type:", 1)[0]
    options = block.split("options:\n", 1)[1]
    return [line.strip()[2:] for line in options.splitlines() if line.strip().startswith("- ")]


@pytest.mark.parametrize("name, codes", [("language", youtube.LANGUAGES), ("region", youtube.REGIONS)])
def test_every_dropdown_option_has_a_code(name, codes):
    options = setting_options(name)
    assert options[0] == "Default"
    assert set(options) == set(codes)
