"""
Standalone debug script - deeper exploration of SportyBet's filter modal and country/league structure.
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

        # --- 1. Click the Filter button ---
        print("\n=== Clicking Filter button ===")
        filter_btn = page.locator(".filter-control").first
        if await filter_btn.count() > 0:
            await filter_btn.click()
            await page.wait_for_timeout(3000)
            print("Clicked Filter button")
        else:
            print("Filter button not found")

        # --- 2. Dump page HTML after filter click ---
        html_snippet = await page.evaluate("() => document.body.innerHTML.slice(0, 8000)")
        print("\n" + "=" * 80)
        print("BODY innerHTML after Filter click (first 8000 chars):")
        print("=" * 80)
        print(html_snippet)

        # --- 3. Look for modal/drawer after filter click ---
        print("\n--- Checking for modal/drawer after filter click ---")
        modal_selectors = [
            "[class*='modal']", "[class*='dialog']", "[class*='drawer']",
            "[class*='sheet']", "[class*='popup']", "[class*='overlay']",
            "[role='dialog']", "[role='modal']",
            "[class*='filter-modal']", "[class*='filter-drawer']",
            "[class*='country-list']", "[class*='league-list']",
            "[class*='category-list']", "[class*='tournament-list']",
        ]
        for sel in modal_selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  Found {count}x: {sel}")
                    for i in range(min(count, 3)):
                        el = page.locator(sel).nth(i)
                        text = await el.inner_text()
                        cls = await el.get_attribute("class")
                        print(f"    [{i}] class=\"{cls}\" text=\"{text[:200]}\"")
            except Exception as e:
                pass

        # --- 4. Find all elements with class containing 'category', 'country', 'league', 'tournament' ---
        print("\n--- All relevant elements after filter click ---")
        js_code = """
        () => {
            const keywords = ['category', 'country', 'league', 'tournament',
                               'filter', 'sport', 'competition', 'accordion',
                               'expand', 'collapse', 'group', 'section'];
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const cls = (el.className || '').toString().toLowerCase();
                const tag = el.tagName.toLowerCase();
                let match = false;
                for (const k of keywords) {
                    if (cls.includes(k)) {
                        match = true;
                        break;
                    }
                }
                if (match) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const vis = el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0;
                    if (vis && text && text.length < 300) {
                        results.push({
                            tag: tag,
                            classes: cls,
                            text: text.substring(0, 200),
                            id: el.id || '',
                        });
                    }
                }
            }
            return results.slice(0, 150);
        }
        """
        elements_data = await page.evaluate(js_code)
        for item in elements_data:
            print(f"  <{item['tag']}> class=\"{item['classes']}\" id=\"{item['id']}\" text=\"{item['text']}\"")

        # --- 5. Search for "England" ---
        print("\n--- Searching for England ---")
        matches = await page.evaluate("""
            (searchTerm) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT
                );
                const results = [];
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.textContent.includes(searchTerm)) {
                        const parent = node.parentElement;
                        let hierarchy = parent ? parent.tagName.toLowerCase() + '.' + (parent.className || '').toString().toLowerCase() : 'unknown';
                        let ancestor = parent ? parent.parentElement : null;
                        if (ancestor) {
                            hierarchy += ' > ' + ancestor.tagName.toLowerCase() + '.' + (ancestor.className || '').toString().toLowerCase();
                        }
                        let ancestor2 = ancestor ? ancestor.parentElement : null;
                        if (ancestor2) {
                            hierarchy += ' > ' + ancestor2.tagName.toLowerCase() + '.' + (ancestor2.className || '').toString().toLowerCase();
                        }
                        results.push({
                            text: node.textContent.trim().substring(0, 100),
                            hierarchy: hierarchy,
                        });
                    }
                }
                return results;
            }
        """, "England")
        for m in matches:
            print(f"  Found 'England': text=\"{m['text']}\"")
            print(f"    Hierarchy: {m['hierarchy']}")

        # --- 6. Look at the top links structure ---
        print("\n--- Top links structure (Popular leagues) ---")
        top_links = await page.locator(".top-link, .top-link-item").all()
        for i, link in enumerate(top_links):
            text = await link.inner_text()
            cls = await link.get_attribute("class")
            href = await link.get_attribute("href")
            print(f"  [{i}] class=\"{cls}\" href=\"{href}\" text=\"{text[:100]}\"")

        # --- 7. Check for accordion/expandable elements ---
        print("\n--- Checking for clickable/expandable elements ---")
        clickable_selectors = [
            "[class*='accordion']", "[class*='expand']", "[class*='collapse']",
            "[class*='arrow']", "[class*='chevron']", "[class*='caret']",
            "[class*='toggle']", "[class*='dropdown']",
            "button[class*='category']", "div[class*='category']",
        ]
        for sel in clickable_selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  Found {count}x: {sel}")
                    for i in range(min(count, 5)):
                        el = page.locator(sel).nth(i)
                        text = await el.inner_text()
                        cls = await el.get_attribute("class")
                        print(f"    [{i}] class=\"{cls}\" text=\"{text[:100]}\"")
            except Exception:
                pass

        # --- 8. Screenshot ---
        screenshot_path = str(Path(__file__).resolve().parent / "debug_sportybet_sidebar2.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\nFull page screenshot saved to: {screenshot_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())