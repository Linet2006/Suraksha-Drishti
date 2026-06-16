import asyncio
import os
import uuid
from typing import Dict, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import pdfplumber

class TradeLicenceVerificationError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

async def verify_trade_licence(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automates the BBMP Trade License Verification portal.
    1. Navigates to the portal.
    2. Inputs application details (Application Number + Trade Type).
    3. Triggers the Download button via ASP.NET __doPostBack.
    4. Downloads the certificate PDF if valid.
    5. Parses the PDF to extract fields.
    """
    url = "https://trade.bbmpgov.in/Forms/frmLicenceAppDownloadPublic.aspx"
    application_number = payload.get("application_number", "")
    # Trade Type: "1" = Trade & Power, "2" = Trade, "3" = Power. Default to "2" (Trade).
    trade_type = payload.get("trade_type", "2")
    
    if not application_number:
        raise TradeLicenceVerificationError("Application Number is required.", 400)

    # Storage setup
    download_dir = os.path.join(os.getcwd(), "data", "trade_licenses")
    os.makedirs(download_dir, exist_ok=True)
    
    unique_tx_id = str(uuid.uuid4())
    pdf_path = os.path.join(download_dir, f"trade_license_{unique_tx_id}.pdf")
    
    extracted_text = ""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Set realistic user agent to prevent bot blocking
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = await context.new_page()
        
        try:
            # 1. Navigate to Target Portal
            print(f"Navigating to {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightError as e:
                error_str = str(e)
                if "ERR_NAME_NOT_RESOLVED" in error_str:
                    raise TradeLicenceVerificationError(
                        "The BBMP portal (trade.bbmpgov.in) is currently unreachable. "
                        "This is a DNS resolution failure — the government server may be down. "
                        "Please try again in a few minutes.", 503
                    )
                elif "ERR_CONNECTION_REFUSED" in error_str or "ERR_CONNECTION_TIMED_OUT" in error_str:
                    raise TradeLicenceVerificationError(
                        "The BBMP portal refused the connection or timed out. "
                        "The government server may be under maintenance. "
                        "Please try again later.", 503
                    )
                else:
                    raise TradeLicenceVerificationError(
                        f"Failed to reach the BBMP portal: {error_str}", 503
                    )
            
            # Wait for form to settle
            await asyncio.sleep(2)
            
            # --- Exact selectors from the live BBMP portal HTML ---
            app_no_selector = "#ContentPlaceHolder1_txtApplicationNumber"
            trade_type_selector = "#ContentPlaceHolder1_ddlTradeType"
            download_btn_selector = "#ContentPlaceHolder1_btnSearch"
            
            # 2. Ensure form fields are interactable and input data
            try:
                await page.wait_for_selector(app_no_selector, state="visible", timeout=10000)
                await page.fill(app_no_selector, application_number)
                print(f"Filled Application Number: {application_number}")
                
                # Select Trade Type from dropdown
                await page.select_option(trade_type_selector, trade_type)
                print(f"Selected Trade Type: {trade_type}")
            except PlaywrightTimeoutError:
                raise TradeLicenceVerificationError("Could not locate input fields on the BBMP portal.", 500)
                
            # Handle javascript alerts (common for 'Invalid ID' on government portals)
            alert_messages = []
            async def handle_dialog(dialog):
                alert_messages.append(dialog.message)
                await dialog.dismiss()
            page.on("dialog", handle_dialog)
            
            # 3. Execute the "Download" button via JS click (bypasses the disabled-on-click handler)
            print("Clicking Download button via JS...")
            download = None
            try:
                # Listen for the download event immediately upon clicking (1-step ASPX flow)
                async with page.expect_download(timeout=20000) as download_info:
                    # Use the ASPX __doPostBack mechanism directly
                    await page.evaluate("""() => {
                        __doPostBack('ctl00$ContentPlaceHolder1$btnSearch','');
                    }""")
                download = await download_info.value
            except PlaywrightTimeoutError:
                # No download triggered — check for errors
                pass
            
            # Wait for any error messages or alerts to appear
            await asyncio.sleep(2)
            
            # 4. Verification Logic: Check for Alerts or "No Records Found"
            if alert_messages:
                error_msg = " | ".join(alert_messages)
                raise TradeLicenceVerificationError(f"Rejection/Invalid: Portal returned alert: {error_msg}", 404)
                
            page_text = await page.content()
            lower_page = page_text.lower()
            
            # Check for common error indicators (but NOT false positives from generic page text)
            error_indicators = ["no record found", "does not exist", "application not found"]
            for indicator in error_indicators:
                if indicator in lower_page:
                    raise TradeLicenceVerificationError(
                        f"Rejection/Invalid: No Records Found for Application Number '{application_number}'.", 404
                    )
            
            # If no download was triggered yet, try finding a download link in the results
            if not download:
                print("No immediate download. Checking for result links...")
                try:
                    async with page.expect_download(timeout=15000) as download_info:
                        # Try clicking any download/print link in the result area
                        await page.evaluate("""() => {
                            const links = Array.from(document.querySelectorAll('a, input[type="image"], input[type="submit"]'));
                            const downloadBtn = links.find(l => 
                                (l.innerText && (l.innerText.toLowerCase().includes('download') || l.innerText.toLowerCase().includes('print'))) || 
                                (l.id && (l.id.toLowerCase().includes('download') || l.id.toLowerCase().includes('print'))) ||
                                (l.value && (l.value.toLowerCase().includes('download') || l.value.toLowerCase().includes('print')))
                            );
                            if(downloadBtn) downloadBtn.click();
                        }""")
                    download = await download_info.value
                except PlaywrightTimeoutError:
                    raise TradeLicenceVerificationError(
                        "Could not download certificate. The Application Number may be invalid, "
                        "not approved, or the Trade Type selection is incorrect.", 404
                    )
            
            # Save the downloaded file
            await download.save_as(pdf_path)
            print(f"Certificate downloaded successfully to: {pdf_path}")
                
        except TradeLicenceVerificationError:
            # Re-raise our custom errors as-is
            raise
        except PlaywrightTimeoutError:
            raise TradeLicenceVerificationError("The BBMP portal timed out. Gateway Timeout.", 504)
        except Exception as e:
            # Catch any other Playwright/network error
            error_str = str(e)
            if "ERR_NAME_NOT_RESOLVED" in error_str:
                raise TradeLicenceVerificationError(
                    "The BBMP portal (trade.bbmpgov.in) is currently unreachable. Please try again later.", 503
                )
            raise TradeLicenceVerificationError(f"Unexpected browser error: {error_str}", 500)
        finally:
            await browser.close()
            
    # 6. PDF Extraction (Verification)
    try:
        print(f"Parsing PDF: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            for pg in pdf.pages:
                page_text = pg.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        raise TradeLicenceVerificationError("Failed to parse the downloaded certificate PDF.", 500)
    
    # 7. Format the Output
    return {
        "application_number": application_number,
        "transaction_id": unique_tx_id,
        "pdf_path": pdf_path,
        "scraped_text": extracted_text.strip()
    }
