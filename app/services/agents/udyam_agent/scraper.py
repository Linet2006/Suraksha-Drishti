import asyncio
import io
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Note: pytesseract requires the Tesseract system binary to be installed.
# Ubuntu/Linux: sudo apt-get install tesseract-ocr
# Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
# You may need to specify the path to the tesseract executable on Windows if it's not in your PATH.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class UdyamVerificationError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def solve_captcha(image_bytes: bytes) -> str:
    """Pre-processes the CAPTCHA image and extracts text via Gemini API."""
    try:
        # Load image from memory
        img = Image.open(io.BytesIO(image_bytes))
        
        # Use gemini-3.5-flash for fast vision tasks
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        prompt = "Extract the text from this CAPTCHA image. Return ONLY the extracted alphanumeric characters, with NO spaces, NO punctuation, and NO markdown formatting. It is usually 6 uppercase letters and numbers."
        
        response = model.generate_content([prompt, img])
        
        captcha_text = response.text.strip().replace(" ", "")
        return captcha_text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return ""

async def verify_udyam_number(udyam_number: str) -> dict:
    """
    Navigates to the Udyam portal, solves CAPTCHA, and extracts verification details.
    Uses Playwright for headless automation and PIL + Tesseract for OCR.
    """
    url = "https://udyamregistration.gov.in/Udyam_Verify.aspx"
    max_retries = 5
    
    async with async_playwright() as p:
        # Launch Chromium (headless)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1 & 2: Navigate to homepage first to avoid bot detection redirects
            home_url = "https://udyamregistration.gov.in/Default.aspx"
            await page.goto(home_url, wait_until="domcontentloaded", timeout=60000)
            
            # Follow the human UI flow: Click Print/Verify dropdown, then Verify Udyam Registration
            print_verify_menu = page.locator("a:has-text('Print/Verify')")
            await print_verify_menu.wait_for(state="visible", timeout=10000)
            await print_verify_menu.hover()
            await print_verify_menu.click()
            
            # Wait for dropdown animation
            import asyncio
            await asyncio.sleep(2)
            
            verify_link = page.locator("a", has_text="Verify Udyam Registration")
            await verify_link.wait_for(state="visible", timeout=5000)
            
            async with page.expect_navigation(wait_until="domcontentloaded"):
                await verify_link.click()
            
            # DOM Element IDs (These might need updating based on the live site's actual DOM)
            udyam_input_id = "#ctl00_ContentPlaceHolder1_txtUdyamNo"
            captcha_input_id = "#ctl00_ContentPlaceHolder1_txtCaptcha"
            captcha_img_id = "#ctl00_ContentPlaceHolder1_imgCaptcha"
            verify_button_id = "#ctl00_ContentPlaceHolder1_btnVerify"
            
            # Wait for main input
            await page.wait_for_selector(udyam_input_id, state="visible", timeout=10000)
            
            # Step 3: Input Udyam Number
            await page.fill(udyam_input_id, udyam_number)
            
            # Step 4: Retry Loop for Zero-Cost CAPTCHA Bypass
            for attempt in range(1, max_retries + 1):
                print(f"Attempt {attempt}: Processing CAPTCHA...")
                
                # Locate CAPTCHA image and save to memory
                captcha_element = await page.query_selector(captcha_img_id)
                if not captcha_element:
                    raise UdyamVerificationError("CAPTCHA image not found on the page.", 500)
                
                captcha_bytes = await captcha_element.screenshot()
                
                # Solve CAPTCHA
                with open(f"data/debug/debug_captcha_attempt_{attempt}.png", "wb") as f:
                    f.write(captcha_bytes)
                captcha_text = solve_captcha(captcha_bytes)
                print(f"Extracted CAPTCHA: '{captcha_text}'")
                
                # Fill CAPTCHA and submit
                if captcha_text:
                    await page.fill(captcha_input_id, captcha_text)
                await page.click(verify_button_id)
                
                # Wait for response (dynamic polling because the government portal can be very slow)
                import asyncio
                
                success_element = None
                captcha_err_text = ""
                err_msg = ""
                
                print("Waiting for government portal to process...")
                for _ in range(20):
                    await asyncio.sleep(1)
                    
                    # 1. Check if success data loaded
                    success_element = await page.query_selector("#ctl00_ContentPlaceHolder1_lblEnterpriseName")
                    if success_element:
                        break
                        
                    # 2. Check if CAPTCHA error appeared
                    lblCaptchaMsg = await page.query_selector("#ctl00_ContentPlaceHolder1_lblCaptchaMsg")
                    if lblCaptchaMsg and await lblCaptchaMsg.is_visible():
                        captcha_err_text = await lblCaptchaMsg.inner_text()
                        if "Invalid" in captcha_err_text:
                            break
                            
                    # 3. Check for Invalid Udyam Number error
                    lblMsg = await page.query_selector("#ctl00_ContentPlaceHolder1_lblMsg")
                    if lblMsg and await lblMsg.is_visible():
                        err_msg = await lblMsg.inner_text()
                        if "Invalid" in err_msg or "does not exist" in err_msg.lower():
                            break
                            
                await page.screenshot(path=f"data/debug/debug_page_after_verify_attempt_{attempt}.png")
                
                # Handle Invalid Udyam Number
                if "Invalid" in err_msg or "does not exist" in err_msg.lower():
                    raise UdyamVerificationError(f"Udyam Number Error: {err_msg}", 400)
                    
                # Handle CAPTCHA error
                if "Invalid Verification Code" in captcha_err_text:
                    print("Invalid Verification Code. Refreshing CAPTCHA and retrying...")
                    refresh_btn = await page.query_selector("#ctl00_ContentPlaceHolder1_ImgRefresh")
                    if refresh_btn:
                        await refresh_btn.click()
                        await asyncio.sleep(2) # Give it time to load the new image
                    continue
                
                # Step 5: Data Extraction
                success_element = await page.query_selector("#ctl00_ContentPlaceHolder1_lblEnterpriseName")
                if success_element:
                    data = {}
                    
                    try:
                        data["udyam_number"] = udyam_number
                        data["enterprise_name"] = await page.inner_text("#ctl00_ContentPlaceHolder1_lblEnterpriseName")
                        data["enterprise_type"] = await page.inner_text("#ctl00_ContentPlaceHolder1_lblOrganisationType")
                        
                        # Major Activity can be in different spans, so get the whole TD text
                        major_act = await page.query_selector("#ctl00_ContentPlaceHolder1_trAMA")
                        data["major_activity"] = await major_act.inner_text() if major_act else ""
                        
                        data["date_of_registration"] = await page.inner_text("#ctl00_ContentPlaceHolder1_lbldateofincorporation")
                    except Exception as e:
                        print(f"Extraction warning: {e}")
                    
                    # Clean strings
                    for k, v in data.items():
                        data[k] = v.strip().replace('\n', ' ') if isinstance(v, str) else v
                    
                    return data
            
            # Step 6: Max retries reached
            raise UdyamVerificationError("Max CAPTCHA retries reached. Gemini API failed to solve the CAPTCHA.", 422)
            
        except PlaywrightTimeoutError:
            raise UdyamVerificationError("Government portal timed out or is unavailable.", 503)
        finally:
            await browser.close()
