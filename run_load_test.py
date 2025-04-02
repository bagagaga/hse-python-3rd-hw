import os
import subprocess
import time
import pandas as pd
from datetime import datetime


def run_locust_test(users=100, spawn_rate=10, runtime='1m', host='http://localhost:9999'):
    os.makedirs('load_test_results', exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stats_file = f'load_test_results/stats_{timestamp}_stats.csv'
    failures_file = f'load_test_results/stats_{timestamp}_failures.csv'

    cmd = [
        'locust',
        '-f', 'locustfile.py',
        '--headless',
        '--users', str(users),
        '--spawn-rate', str(spawn_rate),
        '--run-time', runtime,
        '--host', host,
        '--csv', f'load_test_results/stats_{timestamp}'
    ]

    print(f"Starting load test with {users} users, spawn rate of {spawn_rate}/s, for {runtime}")
    print(f"Command: {' '.join(cmd)}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    while process.poll() is None:
        output = process.stdout.readline()
        if output:
            print(output.strip())

    return stats_file, failures_file


def generate_report(stats_file, failures_file):
    if not os.path.exists(stats_file):
        print(f"Error: Stats CSV file not found at {stats_file}")
        return

    df = pd.read_csv(stats_file)

    print("\n=== Load Test Results ===")
    print(f"Total Requests: {df['Request Count'].sum()}")
    print(f"Total Failures: {df['Failure Count'].sum()}")

    if df['Request Count'].sum() > 0:
        failure_rate = (df['Failure Count'].sum() / df['Request Count'].sum() * 100)
        print(f"Failure Rate: {failure_rate:.2f}%")
    else:
        print("Failure Rate: N/A (no requests)")

    print("\n=== Response Time Statistics (ms) ===")
    for _, row in df.iterrows():
        name = row['Name']
        print(f"\nEndpoint: {name}")
        print(f"  Request Count: {row['Request Count']}")
        print(f"  Failure Count: {row['Failure Count']}")
        print(f"  Min: {row['Min Response Time']:.2f} ms")
        print(f"  Avg: {row['Average Response Time']:.2f} ms")
        print(f"  Max: {row['Max Response Time']:.2f} ms")
        print(f"  P90: {row['90%']:.2f} ms")
        print(f"  P95: {row['95%']:.2f} ms")
        print(f"  P99: {row['99%']:.2f} ms")
        print(f"  Requests/s: {row['Requests/s']:.2f}")

    if os.path.exists(failures_file):
        failures_df = pd.read_csv(failures_file)
        if not failures_df.empty:
            print("\n=== Failures ===")
            for _, row in failures_df.iterrows():
                print(f"Endpoint: {row['Name']}")
                print(f"  Method: {row['Method']}")
                print(f"  Error: {row['Error']}")
                print(f"  Occurrences: {row['Occurrences']}")
                print("")


def process_existing_results(timestamp):
    stats_file = f'load_test_results/stats_{timestamp}_stats.csv'
    failures_file = f'load_test_results/stats_{timestamp}_failures.csv'

    if os.path.exists(stats_file):
        print(f"Processing existing results from {stats_file}")
        generate_report(stats_file, failures_file)
    else:
        print(f"Error: Could not find stats file at {stats_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='URL Shortener Load Test Runner')
    parser.add_argument('--process', type=str, help='Process existing results with timestamp (e.g., 20250402_230712)')
    parser.add_argument('--host', type=str, default='http://localhost:9999', help='Host to test against')
    args = parser.parse_args()

    if args.process:
        process_existing_results(args.process)
        return

    results = []

    print("Running moderate load test...")
    moderate_csv = run_locust_test(users=50, spawn_rate=5, runtime='30s', host=args.host)
    results.append(moderate_csv)

    time.sleep(5)

    print("\nRunning high load test...")
    high_csv = run_locust_test(users=100, spawn_rate=10, runtime='30s', host=args.host)
    results.append(high_csv)

    for stats_file, failures_file in results:
        print(f"\nGenerating report for {stats_file}...")
        generate_report(stats_file, failures_file)


if __name__ == "__main__":
    import sys

    with open("output.txt", "w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        try:
            main()
        finally:
            sys.stdout = original_stdout
