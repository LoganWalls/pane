import graphlab as gl
import os
import json
sf = None
types = [str, int, dict, dict, list, list, str, str, list, str, str, str]
evals = [0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0]
keys = ['body', 'broken_link', 'byline', 'headline', 'keywords', 'multimedia', 'news_desk', 'section_name', 'paper_links', 'pub_date', 'type_of_material', 'web_url']
for fname in os.listdir('nyt_processed'):
    path = os.path.join('nyt_processed', fname)
    if os.path.isfile(path) and fname.endswith('.json'):
        with open(path, 'rb') as f:
            j = json.load(f)
        if 'response' in j and j['response']['docs']:
            # if not keys:
            #     keys = j['response']['docs'][0].keys()
            #     types = [type(j['response']['docs'][0][k]) for k in keys]
            cur_sf = gl.SFrame({k: gl.SArray([x.get(k, None) for x in j['response']['docs']], dtype=str) for t, k in zip(types, keys)})
            # cur_sf = gl.SFrame({'body': gl.SArray([x['body'] for x in j['docs']], dtype=str), 'link_ids': gl.SArray([x['link_ids'] for x in j['docs']], dtype=list)})
            for k, t, e in zip(keys, types, evals):
                if e:
                    cur_sf[k] = cur_sf[k].apply(lambda x: eval(x) if eval(x) else None, dtype=t)
                else:
                    cur_sf[k] = cur_sf[k].astype(t)

        if len(cur_sf):
            print cur_sf
            if not sf:
                sf = cur_sf
            else:
                sf = sf.append(cur_sf)
sf.save('nyt_links')
