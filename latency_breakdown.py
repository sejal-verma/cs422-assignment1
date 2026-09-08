import requests
import csv
import random
import linecache
import subprocess
import re
<<<<<<< HEAD
import pandas as pd
import matplotlib.pyplot as plt

# === PART A - collection and cleaning of network diagnostic data ===
=======
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
>>>>>>> rohini/question-2-part-b-stacked-bar-chart

SERVER_LIST_URL = "https://export.iperf3serverlist.net/listed_iperf3_servers.csv"
SERVER_LIST_FILE = "listed_iperf3_servers.csv"
MAX_NUMBER_OF_IPS = 5

def fetch_latest_server_list():
  print("Downloading IP address list...")
  try:
    response = requests.get(SERVER_LIST_URL)
    response.raise_for_status() # throws error if request fails
    with open(SERVER_LIST_FILE, "wb") as file:
      file.write(response.content)
    print("Download complete!")
    return True

  except requests.RequestException as e:
    print(f"Error: failed to download server list: {e}")
    return False

if not fetch_latest_server_list(): # fetching latest server list data
  exit()
with open(SERVER_LIST_FILE) as file:
  num_lines = sum(1 for line in file)

with open("traceroute_results.csv", "w", newline="") as csv_file:
  writer = csv.writer(csv_file)
  writer.writerow(["IP", "HOP", "RTT"])

  successful_servers = 0
  attempted_servers = set()
  # select 5 random line numbers and thus ip addresses by extension
  while successful_servers < MAX_NUMBER_OF_IPS:
    if num_lines - 1 < MAX_NUMBER_OF_IPS or len(attempted_servers) >= num_lines - 1:
      print("No more distinct ips left to test")
      exit(1)
    line_number = random.randrange(2, num_lines + 1)
    if line_number in attempted_servers:
      continue # prevent retrying the same server
    attempted_servers.add(line_number)
    line = linecache.getline(SERVER_LIST_FILE, line_number).strip()
    ip = line.split(',', 1)[0]
    try:
      traceroute_result = subprocess.run(["traceroute", ip], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
      print(f"traceroute failed for {ip}")
      continue
    responding_hops = []
    for traceroute_line in traceroute_result.stdout.splitlines():
      parts = traceroute_line.split()
      if not parts:
        continue # skips empty line
      hop_number_part = parts[0]
      if not hop_number_part.isdigit():
        continue
      hop_number = int(hop_number_part)
      rtts = re.findall(r"(\d+(?:\.\d+)?)\s*ms", traceroute_line) # find all instances of xx.xx ms to get rtt values
      if len(rtts) == 0:
        continue # skip unresponsive hops
      avg_rtt = round(sum(float(rtt) for rtt in rtts) / len(rtts), 3) # round the avg rtt to 3 decimal places
      responding_hops.append((hop_number, avg_rtt, traceroute_line))
      print(ip, hop_number, rtts)
    if not responding_hops:
      continue # traceroute yielded no responses
    last_hop = responding_hops[-1]
    if ip not in last_hop[2]:
      print(f"{ip}: destination did not respond")
      continue # if destination does not respond, consider it to be an unresponsive hop and try another ip
      # write the ip,hops,rtt to csv
    print(f"writing results to csv for {ip}")
    for hop_number, avg_rtt, _ in responding_hops:
      writer.writerow([ip, hop_number, f"{avg_rtt:.3f}"])
<<<<<<< HEAD
    successful_servers += 1

# === PART B - stacked bar chart ===


# === PART C - scatter plot ===

# Load the data from the CSV file
df = pd.read_csv('traceroute_results.csv')

# Initialize the plot with a specific size
plt.figure(figsize=(10, 6))

# Group the data by Destination IP and plot each group as a separate scatter series
for ip, group in df.groupby('IP'):
    plt.scatter(group['HOP'], group['RTT'], label=ip, alpha=0.8, s=60)

# Add titles and labels
plt.title('Hop Count vs. Round-Trip Time (RTT)')
plt.xlabel('Hop Count')
plt.ylabel('RTT (ms)')

# Place the legend outside the plot area
plt.legend(title='Destination IP', bbox_to_anchor=(1.05, 1), loc='upper left')

# Add a grid for easier reading
plt.grid(True, linestyle='--', alpha=0.6)

# Adjust layout to ensure the legend isn't cut off
plt.tight_layout()

# Display the plot
plt.show()
=======

### QUESTION 2 - PART B ###

RESULTS_FILE = "traceroute_results.csv"

def load_data(filepath):
    """
    Load traceroute results from a CSV file into a dictionary grouped by
    destination IP.

    Args:
        filepath (str): Path to the traceroute_results.csv file. Expected
            columns are IP, HOP, RTT.

    Returns:
        dict[str, list[tuple[int, float]]]: A mapping from destination IP
            (or hostname) to a list of (hop_number, cumulative_rtt_ms)
            tuples, in the order they appear in the file.
    """
    print("Loading data for part 2b...")
    data = defaultdict(list)  # ip -> list of (hop, rtt), in file order
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)  # reads header row automatically, gives us dict rows
        for row in reader:
            # Cast HOP to int and RTT to float since csv reads everything as strings
            data[row["IP"]].append((int(row["HOP"]), float(row["RTT"])))
    return data


