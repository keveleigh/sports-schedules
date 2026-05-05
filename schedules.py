import argparse
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

import dateutil.parser
import pytz
from timezonefinder import TimezoneFinder


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two coordinates using the Haversine formula."""
    if lat1 == 0.0 and lon1 == 0.0:
        return float('inf')
    if lat2 == 0.0 and lon2 == 0.0:
        return float('inf')

    R = 3958.8  # Radius of earth in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def update_local_jsons():
    """Fetch the latest schedules from URLs and update the local JSON files."""
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)

    urls = {
        "seattle-reign.json": "https://fixturedownload.com/feed/json/nwsl-2026/seattle-reign",
        "san-francisco-giants.json": "https://fixturedownload.com/feed/json/mlb-2026/san-francisco-giants",
        "seattle-mariners.json": "https://fixturedownload.com/feed/json/mlb-2026/seattle-mariners",
        "seattle-sounders-fc.json": "https://fixturedownload.com/feed/json/mls-2026/seattle-sounders-fc",
        "atlanta-united.json": "https://fixturedownload.com/feed/json/mls-2026/atlanta-united"
    }
    for filename, url in urls.items():
        filepath = data_dir / filename
        print(f"Downloading latest schedule for {filename}...")
        try:
            # Use a standard user-agent to prevent basic 403 Forbidden errors
            req = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            print(f"Successfully updated {filename}")
        except Exception as e:
            print(f"Failed to update {filename} from {url}: {e}")


def parse_and_combine_schedules(home_mode=False):
    # Get all JSON files in the data directory
    data_dir = Path('data')
    json_files = [f for f in data_dir.glob(
        '*.json') if 'final_schedules' not in f.name]

    all_schedules = []

    # Create a dictionary of all MLB stadiums as keys with their cities and states as the value
    mlb_stadiums = {
        "American Family Field": ("Milwaukee", "WI", 43.028, -87.971),
        "Angel Stadium": ("Anaheim", "CA", 33.800, -117.882),
        "Busch Stadium": ("St. Louis", "MO", 38.622, -90.192),
        "Chase Field": ("Phoenix", "AZ", 33.445, -112.066),
        "Citi Field": ("New York", "NY", 40.757, -73.845),
        "Citizens Bank Park": ("Philadelphia", "PA", 39.905, -75.166),
        "Comerica Park": ("Detroit", "MI", 42.339, -83.048),
        "Coors Field": ("Denver", "CO", 39.755, -104.994),
        "Daikin Park": ("Houston", "TX", 29.757, -95.355),
        "Dodger Stadium": ("Los Angeles", "CA", 34.073, -118.240),
        "Fenway Park": ("Boston", "MA", 42.346, -71.097),
        "Globe Life Field": ("Arlington", "TX", 32.747, -97.083),
        "Great American Ball Park": ("Cincinnati", "OH", 39.097, -84.506),
        "Kauffman Stadium": ("Kansas City", "MO", 39.051, -94.480),
        "loanDepot park": ("Miami", "FL", 25.778, -80.219),
        "Nationals Park": ("Washington", "DC", 38.873, -77.007),
        "Oracle Park": ("San Francisco", "CA", 37.778, -122.389),
        "Oriole Park at Camden Yards": ("Baltimore", "MD", 39.284, -76.621),
        "Petco Park": ("San Diego", "CA", 32.707, -117.156),
        "PNC Park": ("Pittsburgh", "PA", 40.446, -80.005),
        "Progressive Field": ("Cleveland", "OH", 41.496, -81.685),
        "Rate Field": ("Chicago", "IL", 41.830, -87.633),
        "Rogers Centre": ("Toronto", "ON", 43.641, -79.389),
        "Sutter Health Park": ("Sacramento", "CA", 38.580, -121.505),
        "T-Mobile Park": ("Seattle", "WA", 47.591, -122.332),
        "Target Field": ("Minneapolis", "MN", 44.981, -93.277),
        "Tropicana Field": ("St. Petersburg", "FL", 27.768, -82.653),
        "Truist Park": ("Atlanta", "GA", 33.890, -84.467),
        "Wrigley Field": ("Chicago", "IL", 41.948, -87.655),
        "Yankee Stadium": ("New York", "NY", 40.829, -73.926),
    }

    # Create a dictionary of all MLS stadiums as keys with their cities and states as the value
    mls_stadiums = {
        "Allianz Field": ("Saint Paul", "MN", 44.953, -93.165),
        "America First Field": ("Sandy", "UT", 40.582, -111.893),
        "Audi Field": ("Washington", "DC", 38.868, -77.012),
        "Bank of America Stadium": ("Charlotte", "NC", 35.225, -80.852),
        "BC Place": ("Vancouver", "BC", 49.276, -123.111),
        "BMO Field": ("Toronto", "ON", 43.633, -79.418),
        "BMO Stadium": ("Los Angeles", "CA", 34.013, -118.284),
        "DICK'S Sporting Goods Park": ("Commerce City", "CO", 39.805, -104.891),
        "Dignity Health Sports Park": ("Carson", "CA", 33.864, -118.261),
        "Energizer Park": ("St. Louis", "MO", 38.631, -90.210),
        "GEODIS Park": ("Nashville", "TN", 36.130, -86.767),
        "Gillette Stadium": ("Foxborough", "MA", 42.090, -71.264),
        "Inter&Co Stadium": ("Orlando", "FL", 28.541, -81.389),
        "Lumen Field": ("Seattle", "WA", 47.595, -122.331),
        "Mercedes-Benz Stadium": ("Atlanta", "GA", 33.755, -84.400),
        "Nu Stadium": ("Miami", "FL", 25.793, -80.259),
        "PayPal Park": ("San Jose", "CA", 37.351, -121.925),
        "Providence Park": ("Portland", "OR", 45.521, -122.691),
        "Q2 Stadium": ("Austin", "TX", 30.388, -97.719),
        "Red Bull Arena": ("Harrison", "NJ", 40.736, -74.150),
        "ScottsMiracle-Gro Field": ("Columbus", "OH", 39.968, -83.017),
        "Shell Energy Stadium": ("Houston", "TX", 29.752, -95.352),
        "Snapdragon Stadium": ("San Diego", "CA", 32.784, -117.119),
        "Soldier Field": ("Chicago", "IL", 41.862, -87.616),
        "Sporting Park": ("Kansas City", "MO", 39.121, -94.823),
        "Stade Saputo": ("Montreal", "QC", 45.563, -73.551),
        "Subaru Park": ("Chester", "PA", 39.832, -75.378),
        "Sports Illustrated Stadium": ("Harrison", "NJ", 40.094, -73.900),
        "Toyota Stadium": ("Frisco", "TX", 33.154, -96.835),
        "TQL Stadium": ("Cincinnati", "OH", 39.111, -84.522),
    }

    # Create a dictionary of all NWSL stadiums as keys with their cities and states as the value
    nwsl_stadiums = {
        "Providence Park": ("Portland", "OR", 45.521, -122.691),
        "Lumen Field": ("Seattle", "WA", 47.595, -122.331),
        "BMO Stadium": ("Los Angeles", "CA", 34.013, -118.284),
        "Snapdragon Stadium": ("San Diego", "CA", 32.784, -117.119),
        # "Red Bull Arena": ("Harrison", "NJ", 40.736, -74.150),
        "First Horizon Stadium at WakeMed Soccer Park": ("Cary", "NC", 35.785, -78.753),
        "Audi Field": ("Washington", "DC", 38.868, -77.012),
        "Lynn Family Stadium": ("Louisville", "KY", 38.259, -85.733),
        "CPKC Stadium": ("Kansas City", "KS", 39.117, -94.573),
        "Northwestern Medicine Field at Martin Stadium": ("Evanston", "IL", 42.065, -87.674),
        "Inter&Co Stadium": ("Orlando", "FL", 28.541, -81.389),
        "Shell Energy Stadium": ("Houston", "TX", 29.752, -95.352),
        "PayPal Park": ("San Jose", "CA", 37.351, -121.925),
        "America First Field": ("Sandy", "UT", 40.582, -111.893),
        "Centreville Bank Stadium": ("Pawtucket", "RI", 41.875, -71.382),
        "Icahn Stadium": ("New York", "NY", 40.793, -73.925),
        "Centennial Stadium": ("Centennial", "CO", 39.583, -104.827),
    }

    missing_stadiums = set()

    # Parse each JSON file
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                stem = json_file.stem.lower()
                is_mlb = "giants" in stem or "mariners" in stem
                is_mls = "sounders" in stem or "atlanta" in stem
                # Filter in specified away teams
                if home_mode:
                    included_teams = {
                        "Seattle Mariners", "Seattle Sounders FC"}
                else:
                    included_teams = {"San Francisco Giants", "Seattle Mariners",
                                      "Seattle Sounders FC", "Atlanta United", "Seattle Reign"}
                # Handle both list and dict formats
                stadiums = mlb_stadiums if is_mlb else mls_stadiums if is_mls else nwsl_stadiums

                if not isinstance(data, list):
                    data = [data]

                for item in data:
                    team_key = 'HomeTeam' if home_mode else 'AwayTeam'
                    if item.get(team_key) in included_teams:
                        league = 'MLB' if is_mlb else 'MLS' if is_mls else 'NWSL'
                        location = item.get('Location')
                        if location not in stadiums and location is not None:
                            missing_stadiums.add(f"{location} ({league})")

                        city, state, lat, lon = stadiums.get(
                            location, ("Unknown", "Unknown", 0.0, 0.0))
                        all_schedules.append(
                            {**item, 'City': city, 'State': state, 'Lat': lat, 'Lon': lon, 'League': league})
        except json.JSONDecodeError:
            print(f"Error parsing {json_file}")

    if missing_stadiums:
        print("WARNING: The following stadiums were not found in your dictionaries and need to be added:")
        for st in sorted(missing_stadiums):
            print(f" - {st}")

    # Remove duplicate entries from all_schedules
    unique_schedules = {}
    for item in all_schedules:
        identifier = (item.get('League'), item.get('DateUtc'),
                      item.get('HomeTeam'), item.get('AwayTeam'))
        if identifier not in unique_schedules:
            unique_schedules[identifier] = item
    all_schedules = list(unique_schedules.values())

    # Sort by date
    all_schedules.sort(key=lambda x: dateutil.parser.parse(x['DateUtc']))

    # Add Local Time conversion
    tf = TimezoneFinder()
    for game in all_schedules:
        dt_utc = dateutil.parser.parse(game['DateUtc'])
        tz_str = tf.timezone_at(lat=game.get(
            'Lat', 0.0), lng=game.get('Lon', 0.0))
        if tz_str:
            local_tz = pytz.timezone(tz_str)
            dt_local = dt_utc.astimezone(local_tz)
            game['DateLocal'] = dt_local.strftime("%B %d, %Y at %I:%M %p %Z")
        else:
            game['DateLocal'] = dt_utc.strftime("%B %d, %Y at %I:%M %p UTC")

    # Group games into series
    game_to_series = {}
    series_to_games = defaultdict(list)
    active_series = {}
    series_counter = 0

    for item in all_schedules:
        identifier = (item.get('League'), item.get('DateUtc'),
                      item.get('HomeTeam'), item.get('AwayTeam'))
        matchup = (item.get('League'), item.get(
            'HomeTeam'), item.get('AwayTeam'))
        game_date = dateutil.parser.parse(item['DateUtc'])

        if matchup in active_series:
            s_id, last_date = active_series[matchup]
            if (game_date - last_date).days <= 3:
                active_series[matchup] = (s_id, game_date)
                game_to_series[identifier] = s_id
                series_to_games[s_id].append(item)
                continue

        series_counter += 1
        active_series[matchup] = (series_counter, game_date)
        game_to_series[identifier] = series_counter
        series_to_games[series_counter].append(item)

    # Search through all_schedules for games in the same city within a few days of each other
    final_schedules = []
    added_identifiers = set()
    for i, current_game in enumerate(all_schedules):
        current_date = dateutil.parser.parse(current_game['DateUtc'])
        current_lat = current_game.get('Lat', 0.0)
        current_lon = current_game.get('Lon', 0.0)
        current_league = current_game.get('League', '')
        current_local_day = current_game.get('DateLocal', '').split(' at ')[0]

        for j in range(i + 1, len(all_schedules)):
            next_game = all_schedules[j]
            next_date = dateutil.parser.parse(next_game['DateUtc'])
            next_lat = next_game.get('Lat', 0.0)
            next_lon = next_game.get('Lon', 0.0)
            next_league = next_game.get('League', '')
            next_local_day = next_game.get('DateLocal', '').split(' at ')[0]

            if (next_date - current_date).days > 4:
                break

            distance = calculate_distance(
                current_lat, current_lon, next_lat, next_lon)

            if home_mode:
                is_overlap = current_local_day == next_local_day
            else:
                is_overlap = (
                    distance <= 50.0 and current_league != next_league)

            if is_overlap:
                if 'NearbyGames' not in current_game:
                    current_game['NearbyGames'] = []
                if 'NearbyGames' not in next_game:
                    next_game['NearbyGames'] = []

                current_game['NearbyGames'].append({
                    'TargetTeam': next_game.get('HomeTeam') if home_mode else next_game.get('AwayTeam'),
                    'AwayTeam': next_game.get('AwayTeam'),
                    'Location': next_game.get('Location'),
                    'DateLocal': next_game.get('DateLocal'),
                    'DistanceMiles': round(distance, 2)
                })
                next_game['NearbyGames'].append({
                    'TargetTeam': current_game.get('HomeTeam') if home_mode else current_game.get('AwayTeam'),
                    'AwayTeam': current_game.get('AwayTeam'),
                    'Location': current_game.get('Location'),
                    'DateLocal': current_game.get('DateLocal'),
                    'DistanceMiles': round(distance, 2)
                })

                c_id = (current_game.get('League'), current_game.get(
                    'DateUtc'), current_game.get('HomeTeam'), current_game.get('AwayTeam'))
                n_id = (next_game.get('League'), next_game.get('DateUtc'),
                        next_game.get('HomeTeam'), next_game.get('AwayTeam'))

                if home_mode:
                    if c_id not in added_identifiers:
                        final_schedules.append(current_game)
                        added_identifiers.add(c_id)
                    if n_id not in added_identifiers:
                        final_schedules.append(next_game)
                        added_identifiers.add(n_id)
                else:
                    for s_game in series_to_games[game_to_series[c_id]]:
                        s_id = (s_game.get('League'), s_game.get('DateUtc'),
                                s_game.get('HomeTeam'), s_game.get('AwayTeam'))
                        if s_id not in added_identifiers:
                            final_schedules.append(s_game)
                            added_identifiers.add(s_id)

                    for s_game in series_to_games[game_to_series[n_id]]:
                        s_id = (s_game.get('League'), s_game.get('DateUtc'),
                                s_game.get('HomeTeam'), s_game.get('AwayTeam'))
                        if s_id not in added_identifiers:
                            final_schedules.append(s_game)
                            added_identifiers.add(s_id)

    final_schedules.sort(key=lambda x: dateutil.parser.parse(x['DateUtc']))

    # Print results
    print(json.dumps(final_schedules, indent=2))
    print(len(final_schedules))

    # Save results to a file
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / \
        ('final_schedules_home.json' if home_mode else 'final_schedules_away.json')
    with open(output_file, 'w') as f:
        json.dump(final_schedules, f, indent=2)
    print(f"Results successfully saved to {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process sports schedules.")
    parser.add_argument('--update', action='store_true',
                        help="Fetch latest schedules from URLs and update local JSON files.")
    parser.add_argument('--home', action='store_true',
                        help="Find overlapping home games on the same day.")
    args = parser.parse_args()

    if args.update:
        update_local_jsons()

    parse_and_combine_schedules(home_mode=args.home)
