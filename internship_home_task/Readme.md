# Authorized Partner Signup Automation

## Project Overview
This project automates the signup process of the Authorized Partner website using Selenium WebDriver, Python, and Pytest.

The project follows the Page Object Model (POM) design pattern to maintain clean, reusable, and organized automation code.

**Website:** https://authorized-partner.vercel.app/

## Technologies Used
- Python
- Selenium WebDriver
- Pytest
- Page Object Model (POM)
- Gmail API (OTP retrieval)
- Pytest HTML Report
- Git and GitHub

## Project Structure

```text
authorized_partner_signup/
│
├── pages/
│   └── signup_page.py
│
├── tests/
│   └── test_signup.py
│
├── test_data/
│   └── sample.pdf
│
├── conftest.py
├── otp_reader.py
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

## Features

- Automated signup form filling
- Automatic OTP retrieval from Gmail
- OTP verification
- Personal details validation
- Agency details submission
- Professional experience form filling
- PDF document upload
- Signup submission and verification
- HTML test report generation

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/pramila19/authorized-partner.vercel.app-signup-automation.git
```

### 2. Navigate to Project Folder

```bash
cd authorized-partner.vercel.app-signup-automation
```

### 3. Create Virtual Environment

```bash
py -m venv .venv
```

### 4. Activate Virtual Environment

```bash
.venv\Scripts\activate
```

### 5. Install Dependencies

```bash
py -m pip install -r requirements.txt
```

## Gmail OTP Configuration

1. Configure Gmail API credentials.
2. Create a `.env` file.
3. Add the required Gmail configuration.
4. Make sure credentials are not uploaded to GitHub.

## Run Automation Tests

```bash
py -m pytest tests/test_signup.py -v -s
```

## Generate HTML Test Report

```bash
py -m pytest tests/test_signup.py -v -s --html=report.html --self-contained-html
```

After execution, open `report.html` in your browser to view the test results.

## Tools Used

- VS Code
- Chrome Browser
- Selenium WebDriver
- Pytest
- GitHub

## Author

**Pramila Dulal**

GitHub: https://github.com/pramila19

## Project Status

Automation project developed for signup workflow testing and practice.