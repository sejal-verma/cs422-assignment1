import requests
import csv
import random
import socket
import subprocess
import platform
import re
import math
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

SERVER_LIST_URL = "https://export.iperf3serverlist.net/listed_iperf3_servers.csv"
SERVER_LIST_FILE = "listed_iperf3_servers.csv"
PING_RESULTS_FILE = "question1.csv"
TRACEROUTE_RESULTS_FILE = "traceroute_results.csv"
MAX_NUMBER_OF_IPS = 5  # how many destinations Part 2 needs successful traceroutes for
PING_COUNT = "10"      # number of ping probes sent per host in Part 1

COUNT_FLAG = "-n" if platform.system().lower() == "windows" else "-c"
# macOS/Linux ping print "round-trip min/avg/max/...", Windows differs -- this
# pattern assumes macOS/Linux wording, matching the dev/grading environment
PING_PATTERNS = [
    r"PING.*?\(([\d\.]+)\).*?\n.*?rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)",       # Linux
    r"PING.*?\(([\d\.]+)\):.*?\n.*?round-trip min/avg/max/stddev = ([\d\.]+)/([\d\.]+)/([\d\.]+)",  # macOS
]

def fetch_latest_server_list():
    """Download the current iperf3 server list CSV from the public source."""
    print("Downloading IP address list...")
    try:
        response = requests.get(SERVER_LIST_URL)
        response.raise_for_status()  # throws error if request fails
        with open(SERVER_LIST_FILE, "wb") as file:
            file.write(response.content)
        print("Download complete!")
        return True
    except requests.RequestException as e:
        print(f"Error: failed to download server list: {e}")
        return False


def load_all_ips(filepath):
    """Read every IP from the server list file, in file order (no shuffling)."""
    with open(filepath) as f:
        lines = f.readlines()[1:]  # skip header row
    return [line.split(",", 1)[0].strip() for line in lines if line.strip()]


def get_my_ip():
    """Look up this machine's public IP address."""
    return requests.get("https://api.ipify.org?format=json").json()["ip"]


