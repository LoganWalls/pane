import requests
import math
import json
import re
import os
from time import sleep
from datetime import datetime
from datetime import timedelta


# Takes a datetime string of the latest request.
# Returns the 'end_date' parameter to be used in the URI
# (to keep collecting data where the last article left off).
def dt_to_query_param(dt_str):
    # Convert the string to a datetime.
    dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    # Subtract 1 day.
    dt = datetime.fromordinal(dt.toordinal() - 1)
    # Return the new date in the correct format
    # for the query.
    return dt.strftime('%Y%m%d')

# Args
key = "92c395efa9037a667cd2bee2fec3ca0f:3:73218186"
calls_per_second = 10
calls_per_day = 10000
begin_date = datetime.strptime('20130101', '%Y%m%d')
end_date = datetime.strptime('20131231', '%Y%m%d')


# Setup stuff.
wait_interval = timedelta(seconds=1./calls_per_second)
uri = "http://api.nytimes.com/svc/search/v2/articlesearch.json?fq=news_desk.contains%3A%28%22health%22%29+OR+section_name.contains%3A%28%22health%22%29+AND+NOT+type_of_material%3A%28%22Recipe%22+%22Multimedia%22+%22Video%22+%22Interactive+Feature%22%29&begin_date=20130101&end_date=20131231&sort=oldest&fl=headline%2Cnews_desk%2Csection_name%2Ctype_of_material%2Cweb_url%2Cbyline%2C_id%2Ckeywords%2Cmultimedia%2Cpub_date"
uri = uri + "&api-key=" + key

i = 0
req_count = 1
start_time = datetime.utcnow()
prev_time = datetime.utcnow()
prev_r = None
while end_date > begin_date:
    if datetime.utcnow() - start_time > timedelta(days=math.ceil(req_count/calls_per_day)):
        # If we've waited long enough since the last request.
        if datetime.utcnow() - prev_time > wait_interval:

            if i <= 100:
                code = 0
                tries = 0
                # This while-loop allows us to retry
                # up to three times if the connectoin fails.
                while code != 200 and tries < 3:
                    # Update the URI page and send the request.
                    cur_uri = uri + "&page=" + str(i)
                    print 'Requesting page '+str(i)+'...'
                    r = requests.get(cur_uri)
                    req_count += 1
                    tries += 1

                    # Record the time at which we're making the request.
                    prev_time = datetime.utcnow()

                    code = r.status_code
                    # If the request was successful save the data and
                    # increment the page number.
                    if code == 200:
                        with open('__scrape_files__/nyt_pages/page'+str(req_count)+'.json', 'wb') as f:
                            json.dump(r.json(), f)

                        print 'Success!'
                        prev_r = r
                        i += 1
                    else:
                        # If we failed, wait a second before trying again.
                        print '!!!FAILURE!!!'
                        print 'Status Code: ', r.status_code
                        sleep(1)

            # If we've gotten to 100 pages, shift the end-date
            else:
                # Get the final publication date for the most recent
                # response.
                dt_str = prev_r.json()['response']['docs'][-1]['pub_date']
                print 'Changing begin_date to:', dt_str
                begin_date = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
                # Update the URI.
                new_param = dt_to_query_param(dt_str)
                uri = re.sub(r'&begin_date=\d{8}', '&begin_date=' + new_param, uri)
                i = 0

print 'Collection Complete!'
exit()
