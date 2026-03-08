#!/usr/bin/env python3
"""
Albert Heijn Automated Shopping Tool
Automates adding items to AH cart using Selenium
"""

import json
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class AHShopper:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.cart_total = 0
        
    def _load_config(self, path):
        """Load shopping config from JSON"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Config file not found: {path}")
            sys.exit(1)
            
    def _init_driver(self):
        """Initialize Chrome driver"""
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")  # Uncomment for headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        
    def start(self):
        """Start shopping session"""
        print("🛒 Starting AH Shopping Automation...")
        self._init_driver()
        
    def stop(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("✅ Browser closed")
            
    def login(self, email, password):
        """Login to AH account"""
        print(f"🔐 Logging in as {email}...")
        self.driver.get("https://www.ah.nl")
        
        try:
            # Wait for page load
            time.sleep(2)
            
            # Find and click login button
            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Inloggen')]"))
            )
            login_btn.click()
            time.sleep(1)
            
            # Enter email
            email_field = self.driver.find_element(By.ID, "login-email")
            email_field.send_keys(email)
            
            # Enter password
            pwd_field = self.driver.find_element(By.ID, "login-password")
            pwd_field.send_keys(password)
            
            # Submit
            submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_btn.click()
            
            # Wait for dashboard
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Mijn AH')]"))
            )
            print("✅ Login successful!")
            
        except TimeoutException:
            print("❌ Login failed or timeout")
            return False
        return True
        
    def search_and_add(self, product_name, quantity=1):
        """Search for product and add to cart"""
        print(f"🔍 Searching for: {product_name}...")
        
        try:
            # Click search box
            search_box = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='zoek']")
            search_box.clear()
            search_box.send_keys(product_name)
            time.sleep(0.5)
            
            # Press Enter
            search_box.submit()
            time.sleep(2)
            
            # Find first result and add to cart
            add_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Verhoog') or contains(text(), 'Toevoegen')]"))
            )
            
            for _ in range(quantity):
                add_button.click()
                time.sleep(0.5)
                
            print(f"✅ Added {quantity}x {product_name}")
            return True
            
        except (TimeoutException, NoSuchElementException) as e:
            print(f"⚠️ Could not find/add {product_name}: {e}")
            return False
            
    def get_cart_total(self):
        """Get current cart total"""
        try:
            cart_link = self.driver.find_element(By.XPATH, "//span[contains(text(), '€')]")
            total_text = cart_link.text
            # Extract number from "€45.43" format
            self.cart_total = total_text.replace("€", "").strip()
            print(f"🛒 Cart total: {self.cart_total}")
            return self.cart_total
        except NoSuchElementException:
            return None
            
    def checkout(self):
        """Go to checkout"""
        print("💳 Going to checkout...")
        self.driver.get("https://www.ah.nl/mijnlijst")
        time.sleep(2)
        
    def run(self):
        """Execute full shopping workflow"""
        try:
            self.start()
            
            # Login
            if not self.login(
                self.config["credentials"]["email"],
                self.config["credentials"]["password"]
            ):
                return
            
            time.sleep(2)
            
            # Add items
            items = self.config.get("items", [])
            added_count = 0
            for item in items:
                name = item.get("name")
                qty = item.get("quantity", 1)
                if self.search_and_add(name, qty):
                    added_count += 1
                time.sleep(1)
                
            # Get total
            self.get_cart_total()
            
            print(f"\n✅ Successfully added {added_count}/{len(items)} items")
            print(f"📊 Cart ready for checkout at: https://www.ah.nl/mijnlijst")
            
            # Optional: go to checkout
            if self.config.get("auto_checkout"):
                self.checkout()
                print("💳 Opened checkout page")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            if not self.config.get("keep_browser_open"):
                self.stop()
            else:
                print("\n⏸️ Browser kept open (keep_browser_open=true)")


if __name__ == "__main__":
    shopper = AHShopper()
    shopper.run()
