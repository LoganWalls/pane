import csv
import re

with open('journal_urls.csv', 'rb') as read_f:
    with open('journal_domains.csv', 'wb') as write_f:
        reg = re.compile(r'https?://(w{3}\.)?\.?([\w\-\.]*)/?')
        writer = csv.writer(write_f)
        reader = csv.reader(read_f)
        domains = set()
        for line in reader:
            url = line[0]
            domain = re.match(reg, url)
            if domain:
                domains.add(domain.groups()[1])

        for domain in domains:
            writer.writerow([domain])

exit()
