import csv
import subprocess
import platform
import re
import math
import requests
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

filename = "listed_iperf3_servers.csv"  # File name -- change to updated dynamic csv reading in
cols = []  # Column names
rows = []  # Data rows
count_flag = "-n" if platform.system().lower() == "windows" else "-c"

my_ip = requests.get("https://api.ipify.org?format=json").json()["ip"]

# Locate() finds the geolocation coordinates from publicly available data
# off of api.ip2location.io given the 190-something IP addresses
def locate(ip):
    try:
        r = requests.get(f"https://api.ip2location.io/?ip={ip}").json()
        print(ip, r)
        return float(r["latitude"]), float(r["longitude"])
    except:
        return None

#locating our own IP address (latitude, longitude)
my_lat, my_lon = locate(my_ip)
print("My IP:", my_ip)
print("My location:", my_lat, my_lon)

#Using csv reader
with open(filename, 'r') as csvfile:
    csvreader = csv.reader(csvfile)  # Reader object

    cols = next(csvreader)  # Read header
    for row in csvreader:  # Read rows
        rows.append(row)

    #print("Total no. of rows: %d" % csvreader.line_num)  # Row count

test = "question1.csv"
# Using regex string to just locate the line that gives you the IP address, min, average, max and std. dev of RTT
pattern = r"PING.*?\(([\d\.]+)\):.*?\n.*?round-trip min/avg/max/stddev = ([\d\.]+)/([\d\.]+)/([\d\.]+)"  # print('\nFirst 5 rows are:\n')

#process that runs ping 10 times per ip address
def ping_worker(row):
    if isinstance(row, str):
        host = row.strip()
    else:
        host = row[0].strip()
    #running ping 10 times per ip address, -c if mac, -n if windows
    result = subprocess.run(["/sbin/ping", count_flag, "10", host], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    match = re.search(pattern, result.stdout, re.DOTALL)
    if match:
        ip, min_rtt, avg_rtt, max_rtt = match.groups()
        return [ip, min_rtt, avg_rtt, max_rtt]
    return None

#appending own IP address so that it goes through the ping_worker process
rows.append([my_ip])

# using multithreading to run the 10 pings per ip address concurrently, cutting down runtime of program significantly
with ThreadPoolExecutor(max_workers=20) as executor: #threadpool has up to 20 processes running at once
    ping_results = list(executor.map(ping_worker, rows))

with open(test, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ip_address", "min_rtt", "avg_rtt", "max_rtt"]) #writing these results to the test.csv
    for res in ping_results:
        if res:
            writer.writerow(res)
            #print("row printed")

results = list(csv.DictReader(open(test)))

#geolocation
def locate_worker(row):
    ip = row["ip_address"]

    if ip == my_ip:
        row["distance"] = 0
        return row

    location = locate(ip)

    if location is None:
        row["distance"] = None
        return row
    lat, lon = location
    # Haversine formula for calculating great-circle distance between two
    # latitude/longitude coordinates.
    # Source: Chris Veness, "Calculate distance, bearing and more between
    # Latitude/Longitude points," Movable Type Scripts.
    R = 6371
    dlat = math.radians(lat - my_lat)
    dlon = math.radians(lon - my_lon)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(my_lat)) * math.cos(math.radians(lat)) * math.sin(
        dlon / 2) ** 2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # print("Server location:", lat, lon, "distance: ", dist)
    row["distance"] = round(dist, 2)
    return row

# run geolocation lookups concurrently for each ping result.
# up to 10 IP addresses are processed at the same time.
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(locate_worker, results))

# Remove rows where the IP geolocation lookup failed
results = [r for r in results if r.get("distance") is not None]

with open(test, "w", newline="") as f:
    if results:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

df = pd.read_csv("question1.csv")

#plotting our results in a scatterplot to visualize the relationship between distance and average RTT
x = df["distance"]
y = df["avg_rtt"]

plt.scatter(x, y)
plt.title("Distance vs Average RTT")
plt.xlabel("Distance (km)")
plt.ylabel("Average RTT (ms)")
plt.savefig("distance_vs_average_rtt.png")
# save png