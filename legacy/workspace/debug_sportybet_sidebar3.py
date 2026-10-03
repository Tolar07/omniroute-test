"""
Standalone debug script - deep dive into the country/league structure and filter overlay.
"""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(60_000)

        url = "https://www.sportybet.com.ng/ng/sport/football"
        print(f"=== Navigating to {url} ===")
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(8000)

        print(f"Final URL: {page.url}")

        # --- 1. Click the Filter button to see what opens ---
        print("\n=== Clicking Filter button ===")
        filter_btn = page.locator(".filter-control").first
        if await filter_btn.count() > 0:
            await filter_btn.click()
            await page.wait_for_timeout(3000)
            print("Clicked Filter button")
        else:
            print("Filter button not found")

        # --- 2. Look at the filter-overlay in detail ---
        print("\n--- Filter Overlay Details ---")
        overlay = page.locator(".filter-overlay").first
        if await overlay.count() > 0:
            print("filter-overlay found")
            # Get all children
            children = await overlay.locator("*").all()
            for i, child in enumerate(children):
                cls = await child.get_attribute("class")
                text = await child.inner_text()
                tag = await child.evaluate("el => el.tagName.toLowerCase()")
                if text and text.strip():
                    print(f"  [{i}] <{tag}> class=\"{cls}\" text=\"{text[:200]}\"")
        else:
            print("filter-overlay NOT found")

        # --- 3. Check if there's a separate country/league modal ---
        print("\n--- All modals/overlays/popups present ---")
        all_modals = await page.evaluate("""
            () => {
                const selectors = [
                    '[class*="modal"]', '[class*="popup"]', '[class*="overlay"]',
                    '[class*="drawer"]', '[class*="sheet"]', '[class*="dialog"]',
                    '[role="dialog"]', '[role="modal"]',
                    '[class*="filter"]', '[class*="country"]', '[class*="league"]',
                    '[class*="category"]', '[class*="tournament"]',
                ];
                const results = [];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const cls = (el.className || '').toString();
                        const vis = el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0;
                        const text = (el.innerText || el.textContent || '').trim();
                        if (vis && cls && !results.some(r => r.classes === cls)) {
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                classes: cls,
                                id: el.id || '',
                                text: text.substring(0, 300),
                            });
                        }
                    }
                }
                return results.slice(0, 80);
            }
        """)
        for item in all_modals:
            print(f"  <{item['tag']}> id=\"{item['id']}\" class=\"{item['classes']}\" text=\"{item['text']}\"")

        # --- 4. Get all category-name elements (countries) ---
        print("\n--- All category-name elements (countries) ---")
        categories = page.locator(".category-name")
        count = await categories.count()
        print(f"Total .category-name elements: {count}")
        for i in range(count):
            el = categories.nth(i)
            text = await el.inner_text()
            cls = await el.get_attribute("class")
            print(f"  [{i}] class=\"{cls}\" text=\"{text}\"")

        # --- 5. Check the popular league links more thoroughly ---
        print("\n--- Popular league direct URLs ---")
        top_links = page.locator(".top-link")
        link_count = await top_links.count()
        for i in range(link_count):
            el = top_links.nth(i)
            text = await el.inner_text()
            href = await el.get_attribute("href")
            cls = await el.get_attribute("class")
            print(f"  [{i}] class=\"{cls}\" href=\"{href}\" text=\"{text}\"")

        # --- 6. Look for "View All" or similar to expand countries ---
        print("\n--- Searching for 'View All' or expand triggers ---")
        expand_selectors = [
            "button:has-text('View All')", "a:has-text('View All')",
            "button:has-text('All')", "a:has-text('All')",
            "[class*='view-all']", "[class*='show-more']",
            "[class*='expand-all']", "[class*='more']",
        ]
        for sel in expand_selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  Found {count}x: {sel}")
                    for i in range(min(count, 5)):
                        el = page.locator(sel).nth(i)
                        text = await el.inner_text()
                        cls = await el.get_attribute("class")
                        href = await el.get_attribute("href")
                        print(f"    [{i}] class=\"{cls}\" href=\"{href}\" text=\"{text}\"")
            except Exception:
                pass

        # --- 7. Check the sidebar/left navigation area more carefully ---
        print("\n--- Left sidebar / navigation area elements ---")
        sidebar_elements = await page.evaluate("""
            () => {
                // Find elements on the left side (x < 300)
                const results = [];
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    if (rect.left < 300 && rect.width > 50 && rect.height > 20) {
                        const cls = (el.className || '').toString().toLowerCase();
                        const tag = el.tagName.toLowerCase();
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text && text.length > 5 && text.length < 500) {
                            results.push({
                                tag: tag,
                                classes: cls,
                                text: text.substring(0, 200),
                                left: rect.left,
                                top: rect.top,
                                width: rect.width,
                                height: rect.height,
                            });
                        }
                    }
                }
                return results.slice(0, 60);
            }
        """)
        for item in sidebar_elements:
            print(f"  pos({item['left']:.0f},{item['top']:.0f}) size({item['width']:.0f}x{item['height']:.0f}) <{item['tag']}> class=\"{item['classes']}\" text=\"{item['text']}\"")

        # --- 8. Try to navigate directly to a league URL ---
        print("\n--- Testing direct league URL navigation ---")
        test_url = "https://www.sportybet.com/ng/sport/football/sr:category:1/sr:tournament:17?source=sport_menu&sort=2"
        print(f"Navigating to: {test_url}")
        await page.goto(test_url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(5000)
        print(f"New URL: {page.url}")
        print(f"Page title: {await page.title()}")

        # Check if fixtures loaded
        fixtures = await page.locator("tbody.match-row, .match-row, .m-table-row").count()
        print(f"Fixture rows found: {fixtures}")

        # Screenshot
        screenshot_path = str(Path(__file__).resolve().parent / "debug_sportybet_direct_league.png")
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot saved to: {screenshot_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())