"""Read-only canonical/presentation audit; never writes to the operational DB."""
from pathlib import Path
import ast,collections,csv,hashlib,json,os,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro'
settings.DATABASES['default']['OPTIONS']={'uri':True}
import django
django.setup()
from django.db import connection
connection.cursor().execute('pragma query_only=ON')
from reference.models import VehicleDefinition,ImportExecutionReceipt,GenerationCorrespondenceRevision
from reference.services import _label_configuration_choices
from reference.powertrain import engine_label
HERE=Path(__file__).resolve().parent
START='764389b986ec37a58a6b3b7d579409fea382f314'
def sha(path):return 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
initial=sha(ROOT/'db.sqlite3')
old=ast.parse(subprocess.check_output(['git','show',START+':reference/services.py'],text=True))
fn=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='_label_configuration_choices')
space={'Counter':collections.Counter,'engine_label':engine_label};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewed-baseline>','exec'),space)
before=space['_label_configuration_choices']
records=list(VehicleDefinition.objects.select_related('generation__vehicle_model__manufacturer').order_by('generation_id','model_year','trim_name','drivetrain','engine_name','market','slug'))
assert len(records)==934
created=collections.defaultdict(list)
for r in ImportExecutionReceipt.objects.exclude(created_vehicle_definition_id=None):created[r.created_vehicle_definition_id].append(r)
def visible(v):return all(o.is_active for o in [v,v.generation,v.generation.vehicle_model,v.generation.vehicle_model.manufacturer])
visible_records=[r for r in records if visible(r)]
years=collections.defaultdict(list);trims=collections.defaultdict(list)
for r in visible_records:years[r.generation_id,r.model_year].append(r);trims[r.generation_id,r.model_year,r.trim_name].append(r)
labels={}
for kind,groups in [('year',years),('trim',trims)]:
 for rs in groups.values():
  for r in before(rs):labels.setdefault(r.pk,{})[kind+'_before']=r.choice_label
  for r in _label_configuration_choices(rs):labels[r.pk][kind+'_after']=r.choice_label
rows=[];grouped={};token=re.compile(r'\b(?:2WD|4WD|AWD|FWD|RWD|2[xX]4|4[xX]4)\b',re.I)
for r in records:
 model=r.generation.vehicle_model;maker=model.manufacturer
 receipts=created[r.pk];targets=set();resolution_targets=set();with_resolution=0
 for receipt in receipts:
  if receipt.target_drivetrain:targets.add(receipt.target_drivetrain)
  snapshot=receipt.resolution_snapshot_json or {}
  if snapshot:with_resolution+=1
  value=snapshot.get('generation_resolution',{}).get('fields',{}).get('drivetrain')
  if value:resolution_targets.add(value)
 conflicts=sorted((targets|resolution_targets)-{r.drivetrain})
 item={'PK':r.pk,'UUID':str(r.uuid),'slug':r.slug,'manufacturer':maker.name,'model':model.name,'generation_PK':r.generation_id,'generation':r.generation.name,'year':r.model_year,'trim':r.trim_name,'engine':r.engine_name,'market':r.market,'canonical_drivetrain':r.drivetrain,'canonical_field':'VehicleDefinition.drivetrain','canonical_value_recognized':r.drivetrain in ('2WD','4WD','AWD'),'configurator_eligible':visible(r),'inactive_record':not r.is_active,'front_rear_axle':'not represented by canonical enum; not inferred','operating_modes':'no dedicated canonical field; not inferred','indirect_only':False,'trim_drive_tokens':token.findall(r.trim_name),'engine_drive_tokens':token.findall(r.engine_name),'notes_drive_tokens':token.findall(r.notes),'created_receipt_PKs':[x.pk for x in receipts],'receipt_target_drivetrains':sorted(targets),'resolution_field_drivetrains':sorted(resolution_targets),'receipt_snapshot_conflict':conflicts,'receipt_resolution_snapshots_present':with_resolution,'source_review_limit':'Compared applicable retained receipt target/resolution fields only; raw documents not re-adjudicated',**labels.get(r.pk,{})}
 for kind in ['year','trim']:
  text=item.get(kind+'_before');item[kind+'_before_drive_visible']=bool(text and r.drivetrain in [x.strip() for x in text.split('·')])
  text=item.get(kind+'_after');item[kind+'_after_drive_visible']=bool(text and r.drivetrain in [x.strip() for x in text.split('·')])
 item['exact_configuration_url']=r.generation.get_absolute_url()+'?configuration='+r.slug+'#configurations'
 rows.append(item)
 key=(maker.name,model.name,r.generation_id,r.generation.name,r.model_year)
 g=grouped.setdefault(key,{'manufacturer':maker.name,'model':model.name,'generation_PK':r.generation_id,'generation':r.generation.name,'year':r.model_year,'records':0,'eligible':0,'drivetrains':collections.Counter(),'before_year_hidden':0,'before_trim_hidden':0,'after_hidden':0,'PKs':[],'receipt_conflict_PKs':[]})
 g['records']+=1;g['eligible']+=int(visible(r));g['drivetrains'][r.drivetrain]+=1;g['PKs'].append(r.pk)
 if visible(r):
  g['before_year_hidden']+=int(not item['year_before_drive_visible']);g['before_trim_hidden']+=int(not item['trim_before_drive_visible']);g['after_hidden']+=int(not item['trim_after_drive_visible'])
 if conflicts:g['receipt_conflict_PKs'].append(r.pk)
