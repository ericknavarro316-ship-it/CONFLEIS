import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("Navigating to app...")
        await page.goto("http://localhost:8501")
        await asyncio.sleep(3)

        print("Logging in...")
        await page.fill('input[type="text"]', "admin")
        await page.fill('input[type="password"]', "admin")
        await page.click('button:has-text("Ingresar (Staff)")')
        await asyncio.sleep(5)

        print("Navigating to Dashboard...")
        await page.locator('text="Dashboard"').click()
        await asyncio.sleep(3)
        await page.screenshot(path="/home/jules/verification/dashboard_final.png")
        print("Captured Dashboard final screenshot")

        print("Navigating to Personas Físicas...")
        await page.locator('text="Personas Físicas"').click()
        await asyncio.sleep(3)
        await page.locator('button', has_text="Agregar Cliente Nuevo").click()
        await asyncio.sleep(2)
        await page.screenshot(path="/home/jules/verification/pf_final.png")
        print("Captured Personas Físicas final screenshot")

        print("Navigating to Gestió de Equipo...")
        await page.locator('text="Gestión de Equipo (Admin)"').click()
        await asyncio.sleep(3)
        await page.locator('button', has_text="Organigrama").click()
        await asyncio.sleep(2)
        await page.screenshot(path="/home/jules/verification/org_final.png")
        print("Captured Organigrama final screenshot")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
