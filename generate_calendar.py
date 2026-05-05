import json
import argparse
import dateutil.parser
from pathlib import Path
import schedules
from collections import defaultdict


def create_calendar(home_mode=False):
    input_dir = Path('output')
    input_file = input_dir / \
        ('final_schedules_home.json' if home_mode else 'final_schedules_away.json')

    output_dir = Path('html')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / \
        ('calendar_home.html' if home_mode else 'calendar_away.html')

    try:
        with open(input_file, 'r') as f:
            games = json.load(f)
    except FileNotFoundError:
        print(f"No file found at {input_file}")
        return

    if not games:
        print("No games to map!")
        return

    team_colors = {
        "San Francisco Giants": "orange",
        "Seattle Mariners": "cadetblue",
        "Seattle Sounders FC": "green",
        "Seattle Reign": "darkblue",
        "Atlanta United": "red"
    }

    # Build Connected Components to group games into "Trips"
    n = len(games)
    parent = list(range(n))

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n):
        dt_i = dateutil.parser.parse(games[i]['DateUtc'])
        for j in range(i + 1, n):
            dt_j = dateutil.parser.parse(games[j]['DateUtc'])
            if (dt_j - dt_i).days > 4:
                break

            lat1 = games[i].get('Lat', 0.0)
            lon1 = games[i].get('Lon', 0.0)
            lat2 = games[j].get('Lat', 0.0)
            lon2 = games[j].get('Lon', 0.0)

            dist = schedules.calculate_distance(lat1, lon1, lat2, lon2)
            if dist <= 50.0:
                union(i, j)

    trips_dict = defaultdict(list)
    for i in range(n):
        trips_dict[find(i)].append(games[i])

    # Sort trips chronologically by their first game
    trips = list(trips_dict.values())
    trips.sort(key=lambda t: dateutil.parser.parse(t[0]['DateUtc']))

    calendars_html = ""
    js_initializations = ""

    for idx, trip in enumerate(trips):
        events = []
        cities = []
        for game in trip:
            dt = dateutil.parser.parse(game['DateUtc'])

            team = game.get('AwayTeam')
            if team not in team_colors and game.get('HomeTeam') in team_colors:
                team = game.get('HomeTeam')

            events.append({
                "title": f"{game['AwayTeam']} @ {game['HomeTeam']}",
                "start": dt.isoformat(),
                "color": team_colors.get(team, "gray"),
                "extendedProps": {
                    "location": game['Location'],
                    "league": game['League']
                }
            })

            city = game.get('City', 'Unknown')
            if city and city not in cities:
                cities.append(city)

        city_str = " & ".join(cities)
        
        start_date_str = trip[0].get('DateLocal', '').split(' at ')[0] or trip[0]['DateUtc']
        start_date = dateutil.parser.parse(start_date_str).strftime("%b %d")
        
        end_date_str = trip[-1].get('DateLocal', '').split(' at ')[0] or trip[-1]['DateUtc']
        end_date = dateutil.parser.parse(end_date_str).strftime("%b %d")

        if start_date == end_date:
            date_str = start_date
        else:
            date_str = f"{start_date} - {end_date}"

        heading_title = "Homestand" if home_mode else "Trip"
        trip_title = f"{heading_title}: {city_str} ({date_str})"

        calendars_html += f"<h3 class='mt-5 mb-3 text-center' style='color: #495057;'>{trip_title}</h3>\n"
        calendars_html += f"<div id='calendar_{idx}' class='calendar-container'></div>\n"

        js_initializations += f"""
        var calendarEl_{idx} = document.getElementById('calendar_{idx}');
        var calendar_{idx} = new FullCalendar.Calendar(calendarEl_{idx}, {{
          initialView: 'listYear',
          height: 'auto',
          events: {json.dumps(events)},
          eventContent: function(arg) {{
            let html = '<b>' + arg.event.title + '</b><br>';
            html += '<i>' + arg.event.extendedProps.league + ' - ' + arg.event.extendedProps.location + '</i><br>';
            return {{ html: html }};
          }}
        }});
        calendar_{idx}.render();
        """

    # Create an HTML file using FullCalendar
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js'></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <script>
      document.addEventListener('DOMContentLoaded', function() {{
        {js_initializations}
      }});
    </script>
    <style>
      body {{ margin: 40px 10px; padding: 0; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 14px; background-color: #f8f9fa; }}
      .calendar-container {{ max-width: 900px; margin: 0 auto 40px auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
      .fc-list-event-title {{ white-space: normal !important; }}
    </style>
</head>
<body>
    <h2 class="text-center mb-4">{'Home' if home_mode else 'Away'} Schedule Overlaps</h2>
    {calendars_html}
</body>
</html>
"""
    with open(output_file, 'w') as f:
        f.write(html_content)
    print(f"Calendar successfully generated and saved to {output_file}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate calendar visualization.")
    parser.add_argument('--home', action='store_true',
                        help="Use home games data.")
    args = parser.parse_args()

    create_calendar(home_mode=args.home)
