import json
import re
import urllib.request


def scrape_and_update_mls_logos():
    print("Scraping mlssoccer.com for official club logos...")
    url = "https://www.mlssoccer.com/clubs/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch MLS clubs page: {e}")
        return

    scraped_logos = {}

    # Translate MLS website names to the schedule's JSON formatting
    mls_teams = {
        "Atlanta United": "Atlanta United",
        "Austin FC": "Austin FC",
        "Charlotte FC": "Charlotte FC",
        "Chicago Fire": "Chicago Fire FC",
        "FC Cincinnati": "FC Cincinnati",
        "Colorado Rapids": "Colorado Rapids",
        "Columbus Crew": "Columbus Crew",
        "D.C. United": "D.C. United",
        "DC United": "D.C. United",
        "FC Dallas": "FC Dallas",
        "Houston Dynamo": "Houston Dynamo FC",
        "Inter Miami": "Inter Miami CF",
        "LA Galaxy": "LA Galaxy",
        "Los Angeles Football Club": "Los Angeles Football Club",
        "LAFC": "Los Angeles Football Club",
        "Minnesota United": "Minnesota United FC",
        "CF Montréal": "CF Montréal",
        "CF Montreal": "CF Montréal",
        "Nashville SC": "Nashville SC",
        "New England Revolution": "New England Revolution",
        "New York City FC": "New York City Football Club",
        "New York City": "New York City Football Club",
        "NYCFC": "New York City Football Club",
        "New York Red Bulls": "Red Bull New York",
        "Red Bull New York": "Red Bull New York",
        "Orlando City": "Orlando City",
        "Philadelphia Union": "Philadelphia Union",
        "Portland Timbers": "Portland Timbers",
        "Real Salt Lake": "Real Salt Lake",
        "San Jose Earthquakes": "San Jose Earthquakes",
        "Seattle Sounders": "Seattle Sounders FC",
        "Sporting Kansas City": "Sporting Kansas City",
        "Sporting KC": "Sporting Kansas City",
        "St. Louis CITY": "St. Louis CITY SC",
        "St Louis City": "St. Louis CITY SC",
        "Toronto FC": "Toronto FC",
        "Vancouver Whitecaps": "Vancouver Whitecaps FC",
        "San Diego FC": "San Diego FC"
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
                        'crest') or d.get('picture') or d.get('image')

                    if name and logo and isinstance(name, str):
                        for search_name, official_name in mls_teams.items():
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
            for search_name, official_name in mls_teams.items():
                if search_name.lower() in alt_lower and ("logo" in alt_lower or "crest" in alt_lower or "mls" in url):
                    if url.startswith('//'):
                        url = 'https:' + url
                    scraped_logos[official_name] = url

    if not scraped_logos:
        print("No logos found! MLS might have changed their website layout.")
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
                "color": "green",
                "icon": "futbol",
                "prefix": "fa",
                "logo": logo_url
            }
        else:
            config["team_styles"][team_name]["logo"] = logo_url
        updates += 1

    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    print(
        f"Successfully scraped and added {updates} MLS team logos into config.json!")


if __name__ == '__main__':
    scrape_and_update_mls_logos()
