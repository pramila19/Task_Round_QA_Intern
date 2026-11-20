import os

from otp_reader import clear_old_otps, get_otp_from_gmail
from pages.signup_page import SignupPage

BASE_URL = "https://authorized-partner.vercel.app/"
# Change the number (+run4 -> +run5 ...) every time you run, so the email is always new.
# All +runN emails arrive in the normal pramiladulal383@gmail.com inbox.
EMAIL = os.getenv("SIGNUP_EMAIL", "pramiladulal383+run45@gmail.com")
PASSWORD = "Abc123##"
SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "..", "test_data", "sample.pdf")


def test_full_signup(driver):
    signup = SignupPage(driver)

    # ---------- Step 1: Set up your Account ----------
    signup.open_page(BASE_URL)
    signup.click_get_started()
    signup.accept_terms()
    signup.click_continue()

    signup.enter_first_name("Pramila")
    signup.enter_last_name("Dulal")
    signup.enter_email(EMAIL)
    signup.enter_phone("9845982829")
    signup.enter_password(PASSWORD)
    signup.enter_confirm_password(PASSWORD)

    try:
        clear_old_otps()      # ignore OTP emails from earlier runs
    except Exception as exc:
        print(f"[warn] could not clear old OTPs: {exc.__class__.__name__}")
    signup.click_next()

    # ---------- OTP: automatic, with manual fallback ----------
    try:
        otp = get_otp_from_gmail(timeout=60)
        print(f"OTP received: {otp}")
    except Exception as exc:
        print(f"\n[auto OTP failed: {exc.__class__.__name__}]")
        otp = input("Type the OTP from your email here and press Enter: ").strip()
    signup.enter_otp(otp)

    # ---------- Step 2: Agency Details ----------
    signup.wait_for_text("Agency Details", "About your Agency", "Agency")
    signup.fill_agency_details(role="Manager", website="www.pramilaagency.com")
    signup.click_next_step()

    # ---------- Step 3: Professional Experience ----------
    signup.wait_for_text("Professional Experience", "Experience")
    signup.fill_professional_experience(years="2")
    signup.click_next_step()

    # ---------- Step 4: Verification and Preferences ----------
    signup.wait_for_text("Verification", "Preferences")
    signup.upload_document(SAMPLE_PDF)
    signup.autofill_step()
    signup.tick_all_checkboxes()
    signup.submit()

    # ---------- Result ----------
    signup.assert_signup_success()