# 🛒 OpenClaw AH Shopping Automation

Automatically add items to your Albert Heijn (AH) shopping cart using Selenium.

## Features

✅ Automated login to AH.nl
✅ Search for products
✅ Add items to cart (with quantity support)
✅ Get cart total
✅ Optional auto-checkout
✅ JSON-based configuration

## Installation

### Prerequisites
- Python 3.7+
- Chrome/Chromium browser
- ChromeDriver (auto-detected if in PATH)

### Setup

```bash
# Clone or navigate to repo
cd openclaw-ah-shopping

# Install dependencies
pip install -r requirements.txt

# config.json has items only — credentials are handled securely
```

### Credentials (No GitHub Storage!)

Choose one method:

**Method 1: Interactive Prompt** (Easiest)
```bash
python ah_shopper.py
# Script prompts for email & password each time
```

**Method 2: Environment Variables** (Reusable)
```bash
export AH_EMAIL="your@email.com"
export AH_PASSWORD="yourpassword"
python ah_shopper.py
```

**Method 3: .env File** (Local, gitignored)
```bash
# Create .env file (gitignore'ed)
echo "AH_EMAIL=your@email.com" > .env
echo "AH_PASSWORD=yourpassword" >> .env
chmod 600 .env

python ah_shopper.py  # Reads from .env
```

## Usage

### Basic Run
```bash
python ah_shopper.py
```

### Configuration (config.json)

```json
{
  "items": [
    {
      "name": "AH Kipfilet",
      "quantity": 1
    }
  ],
  "auto_checkout": false,
  "keep_browser_open": true
}
```

**Options:**
- `items`: List of products to add (name + quantity)
- `auto_checkout`: Go to checkout after adding items
- `keep_browser_open`: Keep browser open after script ends

**Credentials:** Handled via environment variables or interactive prompt (see above)

## Example: Weekly Shopping

```bash
# Set credentials
export AH_EMAIL="your@email.com"
export AH_PASSWORD="yourpassword"

# Update config.json with your items
{
  "items": [
    {"name": "AH Kipfilet 800g", "quantity": 1},
    {"name": "AH Rundergehakt", "quantity": 2},
    {"name": "AH Broccoli", "quantity": 1},
    {"name": "AH Appels", "quantity": 1}
  ],
  "auto_checkout": false,
  "keep_browser_open": true
}

# Run it
python ah_shopper.py
```

## How It Works

1. **Initialize** Chrome driver
2. **Login** to AH with credentials
3. **Search** for each item
4. **Add** to cart with specified quantity
5. **Display** cart total
6. **Optionally** go to checkout

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ChromeDriver not found | Install: `pip install webdriver-manager` |
| Login fails | Check email/password in config.json |
| Item not found | Use exact AH product name (e.g., "AH Kipfilet 800g") |
| Timeout errors | Increase wait times in code or check internet |

## Headless Mode

Uncomment this line in `ah_shopper.py` to run without UI:
```python
options.add_argument("--headless")
```

## Security

✅ **Credentials are NEVER stored in config.json!**
- Use environment variables (AH_EMAIL, AH_PASSWORD)
- Or interactive prompt (getpass)
- config.json is safe to commit (contains only items)

## Future (ClawHub Skill)

This will be converted to an OpenClaw skill for easier integration.

## License

MIT

---

**Built for efficient meal planning automation** 🍽️
