from __future__ import annotations
import hashlib, json, os, re
from datetime import datetime, timedelta, timezone
from urllib import parse, request
from xml.etree import ElementTree
from pathlib import Path

UA = "Aibros-Discovery/0.2"

def get_json(url, headers=None):
    req=request.Request(url,headers={"User-Agent":UA,**(headers or {})})
    with request.urlopen(req,timeout=45) as r:
        return json.loads(r.read())

def identity(title):
    text=re.sub(r"[^a-z0-9]+"," ",title.lower()).strip()
    return hashlib.sha256(text.encode()).hexdigest()[:20]

def score(item):
    text=(item["title"]+" "+item.get("summary","")).lower()
    practical=min(sum(x in text for x in ("video","image","voice","agent","automation","code","local","open source","free","workflow"))/4,1)
    demo=1 if any(x in text for x in ("video","image","voice","demo","app")) else .45
    return round(25*item["freshness"]+20*practical+15*item["free_signal"]+15*item["popularity"]+10*demo+10+5*(1 if any(x in text for x in ("india","tamil","hindi","indic")) else .2),2)

def github():
    since=(datetime.now(timezone.utc)-timedelta(days=10)).date().isoformat()
    q=f'(ai OR llm OR agent OR "text-to-video") created:>={since} stars:>20'
    url="https://api.github.com/search/repositories?"+parse.urlencode({"q":q,"sort":"stars","order":"desc","per_page":30})
    headers={"Accept":"application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"): headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    out=[]
    for x in get_json(url,headers).get("items",[]):
        out.append({"source":x["owner"]["login"],"source_type":"github_repository","title":x["full_name"],"url":x["html_url"],"summary":x.get("description") or "New AI repository","published_at":x["created_at"],"primary_source":True,"popularity":min(x["stargazers_count"]/500,1),"free_signal":.85,"freshness":.9})
    return out

def huggingface():
    headers={"Authorization":"Bearer "+os.environ["HF_TOKEN"]} if os.getenv("HF_TOKEN") else {}
    out=[]
    for kind,url in (("huggingface_model","https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=30&full=true"),("huggingface_space","https://huggingface.co/api/spaces?sort=trendingScore&direction=-1&limit=30&full=true")):
        for x in get_json(url,headers):
            name=x.get("id","")
            out.append({"source":name.split("/")[0],"source_type":kind,"title":name,"url":"https://huggingface.co/"+("spaces/" if kind.endswith("space") else "")+name,"summary":"Trending "+kind.replace("_"," "),"published_at":x.get("lastModified",""),"primary_source":True,"popularity":min(x.get("likes",0)/1000,1),"free_signal":.9 if kind.endswith("space") else .8,"freshness":.7})
    return out

def arxiv():
    query="cat:cs.AI OR cat:cs.CL OR cat:cs.CV"
    url="https://export.arxiv.org/api/query?"+parse.urlencode({"search_query":query,"start":0,"max_results":30,"sortBy":"submittedDate","sortOrder":"descending"})
    req=request.Request(url,headers={"User-Agent":UA})
    with request.urlopen(req,timeout=45) as r: root=ElementTree.fromstring(r.read())
    ns={"a":"http://www.w3.org/2005/Atom"}
    out=[]
    for e in root.findall("a:entry",ns):
        title=" ".join((e.findtext("a:title",default="",namespaces=ns)).split())
        summary=" ".join((e.findtext("a:summary",default="",namespaces=ns)).split())
        link=e.findtext("a:id",default="",namespaces=ns)
        out.append({"source":"arXiv","source_type":"research_paper","title":title,"url":link,"summary":summary[:700],"published_at":e.findtext("a:published",default="",namespaces=ns),"primary_source":True,"popularity":.1,"free_signal":.35,"freshness":.7})
    return out

def discover(output):
    all_items=[]; errors=[]
    for name,fn in (("github",github),("huggingface",huggingface),("arxiv",arxiv)):
        try: all_items.extend(fn())
        except Exception as e: errors.append(f"{name}: {type(e).__name__}: {e}")
    best={}
    for x in all_items:
        x["identity"]=identity(x["title"]); x["score"]=score(x)
        if x["identity"] not in best or x["score"]>best[x["identity"]]["score"]: best[x["identity"]]=x
    ranked=sorted(best.values(),key=lambda x:x["score"],reverse=True)[:50]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output,"w",encoding="utf-8") as f: json.dump({"generated_at":datetime.now(timezone.utc).isoformat(),"errors":errors,"candidates":ranked},f,ensure_ascii=False,indent=2)
    print(f"Saved {len(ranked)} candidates")
    for x in ranked[:10]: print(x["score"],x["source_type"],x["title"])

if __name__=="__main__":
    import sys; discover(sys.argv[1] if len(sys.argv)>1 else "discovery_candidates.json")
