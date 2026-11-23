import re

import pytest

from gemini_in_chrome.browser import BrowserError


@pytest.fixture
def page(browser, site):
    browser.open(f"{site}/page.html")
    browser.look()
    return browser


def title(b):
    """Page title without the '✨ Gemini working · ' marker the overlay adds to the agent's tab."""
    return re.sub(r"^✨ .*? working · ", "", b.page.title())


def num(browser, label):
    for e in browser.info["elements"]:
        if e["label"] == label:
            return e["i"]
    raise AssertionError(f"no element labelled {label!r}: {[e['label'] for e in browser.info['elements']]}")


def test_look_lists_elements_including_shadow_dom(page):
    text = page.look().text
    assert "Click me" in text and "Shadow upload" in text and "Search box" in text
    assert text.startswith("PAGE: Fixture page")
    assert "more below" in text      # the page is taller than the window


def test_screenshot_is_a_jpeg(page):
    assert page.look().jpeg[:3] == b"\xff\xd8\xff"


def test_click(page):
    page.click(num(page, "Click me"))
    assert page.page.evaluate("document.getElementById('count').textContent") == "Clicked 1"


def test_type_into_input_and_submit(page):
    page.type(num(page, "Search box"), "aurora", submit=True)
    assert title(page) == "submitted aurora"


def test_type_replaces_existing_text_in_contenteditable(page):
    page.type(num(page, "Editor"), "new text")
    assert page.page.evaluate("document.getElementById('editor').innerText") == "new text"


def test_label_for_input_is_used(page):
    assert "Your name" in {e["label"] for e in page.info["elements"]} or "type here" in {e["label"] for e in page.info["elements"]}


def test_overlay_and_tab_marker(page):
    page.say("Testing the overlay")
    assert page.page.evaluate("!!document.getElementById('__gic_overlay')")
    assert page.page.title().startswith("✨ Gemini working")


def test_overlay_can_be_disabled(browser, site):
    browser.cfg["overlay"] = False
    browser.open(f"{site}/page.html")
    browser.say("hidden")
    assert not browser.page.title().startswith("✨")
    assert len(browser.look().text) > 10     # numbered boxes still work


def test_scroll_reveals_more(page):
    assert "Bottom button" not in {e["label"] for e in page.info["elements"]}
    page.scroll("down", 3000)
    page.look()
    assert "Bottom button" in {e["label"] for e in page.info["elements"]}


def test_read_returns_text(page):
    text = page.read()
    assert "Fixture page" in text and "Click me" in text


def test_click_at_and_bounds(page):
    with pytest.raises(BrowserError):
        page.click_at(99999, 5)
    e = next(e for e in page.info["elements"] if e["label"] == "Click me")
    page.click_at(e["x"], e["y"])
    assert page.page.evaluate("document.getElementById('count').dataset.n") == "1"


def test_stale_element_number_is_a_clear_error(page):
    with pytest.raises(BrowserError, match="latest list"):
        page.click(9999)


def test_blocked_host_cannot_be_opened(browser, site):
    with pytest.raises(BrowserError, match="not in allowed_hosts"):
        browser.open(site.replace("127.0.0.1", "localhost") + "/other.html")


def test_navigation_to_blocked_host_by_click_is_undone(page):
    n = num(page, "Link to another site")
    with pytest.raises(BrowserError, match="went back"):
        page.click(n)
        page.page.wait_for_url("**/other.html")
        page.look()
    assert "127.0.0.1" in page.page.url


def test_upload_inside_allowed_dir(page, upload_dir):
    page.upload(num(page, "Shadow upload"), str(upload_dir / "clip.txt"))
    assert title(page) == "got clip.txt"


def test_upload_outside_allowed_dir_is_refused(page, upload_dir):
    with pytest.raises(BrowserError, match="outside the allowed upload_dirs"):
        page.upload(num(page, "Shadow upload"), str(upload_dir.parent / "secret.txt"))


def test_uploads_disabled_by_default(page):
    page.cfg["upload_dirs"] = []
    with pytest.raises(BrowserError, match="uploads are disabled"):
        page.upload(num(page, "Shadow upload"), "anything.txt")


def test_actions_need_an_open_tab(browser):
    with pytest.raises(BrowserError, match="no tab open"):
        browser.look()
