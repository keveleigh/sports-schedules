import argparse
import json
from pathlib import Path


with open('config.json', 'r') as f:
    config = json.load(f)


def create_calendar(home_mode=False):
    input_dir = Path('output')
    input_file = input_dir / 'all_schedules.json'

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

    team_colors = {team: style["color"] for team,
                   style in config.get("team_styles", {}).items()}
    league_colors = {league: style["color"] for league,
                     style in config.get("league_styles", {}).items()}
    team_logos = {team: style.get("logo", "") for team,
                  style in config.get("team_styles", {}).items()}

    unique_teams = set()
    for game in games:
        unique_teams.add(game.get('AwayTeam'))
        unique_teams.add(game.get('HomeTeam'))

    default_teams = ["Seattle Mariners", "Seattle Sounders FC"] if home_mode else [
        "San Francisco Giants", "Seattle Mariners", "Seattle Sounders FC", "Seattle Reign"
    ]

    select_options = "".join(
        [f'<option value="{t}"{" selected" if t in default_teams else ""}>{t}</option>' for t in sorted(list(unique_teams))])
    dropdown_html = f"""
    <div class='mb-5' style='max-width: 600px; margin: 0 auto;'>
        <label for="team-filter" class="form-label fw-bold">Select Teams to Compare:</label>
        <select id="team-filter" multiple>
            {select_options}
        </select>
        <small class="text-muted d-block mt-2">Select at least two teams to find overlapping trips between them.</small>
    </div>
    """

    global_js = f"""
      const allGames = {json.dumps(games)};
      const homeMode = {'true' if home_mode else 'false'};
      const teamColors = {json.dumps(team_colors)};
      const leagueColors = {json.dumps(league_colors)};
      const teamLogos = {json.dumps(team_logos)};

      var calendars = [];

      allGames.forEach(g => {{
          g.parsedDate = new Date(g.DateUtc);
          g.localDay = g.DateLocal ? g.DateLocal.split(' at ')[0] : g.DateUtc;
      }});

      function calculateDistance(lat1, lon1, lat2, lon2) {{
          if (lat1 === 0 && lon1 === 0) return Infinity;
          if (lat2 === 0 && lon2 === 0) return Infinity;
          const R = 3958.8;
          const dLat = (lat2 - lat1) * Math.PI / 180;
          const dLon = (lon2 - lon1) * Math.PI / 180;
          const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
          const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
          return R * c;
      }}

      function generateICS(trip) {{
          let lines = [
              "BEGIN:VCALENDAR",
              "VERSION:2.0",
              "PRODID:-//Sports Schedules//EN",
          ];
          trip.forEach((game, idx) => {{
              let dtStart = game.parsedDate;
              let dtEnd = new Date(dtStart.getTime() + 3 * 60 * 60 * 1000);

              let startStr = dtStart.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
              let endStr = dtEnd.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

              lines.push(
                  "BEGIN:VEVENT",
                  `UID:${{startStr}}-${{idx}}@sports-schedules`,
                  `SUMMARY:${{game.AwayTeam}} @ ${{game.HomeTeam}}`,
                  `DTSTART:${{startStr}}`,
                  `DTEND:${{endStr}}`,
                  `LOCATION:${{game.Location || 'Unknown'}}`,
                  "END:VEVENT"
              );
          }});
          lines.push("END:VCALENDAR");
          return lines.join("\\r\\n");
      }}

      function buildTrips(selectedTeams) {{
          if (selectedTeams.length < 2) return [];

          let activeGames = allGames.filter(g => {{
              if (homeMode) {{
                  return selectedTeams.includes(g.HomeTeam);
              }} else {{
                  return selectedTeams.includes(g.AwayTeam);
              }}
          }});

          let edges = [];
          for (let i = 0; i < activeGames.length; i++) {{
              for (let j = i + 1; j < activeGames.length; j++) {{
                  let g1 = activeGames[i];
                  let g2 = activeGames[j];

                  let diffDays = Math.floor(Math.abs(g2.parsedDate - g1.parsedDate) / (1000 * 60 * 60 * 24));

                  if (g1.HomeTeam === g2.HomeTeam && g1.AwayTeam === g2.AwayTeam && g1.League === g2.League) {{
                      if (!homeMode && diffDays <= 3) {{
                          edges.push({{u: i, v: j, cross: false}});
                      }}
                      continue;
                  }}

                  if (g1.League === g2.League) continue;

                  let timeValid = false;
                  if (homeMode) {{
                      timeValid = (g1.localDay === g2.localDay);
                  }} else {{
                      timeValid = (diffDays <= 4);
                  }}

                  if (!timeValid) continue;

                  let dist = calculateDistance(g1.Lat, g1.Lon, g2.Lat, g2.Lon);
                  if (dist <= 50) {{
                      edges.push({{u: i, v: j, cross: true}});
                  }}
              }}
          }}

          let parent = Array.from({{length: activeGames.length}}, (_, i) => i);
          function find(i) {{
              if (parent[i] === i) return i;
              return parent[i] = find(parent[i]);
          }}
          function union(i, j) {{
              let rootI = find(i);
              let rootJ = find(j);
              if (rootI !== rootJ) parent[rootI] = rootJ;
          }}

          edges.forEach(e => union(e.u, e.v));

          let validRoots = new Set();
          edges.forEach(e => {{
              if (e.cross) validRoots.add(find(e.u));
          }});

          let tripsDict = {{}};
          for (let i = 0; i < activeGames.length; i++) {{
              let r = find(i);
              if (validRoots.has(r)) {{
                  if (!tripsDict[r]) tripsDict[r] = [];
                  tripsDict[r].push(activeGames[i]);
              }}
          }}

          let trips = Object.values(tripsDict);
          trips.sort((a, b) => a[0].parsedDate - b[0].parsedDate);
          return trips;
      }}

      function renderTrips(selectedTeams) {{
          calendars.forEach(c => c.destroy());
          calendars = [];

          let wrapper = document.getElementById('calendars-wrapper');
          wrapper.innerHTML = '';

          if (selectedTeams.length < 2) {{
              wrapper.innerHTML = '<p class="text-center text-muted mt-5">Please select at least 2 teams from the dropdown above to find overlapping trips between them.</p>';
              return;
          }}

          let trips = buildTrips(selectedTeams);

          if (trips.length === 0) {{
              wrapper.innerHTML = '<p class="text-center text-muted mt-5">No overlapping trips found between the selected teams.</p>';
              return;
          }}

          trips.forEach((trip, idx) => {{
              let cities = [...new Set(trip.map(g => g.City || 'Unknown'))];
              let cityStr = cities.join(" & ");

              let startDateStr = trip[0].localDay;
              let endDateStr = trip[trip.length-1].localDay;

              let formatOpts = {{ month: 'short', day: 'numeric' }};
              let startDate = new Date(startDateStr).toLocaleDateString('en-US', formatOpts);
              let endDate = new Date(endDateStr).toLocaleDateString('en-US', formatOpts);

              let dateStr = (startDate === endDate) ? startDate : `${{startDate}} - ${{endDate}}`;

              let headingTitle = homeMode ? "Homestand" : "Trip";
              let tripTitle = `${{headingTitle}}: ${{cityStr}} (${{dateStr}})`;

              let icsContent = generateICS(trip);
              let blob = new Blob([icsContent], {{ type: 'text/calendar;charset=utf-8;' }});
              let icsUrl = URL.createObjectURL(blob);

              let tripContainer = document.createElement('div');
              tripContainer.innerHTML = `
                  <div class='d-flex justify-content-center align-items-center mt-5 mb-3'>
                    <h3 class='mb-0' style='color: #495057;'>${{tripTitle}}</h3>
                    <a href='${{icsUrl}}' class='btn btn-sm btn-outline-primary ms-3' download='trip_${{idx}}.ics'>Export (.ics)</a>
                  </div>
                  <div id='calendar_${{idx}}' class='calendar-container'></div>
              `;
              wrapper.appendChild(tripContainer);

              let events = trip.map(game => {{
                  let team = homeMode ? game.HomeTeam : game.AwayTeam;
                  let color = teamColors[team] || leagueColors[game.League] || "gray";
                  let logo = teamLogos[team] || "";

                  return {{
                      title: `${{game.AwayTeam}} @ ${{game.HomeTeam}}`,
                      start: game.DateUtc,
                      color: color,
                      extendedProps: {{
                          location: game.Location,
                          league: game.League,
                          logo: logo,
                          trackedTeam: team
                      }}
                  }};
              }});

              let calendarEl = document.getElementById(`calendar_${{idx}}`);
              let calendar = new FullCalendar.Calendar(calendarEl, {{
                  initialView: 'listYear',
                  height: 'auto',
                  headerToolbar: false,
                  events: events,
                  eventContent: function(arg) {{
                      let logoHtml = '';
                      if (arg.event.extendedProps.logo) {{
                          logoHtml = `<img src="${{arg.event.extendedProps.logo}}" style="width: 35px; height: 35px; object-fit: contain; margin-right: 15px;">`;
                      }} else {{
                          let initialAvatar = `https://ui-avatars.com/api/?name=${{encodeURIComponent(arg.event.extendedProps.trackedTeam)}}&background=e9ecef&color=495057&bold=true`;
                          logoHtml = `<img src="${{initialAvatar}}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: contain; margin-right: 15px;">`;
                      }}
                      let html = `<div class="d-flex align-items-center">
                                    ${{logoHtml}}
                                    <div>
                                      <b>${{arg.event.title}}</b><br>
                                      <i>${{arg.event.extendedProps.league}} - ${{arg.event.extendedProps.location}}</i>
                                    </div>
                                  </div>`;
                      return {{ html: html }};
                  }}
              }});
              calendar.render();
              calendars.push(calendar);
          }});
      }}

      document.addEventListener('DOMContentLoaded', function() {{
        const filterEl = document.getElementById('team-filter');
        const choices = new Choices(filterEl, {{
            removeItemButton: true,
            placeholderValue: 'Filter by teams...',
            searchPlaceholderValue: 'Search teams'
        }});
        
        filterEl.addEventListener('change', function() {{
            var activeTeams = Array.from(filterEl.selectedOptions).map(opt => opt.value);
            renderTrips(activeTeams);
        }});
        
        var initialTeams = Array.from(filterEl.selectedOptions).map(opt => opt.value);
        renderTrips(initialTeams);
      }});
    """

    # Create an HTML file using FullCalendar
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js'></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js"></script>
    <script>{global_js}</script>
    <style>
      body {{ background-color: #f8f9fa; padding: 40px 15px; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; }}
      .calendar-container {{ max-width: 900px; margin: 0 auto 40px auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
      .fc-list-event-title {{ white-space: normal !important; }}
      .fc-list-event-graphic {{ display: none !important; }}
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: 0 auto; padding-top: 20px;">
        <a href="../index.html" class="btn btn-outline-secondary">&larr; Back to Menu</a>
    </div>
    <h2 class="text-center mb-4">{'Home' if home_mode else 'Away'} Schedule Overlaps</h2>
    {dropdown_html}
    <div id="calendars-wrapper"></div>
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