summary={'records':len(rows),'eligible':len(visible_records),'inactive_records':sum(not r.is_active for r in records),'inactive_ancestry_only':sum(r.is_active and not visible(r) for r in records),'canonical_drivetrains':dict(collections.Counter(r.drivetrain for r in records)),'manufacturer_counts':dict(collections.Counter(r.generation.vehicle_model.manufacturer.name for r in records)),'missing_or_unsupported_canonical':sum(not r['canonical_value_recognized'] for r in rows),'before_year_hidden':sum(r['configurator_eligible'] and not r['year_before_drive_visible'] for r in rows),'before_trim_hidden':sum(r['configurator_eligible'] and not r['trim_before_drive_visible'] for r in rows),'after_year_hidden':sum(r['configurator_eligible'] and not r['year_after_drive_visible'] for r in rows),'after_trim_hidden':sum(r['configurator_eligible'] and not r['trim_after_drive_visible'] for r in rows),'receipt_snapshot_conflicts':[r['PK'] for r in rows if r['receipt_snapshot_conflict']],'no_created_receipt':[r['PK'] for r in rows if not r['created_receipt_PKs']],'created_receipt_but_no_resolution_snapshot':[r['PK'] for r in rows if r['created_receipt_PKs'] and not r['receipt_resolution_snapshots_present']],'trim_or_engine_drive_token_PKs':[r['PK'] for r in rows if r['trim_drive_tokens'] or r['engine_drive_tokens']],'canonical_axle_or_mode_field_available':False,'raw_source_ambiguity':'Not exhaustively re-adjudicated; missing structured snapshots and unverified manufacturer semantics remain provenance limitations, not inferred classifications.','database_sha256_before':initial,'baseline_commit':START,'generation_correspondences':GenerationCorrespondenceRevision.objects.count(),'receipts':ImportExecutionReceipt.objects.count()}
assert summary['generation_correspondences']==159 and summary['receipts']==3148
assert summary['after_trim_hidden']==summary['after_year_hidden']==0
summary['database_sha256_after']=sha(ROOT/'db.sqlite3');assert initial==summary['database_sha256_after']
for name,data in [('all_configurations.json',rows),('grouped_audit.json',list(grouped.values())),('summary.json',summary)]:
 (HERE/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
with (HERE/'all_configurations.csv').open('w',newline='') as f:
 fields=['PK','manufacturer','model','generation','year','trim','canonical_drivetrain','configurator_eligible','year_before','year_after','trim_before','trim_after','exact_configuration_url']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in summary.items() if not isinstance(v,list)},indent=2))
print('receipt conflicts',len(summary['receipt_snapshot_conflicts']),'no created receipt',len(summary['no_created_receipt']),'created receipts without resolution',len(summary['created_receipt_but_no_resolution_snapshot']))
