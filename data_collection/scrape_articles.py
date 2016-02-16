import urllib2
import urllib
import httplib
import re
import pdfminer
import socket
import nltk
import requests
from time import sleep
from  more_itertools import unique_everseen
import bs4
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


def extract_article_body(soup):
    body_paras = soup.find_all("p", class_='story-body-text')
    if body_paras:
        return '\n\n'.join([p.get_text() for p in body_paras])
    else:
        return None


def extract_comment_counts(soup):
    count = soup.find(class_="button-text.count")
    print count
    if count:
        return count.get_text()
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

def save_pdf(url, fname):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0')]
    content = opener.open(url).read()
    with open(fname, 'wb') as f:
        f.write(content)


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

# def process_pdf(url, tries=0):
#     result = {}
#     try:
#         pdf_text = pdf_from_url_to_txt(url, maxpages=3)
#         # Try to extract the doi.
#         result['doi'] = doi_from_pdf(pdf_text)
#         # Save the head of the document.
#         result['head'] = get_pdf_head(pdf_text)
#         result['entities'] = entities_from_pdf(pdf_text)
#     except urllib2.HTTPError:
#         print '!!! Broken Link:\n', url
#         result['broken_link'] = True
#         result['doi'] = []

#     # This error happens sometimes and retrying works,
#     # So try 3 times (each one second apart) before giving up.
#     except pdfminer.pdfparser.PDFSyntaxError:
#         if tries > 3:
#             print '!!! Unreadable PDF\n', url
#             result['unreadable_pdf'] = True
#             result['doi'] = []
#         else:
#             sleep(1)
#             result.update(process_pdf(url, tries + 1))
#     except httplib.BadStatusLine:
#         print '!!! Bad Status Line\n', url
#         result['unreadable_pdf'] = True
#         result['doi'] = []
#     except:
#         print '!!! Unknown Trouble Reading PDF\n', url
#         result['unreadable_pdf'] = True
#         result['doi'] = []

#     return result

def parse_pdf(url):
    path = '___tmp___.pdf'
    call(['wget', '-O', path, url])
    xml = check_output(['curl','-s','--form','input=@'+path, grobid_uri])
    soup = BeautifulSoup(xml, 'xml')
    result = {'raw_parse':xml, 'authors':[], 'ids':[(i['type'],i.text.strip()) for i in soup.find_all('idno')]}
    # Grab the title
    result['titles'] = [i.text for i in soup.find_all('title', attrs={'type':'main'})]
    # Grab all the author names and affiliations.
    for a in soup.find_all('author'):
        name = ' '.join([n.text.strip() for n in a.find('persName').find_all()])
        affil = {aff['type']: aff.text.strip() for aff in a.find('affiliation').find_all('orgName')}
        result['authors'].append((name, affil))
    call(['rm', path])
    return result


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





def process_media_article(url, tries=0):
    result = {'body':None, 'paper_links':[]}
    try:
        soup = soupify(url)
        result['body'] = extract_article_body(soup)
        page_links = extract_links(soup, terms + domains)
        link_results = [i for i in page_links]
        for i, l in enumerate(page_links):
            cur_url = l['link_url']
            # If it's a PDF
            if cur_url.endswith('.pdf+html'):
                cur_url = cur_url[:-5]
            if cur_url.endswith('.pdf'):
                pdf_data = process_pdf(cur_url)
                link_results[i].update(pdf_data)
            else:
                try:
                    cur_soup = soupify(cur_url)
                    link_results[i]['doi'] = extract_dois(cur_soup)
                    # If it's a pubmed page, try to grab the pubmed id.
                    if 'pubmed' in cur_url:
                        link_results[i]['pubmed_id'] = extract_pubmed_ids(cur_soup)
                except urllib2.HTTPError:
                    print '!!! Broken Link:\n', cur_url
                    link_results[i]['broken_link'] = True
                    link_results[i]['doi'] = []
        result['paper_links'] = link_results
    except socket.error:
        if tries > 3:
            print '!!!Socket Error: ', url
            result['linked_dois'] = []
        else:
            sleep(1)
            result.update(process_pdf(url, tries + 1))
    except urllib2.URLError:
        print '!!!Bad URL: ', url
        result['linked_dois'] = []
    except ValueError:
        print '!!!ValueError: ', url
        result['linked_dois'] = []
    except httplib.BadStatusLine:
        if tries > 3:
            print '!!!Bad Status Line: ', url
            result['linked_dois'] = []
        else:
            sleep(1)
            result.update(process_pdf(url, tries + 1))

    result['linked_dois'] = []
    [result['linked_dois'].extend(l['doi']) for l in link_results if 'doi' in l and l['doi']]

    return result


if __name__ == '__main__':
    import os
    import json
    import csv
    import pprint

    printer = pprint.PrettyPrinter()
    
    articles = []
    l_index = 0
    with open('nyt_processed/links.csv', 'wb') as link_file:
        link_writer = csv.writer(link_file)
        start = sorted(os.listdir('nyt_data')).index(sorted(os.listdir('nyt_processed'))[-1])
        for p in sorted(os.listdir('nyt_data'))[start:]:
            print 'Processing: \t', p, '\n\n'
            path = os.path.join('nyt_data', p)
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    j = json.load(f)
                    if 'docs' in j['response']:
                        docs = j['response']['docs']
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
