import os
import time

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"


def ci_contains(expr, text):
    """XPath: case-insensitive contains()."""
    return f"contains(translate({expr},'{UPPER}','{LOWER}'),'{text.lower()}')"


def ci_equals(expr, text):
    """XPath: case-insensitive equals."""
    return f"translate({expr},'{UPPER}','{LOWER}')='{text.lower()}'"


def dump_page(driver):
    """Return a readable text list of everything the user can see/fill on the
    current screen. Used on test failure so you can fix locators quickly."""
    lines = [f"URL: {driver.current_url}", ""]

    def section(title, xpath, describe):
        lines.append(f"--- {title} ---")
        for el in driver.find_elements(By.XPATH, xpath):
            try:
                if el.is_displayed():
                    lines.append("  " + describe(el))
            except WebDriverException:
                pass
        lines.append("")

    section("HEADINGS", "//h1|//h2|//h3|//h4",
            lambda e: e.text.strip().replace("\n", " "))
    section("LABELS", "//label",
            lambda e: f"{e.text.strip()!r} for={e.get_attribute('for')}")
    section(
        "INPUTS / SELECTS / TEXTAREAS",
        "//input|//select|//textarea",
        lambda e: (
            f"<{e.tag_name} type={e.get_attribute('type')} name={e.get_attribute('name')} "
            f"id={e.get_attribute('id')} placeholder={e.get_attribute('placeholder')} "
            f"role={e.get_attribute('role')} value={e.get_attribute('value')!r}>"
        ),
    )
    section(
        "BUTTONS / CHECKBOXES / COMBOBOXES",
        "//button|//*[@role='checkbox']|//*[@role='combobox']|//*[@role='radio']",
        lambda e: (
            f"<{e.tag_name} role={e.get_attribute('role')} id={e.get_attribute('id')} "
            f"aria-checked={e.get_attribute('aria-checked')}> {e.text.strip()!r}"
        ),
    )
    return "\n".join(lines)


