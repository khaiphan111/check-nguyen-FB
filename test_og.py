import requests
import re

def main():
    r = requests.get('https://www.facebook.com/hiennguyen19.12.06', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    match = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
    if match:
        print(match.group(1).replace('&amp;', '&'))
    else:
        print("None")

if __name__ == "__main__":
    main()
