import asyncio
import os
import re
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from playwright.async_api import async_playwright
from PIL import Image
import io

# === Always use Ace folder as base ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "mostbet")
MATCH_FILE = os.path.join(BASE_DIR, "matches.txt")

BATCH_SIZE = 3
MOBILE_EMULATION = {"deviceName": "Pixel 2"}

def normalize(s):
    s = re.sub(r'[^a-zA-Z0-9 ]+', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip().title()

def extract_match_name(driver):
    try:
        home = driver.find_element(By.CSS_SELECTOR, "div.MatchTeam_root__ZvTrK.MatchInfo_teamHome__HkKtf").text.strip()
        away = driver.find_element(By.CSS_SELECTOR, "div.MatchTeam_root__ZvTrK.MatchInfo_teamAway__360bL").text.strip()
    except Exception as e:
        print("Error extracting home/away:", e)
        home = away = "unknown"
    match_name = f"{normalize(home)} vs {normalize(away)}"
    return match_name

def get_all_match_names(match_links):
    chrome_options = Options()
    chrome_options.add_experimental_option("mobileEmulation", MOBILE_EMULATION)
    chrome_options.add_argument("--window-size=411,2000")
    chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=chrome_options)
    link_name_pairs = []
    for i, link in enumerate(match_links):
        try:
            driver.get(link)
            time.sleep(10)
            match_name = extract_match_name(driver)
            if "unknown" in match_name.lower():
                match_name = f"Match {i+1}"
            link_name_pairs.append((link, match_name))
            print(f"[{i+1}] {link} => {match_name}")
        except Exception as e:
            print(f"❌ Error extracting name for {link}: {e}")
            link_name_pairs.append((link, f"Match {i+1}"))
    driver.quit()
    return link_name_pairs

async def process_batch(batch_pairs, batch_num):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for i, (link, match_name) in enumerate(batch_pairs):
            print(f"[Batch {batch_num}] Opening match {i+1}: {link} ({match_name})")
            try:
                await page.goto(link, timeout=60000)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)

                match_folder = os.path.join(OUTPUT_FOLDER, match_name)
                os.makedirs(match_folder, exist_ok=True)

                market_blocks = await page.query_selector_all('.Group_group__UArsk')
                print(f"  Found {len(market_blocks)} market groups.")

                for market_block in market_blocks:
                    market_name_elem = await market_block.query_selector('.Group_title__kDW0l')
                    if not market_name_elem:
                        continue
                    market_name = await market_name_elem.inner_text()
                    market_name_clean = normalize(market_name)
                    save_path_base = os.path.join(match_folder)
                    os.makedirs(save_path_base, exist_ok=True)

                    # Screenshot
                    try:
                        img_bytes = await market_block.screenshot()
                        img = Image.open(io.BytesIO(img_bytes))
                        img.save(f"{save_path_base}/{market_name_clean}.png")
                        print(f"    {market_name_clean} screenshot saved.")
                    except Exception as e:
                        print(f"    Error capturing screenshot for {market_name_clean}: {e}")

                    # Text extraction
                    try:
                        market_text = await market_block.inner_text()
                        with open(f"{save_path_base}/{market_name_clean}.txt", "w", encoding="utf-8") as f:
                            f.write(market_text)
                        print(f"    {market_name_clean} text saved.")
                    except Exception as e:
                        print(f"    Error saving text for {market_name_clean}: {e}")

            except Exception as e:
                print(f"❌ Error on match {i+1}: {e}")

        await browser.close()

async def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(MATCH_FILE, "r") as f:
        match_links = [line.strip() for line in f if line.strip()]

    link_name_pairs = get_all_match_names(match_links)

    total = len(link_name_pairs)
    for batch_num, i in enumerate(range(0, total, BATCH_SIZE), 1):
        batch_pairs = link_name_pairs[i:i+BATCH_SIZE]
        print(f"\n=== Processing batch {batch_num} ({len(batch_pairs)} matches) ===")
        await process_batch(batch_pairs, batch_num)
        print(f"=== Batch {batch_num} done ===\n")
        await asyncio.sleep(2)

    print("All done. All files saved in:", OUTPUT_FOLDER)

if __name__ == "__main__":
    asyncio.run(main())