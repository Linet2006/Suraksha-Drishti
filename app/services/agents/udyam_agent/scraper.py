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

def solve_captcha(image_bytes: bytes) -> str:
    """Pre-processes the CAPTCHA image using PIL and extracts text via Tesseract OCR."""
    try:
        # Load image from memory
        img = Image.open(io.BytesIO(image_bytes))
        
        # Pre-process 1: Convert to Grayscale
        img = img.convert('L')
        
        # Pre-process 2: Increase Contrast to make text stand out
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Pre-process 3: Thresholding (Binarization)
        # Pixels > 128 become white (255), else black (0)
        img = img.point(lambda p: 255 if p > 128 else 0)
        
        # Tesseract configuration for alphanumeric codes
        # --psm 8: Treat image as a single word
        custom_config = r'--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        # Extract text
        captcha_text = pytesseract.image_to_string(img, config=custom_config)
        return captcha_text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
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
                with open(f"debug_captcha_attempt_{attempt}.png", "wb") as f:
                    f.write(captcha_bytes)
                captcha_text = solve_captcha(captcha_bytes)
                print(f"Extracted CAPTCHA: '{captcha_text}'")
                
                # Fill CAPTCHA and submit
                if captcha_text:
                    await page.fill(captcha_input_id, captcha_text)
                await page.click(verify_button_id)
                
                # Wait for response (network activity to settle)
                import asyncio
                await asyncio.sleep(3) # Wait 3 seconds explicitly for any AJAX to complete
                await page.screenshot(path=f"debug_page_after_verify_attempt_{attempt}.png")
                
                # Print all label texts for debugging
                lblMsg = await page.query_selector("#ctl00_ContentPlaceHolder1_lblMsg")
                if lblMsg:
                    print(f"lblMsg text: '{await lblMsg.inner_text()}'")
                
                lblCaptchaMsg = await page.query_selector("#ctl00_ContentPlaceHolder1_lblCaptchaMsg")
                if lblCaptchaMsg:
                    print(f"lblCaptchaMsg text: '{await lblCaptchaMsg.inner_text()}'")
                
                # Check for Invalid Udyam Number
                if lblMsg:
                    err_msg = await lblMsg.inner_text()
                    if "Invalid" in err_msg or "does not exist" in err_msg.lower():
                        raise UdyamVerificationError(f"Udyam Number Error: {err_msg}", 400)
                
                # Check for CAPTCHA error
                if lblCaptchaMsg:
                    captcha_err_text = await lblCaptchaMsg.inner_text()
                    if "Invalid Verification Code" in captcha_err_text:
                        print("Invalid Verification Code. Refreshing CAPTCHA and retrying...")
                        # Click the refresh button to load a new CAPTCHA
                        refresh_btn = await page.query_selector("#ctl00_ContentPlaceHolder1_ImgRefresh")
                        if refresh_btn:
                            await refresh_btn.click()
                            import asyncio
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
            raise UdyamVerificationError("Max CAPTCHA retries reached. Tesseract failed to solve the CAPTCHA.", 422)
            
        except PlaywrightTimeoutError:
            raise UdyamVerificationError("Government portal timed out or is unavailable.", 503)
        finally:
            await browser.close()
