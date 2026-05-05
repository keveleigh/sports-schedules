import argparse
import json
from collections import defaultdict
from pathlib import Path

import dateutil.parser
import folium
from branca.element import MacroElement, Template


with open('config.json', 'r') as f:
    config = json.load(f)


def create_map(home_mode=False):
    input_dir = Path('output')
    input_file = input_dir / \
        ('final_schedules_home.json' if home_mode else 'final_schedules_away.json')

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

    # Create a base map centered roughly on the US
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)

    # Define custom styles for each team
    team_styles = config.get("team_styles", {})
    league_styles = config.get("league_styles", {})

    # Create a FeatureGroup for each league to allow toggling
    league_groups = {league: folium.FeatureGroup(
        name=league, show=True) for league in league_styles.keys()}
    for group in league_groups.values():
        group.add_to(m)

    # Group games by their exact coordinates
    grouped_games = defaultdict(list)
    for game in games:
        grouped_games[(game['Lat'], game['Lon'])].append(game)

    for (lat, lon), location_games in grouped_games.items():
        popup_html = ""

        for i, game in enumerate(location_games):
            # Get the pre-calculated local date string
            date_str = game.get('DateLocal')
            if not date_str:
                date_str = dateutil.parser.parse(
                    game['DateUtc']).strftime("%B %d, %Y at %I:%M %p UTC")

            # Build the HTML popup content
            popup_html += f"<b>{game['AwayTeam']} @ {game['HomeTeam']}</b><br>"
            popup_html += f"<i>{game['League']} - {game['Location']}</i><br>"
            popup_html += f"{date_str}"

            if game.get('NearbyGames'):
                popup_html += "<br><b>Nearby Games:</b><ul>"
                for nearby in game['NearbyGames']:
                    nearby_date = nearby.get('DateLocal', 'Unknown Time')
                    display_team = nearby.get(
                        'TargetTeam', nearby.get('AwayTeam'))
                    popup_html += f"<li>{display_team} ({nearby['DistanceMiles']} mi) - {nearby_date}</li>"
                popup_html += "</ul>"

            # Add a separator line between multiple games at the same location
            if i < len(location_games) - 1:
                popup_html += "<hr>"

        # Add a single marker for this location to the map
        team = location_games[0].get('AwayTeam')
        if team not in team_styles and location_games[0].get('HomeTeam') in team_styles:
            team = location_games[0].get('HomeTeam')
        league = location_games[0].get('League', 'Unknown')

        fallback_style = league_styles.get(
            league, {"color": "gray", "icon": "info-sign", "prefix": "glyphicon"})
        style = team_styles.get(team, fallback_style)

        marker = folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(
                color=style["color"],
                icon=style["icon"],
                prefix=style["prefix"]
            )
        ).add_to(m)

        # Assign the marker to the league's toggle group
        target_group = league_groups.get(league)
        if target_group is not None:
            marker.add_to(target_group)
        else:
            marker.add_to(m)

    # Automatically adjust map zoom and center to fit all markers
    if grouped_games:
        lats, lons = zip(*grouped_games.keys())
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    folium.LayerControl(collapsed=False).add_to(m)

    legend_items = ""
    for team, style in team_styles.items():
        legend_items += f'<span style="color: {style["color"]};">&#9608;</span> {team}<br>\n        '
    legend_items += "<hr style='margin: 5px 0;'>"
    for league, style in league_styles.items():
        legend_items += f'<span style="color: {style["color"]};">&#9608;</span> {league} (Other)<br>\n        '

    # Add a custom legend
    legend_html = f'''
    {{% macro html(this, kwargs) %}}
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        width: auto; 
        height: auto; 
        background-color: white; 
        border: 2px solid grey; 
        z-index: 9999; 
        font-size: 14px;
        padding: 10px;
        ">
        <b>Team Legend</b><br>
        {legend_items.strip()}
    </div>
    {{% endmacro %}}
    '''
    legend = MacroElement()
    legend._template = Template(legend_html)
    m.get_root().add_child(legend)

    # Add a custom back button
    back_button_html = '''
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; 
        top: 20px; 
        left: 60px; 
        z-index: 9999;
        ">
        <a href="../index.html" style="
            background-color: white;
            color: black;
            padding: 8px 15px;
            border: 2px solid grey;
            border-radius: 5px;
            text-decoration: none;
            font-size: 14px;
            font-weight: bold;
            ">&larr; Back to Menu</a>
    </div>
    {% endmacro %}
    '''
    back_button = MacroElement()
    back_button._template = Template(back_button_html)
    m.get_root().add_child(back_button)

    m.save(output_file)
    print(f"Map successfully generated and saved to {output_file}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate map visualization.")
    parser.add_argument('--home', action='store_true',
                        help="Use home games data.")
    args = parser.parse_args()

    create_map(home_mode=args.home)
