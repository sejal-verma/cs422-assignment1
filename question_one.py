import csv
import subprocess
import platform
import re
import math
import requests
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
filename = "listed_iperf3_servers.csv"  # File name
cols = []  # Column names
rows = []    # Data rows
count_flag = "-n" if platform.system().lower() == "windows" else "-c"

my_ip = requests.get("https://api.ipify.org?format=json").json()["ip"]
rows.append(my_ip)

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
    for row in csvreader:     # Read rows
        rows.append(row)

    print("Total no. of rows: %d" % csvreader.line_num)  # Row count

test = "test.csv"
pattern = r"PING.*?\(([\d\.]+)\):.*?\n.*?round-trip min/avg/max/stddev = ([\d\.]+)/([\d\.]+)/([\d\.]+)"#print('\nFirst 5 rows are:\n')
with open(test, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ip_address", "min_rtt", "avg_rtt", "max_rtt"])
for row in rows[:]:
    host = row[0].strip()
    result = subprocess.run(["/sbin/ping", count_flag, "1", host], capture_output=True, text=True)
    if result.returncode != 0:
        continue

    match = re.search(pattern, result.stdout, re.DOTALL)
    if match:
        ip, min_rtt, avg_rtt, max_rtt = match.groups()

        # 4. Append row to output CSV
        with open(test, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ip, min_rtt, avg_rtt, max_rtt])
            print("row printed")



results = list(csv.DictReader(open(test)))

for row in results:
    ip = row["ip_address"]

    if ip == my_ip:
        row["distance"] = 0
        continue

    lat, lon = locate(ip)


    # haversine distance in km
    R = 6371
    dlat = math.radians(lat - my_lat)
    dlon = math.radians(lon - my_lon)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(my_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    #print("Server location:", lat, lon, "distance: ", dist)
    row["distance"] = round(dist, 2)

with open(test, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

df = pd.read_csv("test.csv")

x = df["distance"]
y = df["avg_rtt"]

plt.scatter(x, y)
plt.title("Distance vs Average RTT")
plt.xlabel("Distance (km)")
plt.ylabel("Average RTT (ms)")

plt.show()