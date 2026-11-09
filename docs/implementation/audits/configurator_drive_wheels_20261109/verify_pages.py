"""Render real canonical routes read-only; session history exists only in memory."""
from pathlib import Path
import os,sys,json,hashlib
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro'
settings.DATABASES['default']['OPTIONS']={'uri':True}
import django
django.setup()
from django.db import connection
connection.cursor().execute('pragma query_only=ON')
from django.test import RequestFactory
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser
from reference.models import VehicleDefinition
class Choices(HTMLParser):
    def __init__(self,html):self.choices=[];self.current=None;super().__init__();self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and a.get('class')=='configuration-choice':self.current={'href':a['href'],'text':''}
    def handle_data(self,data):
        if self.current is not None:self.current['text']+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.current is not None:self.choices.append(self.current);self.current=None
class InMemorySession(dict):
    pass

initial=hashlib.sha256((ROOT/'db.sqlite3').read_bytes()).hexdigest();reports=[]
for pk in [161,562,138,724,877]:
 r=VehicleDefinition.objects.select_related('generation').get(pk=pk);path=r.generation.get_absolute_url()
 for mode,params in [('year',{'year':r.model_year}),('trim',{'year':r.model_year,'trim':r.trim_name}),('exact',{'configuration':r.slug})]:
  request=RequestFactory().get(path,params);request.session=InMemorySession();request.user=AnonymousUser()
  route=resolve(path);response=route.func(request,**route.kwargs);response.render()
  assert response.status_code==200
  expected=response.context_data['configuration_browser_choices'];parsed=Choices(response.content.decode()).choices
  assert len(parsed)==len(expected)>0
  for label,vd in zip(parsed,expected):
   assert label['text']==vd.choice_label
   assert label['text'].split(' · ').count(vd.drivetrain)==1
   assert vd.slug in label['href']
  if mode=='exact':assert response.context_data['selected_config'].pk==pk
  reports.append({'PK':pk,'mode':mode,'path':request.get_full_path()+'#configurations','labels':parsed,'HTTP_status':200})
assert hashlib.sha256((ROOT/'db.sqlite3').read_bytes()).hexdigest()==initial
(Path(__file__).parent/'rendered_page_verification.json').write_text(json.dumps({'status':'passed','pages':reports,'live_database_sha256_unchanged':initial,'database_access':'read-only/query_only','session_history':'RequestFactory in-memory dict;no SessionMiddleware/no persistence'},indent=2)+'\n')
print('Rendered15 canonical configurator requests across Toyota,Volkswagen,Jeep;year/trim/exact links passed;database unchanged')
