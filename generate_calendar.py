import json
import argparse
import dateutil.parser
from pathlib import Path


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
    }

    events = []
    for game in games:
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

    # Create an HTML file using FullCalendar
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js'></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <script>
      document.addEventListener('DOMContentLoaded', function() {{
        var calendarEl = document.getElementById('calendar');
        var calendar = new FullCalendar.Calendar(calendarEl, {{
          initialView: 'listYear',
          events: {json.dumps(events)},
          eventContent: function(arg) {{
            let html = '<b>' + arg.event.title + '</b><br>';
            html += '<i>' + arg.event.extendedProps.league + ' - ' + arg.event.extendedProps.location + '</i><br>';
            return {{ html: html }};
          }}
        }});
        calendar.render();
      }});
    </script>
    <style>
      body {{ margin: 40px 10px; padding: 0; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; font-size: 14px; background-color: #f8f9fa; }}
      #calendar {{ max-width: 900px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
      .fc-list-event-title {{ white-space: normal !important; }}
    </style>
</head>
<body>
    <h2 class="text-center mb-4">{'Home' if home_mode else 'Away'} Schedule Overlaps</h2>
    <div id='calendar'></div>
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
