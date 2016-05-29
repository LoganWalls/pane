import graphlab as gl
import os
import json
# types = [str, int, dict, dict, list, list, str, str, list, str, str, str]
# evals = [0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0]
# keys = ['body', 'broken_link', 'byline', 'headline', 'keywords', 'multimedia', 'news_desk', 'section_name', 'paper_links', 'pub_date', 'type_of_material', 'web_url']

def combine(row):
    if row['DOI'] and row['ID_TYPE']:
        return row['DOI'] + [row['ID_TYPE']]
    elif row['DOI'] and not row['ID_TYPE']:
        return row['DOI']
    elif row['ID_TYPE'] and not row['DOI']:
        return [row['ID_TYPE']]
    else:
        return None

d = []
for fname in os.listdir('old_data/nyt_processed_urls/'):
    path = os.path.join('old_data/nyt_processed_urls/', fname)
    if os.path.isfile(path) and fname.endswith('.json'):
        with open(path, 'rb') as f:
            j = json.load(f)
        if j:
            d.append(j)

sf = gl.SFrame(d).unpack('X1', column_name_prefix='')
sf.rename({'0':'link_id', '1':'link_url', '2':'response'})
sf = sf.unpack('response', column_name_prefix='')
sf['ids'] = sf['ids'].apply(lambda x: {i[0]:i[1] for i in x})
sf = sf.unpack('ids', column_name_prefix='')
sf['DOI'] = sf.apply(combine)
del sf['ID_TYPE']
sf = sf.stack('DOI', 'DOI').stack('PUBMED','PUBMED')
sf['link_id'] = sf['link_id'].astype(int)
sf = sf.sort('link_id')
sf.save('nyt_link_data')