class SignupPage:
    # Default values used by autofill_step() for any field you didn't fill
    # explicitly. The key is searched inside placeholder/name/id/label text.
    AUTOFILL_HINTS = [
        (("website", "url", "www", "http"), "www.pramilaagency.com"),
        (("email",), os.getenv("SIGNUP_EMAIL", "pramiladulal383@gmail.com")),
        (("phone", "mobile", "contact number", "tel"), "9845568282"),
        (("year", "experience", "number", "count", "student"), "2"),
        (("address",), "Kathmandu, Nepal"),
        (("city",), "Kathmandu"),
        (("zip", "postal"), "44600"),
        (("registration", "license", "licence", "pan", "vat"), "123456789"),
        (("agency", "company", "business", "organization", "organisation"), "Pramila Agency"),
    ]
    DEFAULT_TEXT = "Test"
    DEFAULT_TEXTAREA = "This is an automated QA test entry."

    NEXT_TEXTS = ("Next", "Continue", "Save & Continue", "Save and Continue", "Proceed")
    SUBMIT_TEXTS = ("Submit", "Finish", "Complete", "Complete Signup", "Create Account",
                    "Sign Up", "Register", "Done", "Next", "Continue")

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self._handled_dropdowns = set()  # dropdowns already chosen (autofill must not touch them)

        # Home page
        self.get_started_btn = (By.XPATH, "//button[normalize-space(text())='Get Started'] | //a[normalize-space(text())='Get Started']")

        # Terms page (/register)
        self.terms_checkbox = (By.ID, "remember")
        self.continue_button = (By.XPATH, "//button[normalize-space(text())='Continue']")

        # Step 1 form (/register?step=setup)
        self.first_name_input = (By.XPATH, "//input[@placeholder='Enter Your First Name']")
        self.last_name_input = (By.XPATH, "//input[@placeholder='Enter Your Last Name']")
        self.email_input = (By.XPATH, "//input[@placeholder='Enter Your Email Address']")
        self.phone_input = (By.XPATH, "//input[@placeholder='00-00000000']")
        self.password_input = (By.XPATH, "//input[@name='password']")
        self.confirm_password_input = (By.XPATH, "//input[@name='confirmPassword']")
        self.next_button = (By.XPATH, "//button[normalize-space(text())='Next']")

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #
    def open_page(self, url):
        self.driver.get(url)

    def _fill(self, locator, text):
        field = self.wait.until(EC.visibility_of_element_located(locator))
        field.clear()
        field.send_keys(text)

    def _visible(self, xpath):
        found = []
        for el in self.driver.find_elements(By.XPATH, xpath):
            try:
                if el.is_displayed():
                    found.append(el)
            except StaleElementReferenceException:
                pass
        return found

    def _click(self, el):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        try:
            el.click()
        except WebDriverException:
            self.driver.execute_script("arguments[0].click();", el)

    def _hints(self, el):
        """All text that describes an input (placeholder, name, id, label...)."""
        parts = [el.get_attribute(a) or "" for a in
                 ("placeholder", "name", "id", "aria-label", "type")]
        el_id = el.get_attribute("id")
        if el_id:
            for lab in self.driver.find_elements(By.XPATH, f"//label[@for='{el_id}']"):
                parts.append(lab.text)
        try:
            parts.append(el.find_element(By.XPATH, "preceding::label[1]").text)
        except NoSuchElementException:
            pass
        return " ".join(parts).lower()

    def screenshot(self, name):
        os.makedirs("screenshots", exist_ok=True)
        path = os.path.join("screenshots", f"{name}.png")
        self.driver.save_screenshot(path)
        return path

    def click_button(self, *texts, timeout=15):
        """Click the first visible + enabled button whose text matches one of
        `texts` (checked in the order given, case-insensitive)."""

        def find(_):
            for t in texts:
                xp = f"//button[{ci_equals('normalize-space(.)', t)}]"
                for b in self._visible(xp):
                    if b.is_enabled():
                        return b
            return False

        try:
            btn = WebDriverWait(self.driver, timeout).until(find)
        except TimeoutException:
            raise AssertionError(f"No enabled button found with text {texts}. "
                                 f"Current URL: {self.driver.current_url}")
        self._click(btn)
        time.sleep(1.5)  # let the next step render

    def wait_for_text(self, *texts, timeout=15, strict=False):
        """Wait until ANY of the texts appears on the page. If strict=False we
        only warn instead of failing (our guessed titles might be slightly off)."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(t.lower() in d.page_source.lower() for t in texts))
            return True
        except TimeoutException:
            msg = f"[warn] none of {texts} appeared; URL={self.driver.current_url}"
            if strict:
                raise AssertionError(msg)
            print(msg)
            return False

    # ------------------------------------------------------------------ #
    # Home + Terms + Step 1  (your original code)
    # ------------------------------------------------------------------ #
    def click_get_started(self):
        btn = self.wait.until(EC.element_to_be_clickable(self.get_started_btn))
        btn.click()

    def accept_terms(self):
        checkbox = self.wait.until(EC.presence_of_element_located(self.terms_checkbox))
        self.driver.execute_script("arguments[0].click();", checkbox)
        time.sleep(1)

    def click_continue(self):
        self.wait.until(lambda d: d.find_element(
            *self.terms_checkbox).get_attribute("aria-checked") == "true")
        btn = self.wait.until(EC.presence_of_element_located(self.continue_button))
        self.driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)

    def enter_first_name(self, first_name):
        self._fill(self.first_name_input, first_name)

    def enter_last_name(self, last_name):
        self._fill(self.last_name_input, last_name)

    def enter_email(self, email):
        self._fill(self.email_input, email)

    def enter_phone(self, phone):
        self._fill(self.phone_input, phone)

    def enter_password(self, password):
        self._fill(self.password_input, password)

    def enter_confirm_password(self, password):
        self._fill(self.confirm_password_input, password)

    def click_next(self):
        btn = self.wait.until(EC.element_to_be_clickable(self.next_button))
        btn.click()

    # ------------------------------------------------------------------ #
    # OTP screen
    # ------------------------------------------------------------------ #
    def enter_otp(self, otp):
        """Works for both a single OTP input and 4-6 separate digit boxes."""
        otp = str(otp)

        def find_inputs(_):
            single = self._visible(
                "//input[@autocomplete='one-time-code' or @inputmode='numeric' "
                f"or @maxlength='{len(otp)}' or {ci_contains('@name', 'otp')} "
                f"or {ci_contains('@placeholder', 'otp')} or {ci_contains('@placeholder', 'code')}]")
            boxes = self._visible("//input[@maxlength='1']")
            return (single, boxes) if (single or boxes) else False

        try:
            single, boxes = WebDriverWait(self.driver, 20).until(find_inputs)
        except TimeoutException:
            raise AssertionError("OTP input not found. Check the screenshot / page dump.")

        # separate boxes (one digit each)
        if len(boxes) >= len(otp) and not any(
                (s.get_attribute("maxlength") or "") == str(len(otp)) for s in single):
            for box, digit in zip(boxes, otp):
                box.send_keys(digit)
        else:
            target = single[0]
            target.click()
            target.send_keys(otp)

        time.sleep(1)
        # Some sites auto-submit; others need a Verify button.
        try:
            self.click_button("Verify Code", "Verify", "Verify OTP", "Confirm", "Submit", "Continue", "Next", timeout=10)
        except AssertionError:
            time.sleep(2)

    # ------------------------------------------------------------------ #
    # Generic form helpers for steps 2-4
    # ------------------------------------------------------------------ #
    def _find_field(self, label, timeout=5):
        xpaths = [
            f"//*[@id=//label[{ci_contains('normalize-space(.)', label)}]/@for]",
            f"//label[{ci_contains('normalize-space(.)', label)}]/following::*"
            "[self::input or self::textarea or self::select or (self::button and @role='combobox')][1]",
            f"//*[(self::input or self::textarea) and {ci_contains('@placeholder', label)}]",
            f"//*[(self::input or self::textarea or self::select) and {ci_contains('@name', label)}]",
            f"//*[(self::input or self::textarea or self::select or self::button) and {ci_contains('@aria-label', label)}]",
        ]
        end = time.time() + timeout
        while time.time() < end:
            for xp in xpaths:
                found = self._visible(xp)
                if found:
                    return found[0]
            time.sleep(0.4)
        return None

    def _pick_option(self, text, timeout=6):
        """After a dropdown is open, click the option with this text."""
        generic = "(@role='option' or self::li or @data-radix-collection-item or @cmdk-item or @role='menuitem')"
        exact = f"//*[{generic} and {ci_equals('normalize-space(.)', text)}]"
        partial = f"//*[{generic} and {ci_contains('normalize-space(.)', text)}]"

        def find(_):
            for xp in (exact, partial):
                found = self._visible(xp)
                if found:
                    return found[0]
            return False

        option = WebDriverWait(self.driver, timeout).until(find)
        self._click(option)
        time.sleep(0.5)

    def _pick_first_option(self, timeout=6):
        xp = "//*[@role='option' or @role='menuitem' or @data-radix-collection-item or @cmdk-item]"

        def find(_):
            found = [e for e in self._visible(xp) if (e.get_attribute("aria-disabled") != "true")]
            return found[0] if found else False

        self._click(WebDriverWait(self.driver, timeout).until(find))
        time.sleep(0.5)

    def _native_select(self, el, value):
        sel = Select(el)
        try:
            sel.select_by_visible_text(value)
            return
        except NoSuchElementException:
            pass
        for opt in sel.options:
            if value.lower() in opt.text.lower():
                sel.select_by_visible_text(opt.text)
                return
        raise AssertionError(f"Option '{value}' not found in <select>")

    def set_field(self, label, value, required=True):
        """Fill ANY field (text box, textarea, <select>, custom dropdown) found
        by its label / placeholder / name text."""
        el = self._find_field(label)
        if el is None:
            if required:
                raise AssertionError(
                    f"Could not find a field for '{label}'. Open the page dump / "
                    f"screenshot in the 'screenshots' folder and adjust the label text.")
            print(f"[skip] field '{label}' not found")
            return False

        tag = el.tag_name.lower()
        role = (el.get_attribute("role") or "").lower()
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        if tag == "select":
            self._native_select(el, value)
        elif tag == "button" or (role == "combobox" and tag != "input"):
            self._click(el)
            self._pick_option(value)
        elif role == "combobox":  # searchable dropdown (input)
            self._click(el)
            el.send_keys(value)
            self._pick_option(value)
        else:
            el.click()
            el.clear()
            el.send_keys(value)
        return True

    def autofill_step(self):
        """Fill every EMPTY visible field on the current screen with sensible
        test data. This is the safety net for fields we don't know about."""
        filled = []

        # text-like inputs + textareas
        xp = ("//input[not(@type) or @type='text' or @type='number' or @type='url' "
              "or @type='tel' or @type='email'] | //textarea")
        for el in self._visible(xp):
            try:
                if el.get_attribute("readonly") or not el.is_enabled():
                    continue
                if el.get_attribute("value"):
                    continue
                if (el.get_attribute("role") or "") == "combobox":
                    self._click(el)
                    self._pick_first_option()
                    filled.append("combobox(input)")
                    continue
                hints = self._hints(el)
                if el.tag_name.lower() == "textarea":
                    value = self.DEFAULT_TEXTAREA
                elif (el.get_attribute("type") or "") == "number":
                    value = "2"
                else:
                    value = self.DEFAULT_TEXT
                    for keys, val in self.AUTOFILL_HINTS:
                        if any(k in hints for k in keys):
                            value = val
                            break
                el.click()
                el.send_keys(value)
                filled.append(f"{hints.strip()[:40]} = {value}")
            except WebDriverException as exc:
                print(f"[autofill] skipped a field: {exc.__class__.__name__}")

        # native <select>
        for sel_el in self._visible("//select"):
            try:
                sel = Select(sel_el)
                if sel.first_selected_option.get_attribute("value"):
                    continue
                for opt in sel.options:
                    if opt.get_attribute("value"):
                        sel.select_by_visible_text(opt.text)
                        filled.append(f"select = {opt.text}")
                        break
            except WebDriverException:
                pass

        # custom dropdowns that still show placeholder text ("Select ...")
        for btn in self._visible("//button[@role='combobox']"):
            try:
                if btn.id in self._handled_dropdowns:
                    continue
                text = btn.text.strip().lower()
                if not text or text.startswith(("select", "choose", "pick")):
                    self._operate_dropdown(btn, "", "dropdown")
                    filled.append("dropdown = first option")
            except WebDriverException:
                pass

        # radio groups: choose the first one if nothing selected
        groups = {}
        for r in self._visible("//input[@type='radio'] | //*[@role='radio']"):
            groups.setdefault(r.get_attribute("name") or "_role", []).append(r)
        for items in groups.values():
            checked = any(i.get_attribute("aria-checked") == "true" or
                          (i.tag_name == "input" and i.is_selected()) for i in items)
            if not checked:
                self.driver.execute_script("arguments[0].click();", items[0])
                filled.append("radio = first option")

        print(f"[autofill] {len(filled)} field(s): {filled}")
        return filled

    def tick_all_checkboxes(self):
        """Tick every unticked checkbox (preferences, declarations, terms)."""
        count = 0
        xp = "//input[@type='checkbox'] | //*[@role='checkbox']"
        for cb in self.driver.find_elements(By.XPATH, xp):
            try:
                if cb.get_attribute("aria-hidden") == "true":
                    continue  # hidden twin of a custom checkbox
                if cb.tag_name != "input" and not cb.is_displayed():
                    continue
                checked = (cb.get_attribute("aria-checked") == "true"
                           or (cb.tag_name == "input" and cb.is_selected()))
                if not checked:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});"
                        "arguments[0].click();", cb)
                    count += 1
                    time.sleep(0.3)
            except WebDriverException:
                pass
        print(f"[checkbox] ticked {count}")
        return count

    # ------------------------------------------------------------------ #
    # Step 2: Agency details
    # ------------------------------------------------------------------ #
    POPUP_XPATH = ("//*[@role='listbox' or @role='menu' or @role='dialog' or @cmdk-list "
                   "or @cmdk-root or @data-radix-popper-content-wrapper "
                   "or @data-radix-select-viewport]")

    def _dropdown_changed(self, el, before):
        try:
            now = el.text.strip()
        except WebDriverException:
            return True
        return now != before and not now.lower().startswith(("select", "choose", "pick"))

    def _choose_in_popup(self, value):
        """Click an item inside whatever popup is open: the item with `value`
        text, otherwise the first item. Works for custom lists too."""
        popups = self._visible(self.POPUP_XPATH)
        for popup in popups:
            items = [e for e in popup.find_elements(
                By.XPATH, ".//*[normalize-space(text())!='' and not(*)]") if e.is_displayed()]
            if not items:
                continue
            print("[dropdown options]", [i.text for i in items][:10])
            wanted = [i for i in items if value.lower() in i.text.lower()]
            self._click((wanted or items)[0])
            return True
        return False

    def _select_dropdown(self, label, value):
        """Pick `value` in the dropdown whose label contains `label`
        (e.g. 'Country', 'Region'). If `value` isn't in the list, the first
        option is chosen. Returns False (and skips) if the field isn't found."""
        el = self._find_field(label, timeout=4)
        if el is None:
            # custom dropdown: first button after a text that contains the label
            found = self._visible(
                f"//*[self::label or self::p or self::span or self::div]"
                f"[{ci_contains('normalize-space(text())', label)}]/following::button[1]")
            el = found[0] if found else None
        if el is None:
            print(f"[skip] '{label}' field not found")
            return False

        if el.tag_name.lower() == "select":
            try:
                self._native_select(el, value)
            except (AssertionError, NoSuchElementException):
                Select(el).select_by_index(1)
            return True

        return self._operate_dropdown(el, value, label)

    def _operate_dropdown(self, el, value, label="dropdown"):
        """Open the given dropdown element and choose `value` (empty string =
        first option). Handles searchable popups, normal option lists, chips
        and keyboard-only lists."""
        shown = el.text.strip().lower()
        is_combo = (el.get_attribute("role") == "combobox"
                    or el.get_attribute("aria-haspopup")
                    or el.get_attribute("aria-expanded") is not None
                    or el.tag_name.lower() != "button"
                    or shown.startswith(("select", "choose", "pick")))
        if not is_combo:
            # plain button / chip: one click selects it
            self._click(el)
            self._handled_dropdowns.add(el.id)
            print(f"[{label}] clicked {el.text.strip()!r}")
            time.sleep(0.5)
            return True

        before = el.text.strip()

        def ensure_open():
            if not self._visible(self.POPUP_XPATH):
                self._click(el)
                time.sleep(0.8)

        # Strategy 1: searchable list (popup with a 'Search...' box):
        # type the value, then press Enter / click the filtered item
        ensure_open()
        search = self._visible("//input[@cmdk-input or contains(@placeholder,'earch')]")
        if search:
            try:
                search[0].click()
                if value:
                    search[0].send_keys(value)
                    time.sleep(0.8)
                search[0].send_keys(Keys.ENTER)
            except WebDriverException:
                pass
            time.sleep(0.6)
            if not self._dropdown_changed(el, before):
                try:
                    self._choose_in_popup(value)
                except WebDriverException:
                    pass
                time.sleep(0.6)

        # Strategy 2: standard option elements (exact text, then first option)
        if not self._dropdown_changed(el, before):
            ensure_open()
            try:
                self._pick_option(value, timeout=3)
            except TimeoutException:
                try:
                    self._pick_first_option(timeout=3)
                except TimeoutException:
                    pass
            time.sleep(0.5)

        # Strategy 3: click an item inside whatever popup is open
        if not self._dropdown_changed(el, before):
            ensure_open()
            try:
                self._choose_in_popup(value)
            except WebDriverException:
                pass
            time.sleep(0.5)

        # Strategy 4: keyboard (arrow down + enter)
        if not self._dropdown_changed(el, before):
            try:
                ensure_open()
                active = self.driver.switch_to.active_element
                active.send_keys(Keys.ARROW_DOWN)
                active.send_keys(Keys.ENTER)
            except WebDriverException:
                pass
            time.sleep(0.5)

        # close multi-select lists that stay open
        try:
            if self._visible(self.POPUP_XPATH):
                self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        except WebDriverException:
            pass

        self._handled_dropdowns.add(el.id)
        print(f"[{label}] now shows: {el.text.strip()!r}")
        time.sleep(0.5)
        return True

    def fill_agency_details(self, role="Manager", website="www.pramilaagency.com",
                            country="Nepal", region="Nepal"):
        self.set_field("Role", role, required=False)
        self.set_field("Website", website, required=False)
        self._select_dropdown("Country", country)   # country first (region may depend on it)
        self._select_dropdown("Region", region)     # 'Region of Operation'
        self.autofill_step()  # any other required fields

    # ------------------------------------------------------------------ #
    # Step 3: Professional experience
    # ------------------------------------------------------------------ #
    def _select_services(self, service=""):
        """Select a service (empty = first option). Works for a dropdown, chips
        or tick boxes under the 'Services' heading."""
        if self._select_dropdown("Service", service):
            return True
        boxes = self.driver.find_elements(
            By.XPATH,
            f"//*[{ci_contains('normalize-space(text())', 'service')}]"
            "/following::*[@role='checkbox' or (self::input and @type='checkbox')][1]")
        if boxes:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});arguments[0].click();", boxes[0])
            print("[Service] ticked first checkbox")
            return True
        print("[skip] Services field not found")
        return False

    def fill_professional_experience(self, years="2", services=""):
        self.set_field("Year", years, required=False)
        self._select_services(services)
        self.autofill_step()

    # ------------------------------------------------------------------ #
    # Step 4: Verification & preferences
    # ------------------------------------------------------------------ #
    def upload_document(self, file_path):
        """Upload a file into every <input type=file> on the screen."""
        file_path = os.path.abspath(file_path)
        assert os.path.exists(file_path), f"File not found: {file_path}"
        inputs = self.wait.until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "input[type='file']") or False)
        for inp in inputs:
            self.driver.execute_script(
                "arguments[0].style.display='block';arguments[0].style.visibility='visible';"
                "arguments[0].style.opacity=1;", inp)
            inp.send_keys(file_path)
            time.sleep(1.5)
        return len(inputs)

    # ------------------------------------------------------------------ #
    # Navigation buttons
    # ------------------------------------------------------------------ #
    def click_next_step(self):
        self.click_button(*self.NEXT_TEXTS)

    def submit(self):
        self.click_button(*self.SUBMIT_TEXTS)

    def assert_signup_success(self, timeout=30):
        words = ("success", "congratulations", "thank you", "under review",
                 "pending", "dashboard", "welcome", "submitted")

        def done(d):
            url = d.current_url.lower()
            text = d.page_source.lower()
            return ("register" not in url) or any(w in text for w in words)

        try:
            WebDriverWait(self.driver, timeout).until(done)
        except TimeoutException:
            raise AssertionError(
                f"Signup did not finish. Still on: {self.driver.current_url}. "
                "Check for validation errors in the screenshot.")