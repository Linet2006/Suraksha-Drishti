import asyncio
from playwright.async_api import async_playwright

async def test_udyam_site():
    home_url = "https://udyamregistration.gov.in/Default.aspx"
    
    async with async_playwright() as p:
        print("Launching browser with headless=True...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"Navigating to homepage: {home_url}...")
            await page.goto(home_url, wait_until="domcontentloaded", timeout=60000)
            
            print("Finding 'Print/Verify' menu...")
            print_verify_menu = page.locator("a:has-text('Print/Verify')")
            await print_verify_menu.wait_for(state="visible", timeout=10000)
            
            print("Hovering and Clicking 'Print/Verify'...")
            await print_verify_menu.hover()
            await print_verify_menu.click()
            await asyncio.sleep(2)
            
            print("Clicking 'Verify Udyam Registration'...")
            verify_link = page.locator("a", has_text="Verify Udyam Registration")
            await verify_link.wait_for(state="visible", timeout=5000)
            
            async with page.expect_navigation(wait_until="domcontentloaded"):
                await verify_link.click()
                
            print(f"Current URL: {page.url}")
            
            # Wait for an input to appear
            await page.wait_for_selector("input[type='text']", timeout=10000)
            
            print("Scanning inputs on the page:")
            inputs = await page.locator("input").all()
            for i, element in enumerate(inputs):
                id_attr = await element.get_attribute("id")
                name_attr = await element.get_attribute("name")
                type_attr = await element.get_attribute("type")
                placeholder = await element.get_attribute("placeholder")
                print(f"Input {i}: id='{id_attr}', name='{name_attr}', type='{type_attr}', placeholder='{placeholder}'")
            
            print("Scanning for CAPTCHA image...")
            images = await page.locator("img").all()
            for i, element in enumerate(images):
                src = await element.get_attribute("src")
                id_attr = await element.get_attribute("id")
                if "captcha" in (src or "").lower() or "captcha" in (id_attr or "").lower():
                    print(f"Found CAPTCHA img: id='{id_attr}', src='{src}'")
                    
            print("Scanning for buttons...")
            buttons = await page.locator("button, input[type='submit'], input[type='button']").all()
            for i, element in enumerate(buttons):
                id_attr = await element.get_attribute("id")
                val = await element.get_attribute("value")
                text = await element.text_content()
                print(f"Button {i}: id='{id_attr}', value='{val}', text='{text}'")

        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_udyam_site())
