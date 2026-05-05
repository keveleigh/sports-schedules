import argparse
import json
from pathlib import Path


with open('config.json', 'r') as f:
    config = json.load(f)


def create_map(home_mode=False):
    input_dir = Path('output')
    input_file = input_dir / 'all_schedules.json'

    output_dir = Path('html')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / \
        ('map_home.html' if home_mode else 'map_away.html')

    try:
        with open(input_file, 'r') as f:
            games = json.load(f)
    except FileNotFoundError:
        print(f"No games found at {input_file} to map!")
        return

    if not games:
        print("No games to map!")
        return

    team_styles = config.get("team_styles", {})
    league_styles = config.get("league_styles", {})
    team_logos = {team: style.get("logo", "")
                  for team, style in team_styles.items()}

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
        <small class="text-muted d-block mt-2">Select at least two teams to map overlapping trips between them.</small>
    </div>
    """

    global_js = f"""
      const allGames = {json.dumps(games)};
      const homeMode = {'true' if home_mode else 'false'};
      const teamStyles = {json.dumps(team_styles)};
      const leagueStyles = {json.dumps(league_styles)};
      const teamLogos = {json.dumps(team_logos)};

      var map;
      var markersLayer;
      
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

      function renderMap(selectedTeams) {{
          markersLayer.clearLayers();

          if (selectedTeams.length < 2) {{
              map.setView([39.8283, -98.5795], 4);
              return;
          }}

          let trips = buildTrips(selectedTeams);

          if (trips.length === 0) {{
              map.setView([39.8283, -98.5795], 4);
              return;
          }}

          // Group games by exact coordinates
          let locationGroups = {{}};
          trips.forEach(trip => {{
              trip.forEach(game => {{
                  let key = game.Lat + "," + game.Lon;
                  if (!locationGroups[key]) {{
                      locationGroups[key] = {{ lat: game.Lat, lon: game.Lon, games: [] }};
                  }}
                  // Ensure unique games per location
                  let existing = locationGroups[key].games.find(g => g.MatchNumber === game.MatchNumber && g.League === game.League);
                  if (!existing) {{
                      locationGroups[key].games.push(game);
                  }}
              }});
          }});

          let bounds = [];

          for (let key in locationGroups) {{
              let loc = locationGroups[key];
              
              loc.games.sort((a, b) => a.parsedDate - b.parsedDate);
              let popupHtml = "";

              loc.games.forEach((game, i) => {{
                  let dateStr = game.DateLocal || (game.DateUtc + " UTC");
                  let team = homeMode ? game.HomeTeam : game.AwayTeam;
                  let logo = teamLogos[team] || "";

                  let logoHtml = '';
                  if (logo) {{
                      logoHtml = `<img src="${{logo}}" style="width: 35px; height: 35px; object-fit: contain; margin-right: 15px;">`;
                  }} else {{
                      let initialAvatar = `https://ui-avatars.com/api/?name=${{encodeURIComponent(team)}}&background=e9ecef&color=495057&bold=true`;
                      logoHtml = `<img src="${{initialAvatar}}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: contain; margin-right: 15px;">`;
                  }}

                  popupHtml += `
                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                        ${{logoHtml}}
                        <div>
                            <b>${{game.AwayTeam}} @ ${{game.HomeTeam}}</b><br>
                            <i>${{game.League}} - ${{game.Location}}</i><br>
                            ${{dateStr}}
                        </div>
                    </div>`;

                  if (i < loc.games.length - 1) {{
                      popupHtml += "<hr style='margin: 10px 0;'>";
                  }}
              }});

              let firstGame = loc.games[0];
              let team = homeMode ? firstGame.HomeTeam : firstGame.AwayTeam;
              let fallbackStyle = leagueStyles[firstGame.League] || {{color: "gray", icon: "info-sign", prefix: "glyphicon"}};
              let style = teamStyles[team] || fallbackStyle;
              
              let markerColor = style.color;
              if (!['red', 'darkred', 'orange', 'green', 'darkgreen', 'blue', 'purple', 'darkpurple', 'cadetblue', 'star', 'lightred', 'beige', 'darkblue', 'darkgray', 'lightgreen', 'lightgray', 'pink', 'white', 'black'].includes(markerColor)) {{
                  markerColor = 'blue';
              }}
              
              let icon = L.AwesomeMarkers.icon({{
                  icon: style.icon,
                  prefix: style.prefix,
                  markerColor: markerColor
              }});

              let marker = L.marker([loc.lat, loc.lon], {{icon: icon}});
              marker.bindPopup(popupHtml, {{maxWidth: 350}});
              markersLayer.addLayer(marker);
              bounds.push([loc.lat, loc.lon]);
          }}

          if (bounds.length > 0) {{
              map.fitBounds(bounds, {{padding: [50, 50]}});
          }}
      }}

      document.addEventListener('DOMContentLoaded', function() {{
          map = L.map('map').setView([39.8283, -98.5795], 4);
          L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
              attribution: '&copy; OpenStreetMap contributors'
          }}).addTo(map);

          markersLayer = L.featureGroup().addTo(map);

          const filterEl = document.getElementById('team-filter');
          const choices = new Choices(filterEl, {{
              removeItemButton: true,
              placeholderValue: 'Filter by teams...',
              searchPlaceholderValue: 'Search teams'
          }});
          
          filterEl.addEventListener('change', function() {{
              var activeTeams = Array.from(filterEl.selectedOptions).map(opt => opt.value);
              renderMap(activeTeams);
          }});
          
          var initialTeams = Array.from(filterEl.selectedOptions).map(opt => opt.value);
          renderMap(initialTeams);
      }});
    """

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css"/>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js"></script>
    <script>{global_js}</script>
    <style>
      body {{ background-color: #f8f9fa; padding: 40px 15px; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; }}
      #map-container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
      #map {{ width: 100%; height: 600px; border-radius: 6px; z-index: 1; }}
    </style>
</head>
<body>
    <div style="max-width: 1000px; margin: 0 auto; padding-top: 20px;">
        <a href="../index.html" class="btn btn-outline-secondary">&larr; Back to Menu</a>
    </div>
    <h2 class="text-center mb-4">{'Home' if home_mode else 'Away'} Schedule Map</h2>
    {dropdown_html}
    <div id="map-container">
        <div id='map'></div>
    </div>
</body>
</html>
"""
    with open(output_file, 'w') as f:
        f.write(html_content)
    print(f"Map successfully generated and saved to {output_file}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate map visualization.")
    parser.add_argument('--home', action='store_true',
                        help="Use home games data.")
    args = parser.parse_args()

    create_map(home_mode=args.home)
