import argparse
import importlib

import generate_calendar
import generate_map
import schedules
import update_mlb_logos
import update_mls_logos
import update_nwsl_logos


def main():
    parser = argparse.ArgumentParser(
        description="Run the full sports schedules pipeline.")
    parser.add_argument('--update', action='store_true',
                        help="Fetch latest schedules from URLs and update local JSON files.")
    args = parser.parse_args()

    if args.update:
        print("--- Updating Logos ---")
        update_mlb_logos.scrape_and_update_mlb_logos()
        update_mls_logos.scrape_and_update_mls_logos()
        update_nwsl_logos.scrape_and_update_nwsl_logos()

        # Reload modules so they use the newly updated config.json
        importlib.reload(schedules)
        importlib.reload(generate_map)
        importlib.reload(generate_calendar)

        print("--- Updating Schedules ---")
        schedules.update_local_jsons()

    print("\n--- Parsing Schedules ---")
    schedules.parse_and_combine_schedules()

    print("\n--- Generating Away Dashboards ---")
    generate_map.create_map(home_mode=False)
    generate_calendar.create_calendar(home_mode=False)

    print("\n--- Generating Home Dashboards ---")
    generate_map.create_map(home_mode=True)
    generate_calendar.create_calendar(home_mode=True)

    print("\n--- Pipeline Complete! ---")


if __name__ == '__main__':
    main()