def locate(ip):
    """
    Look up (latitude, longitude) for an IP address using the free
    ip2location.io API. Returns None if the lookup fails.
    """
    try:
        r = requests.get(f"https://api.ip2location.io/?ip={ip}").json()
        print(ip, r)
        return float(r["latitude"]), float(r["longitude"])
    except Exception:
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Great-circle distance between two lat/lon points, in kilometers.
    Source: Chris Veness, "Calculate distance, bearing and more between
    Latitude/Longitude points," Movable Type Scripts.
    """
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# === PART 1A - ping every server (concurrently) and record min/avg/max RTT ===

def ping_worker(host):
    """Ping one host PING_COUNT times and parse out min/avg/max RTT. Returns None on failure."""
    # -c sets ping count on macOS/Linux, -n sets it on Windows
    result = subprocess.run(["ping", COUNT_FLAG, PING_COUNT, host], capture_output=True, text=True)
    if result.returncode != 0:
        return None  # host unreachable -- skip per assignment instructions

    for pattern in PING_PATTERNS:
        match = re.search(pattern, result.stdout, re.DOTALL)
        if match:
            ip, min_rtt, avg_rtt, max_rtt = match.groups()
            return [ip, min_rtt, avg_rtt, max_rtt]
    return None


def run_ping_tests(hosts):
    """Ping all hosts concurrently and write successful results to PING_RESULTS_FILE."""
    # multithreaded so all ~190 hosts ping in parallel instead of one at a
    # time -- cuts runtime down significantly since ping is mostly just waiting
    with ThreadPoolExecutor(max_workers=20) as executor:
        ping_results = list(executor.map(ping_worker, hosts))

    with open(PING_RESULTS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ip_address", "min_rtt", "avg_rtt", "max_rtt"])
        for res in ping_results:
            if res:
                writer.writerow(res)


# === PART 1B - geolocate each responding IP (concurrently) and compute distance from us ===

def locate_worker(row, my_ip, my_lat, my_lon):
    """Add a `distance` field (km from us) to one ping-result row. `distance` is None on lookup failure."""
    ip = row["ip_address"]
    if ip == my_ip:
        row["distance"] = 0
        return row

    location = locate(ip)
    if location is None:
        row["distance"] = None
        return row

    lat, lon = location
    row["distance"] = round(haversine_km(my_lat, my_lon, lat, lon), 2)
    return row


def add_distances(my_ip, my_lat, my_lon):
    """Geolocate every row in PING_RESULTS_FILE and add a distance column, dropping failed lookups."""
    results = list(csv.DictReader(open(PING_RESULTS_FILE)))

    # geolocation lookups are also run concurrently (up to 10 at once) for the same reason as the pings
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda row: locate_worker(row, my_ip, my_lat, my_lon), results))

    results = [r for r in results if r.get("distance") is not None]  # drop failed geolocations

    with open(PING_RESULTS_FILE, "w", newline="") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)


# === PART 1C - scatter plot: distance vs average RTT ===

def plot_distance_vs_rtt(df):
    """Scatter plot visualizing the relationship between distance and average RTT."""
    print("Building distance vs RTT scatter plot...")
    plt.figure()
    plt.scatter(df["distance"], df["avg_rtt"])
    plt.title("Distance vs Average RTT")
    plt.xlabel("Distance (km)")
    plt.ylabel("Average RTT (ms)")
    plt.tight_layout()
    plt.savefig("distance_vs_average_rtt.pdf")
    plt.close()


def run_part_one():
    """Ping every server in the list, geolocate responders, and plot distance vs RTT."""
    my_ip = get_my_ip()
    #my_lat, my_lon = locate(my_ip)
    print("My IP:", my_ip)
    #print("My location:", my_lat, my_lon)

    hosts = load_all_ips(SERVER_LIST_FILE) + [my_ip]  # include ourselves as one of the pinged destinations

    run_ping_tests(hosts)
    #add_distances(my_ip, my_lat, my_lon)

    #df = pd.read_csv(PING_RESULTS_FILE)
    #plot_distance_vs_rtt(df)


# === PART 2A - collect traceroute data for random IPs ===

def load_candidate_ips(filepath):
    """Read all IPs from the server list file and return them in random order."""
    ips = load_all_ips(filepath)
    random.shuffle(ips)  # shuffle once; we consume from this list as we go
    return ips


def traceroute_ip(ip):
    """
    Run traceroute against a single IP and return a list of
    (hop_number, avg_rtt_ms) tuples for hops that responded.
    Returns None if the destination never responded.
    """
    try:
        result = subprocess.run(
            ["traceroute", "-n", "-w", "2", "-m", "20", ip],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        print(f"traceroute failed for {ip}")
        return None

    responding_hops = []
    last_ip_seen = None  # tracks the IP printed on the most recent responding hop line
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue  # skip empty lines / header line
        hop_number = int(parts[0])
        rtts = re.findall(r"(\d+(?:\.\d+)?)\s*ms", line)
        if not rtts:
            continue  # skip unresponsive hops (e.g. "* * *")
        avg_rtt = round(sum(float(r) for r in rtts) / len(rtts), 3)
        responding_hops.append((hop_number, avg_rtt))

        # grab the IP token straight from this line instead of trying to
        # re-locate it later by line index (unreliable: some hops span
        # multiple output lines, e.g. when probes hit different routers)
        ip_match = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", line)
        if ip_match:
            last_ip_seen = ip_match.group()

        print(ip, hop_number, rtts)

    if not responding_hops:
        return None

    # -n prints raw IPs only (no hostnames), so we must compare against the
    # resolved IP of `ip`, not the hostname string itself
    try:
        resolved_ip = socket.gethostbyname(ip)
    except socket.gaierror:
        print(f"{ip}: could not resolve hostname")
        return None

    if last_ip_seen != resolved_ip:
        print(f"{ip}: destination did not respond")
        return None

    return responding_hops


def collect_traceroute_data():
    """
    Traceroute randomly chosen IPs until MAX_NUMBER_OF_IPS have produced a
    successful (destination-reachable) result. Writes results to
    TRACEROUTE_RESULTS_FILE as they're collected.
    """
    candidate_ips = load_candidate_ips(SERVER_LIST_FILE)

    with open(TRACEROUTE_RESULTS_FILE, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["IP", "HOP", "RTT"])

        successful_servers = 0
        while successful_servers < MAX_NUMBER_OF_IPS:
            if not candidate_ips:
                print("No more distinct ips left to test")
                exit(1)

            ip = candidate_ips.pop()  # already shuffled, so pop() = random pick w/o repeats
            print(f"Trying {ip}...", flush=True)
            hops = traceroute_ip(ip)
            if hops is None:
                continue

            print(f"writing results to csv for {ip}")
            for hop_number, avg_rtt in hops:
                writer.writerow([ip, hop_number, f"{avg_rtt:.3f}"])
            successful_servers += 1


# === PART 2B - stacked bar chart (latency breakdown per hop) ===

def plot_stacked_bar(df):
    """
    Build and save a stacked bar chart showing the latency breakdown per
    hop for each destination IP. traceroute RTTs are cumulative, so we
    use .diff() per IP to get each hop's individual (incremental)
    contribution before plotting.
    """
    print("Building stacked bar chart...")
    df = df.sort_values(["IP", "HOP"]).copy()
    # incremental latency = RTT minus the previous hop's RTT for that IP;
    # the first hop per IP has no previous value, so treat it as the baseline
    df["increment"] = df.groupby("IP")["RTT"].diff()
    df["increment"] = df["increment"].fillna(df["RTT"]).clip(lower=0)

    # reshape so each row is a hop position (1st, 2nd, ...) and each
    # column is a destination IP -- this is what a stacked bar needs
    df["hop_position"] = df.groupby("IP").cumcount()
    pivot = df.pivot(index="hop_position", columns="IP", values="increment")

    ax = pivot.T.plot(kind="bar", stacked=True, figsize=(10, 6), colormap="tab20", legend=False)
    ax.set_ylabel("Round-Trip Time (ms)")
    ax.set_xlabel("Destination IP")
    ax.set_title("Latency Breakdown by Hop for Each Destination")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig("latency_breakdown.pdf")
    plt.close()


# === PART 2C - scatter plot (hop count vs RTT) ===

def plot_scatter(df):
    """Scatter plot of hop count vs RTT, one point per destination IP."""
    print("Building hop count vs RTT scatter plot...")

    # Sort locally (doesn't affect the caller's df) so "last RTT per IP"
    # reliably means "RTT at the deepest hop", regardless of row order
    # the CSV happened to be in when it was read.
    sorted_df = df.sort_values(["IP", "HOP"])

    # group by IP first, then reduce each group down to a single
    # (hop_count, final_rtt) summary point before any plotting happens
    summary = sorted_df.groupby("IP").agg(
        hop_count=("HOP", "max"),
        final_rtt=("RTT", "last")  # RTT at the final (deepest) responding hop
    ).reset_index()

    plt.figure(figsize=(10, 6))
    for _, row in summary.iterrows():
        plt.scatter(row["hop_count"], row["final_rtt"], label=row["IP"], alpha=0.8, s=60)

    plt.title("Hop Count vs. Round-Trip Time (RTT)")
    plt.xlabel("Hop Count")
    plt.ylabel("RTT (ms)")
    plt.legend(title="Destination IP", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("hopcount_vs_rtt.pdf")
    plt.close()


def run_part_two():
    """Traceroute 5 random servers and plot the latency-breakdown and hop-count charts."""
    collect_traceroute_data()
    df = pd.read_csv(TRACEROUTE_RESULTS_FILE)
    plot_stacked_bar(df)
    plot_scatter(df)


def main():
    if not fetch_latest_server_list():
        exit(1)
    run_part_one()
    run_part_two()


if __name__ == "__main__":
    main()