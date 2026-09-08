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
# todo: add in comments before each section explaining work for question 1

my_ip = requests.get("https://api.ipify.org?format=json").json()["ip"]


def locate(ip):
    r = requests.get(f"https://api.ip2location.io/?ip={ip}").json()
    print(ip, r)
    return float(r["latitude"]), float(r["longitude"])


my_lat, my_lon = locate(my_ip)
print("My IP:", my_ip)
print("My location:", my_lat, my_lon)

with open(filename, 'r') as csvfile:
    csvreader = csv.reader(csvfile)  # Reader object

    cols = next(csvreader)  # Read header
    for row in csvreader:  # Read rows
        rows.append(row)

    #print("Total no. of rows: %d" % csvreader.line_num)  # Row count

test = "question1.csv"
pattern = r"PING.*?\(([\d\.]+)\):.*?\n.*?round-trip min/avg/max/stddev = ([\d\.]+)/([\d\.]+)/([\d\.]+)"  # print('\nFirst 5 rows are:\n')


def ping_worker(row):
    if isinstance(row, str):
        host = row.strip()
    else:
        host = row[0].strip()

    result = subprocess.run(["/sbin/ping", count_flag, "10", host], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    match = re.search(pattern, result.stdout, re.DOTALL)
    if match:
        ip, min_rtt, avg_rtt, max_rtt = match.groups()
        return [ip, min_rtt, avg_rtt, max_rtt]
    return None


with ThreadPoolExecutor(max_workers=20) as executor:
    ping_results = list(executor.map(ping_worker, rows))

with open(test, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ip_address", "min_rtt", "avg_rtt", "max_rtt"])
    for res in ping_results:
        if res:
            writer.writerow(res)
            #print("row printed")

results = list(csv.DictReader(open(test)))


def locate_worker(row):
    ip = row["ip_address"]

    if ip == my_ip:
        row["distance"] = 0
        return row

    try:
        lat, lon = locate(ip)
        # haversine distance in km
        # way to calculate distance given only the latitude and the longitude.
        R = 6371
        dlat = math.radians(lat - my_lat)
        dlon = math.radians(lon - my_lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(my_lat)) * math.cos(math.radians(lat)) * math.sin(
            dlon / 2) ** 2
        dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        # print("Server location:", lat, lon, "distance: ", dist)
        row["distance"] = round(dist, 2)
    except Exception:
        row["distance"] = None
    return row


with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(locate_worker, results))

results = [r for r in results if r.get("distance") is not None]

with open(test, "w", newline="") as f:
    if results:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

df = pd.read_csv("question1.csv")

x = df["distance"]
y = df["avg_rtt"]

plt.scatter(x, y)
plt.title("Distance vs Average RTT")
plt.xlabel("Distance (km)")
plt.ylabel("Average RTT (ms)")
plt.savefig("distance_vs_average_rtt.png")
# save png