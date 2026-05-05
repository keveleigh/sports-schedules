import argparse

import generate_calendar
import generate_map
import schedules


def main():
    parser = argparse.ArgumentParser(
        description="Run the full sports schedules pipeline.")
    parser.add_argument('--update', action='store_true',
                        help="Fetch latest schedules from URLs and update local JSON files.")
    args = parser.parse_args()

    if args.update:
        print("--- Updating Schedules ---")
        schedules.update_local_jsons()

    print("\n--- Processing Away Games ---")
    schedules.parse_and_combine_schedules(home_mode=False)
    generate_map.create_map(home_mode=False)
    generate_calendar.create_calendar(home_mode=False)

    print("\n--- Processing Home Games ---")
    schedules.parse_and_combine_schedules(home_mode=True)
    generate_map.create_map(home_mode=True)
    generate_calendar.create_calendar(home_mode=True)

    print("\n--- Pipeline Complete! ---")


if __name__ == '__main__':
    main()
