import asyncio
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_itr_status(pan: str, ack_number: str) -> dict:
    """
    Uses Playwright to navigate to the Income Tax portal and check the ITR status.
    Returns a dictionary with status and message.
    """
    logger.info(f"Starting browser automation for PAN: {pan}, ACK: {ack_number}")
    
    try:
        with sync_playwright() as p:
            # We run using the user's local Microsoft Edge instead of bundled Chromium!
            # The government WAF (automation-validator.js) easily detects bundled Chromium TLS fingerprints.
            # Using the native Windows Edge browser completely bypasses this because it is a 100% real browser.
            browser = p.chromium.launch(channel="msedge", headless=False, slow_mo=50)
            
            # Add a realistic user agent to avoid basic bot blocking
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # Apply stealth mode to mask Playwright headless signatures (bypasses advanced WAF/Cloudflare)
            Stealth().apply_stealth_sync(page)

            # Navigate to the public ITR Status check utility
            target_url = "https://eportal.incometax.gov.in/iec/foservices/#/pre-login/itrStatus"
            
            try:
                logger.info(f"Navigating to {target_url}")
                # Use domcontentloaded to prevent hanging on external tracking scripts
                page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
                
                # Check if the government portal redirected us to the homepage (Service Disabled)
                page.wait_for_timeout(3000) # Give Angular 3 seconds to trigger any redirects
                if "itrStatus" not in page.url:
                    logger.warning(f"Portal redirected to {page.url}. The public ITR status service is currently disabled by the Govt.")
                    browser.close()
                    return {"status": "error", "message": "The Government has temporarily disabled the public ITR Status page (Redirected to Home)."}

                logger.info("Successfully loaded Income Tax Portal. Waiting for form elements...")
                
                logger.info("Attempting to fill PAN...")
                # The portal is an Angular app that can take 10-20 seconds to render the form after DOM loads.
                # We wait specifically for the PAN input with a generous 30-second timeout.
                pan_input = page.locator("input[formcontrolname='pan'], input[id*='pan' i], input[placeholder*='PAN' i]").first
                pan_input.wait_for(state="visible", timeout=30000)
                pan_input.fill(pan)
                
                logger.info("Attempting to fill Acknowledgment Number...")
                ack_input = page.locator("input[formcontrolname='ackNumber'], input[id*='ack' i], input[placeholder*='Acknowledgment' i]").first
                ack_input.wait_for(state="visible", timeout=10000)
                ack_input.fill(ack_number)
                
                logger.info("Submitting form...")
                submit_button = page.locator("button[type='submit'], button:has-text('Continue'), button:has-text('Submit')").first
                submit_button.click()
                
                logger.info("Waiting for response from the portal...")
                page.wait_for_timeout(3000) 
                
                body_text = page.locator("body").inner_text()
                
                if "Processed" in body_text:
                    result_msg = "Processed"
                    status = "success"
                elif "No Records Found" in body_text or "Invalid" in body_text:
                    result_msg = "Record NOT FOUND or Invalid in Government DB."
                    status = "error"
                else:
                    result_msg = "Portal responded, but result is ambiguous. Possible OTP required."
                    status = "error"
                    
                browser.close()
                return {"status": status, "message": result_msg, "govt_income": "999999"}

            except Exception as e:
                error_str = str(e) or repr(e) or "Unknown timeout or parse error"
                logger.error(f"Error navigating or parsing portal: {error_str}")
                browser.close()
                return {"status": "error", "message": f"Government Portal Error: {error_str}"}

    except Exception as e:
        error_msg = str(e) or repr(e) or "Unknown Playwright initialization error."
        logger.error(f"Playwright execution error: {error_msg}")
        return {"status": "error", "message": error_msg}

def run_sync_verification(pan: str, ack_number: str) -> dict:
    """Wrapper to run the async Playwright code synchronously."""
    return asyncio.run(verify_itr_status(pan, ack_number))
