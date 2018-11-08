# Author: Michal Tomczyk
# michal.tomczyk@cs.put.poznan.pl
# Poznan University of Technology
# Institute of Computing Science
# Laboratory of Intelligent Decision Support Systems
# -------------------------------------------------------------------------
import os
import urllib.request as req
from html.parser import HTMLParser


# -------------------------------------------------------------------------
# generatePolicy classes


# Dummy fetch policy. Returns first element. Does nothing ;)
class Dummy_Policy:
    def getURL(self, c, iteration):
        if len(c.URLs) == 0:
            return None
        else:
            return c.seedURLs[0]

    def updateURLs(self, c, newURLs, newURLsWD, iteration):
        pass


# LIFO fetch policy.
class LIFO_Policy:
    def __init__(self, c):
        self.queue = c.seedURLs
        self.copyQueue = c.seedURLs.copy()

    def getURL(self, c, iteration):
        if len(self.queue) == 0:
            self.copyQueue = [self.copyQueue[0]]
            return self.copyQueue[0]
        else:
            item = self.queue[len(self.queue) - 1]
            self.queue.remove(item)
            return item

    def updateURLs(self, c, newURLs, newURLsWD, iteration):
        tempList = list(newURLs)
        tempList.sort(key=lambda url: url[len(url) - url[::-1].index('/'):])

        self.queue.extend(tempList)
        pass


class LIFO_Cycle_Policy:
    def __init__(self, c):
        self.queue = c.seedURLs
        self.copyQueue = c.seedURLs.copy()
        self.fetched = set()

    def getURL(self, c, iteration):
        if len(self.queue) == 0:
            self.copyQueue = [self.copyQueue[0]]
            self.fetched.clear()
            return self.copyQueue[0]
        else:
            r = []
            r.extend(reversed(self.queue))

            for x in r:
                if x in self.fetched:
                    self.queue.remove(x)
                    self.fetched.add(x)
                    if len(self.queue) == 0:
                        self.copyQueue = [self.copyQueue[0]]
                        self.fetched.clear()
                        return self.copyQueue[0]
                else:
                    self.fetched.add(x)
                    return x

    def updateURLs(self, c, newURLs, newURLsWD, iteration):
        tempList = list(newURLs)
        tempList.sort(key=lambda url: url[len(url) - url[::-1].index('/'):])

        self.queue.extend(tempList)
        # pass


# FIFO fetch policy.
class FIFO_Policy:
    def __init__(self, c):
        self.queue = c.seedURLs
        self.copyQueue = c.seedURLs.copy()

    def getURL(self, c, iteration):

        if len(self.queue) == 0:
            self.copyQueue = [self.copyQueue[0]]
            return self.copyQueue[0]
        else:
            item = self.queue[0]
            self.queue.remove(item)
            return item

    def updateURLs(self, c, newURLs, newURLsWD, iteration):
        tempList = list(newURLs)
        tempList.sort(key=lambda url: url[len(url) - url[::-1].index('/'):])

        self.queue.extend(tempList)
        pass


class Parser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.output_list = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.output_list.append(dict(attrs).get('href'))


# -------------------------------------------------------------------------
# Data container
class Container:
    def __init__(self):
        # The name of the crawler"
        self.crawlerName = "IRbot"
        # Example ID
        # self.example = "exercise1"
        self.example = "exercise2"
        # Root (host) page
        self.rootPage = "http://www.cs.put.poznan.pl/alabijak/ezi/lab1/" + self.example
        # Initial links to visit
        self.seedURLs = [
            "http://www.cs.put.poznan.pl/alabijak/ezi/lab1/" + self.example +
            "/s0.html"
        ]
        # Maintained URLs
        self.URLs = set([])
        # Outgoing URLs (from -> list of outgoing links)
        self.outgoingURLs = {}
        # Incoming URLs (to <- from; set of incoming links)
        self.incomingURLs = {}

        # Class which maintains a queue of urls to visit.
        # self.generatePolicy = Dummy_Policy()
        # self.generatePolicy = LIFO_Policy(self)
        self.generatePolicy = LIFO_Cycle_Policy(self)
        # self.generatePolicy = FIFO_Policy(self)
        # Page (URL) to be fetched next
        self.toFetch = None
        # Number of iterations of a crawler.
        # self.iterations = 3
        self.iterations = 10

        # If true: store all crawled html pages in the provided directory.
        self.storePages = True
        self.storedPagesPath = "./" + self.example + "/pages/"
        # If true: store all discovered URLs (string) in the provided directory
        self.storeURLs = True
        self.storedURLsPath = "/" + self.example + "/urls/"
        # If true: store all discovered links (dictionary of sets: from->set to),
        # for web topology analysis, in the provided directory
        self.storeOutgoingURLs = True
        self.storedOutgoingURLs = "/" + self.example + "/outgoing/"
        # Analogously to outgoing
        self.storeIncomingURLs = True
        self.storedIncomingURLs = "/" + self.example + "/incoming/"

        # If True: debug
        self.debug = True
        # self.debug = False


