import pytest
from playwright.sync_api import Page, expect
from app import db, Product, User

def test_user_journey(app, live_server, page: Page):
    # 1. Setup Data
    with app.app_context():
        # Create a product
        product = Product(
            name="Frontend Coffee",
            price=5.50,
            category="drink",
            description="Best coffee for testing",
            image_url="/static/images/test.jpg"
        )
        db.session.add(product)
        db.session.commit()

    # 2. Start Journey
    # Use the SERVER_NAME from config if available to ensure matching
    server_name = app.config.get('SERVER_NAME')
    if server_name:
        base_url = f"http://{server_name}"
    else:
        base_url = live_server.url()

    page.goto(base_url)
    expect(page).to_have_title("Cozy Coffee Shop")

    # 3. Signup
    # Click "Start Your Journey" or navigate to register
    page.get_by_role("link", name="Start Your Journey").click()
    # Expect to be on register page
    expect(page.locator("h3.text-center")).to_contain_text("Register")

    page.fill('input[name="username"]', "frontenduser")
    page.fill('input[name="email"]', "front@example.com")
    page.fill('input[name="password"]', "password123")
    page.get_by_role("button", name="Register").click()

    # 4. Login (Redirects to Login)
    expect(page.locator("h3.text-center")).to_contain_text("Login")
    # Check for flash message
    expect(page.locator(".alert")).to_contain_text("Registration successful")

    page.fill('input[name="username"]', "frontenduser")
    page.fill('input[name="password"]', "password123")
    page.get_by_role("button", name="Login").click()

    # 5. Homepage (Logged in)
    expect(page.get_by_role("link", name="View Menu").first).to_be_visible()

    # 6. Add to Cart
    page.goto(f"{base_url}/menu")

    add_btn = page.locator(".add-to-cart").first
    add_btn.click()

    # Wait for "Added!" text
    expect(add_btn).to_contain_text("Added!")

    # 7. View Cart
    page.get_by_role("link", name="View Cart").click()
    expect(page.locator("h2")).to_contain_text("Shopping Cart")
    expect(page.locator(".card-title").first).to_contain_text("Frontend Coffee")

    # 8. Checkout
    page.get_by_role("link", name="Proceed to Checkout").click()
    expect(page.locator("h3")).to_contain_text("Checkout")

    # Select Cash
    page.locator('input[value="cash"]').check()

    # Complete Order
    page.get_by_role("button", name="Complete Order").click()

    # 9. Verify Success
    # Redirects to menu
    expect(page.locator("h1")).to_contain_text("Our Menu")
    expect(page.locator(".alert")).to_contain_text("processed successfully")
