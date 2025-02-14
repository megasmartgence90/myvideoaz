import re
import requests
import sys
import json
import os
from urllib.parse import urljoin
from slugify import slugify
from tqdm import tqdm

def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers)
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers)
        else:
            print(f"{method} is not supported or wrong.")
            return None

        results = re.findall(pattern, r.text)
        if results:
            return results[0]
        else:
            print(f"No result found in the response. Check your regex pattern {pattern} for {url}")
            return None
    except Exception as e:
        print(f"Error fetching stream URL: {e}")
        return None

def playlist_text(url):
    try:
        text = ""
        r = requests.get(url)
        if r.status_code == 200:
            for line in r.iter_lines():
                line = line.decode("utf-8")
                if not line:
                    continue
                if line[0] != "#":
                    text += urljoin(url, line) + "\n"
                else:
                    text += line + "\n"
            return text
        else:
            print(f"Failed to fetch playlist: HTTP {r.status_code}")
            return ""
    except Exception as e:
        print(f"Error fetching playlist text: {e}")
        return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <config_file>")
        return

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return

    for site in config:
        site_path = os.path.join(os.getcwd(), site["slug"])
        os.makedirs(site_path, exist_ok=True)

        for channel in tqdm(site["channels"], desc=f"Processing {site['slug']}"):
            channel_file_path = os.path.join(site_path, slugify(channel["name"].lower()) + ".m3u8")
            channel_url = site["url"]

            for variable in channel.get("variables", []):
                channel_url = channel_url.replace(variable["name"], variable["value"])

            stream_url = get_stream_url(channel_url, site["pattern"])
            if not stream_url:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)
                continue

            if site.get("output_filter") and site["output_filter"] not in stream_url:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)
                continue

            if site["mode"] == "variant":
                text = playlist_text(stream_url)
            elif site["mode"] == "master":
                text = f"#EXTM3U\n##EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH={site.get('bandwidth', 0)}\n{stream_url}"
            else:
                print("Wrong or missing playlist mode argument")
                text = ""

            if text:
                with open(channel_file_path, "w+", encoding="utf-8") as channel_file:
                    channel_file.write(text)
            else:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)

if __name__ == "__main__":
    main()