def main():
    # Initialise data
    c = Container()
    # Inject: parse seed links into the base of maintained URLs
    inject(c)

    # Iterate...
    for iteration in range(c.iterations):

        if c.debug:
            print("=====================================================")
            print("Iteration = " + str(iteration + 1))
            print("=====================================================")
        # Prepare a next page to be fetched
        generate(c, iteration)
        if (c.toFetch == None):
            if c.debug:
                print("   No page to fetch!")
            continue

        # Generate: it downloads html page under "toFetch URL"
        page = fetch(c)

        if page == None:
            if c.debug:
                print("   Unexpected error; skipping this page")
            removeWrongURL(c)
            continue

        # Parse file
        htmlData, newURLs = parse(c, page, iteration)

        # Store pages
        if c.storePages:
            storePage(c, htmlData)

        # normalise newURLs
        newURLs = getNormalisedURLs(newURLs)

        # update outgoing/incoming links
        updateOutgoingURLs(c, newURLs)
        updateIncomingURLs(c, newURLs)

        # Filter out some URLs
        newURLs = getFilteredURLs(c, newURLs)

        # removeDuplicates
        newURLsWD = removeDuplicates(c, newURLs)

        # update urls
        c.generatePolicy.updateURLs(c, newURLs, newURLsWD, iteration)

        # Add newly obtained URLs to the container
        if c.debug:
            print("   Maintained URLs...")
            for url in c.URLs:
                print("      " + str(url))

        if c.debug:
            print(
                "   Newly obtained URLs (duplicates with maintaines URLs possible) ..."
            )
            for url in newURLs:
                print("      " + str(url))
        if c.debug:
            print("   Newly obtained URLs (without duplicates) ...")
            for url in newURLsWD:
                print("      " + str(url))
            for url in newURLsWD:
                c.URLs.add(url)

    # store urls
    if c.storeURLs:
        storeURLs(c)
    if c.storeOutgoingURLs:
        storeOutgoingURLs(c)
    if c.storeIncomingURLs:
        storeIncomingURLs(c)


# -------------------------------------------------------------------------
# Inject seed URL into a queue (DONE)
def inject(c):
    for l in c.seedURLs:
        if c.debug:
            print("Injecting " + str(l))
        c.URLs.add(l)


# -------------------------------------------------------------------------
# Produce next URL to be fetched (DONE)
def generate(c, iteration):
    url = c.generatePolicy.getURL(c, iteration)
    if url == None:
        if c.debug:
            print("   Fetch: error")
        c.toFetch = None
        return None
    # WITH NO DEBUG!
    print("   Next page to be fetched = " + str(url))
    c.toFetch = url


# -------------------------------------------------------------------------
# Generate (download html) page (DONE)
def fetch(c):
    URL = c.toFetch
    if c.debug:
        print("   Downloading " + str(URL))
    try:
        opener = req.build_opener()
        opener.addheadders = [('User-Agent', c.crawlerName)]
        webPage = opener.open(URL)
        return webPage
    except:
        return None


# -------------------------------------------------------------------------
# Remove wrong URL (TODO)
def removeWrongURL(c):
    c.URLs.remove(c.toFetch)
    pass


# -------------------------------------------------------------------------
# Parse this page and retrieve text (whole page) and URLs (TODO)
def parse(c, page, iteration):
    # data to be saved (DONE)
    htmlData = page.read()
    # obtained URLs (TODO)
    newURLs = set([])
    if c.debug:
        print("   Extracted " + str(len(newURLs)) + " links")

    p = Parser()
    p.feed(str(htmlData))
    newURLs = set(p.output_list)

    return htmlData, newURLs


# -------------------------------------------------------------------------
# Normalise newly obtained links (TODO)
def getNormalisedURLs(newURLs):
    temp = []
    for s in newURLs:
        temp.append(s.lower())

    return set(temp)


# -------------------------------------------------------------------------
# Remove duplicates (duplicates) (TODO)
def removeDuplicates(c, newURLs):
    list = []
    for new in newURLs:
        if (new not in c.URLs):
            list.append(new)

    return list


# -------------------------------------------------------------------------
# Filter out some URLs (TODO)
def getFilteredURLs(c, newURLs):
    if (c.toFetch in newURLs):
        while c.toFetch in newURLs:
            newURLs.remove(c.toFetch)

    toLeft = set(
        [url for url in newURLs if url.lower().startswith(c.rootPage)])
    if c.debug:
        print("   Filtered out " + str(len(newURLs) - len(toLeft)) + " urls")
    return toLeft


# -------------------------------------------------------------------------
# Store HTML pages (DONE)
def storePage(c, htmlData):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/pages/" + c.toFetch[relBeginIndex + 1:]

    if c.debug:
        print("   Saving HTML page " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    with open(totalPath, "wb+") as f:
        f.write(htmlData)
        f.close()


# -------------------------------------------------------------------------
# Store URLs (DONE)
def storeURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/urls/urls.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.URLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            f.write(line + "\n")
        f.close()


# -------------------------------------------------------------------------
# Update outgoing links (DONE)
def updateOutgoingURLs(c, newURLsWD):
    if c.toFetch not in c.outgoingURLs:
        c.outgoingURLs[c.toFetch] = set([])
    for url in newURLsWD:
        c.outgoingURLs[c.toFetch].add(url)


# -------------------------------------------------------------------------
# Update incoming links (DONE)
def updateIncomingURLs(c, newURLsWD):
    for url in newURLsWD:
        if url not in c.incomingURLs:
            c.incomingURLs[url] = set([])
        c.incomingURLs[url].add(c.toFetch)


# -------------------------------------------------------------------------
# Store outgoing URLs (DONE)
def storeOutgoingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/outgoing_urls/outgoing_urls.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.outgoingURLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.outgoingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()


# -------------------------------------------------------------------------
# Store incoming URLs (DONE)
def storeIncomingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/incoming_urls/incoming_urls.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.incomingURLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.incomingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()


if __name__ == "__main__":
    main()
