import urllib2
import urllib
import httplib
import re
import socket
import nltk
from time import sleep
from  more_itertools import unique_everseen
from bs4 import BeautifulSoup

# Set some re-used values.
sub_directory = re.compile(r'\..*/.+', re.IGNORECASE)
terms = ['pubmed', '.gov', '.edu', 'doi', 'abstract', '.pdf']
with open('journal_domains.csv', 'rb') as f:
    domains = f.read().split('\r\n')[:-1]


def extract_article_body(soup):
    body_paras = soup.find_all("p", class_='story-body-text')
    if body_paras:
        return '\n\n'.join([p.get_text() for p in body_paras])
    else:
        return None


def soupify(url):
    # ## Fetch the page.
    # We need to use the cookie processor because some websites
    # won't allow access without tracking cookies.
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0')]
    page_html = opener.open(url)
    return BeautifulSoup(page_html, 'html.parser')


def is_paper(url, terms):
    # If the link is to a homepage ('http://google.com/')
    # not a subdirectory ('http://google.com/papers')
    # then we will assume it is not a paper.
    # Also we will not follow self-links.
    if (not re.search(sub_directory, url)) or 'nytimes.com' in url:
        return False
    else: 
        for t in terms:
            # If the url matches a term in the list
            # it might be a paper.
            if t in url:
                return True
    return False


def extract_links(soup, terms):
    # ## Grab the links.
    links = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and is_paper(href, terms):
            links.append({'paragraph_text':a.parent.get_text(), 'link_text':a.get_text(), 'link_url': href})
    return links


def scrape_nyt(url):
    result = {'body':None, 'paper_links':[], 'error':None}
    try:
        soup = soupify(url)
        result['body'] = extract_article_body(soup)
        result['links'] = extract_links(soup, terms + domains)
    except socket.error:
        if tries > 3:
            print '!!!Socket Error: ', url
            result['error'] = 'socket_error'
        else:
            sleep(1)
            result.update(process_pdf(url, tries + 1))
    except urllib2.URLError:
        print '!!!Bad URL: ', url
        result['error'] = 'bad_url'
    except ValueError:
        print '!!!ValueError: ', url
        result['error'] = 'value_error'
    except httplib.BadStatusLine:
        if tries > 3:
            print '!!!Bad Status Line: ', url
            result['error'] = 'bad_status_line'
        else:
            sleep(1)
            result.update(process_pdf(url, tries + 1))

    return result


if __name__ == '__main__':
    import os
    import json
    import csv
    import pprint

    printer = pprint.PrettyPrinter()
    
    ### First get the links and body from each article.
    l_index = 0
    with open('nyt_links.csv', 'wb') as link_file:
        link_writer = csv.writer(link_file)
        if len(os.listdir('nyt_processed')):
            start = sorted(os.listdir('nyt_data')).index(sorted(os.listdir('nyt_processed'))[-1])
        else:
            start = 0

        for p in sorted(os.listdir('nyt_data'))[start:]:
            print 'Processing: \t', p, '\n\n'
            path = os.path.join('nyt_data', p)
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    j = json.load(f)
                    if 'docs' in j['response']:
                        docs = j['response']['docs']
                        result = []
                        for d in docs:
                            url = d['web_url']
                            scrape = scrape_nyt(url)
                            # Assign IDs to the links and write them to the file.
                            cur_links = [[i + l_index, v] for i, v in enumerate(scrape['links'])]
                            l_index += len(cur_links)
                            for x in cur_links:
                                link_writer.writerow(x)
                            # Store the link IDs in the article metadata.
                            scrape['link_ids'] = [x[0] for x in cur_links]
                            # Store the article data.
                            result.append(scrape)

                        with open(os.path.join('nyt_processed', p), 'wb') as out_file:
                            json.dump({'docs':result}, out_file)
