import requests

SERVER_LIST_URL = "https://export.iperf3serverlist.net/listed_iperf3_servers.csv"
SERVER_LIST_FILE = "listed_iperf3_servers.csv"

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

