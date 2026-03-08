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

# Configure your account
nano config.json  # Edit with your AH email & password
```

## Usage

### Basic Run
```bash
python ah_shopper.py
```

### Configuration (config.json)

```json
{
  "credentials": {
    "email": "your.email@example.com",
    "password": "your-password"
  },
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
- `credentials.email`: Your AH account email
- `credentials.password`: Your AH account password  
- `items`: List of products to add (name + quantity)
- `auto_checkout`: Go to checkout after adding items
- `keep_browser_open`: Keep browser open after script ends

## Example: Weekly Shopping

```json
{
  "credentials": {...},
  "items": [
    {"name": "AH Kipfilet 800g", "quantity": 1},
    {"name": "AH Rundergehakt", "quantity": 2},
    {"name": "AH Broccoli", "quantity": 1},
    {"name": "AH Appels", "quantity": 1}
  ],
  "auto_checkout": false,
  "keep_browser_open": true
}
```

Run it:
```bash
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

⚠️ **Never commit config.json with real credentials!**

```bash
# Add to .gitignore
echo "config.json" >> .gitignore
```

Or use environment variables:
```bash
export AH_EMAIL="your@email.com"
export AH_PASSWORD="password"
```

## Future (ClawHub Skill)

This will be converted to an OpenClaw skill for easier integration.

## License

MIT

---

**Built for efficient meal planning automation** 🍽️
