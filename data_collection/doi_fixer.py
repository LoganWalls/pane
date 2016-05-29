import re
import graphlab as gl
import json
import urllib2
from bs4 import BeautifulSoup


def extract_dois(soup):
    matches = re.search(doi_regex, soup.text)
    if matches:
        return list(set(matches.groups()))
    else:
        return []


def soupify(url):
    # ## Fetch the page.
    # We need to use the cookie processor because some websites
    # won't allow access without tracking cookies.
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0')]
    page_html = opener.open(url)
    return BeautifulSoup(page_html, 'html.parser')

doi_regex = re.compile(r'\b(10[.][0-9]{4,}(?:[.][0-9]+)*/(?:(?!["&\'<>])\S)+)\b', re.IGNORECASE)
sf = gl.SFrame('links_missing_doi')

for i, row in enumerate(sf):
    print 'Progress:\t{}%'.format((float(i)/sf.num_rows()) * 100)
    _id = row['id']
    url = row['link_url']
    try:
        soup = soupify(url)
        dois = extract_dois(soup)
        error = None

    except Exception as e:
        print e
        dois = []
        error = str(e)

    with open('doi_fix_json/{}.json'.format('id_'+str(_id)), 'wb') as f:
        json.dump({'id':_id, 'link_url': url, 'DOI':dois, 'error': error}, f)
