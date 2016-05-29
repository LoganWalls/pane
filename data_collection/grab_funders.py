import requests
import json
import re
import graphlab as gl

funder_list_uri = "http://api.crossref.org/funders?offset=0"
headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:10.0) Gecko/20100101 Firefox/10.0'}
offset = 0
funder_list = []
# They have this many funders
while offset < 11503:
    print "Progress:\t{}%".format((offset / float(11503)) * 100)
    r = requests.get(funder_list_uri, headers=headers)
    if r.status_code == 200:
        funder_list.extend(r.json()['message']['items'])
        offset += 20
        funder_list_uri = re.sub(r'offset=\d+', 'offset='+str(offset), funder_list_uri)
    else:
        print 'FAILURE Status Code: ', r.status_code

sf = gl.SFrame(funder_list)
sf = sf.unpack('X1', column_name_prefix='')
sf.save('funder_list.csv')
exit()
