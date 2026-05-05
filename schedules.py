import argparse
import json
import urllib.request
from pathlib import Path

import dateutil.parser
import pytz


with open('config.json', 'r') as f:
    config = json.load(f)


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


def parse_and_combine_schedules():
    # Get all JSON files in the data directory
    data_dir = Path('data')
    json_files = list(data_dir.glob('*.json'))

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

    # Save results to a file
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'all_schedules.json'
    with open(output_file, 'w') as f:
        json.dump(all_schedules, f, indent=2)
    print(f"Results successfully saved to {output_file}")
    print(f"Total Unique Games Parsed: {len(all_schedules)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process sports schedules.")
    parser.add_argument('--update', action='store_true',
                        help="Fetch latest schedules from URLs and update local JSON files.")
    args = parser.parse_args()

    if args.update:
        update_local_jsons()

    parse_and_combine_schedules()
