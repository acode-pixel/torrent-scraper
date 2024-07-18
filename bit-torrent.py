import requests, bencodepy, argparse, socket, csv, time, xlsxwriter
from urllib.parse import urlparse

class torrentFile:
    def __init__(self, name, downloaded, complete, incomplete, info_hash) -> None:
        self.name = name
        self.downloaded = downloaded
        self.complete = complete
        self.incomplete = incomplete
        self.info_hash = info_hash

    def __str__(self):
        return f"{self.info_hash} {self.name}"
    
def getScapeData(scrapeURL: str):
    print(f"Trying scrape url: {scrapeURL}")
    URL = urlparse(scrapeURL)
    if URL.scheme == "http" or URL.scheme == "https":
            
        try:
            r = requests.get(scrapeURL, verify=False)
            r.raise_for_status()
            
            if args.verbose:
                print(f"RAW_CONTENT: {r.content.decode()}")
                print(f"SCRAPE_CONTENT: {bencodepy.decode(r.content)}")
            
            scrapeData = bencodepy.decode(r.content)
            file_hashes = list(scrapeData[b"files"].keys())
            file_stats = list(scrapeData[b"files"].values())
            hash_index = 0
            
            if args.verbose:
                print(f"FILE_STATS: {file_stats}\nFILE_HASHES: {file_hashes}")
            
            for i in file_stats:
                try:
                    name = (i[b"name"]).decode("utf-8")
                except Exception:
                    name = "Unknown"
                    
                torrentFiles.append(torrentFile(name,
                                                i[b"downloaded"],
                                                i[b"complete"],
                                                i[b"incomplete"],
                                                file_hashes[hash_index].hex()))
                hash_index += 1
            
            for i in torrentFiles:
                print(i)

            print(f"Total files: {len(torrentFiles)}")

        except Exception as error:
            if type(error).__name__ == "HTTPError":
                getScapeData(scrapeURL.replace("http://", "https://"))
                exit()
                
            print("Failed to get scrape info.", type(error).__name__)
            exit()
    elif URL.scheme == "udp":
        try:
            getScapeData(scrapeURL.replace("udp://", "http://"))
            
        except requests.exceptions.RequestException as error:
            print("Failed to get scrape info.", type(error).__name__)
            exit()
    else:
        print(f"Unknown protocol {URL.scheme}")
        exit()    

def fileOutput(URL):
    fields = ["filename", "info_hash", "seeders", "leechers", "downloads"]
    filename = f"{time.strftime('%H-%M-%S')}-{URL.hostname}"

    if args.xlsx:
        # xlsx output
        workbook = xlsxwriter.Workbook(f'{filename}.xlsx')
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True})

        col = 0
        for i in fields:
            worksheet.write(0, col, i)
            col += 1
                
        col = 0
        row = 1
        for i in torrentFiles:
            worksheet.write(row, col, i.name)
            worksheet.write(row, col+1, i.info_hash)
            worksheet.write(row, col+2, i.complete)
            worksheet.write(row, col+3, i.incomplete)
            worksheet.write(row, col+4, i.downloaded)
            row += 1
                
        worksheet.write(row, 0, "Total files", bold)
        worksheet.write(row, 4, len(torrentFiles), bold)
        workbook.close()

    elif args.csv:
        # csv output
        with open(filename+".csv", "w", newline='') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(fields)
            for i in torrentFiles:
                csvwriter.writerow([i.name, i.info_hash, i.complete, i.incomplete, i.downloaded])
            csvwriter.writerow([f"Total files: {len(torrentFiles)}"])
            f.close()

if __name__ ==  "__main__" :
    parser = argparse.ArgumentParser(description="torrent parser")
    parser.add_argument("-f", "--torrent_file", help="torrent file to parse")
    parser.add_argument("-a", "--announce_uri", help="use uri as announce")
    parser.add_argument("--csv", action="store_true", help="store output in csv file")
    parser.add_argument("--xlsx", action="store_true", help="store output in xlsx file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Output verbose")

    args = parser.parse_args()
    
    if args.announce_uri != None:
        scrapeURL = args.announce_uri.replace("announce", "scrape")
        
        URL = urlparse(scrapeURL)
        torrentFiles = []

        getScapeData(scrapeURL)
        fileOutput(URL)
        
        
    elif args.torrent_file != None:
        with open(args.torrent_file, "rb") as f:
            metainfo = bencodepy.decode(f.read())
            try:
                announceURL = metainfo[b"announce"].decode("utf-8")
                scrapeURL = announceURL.replace("announce", "scrape")
                print(f"scrape: {scrapeURL}")

                URL = urlparse(scrapeURL)
                torrentFiles = []

                getScapeData(scrapeURL)
                fileOutput(URL)
                
            except Exception as error:
                print("Failed to get scrape info.", type(error).__name__)
                exit()