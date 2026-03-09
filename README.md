# AH Shopping — Koopknop URL Builder

Automatically build Albert Heijn cart URLs to add multiple items at once.

## How it Works

Instead of manually searching for each product on AH, this tool:

1. **Searches** the AH product API for each item
2. **Finds** the best match (with smart filtering of bad results)
3. **Builds** a koopknop deep link: `https://www.ah.nl/mijnlijst/add-multiple?p=<id>:<qty>&...`
4. **Prints** the URL — click it in an AH-logged-in browser to add all items to cart instantly

## Why?

The AH website blocks headless browsers (Selenium, Puppeteer). The koopknop URL is **the only reliable way** to automate adding items to cart.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Default (uses `config.json`)
```bash
python3 ah_koopknop.py
```

### Custom items file
```bash
python3 ah_koopknop.py --items my_shopping_list.json
```

## Items Format

`config.json`:
```json
{
  "items": [
    { "name": "kipfilet", "quantity": 1 },
    { "name": "melk", "quantity": 2 },
    { "name": "rijst", "quantity": 1 }
  ]
}
```

## Example Output

```
🛒 Searching AH for 3 items...

   ✅ kipfilet → AH Scharrel kipfilet naturel (€2.99 x1)
   ✅ melk → Campina Langlekker halfvol (€2.29 x2) 🏷️ BONUS
   ✅ rijst → Lassie Toverrijst (€2.35 x1)

────────────────────────────────────────────────────────
✅ Found: 3/3 items
💶 Est. total: €9.92

🔗 Koopknop URL:
https://www.ah.nl/mijnlijst/add-multiple?p=543332:1&p=605202:2&p=484982:1

💡 Open this URL in your AH browser (logged in) to add all items at once.
```

## How to Use the URL

1. Make sure you're logged into https://www.ah.nl on your browser
2. Copy the generated URL
3. Paste it in address bar and press Enter
4. All items instantly appear in your cart ✅
5. Proceed to checkout

## API Used

- **supermarktconnector** — Python wrapper for AH mobile API
  - No official AH API exists for product search
  - This is the most reliable 3rd-party wrapper available
  - Returns: webshopId, title, price, bonus info

## Notes

- Search results are filtered to avoid bad matches (maaltijdmix, babyvoeding, etc.)
- Bonus items are flagged with 🏷️
- Estimated price is shown (actual price may vary based on bonus/promos)
- URL is valid for the current day; use it immediately

## Future Ideas

- Integration with Telegram/WhatsApp (send URL via bot)
- Browser relay automation (click URL automatically)
- Weekly meal planning + automatic shopping list generation
- Discount code integration

---

**Built for:** Dutch SMBs who want to automate grocery shopping while keeping costs low.
