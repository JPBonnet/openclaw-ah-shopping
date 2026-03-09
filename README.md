# openclaw-ah-shopping

> Add your weekly groceries to Albert Heijn cart with one click.

Uses the AH product API to find items, then generates a **koopknop deep link** that adds everything to your cart at once — no login required in the script.

## How it works

1. Script searches AH product API for each item in your list
2. Gets the `webshopId` for the best match
3. Builds a single URL: `https://www.ah.nl/mijnlijst/add-multiple?p=<id>:<qty>&...`
4. You click the URL in your logged-in AH browser → all items added instantly ✅

## Usage

```bash
pip install -r requirements.txt
python ah_koopknop.py
```

Custom items file:
```bash
python ah_koopknop.py --items mijn-boodschappen.json
```

## Items format (config.json)

```json
{
  "items": [
    { "name": "kipfilet",     "quantity": 1 },
    { "name": "melk",         "quantity": 2 },
    { "name": "appels",       "quantity": 1 }
  ]
}
```

## Output

```
🛒 Searching AH for 3 items...

   ✅ kipfilet → AH Kipfilet (€4.79 x1)
   ✅ melk → AH Volle melk 1L (€1.09 x2)
   ✅ appels → Elstar appels (€2.49 x1) 🏷️ BONUS

✅ Found:     3/3 items
💶 Est. total: €9.46

🔗 Koopknop URL:
https://www.ah.nl/mijnlijst/add-multiple?p=531825:1&p=450534:2&p=195093:1
```

## Notes

- Uses `supermarktconnector` (unofficial AH API wrapper)
- No AH credentials needed — URL works with browser cookies
- Bonus items flagged with 🏷️
- Old `ah_shopper.py` (Selenium approach) is deprecated — CloudFlare blocks headless browsers
