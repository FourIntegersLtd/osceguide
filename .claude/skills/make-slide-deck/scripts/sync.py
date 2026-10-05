import json,sys
snap,dst=sys.argv[1],sys.argv[2]
c=json.load(open(snap))['content']; deck=json.load(open(dst))
# Decks fact-checked by hand (no Clinical Buddy) have no facts review: sync the slides, keep their refs.
facts=(c.get('review') or {}).get('facts')
claims=facts['claims'] if facts else []
src={}; refs=[]; slide_refs={}
for cl in claims:
    if cl.get('decision')=='dismissed': continue
    for e in cl['evidence']:
        if e.get('verdict') not in ('supported','supports','confirmed') or not e.get('source'): continue
        key=e['source']
        if key not in src:
            src[key]=f"R{len(src)+1}"
            r={"id":src[key],"title":e['source']}
            if e['kind']=='guideline': r["document"]=e['source']
            else: r["url"]=e.get('url')
            r["citations"]=[]; refs.append(r)
        r=next(x for x in refs if x['id']==src[key])
        cit={"claim":cl['claim']}
        if e.get('page') is not None: cit["page"]=e['page']
        if e.get('url') and e['kind']=='web': cit["url"]=e['url']
        if cit not in r['citations']: r['citations'].append(cit)
        slide_refs.setdefault(cl['slide'],[]).append(src[key])
assert len(deck['slides'])==len(c['slides'])
for i,(ds,cs) in enumerate(zip(deck['slides'],c['slides']),1):
    for k in ('title','bullets','highlights','source_notes','explanation'):
        if k in cs: ds[k]=cs[k]
    if facts: ds['refs']=sorted(set(slide_refs.get(i,[])),key=lambda x:int(x[1:]))
if facts: deck['references']=refs
json.dump(deck,open(dst,'w'),indent=2,ensure_ascii=False)
print(dst,*((len(refs),'refs',sum(len(r['citations']) for r in refs),'citations') if facts else ('refs kept (fact-checked by hand)',)))
