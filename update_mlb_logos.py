import json
import re
import urllib.request


def scrape_and_update_mlb_logos():
    print("Scraping mlb.com for official club logos...")
    url = "https://www.mlb.com/team"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch MLB teams page: {e}")
        return

    scraped_logos = {}

    mlb_teams = {
        "Arizona Diamondbacks": "Arizona Diamondbacks",
        "Atlanta Braves": "Atlanta Braves",
        "Baltimore Orioles": "Baltimore Orioles",
        "Boston Red Sox": "Boston Red Sox",
        "Chicago White Sox": "Chicago White Sox",
        "Chicago Cubs": "Chicago Cubs",
        "Cincinnati Reds": "Cincinnati Reds",
        "Cleveland Guardians": "Cleveland Guardians",
        "Colorado Rockies": "Colorado Rockies",
        "Detroit Tigers": "Detroit Tigers",
        "Houston Astros": "Houston Astros",
        "Kansas City Royals": "Kansas City Royals",
        "Los Angeles Angels": "Los Angeles Angels",
        "Los Angeles Dodgers": "Los Angeles Dodgers",
        "Miami Marlins": "Miami Marlins",
        "Milwaukee Brewers": "Milwaukee Brewers",
        "Minnesota Twins": "Minnesota Twins",
        "New York Yankees": "New York Yankees",
        "New York Mets": "New York Mets",
        "Oakland Athletics": "Athletics",
        "Athletics": "Athletics",
        "Philadelphia Phillies": "Philadelphia Phillies",
        "Pittsburgh Pirates": "Pittsburgh Pirates",
        "San Diego Padres": "San Diego Padres",
        "San Francisco Giants": "San Francisco Giants",
        "Seattle Mariners": "Seattle Mariners",
        "St. Louis Cardinals": "St. Louis Cardinals",
        "Tampa Bay Rays": "Tampa Bay Rays",
        "Texas Rangers": "Texas Rangers",
        "Toronto Blue Jays": "Toronto Blue Jays",
        "Washington Nationals": "Washington Nationals"
    }

    # Attempt 1: Extract from Next.js __NEXT_DATA__ JSON blob (common on modern sports sites)
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))

            def extract_logos(d):
                if isinstance(d, dict):
                    name = d.get('name') or d.get('shortName') or d.get(
                        'fullName') or d.get('franchiseName') or d.get('title')
                    logo = d.get('logoFallback') or d.get('logo') or d.get(
                        'crest') or d.get('picture') or d.get('image') or d.get('src')

                    if name and logo and isinstance(name, str):
                        for search_name, official_name in mlb_teams.items():
                            if search_name.lower() in name.lower() or name.lower() in search_name.lower():
                                logo_url = ""
                                if isinstance(logo, str):
                                    logo_url = logo
                                elif isinstance(logo, dict) and 'url' in logo:
                                    logo_url = logo['url']
                                elif isinstance(logo, dict) and 'fallback' in logo:
                                    logo_url = logo['fallback']

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
    if not scraped_logos or len(scraped_logos) < 10:
        pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\']|<img[^>]+alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(pattern, html):
            url = match.group(1) if match.group(1) else match.group(4)
            alt = match.group(2) if match.group(2) else match.group(3)

            alt_lower = alt.lower()
            for search_name, official_name in mlb_teams.items():
                if search_name.lower() == alt_lower or (search_name.lower() in alt_lower and ("logo" in alt_lower or "crest" in alt_lower or ".svg" in url or ".png" in url)):
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://www.mlb.com' + url
                    scraped_logos[official_name] = url

    if not scraped_logos:
        print("No logos found! MLB might have changed their website layout.")
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
                "color": "red",
                "icon": "baseball",
                "prefix": "fa",
                "logo": logo_url
            }
        else:
            config["team_styles"][team_name]["logo"] = logo_url
        updates += 1

    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    print(
        f"Successfully scraped and added {updates} MLB team logos into config.json!")


if __name__ == '__main__':
    scrape_and_update_mlb_logos()