def compute_incremental_latencies(hops):
    """
    Convert a list of cumulative RTT values into per-hop incremental
    latencies.

    traceroute reports RTT as the round-trip time from the source machine
    to that specific hop, meaning each value already includes the delay
    of every hop before it. To find out how much latency each individual
    hop actually contributes, we need to subtract the previous hop's
    cumulative RTT from the current one.

    Args:
        hops (list[tuple[int, float]]): List of (hop_number, cumulative_rtt_ms)
            tuples for a single destination IP, not necessarily sorted and
            possibly missing some hop numbers (non-responsive hops filtered
            out during collection).

    Returns:
        list[tuple[int, float]]: List of (hop_number, incremental_latency_ms)
            tuples sorted by hop number, where incremental_latency_ms is the
            latency added since the previous responsive hop.
    """
    print("Computing data for part 2b...")
    # Sort by hop number first in case rows aren't already in order
    hops = sorted(hops, key=lambda h: h[0])
    increments = []
    prev_rtt = 0.0  # essentially acts as the "latency so far" - starts at 0
    for hop_number, rtt in hops:
        # Incremental latency = how much RTT increased since the last hop
        delta = max(rtt - prev_rtt, 0)  # clamp negatives just in case of jitter/measurement noise
        increments.append((hop_number, delta))
        prev_rtt = rtt  # update baseline for the next iteration
    return increments

def plot_stacked_bar(data):
    """
    Build and save a stacked bar chart showing the latency breakdown per
    hop for each destination IP.

    Each bar corresponds to one destination IP. Each colored segment
    within a bar represents the incremental latency contributed by one
    hop along the path. The total height of a bar equals the RTT to the
    final (last responsive) hop for that destination.

    Args:
        data (dict[str, list[tuple[int, float]]]): Output of load_data(),
            mapping each destination IP to its list of (hop, cumulative_rtt)
            tuples.

    Returns:
        Nonthing returned, it just saves the chart to 'latency_breakdown.png'.
    """
    print("Starting plotting process for part 2b...")
    ips = list(data.keys())  # x-axis categories: one per destination IP

    # Convert every IP's cumulative RTTs into per-hop incremental latencies
    per_ip_increments = {ip: compute_incremental_latencies(data[ip]) for ip in ips}

    # Different IPs may have different numbers of responsive hops, so we
    # need to know the tallest stack (most hop-segments) to loop over
    max_segments = max(len(v) for v in per_ip_increments.values())

    fig, ax = plt.subplots(figsize=(10, 6))
    bottoms = [0] * len(ips)  # tracks the running height of each bar as we stack segments
    cmap = plt.colormaps["tab20"]
    colors = [cmap(i % cmap.N) for i in range(max_segments)]

    # Build the stacked bar one "layer" (segment index) at a time, across all IPs.
    # segment_index 0 = hop 1 for each IP (roughly), segment_index 1 = hop 2, etc.
    for segment_index in range(max_segments):
        segment_values = []

        for ip in ips:
            increments = per_ip_increments[ip]
            if segment_index < len(increments):
                # This IP has a hop at this segment index; use its latency value
                segment_values.append(increments[segment_index][1])
            else:
                # This IP's path was shorter (fewer hops); pad with 0 so bars align
                segment_values.append(0)

        # Draw this layer across all bars at once, stacked on top of previous layers
        ax.bar(
            ips,
            segment_values,
            bottom=bottoms,  # start each bar's segment where the previous one ended
            color=cmap(segment_index / max(max_segments - 1, 1)),  # vary color by hop depth
            edgecolor="white",
            linewidth=0.3,
        )

        # Update running totals so the next layer stacks on top correctly
        bottoms = [b + v for b, v in zip(bottoms, segment_values)]

    ax.set_ylabel("Round-Trip Time (ms)")
    ax.set_xlabel("Destination IP")
    ax.set_title("Latency Breakdown by Hop for Each Destination")
    plt.xticks(rotation=30, ha="right")  # angle labels so long hostnames don't overlap
    plt.tight_layout()
    plt.savefig("latency_breakdown.png", dpi=150)  # save chart as an image file
    plt.show()  # display the chart in a window (if running in a GUI-capable environment)


if __name__ == "__main__":
    # Entry point: load the traceroute data, then generate and save the chart
    data = load_data(RESULTS_FILE)
    plot_stacked_bar(data)
>>>>>>> rohini/question-2-part-b-stacked-bar-chart
