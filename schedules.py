import argparse
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

import dateutil.parser
import pytz


with open('config.json', 'r') as f:
    config = json.load(f)


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

    # Clean up old team-specific files
    for old_file in data_dir.glob('*.json'):
        old_file.unlink()

    urls = config.get("urls", {})
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

    stadiums = config.get("stadiums", {})
    file_leagues = config.get("file_leagues", {})

    missing_stadiums = set()

    # Parse each JSON file
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

                if not isinstance(data, list):
                    data = [data]

                for item in data:
                    league = file_leagues.get(json_file.name, 'Unknown')
                    location = item.get('Location')
                    if location not in stadiums and location is not None:
                        missing_stadiums.add(f"{location} ({league})")

                    stadium_info = stadiums.get(
                        location, ["Unknown", "Unknown", 0.0, 0.0, None])
                    city, state, lat, lon = stadium_info[0], stadium_info[1], stadium_info[2], stadium_info[3]
                    tz_str = stadium_info[4] if len(stadium_info) > 4 else None

                    all_schedules.append(
                        {**item, 'City': city, 'State': state, 'Lat': lat, 'Lon': lon, 'League': league, 'Timezone': tz_str})
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
    for game in all_schedules:
        dt_utc = dateutil.parser.parse(game['DateUtc'])
        tz_str = game.get('Timezone')
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
                is_overlap = (distance <= 50.0 and current_league !=
                              next_league and current_local_day == next_local_day)
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
