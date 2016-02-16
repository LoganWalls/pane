import re
import json
import graphlab as gl
import os
from subprocess import check_output
from time import sleep

def process_response(resp, data_ex, escape):
    result = {'authors':[], 'paper_info':[], 'publication_info':[], 'other':[], 'error':None}
    if '!DOCTYPE html PUBLIC' in resp:
        result['error'] = '404'
        return result
    
    resp = re.sub(escape, r'\1\2', resp)
    chunks = resp.split('\n\n')
    for c in chunks:
        lines = c.split(';')
        items = {'url': lines[0].split('\n')[0].strip().replace('<', '').replace('>', '')}
        lines = lines[1:]
        for l in lines:
            k, v = l.strip().split('\n')
            key = k.split('/')[-1].replace('>', '')
            values = re.findall(data_ex, v)
            items[key] = values
        if 'issn' in items['url']:
            items['dtype'] = 'publication'
            result['publication_info'].append(items)
        elif 'contributor' in items['url']:
            items['dtype'] = 'person'
            result['authors'].append(items)
        elif '.doi.org' in items['url']:
            items['dtype'] = 'paper_info'
            result['paper_info'].append(items)
        else:
            items['dtype'] = 'other'
            result['other'].append(items)

    return result

data_ex = re.compile(r'\"([^"]+)\"', re.IGNORECASE)
escape = re.compile(r'"(.*);(.*)"', re.IGNORECASE)
fixer = re.compile(r'(10[.][0-9]{4,}(?:[.][0-9]+)*/(?:(?!["&\'<>])\S)+[0-9])', re.IGNORECASE)
sf = gl.SFrame('fixed_dois')
dois = sorted(list(set(sf['DOI'])))
num_reqs = len(dois)
grabbed_data = []
previous = list(os.listdir('metadata2'))

for i, doi in enumerate(dois):
    if 'req_{}.json'.format(i) in previous:
        continue

    print '-'*40
    print (' '*20) + 'Progress:\t{}%'.format((float(i)/num_reqs) * 100)
    print '-'*40
    resp = check_output(['curl',
                         '-L',
                         '-H',
                         "Accept: text/turtle",
                         '-A',
                         'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0',
                         "http://dx.doi.org/"+doi])
    print "http://dx.doi.org/"+doi
    try:
        result = {'DOI':doi, 'info':process_response(resp, data_ex, escape)}
        if result['info']['error'] == '404':
            doi = re.search(fixer,doi).groups()[0]
            resp = check_output(['curl',
                     '-L',
                     '-H',
                     "Accept: text/turtle",
                     '-A',
                     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0',
                     "http://dx.doi.org/"+doi])
            print "http://dx.doi.org/"+doi
            result = {'DOI':doi, 'info':process_response(resp, data_ex, escape)}
            if result['info']['error'] == '404':
                print '-'*40
                print (' '*20) + '404'
                print '-'*40

    except ValueError as e:
        print e
        print resp
        exit()
    except Exception as e:
        print e
        result = {'DOI':doi, 'info':{'authors':[], 'paper_info':[], 'publication_info':[], 'other':[], 'error':str(e)}}
    
    with open('metadata2/req_{}.json'.format(i), 'wb') as f:
        json.dump(result, f)
    sleep(1)

