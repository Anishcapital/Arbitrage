import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from PIL import Image
import io
import re

# === Always use Ace folder as base ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "melbet")
MATCH_FILE = os.path.join(BASE_DIR, "match.txt")

SITE_NAME = "melbet"
BATCH_SIZE = 3
MOBILE_HEIGHT = 731

MOBILE_DEVICE = {
    "viewport": {"width": 411, "height": MOBILE_HEIGHT},
    "user_agent": "Mozilla/5.0 (Linux; Android 10; Pixel 2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

def normalize(s):
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9. ]+', '', s)
    return s.strip()

def get_match_name_from_link(link):
    path = urlparse(link).path
    last_part = path.rstrip('/').split('/')[-1]
    match = re.search(r'\d+-(.+)$', last_part)
    if match:
        team_names = match.group(1)
        team_names = team_names.replace('-', ' ')
        return team_names
    return normalize(last_part)

async def robust_auto_scroll(page, max_wait=20):
    last_height = await page.evaluate("() => document.body.scrollHeight")
    for _ in range(max_wait * 2):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        await page.wait_for_timeout(500)
        new_height = await page.evaluate("() => document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

async def wait_for_markets(page, timeout=15000):
    try:
        await page.wait_for_selector(".game-markets-group", timeout=timeout)
        await page.wait_for_timeout(2000)
    except:
        print("⚠️ Markets/odds not found after waiting.")

async def process_batch(batch_links, batch_num):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=MOBILE_DEVICE["viewport"],
            user_agent=MOBILE_DEVICE["user_agent"],
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page = await context.new_page()

        for i, link in enumerate(batch_links):
            print(f"[Batch {batch_num}] Opening match {i+1}: {link}")
            try:
                await page.goto(link, timeout=60000)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)

                tabs = await page.query_selector_all('.game-sub-games__item')
                print(f"  Found {len(tabs)} market sections.")

                match_name = get_match_name_from_link(link)
                match_folder = os.path.join(OUTPUT_FOLDER, match_name)
                os.makedirs(match_folder, exist_ok=True)

                for idx in range(len(tabs)):
                    tabs = await page.query_selector_all('.game-sub-games__item')
                    tab = tabs[idx]
                    section_name = await tab.inner_text()
                    section_name = normalize(section_name)
                    await tab.click()
                    await page.wait_for_timeout(2000)
                    await robust_auto_scroll(page, max_wait=20)
                    await wait_for_markets(page, timeout=10000)

                    await page.evaluate("""
                        () => {
                            let footer = document.querySelector('footer');
                            if (footer) footer.remove();
                            let nav = document.querySelector('nav');
                            if (nav) nav.remove();
                            let pop = document.querySelector('.popup, .modal, .cookie, .banner');
                            if (pop) pop.remove();
                            let sticky = document.querySelector('.default__nav');
                            if (sticky) sticky.remove();
                            let header = document.querySelector('.default__header');
                            if (header) header.remove();
                            let scoreboard = document.querySelector('.scoreboard-layout');
                            if (scoreboard) scoreboard.remove();
                            let sectionnav = document.querySelector('.ui-section-nav');
                            if (sectionnav) sectionnav.remove();
                            let catfish = document.querySelector('.download-apps-catfish__link');
                            if (catfish) catfish.style.display = "none";
                        }
                    """)

                    try:
                        await page.wait_for_selector(".ui-market__value", timeout=15000)
                    except:
                        print("⚠️ Market values not found, continuing anyway...")
                    
                    await page.wait_for_timeout(1000)

                    market_blocks = await page.query_selector_all(
                        "div.game-markets-group"
                    )
                    
                    save_path_base = match_folder
                    os.makedirs(save_path_base, exist_ok=True)
                    
                    for market_block in market_blocks:
                        market_name_elem = await market_block.query_selector(".game-markets-group-header__name")
                        if not market_name_elem:
                            continue
                        market_name = await market_name_elem.inner_text()
                        market_name_clean = normalize(market_name)
                        file_base = f"{market_name_clean}".strip()
                        
                        try:
                            img_bytes = await market_block.screenshot()
                            img = Image.open(io.BytesIO(img_bytes))
                            img.save(f"{save_path_base}/{file_base}.png")
                            
                            market_text = await market_block.inner_text()
                            if market_text.strip():
                                with open(f"{save_path_base}/{file_base}.txt", "w", encoding="utf-8") as f:
                                    f.write(market_text)
                                print(f"    {file_base} market saved in {save_path_base}")
                            else:
                                print(f"    Warning: Empty text for {file_base}")

                        except Exception as e:
                            print(f"    Error capturing {file_base}: {e}")

            except Exception as e:
                print(f"❌ Error on match {i+1}: {e}")

        await browser.close()

async def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(MATCH_FILE, "r") as f:
        match_links = [line.strip() for line in f if line.strip()]

    total = len(match_links)
    for batch_num, i in enumerate(range(0, total, BATCH_SIZE), 1):
        batch_links = match_links[i:i+BATCH_SIZE]
        print(f"\n=== Processing batch {batch_num} ({len(batch_links)} matches) ===")
        await process_batch(batch_links, batch_num)
        print(f"=== Batch {batch_num} done ===\n")
        await asyncio.sleep(2)

    print("All done. All files saved in:", OUTPUT_FOLDER)

if __name__ == "__main__":
    asyncio.run(main())