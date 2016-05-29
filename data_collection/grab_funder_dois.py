import requests
import json
import re
import os
import graphlab as gl
from time import sleep

base_uri = "http://api.crossref.org/funders/"
headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0'}
funders = gl.SFrame('funder_list')
previous = [i.replace('fid_','') for i in os.listdir('funder_works') if i.startswith('fid_')]

for i, f_id in enumerate(funders['id']):
    print 'Progress:\t{}%'.format((float(i)/funders.num_rows()) * 100)
    # Skip if we've processed this funder already.
    if f_id in previous:
        continue
    cur_items = []
    cur_uri = "http://api.crossref.org/funders/{}/works?offset=0".format(f_id)
    offset = 0
    num_items = 1
    while offset < num_items:
        r = requests.get(cur_uri, headers=headers)
        if r.status_code == 200:
            j = r.json()
            num_items = j['message']['total-results']
            cur_items.extend(j['message']['items'])
            offset += 20
            cur_uri = re.sub(r'offset=\d+', 'offset='+str(offset), cur_uri)
            sleep(1)
        else:
            print 'FAILURE Status Code: ', r.status_code
    tmp = gl.SFrame(cur_items)
    if tmp.num_rows():
        tmp = tmp.unpack('X1', column_name_prefix='')
        tmp['funder_id'] = gl.SArray.from_const(f_id, tmp.num_rows())
        tmp.save('funder_works/fid_{}'.format(f_id))


exit()
