"""
Standalone debug script to inspect SportyBet's sidebar/navigation structure.
"""
import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(60_000)

        url = "https://www.sportybet.com.ng/ng/sport/football"
        print(f"=== Navigating to {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"Initial load error: {e}")

        # Wait for SPA to render
        await page.wait_for_timeout(8000)

        # --- 1. Dump first 5000 chars of body innerHTML ---
        html_snippet = await page.evaluate(
            "() => document.body.innerHTML.slice(0, 5000)"
        )
        print("\n" + "=" * 80)
        print("BODY innerHTML (first 5000 chars):")
        print("=" * 80)
        print(html_snippet)
        print("=" * 80)

        # --- 2. Check for common sidebar/filter patterns ---
        print("\n--- Checking for common selectors ---")
        common_selectors = [
            ".category-list-item", ".category-item", ".category-item",
            ".sport-list", ".sport-list-item",
            ".tournament-list", ".tournament-list-item",
            ".nav-item", ".sidebar", "[class*='sidebar']",
            "[class*='category']", "[class*='tournament']",
            "[class*='league']", "[class*='country']",
            "[class*='filter']", "[class*='nav']",
            "[class*='competition']", "[class*='match-list']",
            "[class*='fixture']", "[class*='event']",
            # Generic reactive UI classes
            ".v-expansion-panel", ".v-list", ".v-navigation-drawer",
            ".el-menu", ".el-submenu", ".el-menu-item",
            ".ant-menu", ".ant-menu-item", ".ant-menu-submenu",
            "[data-category]", "[data-league]",
            # Possible new SportyBet patterns
            ".country-item", ".country-list",
            ".league-item", ".league-list",
            ".filter-btn", ".filter-button",
            "button:has-text('Filter')", "button:has-text('Country')",
        ]
        found = {}
        for sel in common_selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    found[sel] = count
            except Exception:
                pass
        print(json.dumps(found, indent=2))

        # --- 3. Gather all elements with classes containing relevant keywords ---
        print("\n--- Elements with navigation/sidebar classes ---")
        js_code = """
        () => {
            const keywords = ['category', 'country', 'league', 'tournament',
                               'filter', 'sidebar', 'nav', 'competition',
                               'sport', 'league-filter', 'country-filter'];
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const cls = (el.className || '').toString().toLowerCase();
                const tag = el.tagName.toLowerCase();
                let match = false;
                for (const k of keywords) {
                    if (cls.includes(k) || tag.includes(k)) {
                        match = true;
                        break;
                    }
                }
                if (match) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const vis = el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0;
                    if (vis && text && text.length < 200) {
                        results.push({
                            tag: tag,
                            classes: cls,
                            text: text.substring(0, 120),
                            id: el.id || '',
                        });
                    }
                }
            }
            return results.slice(0, 80);
        }
        """
        elements_data = await page.evaluate(js_code)
        for item in elements_data:
            print(f"  <{item['tag']}> class=\"{item['classes']}\" id=\"{item['id']}\" text=\"{item['text']}\"")

        # --- 4. Search for "England" and "Premier League" ---
        print("\n--- Searching for England / Premier League ---")
        search_terms = ["England", "Premier League"]
        for term in search_terms:
            js_search = f"""
            (searchTerm) => {{
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT
                );
                const results = [];
                while (walker.nextNode()) {{
                    const node = walker.currentNode;
                    if (node.textContent.includes(searchTerm)) {{
                        const parent = node.parentElement;
                        let hierarchy = parent ? parent.tagName.toLowerCase() + '.' + (parent.className || '').toString().toLowerCase() : 'unknown';
                        let ancestor = parent ? parent.parentElement : null;
                        if (ancestor) {{
                            hierarchy += ' > ' + ancestor.tagName.toLowerCase() + '.' + (ancestor.className || '').toString().toLowerCase();
                        }}
                        results.push({{
                            text: node.textContent.trim().substring(0, 100),
                            hierarchy: hierarchy,
                        }});
                    }}
                }}
                return results;
            }}
            """
            matches = await page.evaluate(js_search, term)
            if matches:
                for m in matches:
                    print(f"  Found '{term}': text=\"{m['text']}\"")
                    print(f"    Hierarchy: {m['hierarchy']}")
            else:
                print(f"  NOT found: '{term}'")

        # --- 5. Look for filter/modal/dialog ---
        print("\n--- Checking for filters/modals/dialogs ---")
        dialog_selectors = [
            "[class*='modal']", "[class*='dialog']", "[class*='overlay']",
            "[class*='popup']", "[class*='drawer']", "[class*='sheet']",
            "[role='dialog']", "[role='modal']",
            "button:has-text('Filter')", "button:has-text('All sports')",
            "button:has-text('Top')", "button:has-text('Today')",
            "[class*='filter-bar']", "[class*='filter-bar']",
        ]
        for sel in dialog_selectors:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  Found {count}x: {sel}")
                    for i in range(min(count, 3)):
                        el = page.locator(sel).nth(i)
                        text = await el.inner_text()
                        cls = await el.get_attribute("class")
                        print(f"    [{i}] class=\"{cls}\" text=\"{text[:80]}\"")
            except Exception:
                pass

        # --- 6. Full page text for context ---
        print("\n--- Page visible text (first 3000 chars) ---")
        page_text = await page.evaluate("() => document.body.innerText.slice(0, 3000)")
        print(page_text)

        # --- 7. Screenshot for visual reference ---
        screenshot_path = r"C:\Users\Motunrayo\omniroute test\debug_sportybet_sidebar.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"\nScreenshot saved to: {screenshot_path}")

        # --- 8. Check the page URL after load ---
        print(f"\nFinal URL: {page.url}")
        print(f"Page title: {await page.title()}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())