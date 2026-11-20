import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from pages.signup_page import dump_page


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
def driver(request):
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    drv = webdriver.Chrome(options=options)
    yield drv

    # If the test failed, save a screenshot + list of fields on the screen
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        os.makedirs("screenshots", exist_ok=True)
        name = request.node.name
        drv.save_screenshot(os.path.join("screenshots", f"{name}.png"))
        dump = dump_page(drv)
        with open(os.path.join("screenshots", f"{name}_page_dump.txt"), "w", encoding="utf-8") as f:
            f.write(dump)
        print("\n===== PAGE DUMP AT FAILURE =====\n" + dump)
    drv.quit()
