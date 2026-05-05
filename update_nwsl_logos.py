import json
import re
import urllib.request


def scrape_and_update_nwsl_logos():
    print("Scraping nwslsoccer.com for official club logos...")
    url = "https://www.nwslsoccer.com/teams"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch NWSL teams page: {e}")
        return

    scraped_logos = {}

    # Translate NWSL website names to the schedule's JSON formatting
    nwsl_teams = {
        "Angel City": "Angel City",
        "Bay FC": "Bay",
        "Chicago Red Stars": "Chicago Stars",
        "Chicago Stars": "Chicago Stars",
        "Houston Dash": "Houston Dash",
        "Kansas City Current": "Kansas City Current",
        "NJ/NY Gotham FC": "Gotham FC",
        "Gotham FC": "Gotham FC",
        "North Carolina Courage": "North Carolina Courage",
        "Orlando Pride": "Orlando Pride",
        "Portland Thorns FC": "Portland Thorns",
        "Portland Thorns": "Portland Thorns",
        "Racing Louisville FC": "Racing Louisville",
        "Racing Louisville": "Racing Louisville",
        "San Diego Wave FC": "San Diego Wave",
        "San Diego Wave": "San Diego Wave",
        "Seattle Reign FC": "Seattle Reign",
        "Seattle Reign": "Seattle Reign",
        "Utah Royals FC": "Utah Royals",
        "Utah Royals": "Utah Royals",
        "Washington Spirit": "Washington Spirit",
        "Boston Legacy": "Boston Legacy",
        "Denver Summit": "Denver Summit"
    }

    # Attempt 1: Extract from Next.js __NEXT_DATA__ JSON blob (common on modern sports sites)
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))

            def extract_logos(d):
                if isinstance(d, dict):
                    name = d.get('name') or d.get('teamName') or d.get('title')
                    logo = d.get('logo') or d.get('lightLogo') or d.get(
                        'darkLogo') or d.get('logoUrl')

                    if name and logo and isinstance(name, str):
                        for search_name, official_name in nwsl_teams.items():
                            if search_name.lower() in name.lower() or name.lower() in search_name.lower():
                                logo_url = ""
                                if isinstance(logo, str):
                                    logo_url = logo
                                elif isinstance(logo, dict) and 'url' in logo:
                                    logo_url = logo['url']

                                if logo_url:
                                    if logo_url.startswith('//'):
                                        logo_url = 'https:' + logo_url
                                    scraped_logos[official_name] = logo_url

                    for k, v in d.items():
                        extract_logos(v)
                elif isinstance(d, list):
                    for item in d:
                        extract_logos(item)
            extract_logos(next_data)
        except:
            pass

    # Attempt 2: Fallback to HTML img tags if the JSON strategy misses anything
    if not scraped_logos:
        pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\']|<img[^>]+alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(pattern, html):
            url = match.group(1) if match.group(1) else match.group(4)
            alt = match.group(2) if match.group(2) else match.group(3)

            alt_lower = alt.lower()
            for search_name, official_name in nwsl_teams.items():
                if search_name.lower() in alt_lower and ("logo" in alt_lower or "crest" in alt_lower or ".png" in url or ".svg" in url):
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://www.nwslsoccer.com' + url
                    scraped_logos[official_name] = url

    if not scraped_logos:
        print("No logos found! NWSL might have changed their website layout.")
        return

    # Load existing config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print("Could not load config.json")
        return

    if "team_styles" not in config:
        config["team_styles"] = {}

    updates = 0
    # Apply scraped logos to config
    for team_name, logo_url in scraped_logos.items():
        if team_name not in config["team_styles"]:
            config["team_styles"][team_name] = {
                "color": "darkblue",
                "icon": "crown",
                "prefix": "fa",
                "logo": logo_url
            }
        else:
            config["team_styles"][team_name]["logo"] = logo_url
        updates += 1

    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    print(
        f"Successfully scraped and added {updates} NWSL team logos into config.json!")


if __name__ == '__main__':
    scrape_and_update_nwsl_logos()
