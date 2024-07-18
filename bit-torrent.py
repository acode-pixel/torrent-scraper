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
            r.close()
            return

        except Exception as error:
            if type(error).__name__ == "HTTPError" and URL.scheme == "http":
                print("Failed to get scrape info.", type(error).__name__, f"HTTP status code {r.status_code}")
                return getScapeData(scrapeURL.replace("http://", "https://"))
                
                
            print("Failed to get scrape info.", type(error).__name__)
            return -1
    elif URL.scheme == "udp":
        
        """try:
            
        except:"""
            
        try:
            return getScapeData(scrapeURL.replace("udp://", "http://"))
            
        except requests.exceptions.RequestException as error:
            print("Failed to get scrape info.", type(error).__name__)
            return -1
    else:
        print(f"Unknown protocol {URL.scheme}")
        return -1 

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
            
    elif args.storeInfoHashes != None:
        
        try:
            f = open(args.storeInfoHashes, "w")
        except Exception as error:
            print(f"Failed creating outFile {args.storeInfoHashes}.", type(error).__name__)
            return
        
        for i in torrentFiles:
            f.write(i.info_hash+"\n")
        f.close()
        
def parseURL(scrapeURL: str):
    maxRetries = args.maxRetries
    while True:
        if getScapeData(scrapeURL) == 0:
            break
        else:
            maxRetries -= 1
            if maxRetries == 0:
                return
            print("\nRetrying")

if __name__ ==  "__main__" :
    parser = argparse.ArgumentParser(description="torrent parser")
    parser.add_argument("-f", "--torrent_file", help="torrent file to parse")
    parser.add_argument("-a", "--announce_uri", help="use uri as announce")
    parser.add_argument("--csv", action="store_true", help="store output in csv file")
    parser.add_argument("--xlsx", action="store_true", help="store output in xlsx file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Output verbose")
    parser.add_argument("--max-retries", action="store", dest="maxRetries", default=5, type=int, help="Maximum amount of retries")
    parser.add_argument("-oi", "--out-infoHashes", action="store", dest="storeInfoHashes", help="Output info hashes to designated file")
    parser.add_argument("-in", "--input-tacker", dest="trackerFile", help="Input a list of trackers in a file")
    args = parser.parse_args()
    
    if args.announce_uri != None:
        scrapeURL = args.announce_uri.replace("announce", "scrape")
        
        URL = urlparse(scrapeURL)
        torrentFiles = []
        
        parseURL(scrapeURL)    
        fileOutput(URL)
        
    elif args.trackerFile != None:
        try:
            f = open(args.trackerFile, "r")
            while True:
                announceURL = f.readline()
                if announceURL == '\n':
                    continue
                elif announceURL == '':
                    break
                parseURL(announceURL.replace("announce", "scrape"))
            f.close()
                
        except Exception as error:
            print(f"Failed parsing tracker file {type(error).__name__}")
            f.close()
            exit()
            
        
    elif args.torrent_file != None:
        with open(args.torrent_file, "rb") as f:
            metainfo = bencodepy.decode(f.read())
            try:
                announceURL = metainfo[b"announce"].decode("utf-8")
                scrapeURL = announceURL.replace("announce", "scrape")
                print(f"scrape: {scrapeURL}")

                URL = urlparse(scrapeURL)
                torrentFiles = []

                parseURL(scrapeURL)
                fileOutput(URL)
                
            except Exception as error:
                print("Failed to get scrape info.", type(error).__name__)
                exit()