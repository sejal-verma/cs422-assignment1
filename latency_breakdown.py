import requests
import csv
import random
import linecache
import subprocess
import re

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

  except:
    print(f"Error: failed to download server list: {requests.RequestException}")
    return False

fetch_latest_server_list()
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
    traceroute_result = subprocess.run(["traceroute", ip], capture_output=True, text=True)
    responding_hops = []
    for traceroute_line in traceroute_result.stdout.splitlines():
      hop_number_part = traceroute_line.split()[0]
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
      print("writing results to csv for {ip}")
      for hop_number, avg_rtt, _ in responding_hops:
        writer.writerow([ip, hop_number, f"{avg_rtt:.3f}"])
    successful_servers += 1
