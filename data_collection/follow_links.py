import urllib2
import urllib
import httplib
import re
import socket
from time import sleep
from  more_itertools import unique_everseen
from bs4 import BeautifulSoup
from subprocess import check_output, call

# Set some re-used values.
doi_field = re.compile(r'\W*doi:?', re.IGNORECASE)
doi_reg = re.compile(r'\d+\.\d+\/[A-z0-9]+[A-z0-9\./]+', re.IGNORECASE)
sub_directory = re.compile(r'\..*/.+', re.IGNORECASE)
entity_cleaning = re.compile(r'[\W\d]+', re.IGNORECASE)
grobid_uri = "http://localhost:8080/processHeaderDocument"
terms = ['pubmed', '.gov', '.edu', 'doi', 'abstract', '.pdf']
with open('journal_domains.csv', 'rb') as f:
    domains = f.read().split('\r\n')[:-1]


def extract_dois(soup):
    dois = set()
    for r in soup.find_all(text=doi_field):
        match = re.search(doi_reg, r)
        if match:
            dois.add(match.group())
    return list(dois)


def extract_pubmed_ids(soup):
    # Get the pubmed ID.
    report_ids = soup.find_all(class_='rprtid')
    pm_ids = set()
    for tag in report_ids:
        for c in tag.children:
            if 'get_text' in dir(c):
                text = c.get_text()
                if text.isdigit():
                    pm_ids.add(text)
    return list(pm_ids)


def soupify(url):
    # ## Fetch the page.
    # We need to use the cookie processor because some websites
    # won't allow access without tracking cookies.
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0')]
    page_html = opener.open(url)
    return BeautifulSoup(page_html, 'html.parser')

def save_pdf(url, fname):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0')]
    content = opener.open(url).read()
    with open(fname, 'wb') as f:
        f.write(content)


def parse_pdf(url):
    path = '___tmp___.pdf'
    call(['wget', '-O', path, url])
    xml = check_output(['curl','-s','--header', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0', '--form','input=@'+path, grobid_uri])
    soup = BeautifulSoup(xml, 'xml')
    result = {'raw_parse':xml, 'authors':[], 'ids':[(i['type'],i.text.strip()) if 'type' in i else ('ID_TYPE', i.text.strip()) for i in soup.find_all('idno')]}
    # Grab the title
    result['titles'] = [i.text for i in soup.find_all('title', attrs={'type':'main'})]
    # Grab all the author names and affiliations.
    for a in soup.find_all('author'):
        persName = a.find('persName')
        if persName:
            name = ' '.join([n.text.strip() for n in persName.find_all()])
        else:
            name = 'NO_NAME_FOUND'
        affil = a.find('affiliation')
        if affil:
            affils = {(aff['type'] if 'type' in i else 'AFFIL_TYPE'): aff.text.strip() for aff in affil.find_all('orgName')}
        else:
            affils = {}
        result['authors'].append((name, affils))
    call(['rm', path])
    return result



if __name__ == '__main__':
    import os
    import json
    import csv
    import pprint

    printer = pprint.PrettyPrinter()
    with open('__scrape_progress__', 'rb') as prog_file:
        start_point = max([int(x) for x in prog_file.read().split('\n') if x])
        print 'Resuming from line ', start_point
    with open('__scrape_progress__', 'ab') as prog_file:
        with open('nyt_urls.csv', 'rb') as f:
            links = [x for x in csv.reader(f)]
            result = []
            for l in links[start_point:]:
                i, url = l
                data = {'ids':[], 'authors':[], 'titles':[], 'raw_parse':''}
                # If it's a PDF
                if '.pdf' in url:
                    trimmed_url = url[:url.index('.pdf')+4]
                    data = parse_pdf(trimmed_url)
                    # try:
                    #     data = parse_pdf(trimmed_url)
                    # except:
                    #     data['error'] = 'pdf_parsing_failed'
                else:
                    try:
                        cur_soup = soupify(url)
                        data['ids'].append(('DOI', extract_dois(cur_soup)))
                        # If it's a pubmed page, try to grab the pubmed id.
                        if 'pubmed' in url:
                            data['ids'].append(('PUBMED', extract_pubmed_ids(cur_soup)))
                    except urllib2.HTTPError:
                        data['error'] = 'broken_link'
                    except urllib2.URLError:
                        data['error'] = 'bad_connection'

                with open('nyt_processed_urls/{}.json'.format('link_'+str(i)), 'wb') as f:
                    json.dump([i, url, data], f)

                # Record progress
                prog_file.write(str(i)+'\n')

    exit()
