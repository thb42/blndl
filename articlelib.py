import requests, json, sys, logging, pypandoc, webkit_server, html
from html.parser import HTMLParser

class blndl:
    def __init__(self, loglevel=logging.WARNING, logfile=None):

        logging.basicConfig(level=loglevel)

        self._loggedin = False
        self._session = requests.Session()
        self._header = None
        self._lastresponse = None
        self._loginresponse = None
        self._items = []

    def login(self, username, password):
        data = {"login":username, "password":password}
        try:
            r = self._session.post("https://ws.blendle.com/credentials", data = json.dumps(data))
            if(r.status_code == 200):
                self._loggedin = True
                self._loginresponse = json.loads(r.text)
                self._lastresponse = self._loginresponse
                self._header = {"Host": "ws.blendle.com", "Accept":"application/json", "Authorization": "Bearer " + self._loginresponse["jwt"]}
                logging.debug("Login successfull!")
                return True
            else:
                logging.info("Login failed!")
                return False
        except Exception as e:
            logging.error("Error on login! {0}".format(e))
            logging.error("HTTP response was: {0}".format(self._session.status_code))
            return False

    def logout(self):
        if(self._loggedin == True):
            r = self._session.get("https://blendle.com/logout")
            if(r.status_code == 200):
                self._loggedin = False
            else:
                logging.error("Something went wrong during logout! HTTP Code: {0}".format(r.status_code))
                self._loggedin = None

    def _loadByURL(self, url):
        if(self._loggedin == False):
            lgging.error("Login first!")
            return False
        resp = self._session.get(url = url, headers = self._header)
        try:
            self._lastresponse = json.loads(resp.text)
        except Exception as e:
            logging.warning("Could not handle repsonse as json! Response loaded as text.")
            self._lastresponse = resp.text

        if(resp.status_code == 200):
            self._items.extend(self._lastresponse['_embedded']['items'])
            logging.debug("Loaded items!")
            return True
        else:
            logging.warning("Could not load item. Response status code: {0}".format(resp.status_code))
            return False

    # depending on how many article one has bought, it could take some time to load them
    # onlyLatestArticle = True shoud load the latest 10 articles
    def loadArticles(self, onlyLatestArticle=False):
        if(self._loggedin == False):
            print("Login first!")
            return False

        if(onlyLatestArticle):
            logging.debug("Load only latest articles!")

        try:
            next = self._loginresponse["_embedded"]["user"]["_links"]["reads"]["href"]
            ret = self._loadByURL(next)

            if(ret):
                next = self._lastresponse["_links"]["next"]["href"]

            while (ret) and (not onlyLatestArticle) and (not next == None):
                ret = self._loadByURL(next)
                next = self._lastresponse["_links"]["next"]["href"]

        except Exception as e:
            print("Error while loading articles.\n\t{0}".format(e))
            #print(self._lastresponse)
            return False
        return True

    def listArticles(self):
        if(self._items == None):
            logging.info("No items loaded!")
            return

        for index in range(0, len(self._items)):
            body = self._items[index]["_embedded"]["manifest"]["body"]
            hl1, intro, kicker = ("", "", "")
            for t in body:
                if(t["type"] == "hl1"):
                    hl1 = t["content"]
                elif(t["type"] == "intro"):
                    intro = t["content"]
                elif(t["type"] == "kicker"):
                        kicker = t["content"]
            print("{0}: {1} {2} {3}...".format(index, hl1, kicker, intro[0:20]))
        return


    def showArticle(self, item_index):
        if(self._items == None):
            logging.info("No items loaded!")
            return

        if(item_index >= len(self._items)):
            raise IndexError
            return False

        a = self._items[item_index]

        provider = a["_embedded"]["manifest"]["provider"]["id"]
        hl1, hl2, kicker, intro, p, byline = ("", "", "", "", "", "")
        for b in a["_embedded"]["manifest"]["body"]:
            if(b["type"] == "hl1"):
                hl1 = b["content"]
            elif(b["type"] == "hl2"):
                hl2 = b["content"]
            elif(b["type"] == "intro"):
                intro = b["content"]
            elif(b["type"] == "byline"):
                byline = b["content"]
            elif(b["type"] == "p" ):
                p = b["content"]
            elif(b["type"] == "kicker"):
                kicker = b["content"]

        if(byline == ""):
            print("From {0}".format(provider))
        else:
            print("From {0} by {1}".format(provider, byline))

        if not(kicker == ""):
            print("{0}\n".format(kicker))
        print(hl1)
        if not(hl2 == ""):
            print(hl2)
        if not(intro == ""):
            print("\n {0}\n".format(intro))
        if not(p == ""):
            print(p)


    def downloadArticle(self, item_index, path):
        if(self._items == None):
            logging.warning("No items loaded!")
            return False

        if(item_index >= len(self._items)):
            raise IndexError
            return False

        a = self._items[item_index]

        provider = a["_embedded"]["manifest"]["provider"]["id"]
        article_id = a["_embedded"]["manifest"]["id"]
        headline = ""
        for t in a["_embedded"]["manifest"]["body"]:
            if(t["type"] == "hl1"):
                headline = t["content"]
                headline = headline.casefold()
                if(headline.startswith('<')):
                    tag = headline[1:headline.find(">")]
                    headline = headline.strip("</" + tag + ">")
                headline = headline.replace(" ", "-")

        if(headline == ""):
            logging.error("Error headline (hl1) not found!")
            return False

        url = "https://blendle.com/i/{0}/{1}/{2}".format(provider, headline, article_id)

        mod_header = self._header
        mod_header["Host"] = "blendle.com"

        # print(url)
        #let webkit visit url to exec javascript
        c = webkit_server.Client()
        for k,v in mod_header.items():
            c.set_header(key=k, value=v)
        c.visit(url)

        if(c.status_code() != 200):
            logging.error("Could not handle JavaScript! HTML Error:{0}".format(c.status_code()))
            return False

        p = JS_HTML_Parser(c)
        p.feed(str(c.body))
        p.close()

        html = c.body()

        # convert html to pdf with pandoc
        of=path+"{0}_{1}.pdf".format(provider, headline.replace(" ", "_"))
        output = pypandoc.convert_text(html, 'pdf', outputfile=of, format='html')
        assert output == ""
        return True

class JS_HTML_Parser(HTMLParser):
    def __init__(self, wk_client):
        HTMLParser.__init__(self)
        self._c = wk_client
        self.script = False
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.script = True
    def handle_endtag(self, tag):
        if tag == 'script':
            self.script = False
    def handle_data(self, data):
        try:
            self._c.exec_script(data)
        except webkit_server.InvalidResponseError:
            pass
