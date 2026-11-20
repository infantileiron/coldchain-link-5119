import os,json,secrets
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Shipment,Sample,Study,Recommendation,Audit,Survey,Inspection
from src.schemas.business import Login,ShipmentInput,SampleInput,StudyInput,RecommendationInput,SurveyInput,SupplementInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services.survey import draw,combined_pi,estimate
from src.controllers.business import ensure_shipment,ensure_study,study_rows
from src.controllers.survey import ensure_survey,latest_loss,survey_detail
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/shipments')
def ships(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Shipment).all()]
@router.post('/shipments')
def ship(data:ShipmentInput,u=Depends(editor),s=Depends(db)):
 r=Shipment(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'班次编号重复')
 audit(s,u,'创建班次 '+r.code);return dump(r)
@router.get('/samples')
def samples(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Sample).all()]
@router.post('/samples')
def sample(data:SampleInput,u=Depends(editor),s=Depends(db)):
 ensure_shipment(s,data.shipment_id);r=Sample(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'样本编号重复')
 audit(s,u,'录入样本 '+r.code);return dump(r)
@router.get('/studies')
def studies(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Study).order_by(Study.id.desc()).all()]
@router.post('/studies')
def study(data:StudyInput,u=Depends(editor),s=Depends(db)):
 rows=study_rows(s,data.zone);r=Study(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('studies',r.id)
 except redis.RedisError:
  r.state='failed';r.error='队列暂不可用，请重新创建研究';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交研究 '+str(r.id));return dump(r)
@router.get('/studies/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_study(s,i))
@router.get('/studies/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_study(s,i)
 if r.state!='done':raise HTTPException(409,'研究未成功完成')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="coldchain-link-{i}.json"'})
@router.get('/recommendations')
def recs(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Recommendation).order_by(Recommendation.id.desc()).all()]
@router.post('/recommendations')
def rec(data:RecommendationInput,u=Depends(editor),s=Depends(db)):
 if ensure_study(s,data.study_id).state!='done':raise HTTPException(409,'仅已完成研究可以起草建议')
 r=Recommendation(**data.model_dump());s.add(r);s.commit();audit(s,u,'起草建议 '+str(r.id));return dump(r)
@router.post('/recommendations/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=s.get(Recommendation,i)
 if not r:raise HTTPException(404,'建议不存在')
 r.status='approved';s.commit();audit(s,u,'签核建议 '+str(i));return dump(r)
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]

@router.get('/surveys')
def surveys(u=Depends(current),s=Depends(db)):
 out=[]
 for r in s.query(Survey).order_by(Survey.id.desc()).all():
  d=dump(r);d.pop('frame');orders=s.query(Inspection).filter_by(survey_id=r.id).all()
  d['total']=len(orders);d['returned']=sum(1 for o in orders if o.state=='returned');out.append(d)
 return out
@router.post('/surveys')
def survey(data:SurveyInput,u=Depends(editor),s=Depends(db)):
 if data.request_key:
  old=s.query(Survey).filter_by(request_key=data.request_key).first()
  if old:return survey_detail(s,old)
 frame=[{'shipment_id':r.id,'code':r.code,'route':r.route} for r in s.query(Shipment).filter_by(zone='冷藏').order_by(Shipment.id).all()]
 if not frame:raise HTTPException(409,'冷藏班次为空，无法抽查')
 if data.n1>len(frame):raise HTTPException(422,f'头批样本量超过全批 {len(frame)} 件')
 r=Survey(name=data.name,request_key=data.request_key or None,zone='冷藏',seed=secrets.token_hex(8),frame=frame,n=len(frame),n1=data.n1,key_routes=None,state='inspecting')
 s.add(r);s.flush()
 by_id={f['shipment_id']:f for f in frame}
 for sid in draw([f['shipment_id'] for f in frame],data.n1,r.seed,'p1'):
  f=by_id[sid];s.add(Inspection(survey_id=r.id,shipment_id=sid,code=f['code'],route=f['route'],phase=1,probability=data.n1/len(frame)))
 try:s.commit()
 except IntegrityError:
  s.rollback()
  if data.request_key:
   old=s.query(Survey).filter_by(request_key=data.request_key).first()
   if old:return survey_detail(s,old)
  raise HTTPException(409,'派单冲突，请重试')
 audit(s,u,f'发起抽查 {r.id} 头批{data.n1}件');return survey_detail(s,r)
@router.get('/surveys/{i}')
def survey_one(i:int,u=Depends(current),s=Depends(db)):return survey_detail(s,ensure_survey(s,i))
@router.post('/surveys/{i}/supplement')
def supplement(i:int,data:SupplementInput,u=Depends(editor),s=Depends(db)):
 r=ensure_survey(s,i)
 if r.state!='inspecting':raise HTTPException(409,'批次已结案，不能补抽')
 if r.key_routes:return survey_detail(s,r)
 known={f['route'] for f in r.frame};unknown=[x for x in data.key_routes if x not in known]
 if unknown:raise HTTPException(422,'线路不在冻结名单内：'+'、'.join(unknown))
 sampled={o.shipment_id for o in s.query(Inspection).filter_by(survey_id=r.id).all()}
 pool={f['shipment_id']:f for f in r.frame if f['route'] in data.key_routes and f['shipment_id'] not in sampled}
 if not pool:raise HTTPException(409,'重点线路的货已全部入样，无可补抽')
 n2=min(data.quota,len(pool));pi=combined_pi(r.n1,r.n,n2,len(pool))
 for sid in draw(list(pool),n2,r.seed,'p2'):
  f=pool[sid];s.add(Inspection(survey_id=r.id,shipment_id=sid,code=f['code'],route=f['route'],phase=2,probability=pi))
 for o in s.query(Inspection).filter_by(survey_id=r.id,phase=1).all():
  if o.route in data.key_routes:o.probability=pi
 r.key_routes=data.key_routes;r.n2_quota=data.quota;r.n2=n2;r.pool=len(pool)
 try:s.commit()
 except IntegrityError:s.rollback();return survey_detail(s,ensure_survey(s,i))
 audit(s,u,f'补抽 {r.id} 重点线路{n2}件');return survey_detail(s,r)
@router.post('/surveys/{i}/collect')
def collect(i:int,u=Depends(editor),s=Depends(db)):
 r=ensure_survey(s,i)
 if r.state!='inspecting':raise HTTPException(409,'批次已结案')
 filled=0
 for o in s.query(Inspection).filter_by(survey_id=r.id,state='pending').all():
  loss=latest_loss(s,o.shipment_id)
  if loss is not None:o.loss=loss;o.state='returned';filled+=1
 s.commit();d=survey_detail(s,r)
 audit(s,u,f'收回验损 {r.id} 本次回填{filled}件 已回{d["returned"]}/{d["total"]}');return d
@router.post('/surveys/{i}/close')
def close(i:int,u=Depends(editor),s=Depends(db)):
 r=ensure_survey(s,i)
 if r.state=='closed':return survey_detail(s,r)
 orders=s.query(Inspection).filter_by(survey_id=r.id).all()
 pending=[o for o in orders if o.state!='returned']
 if pending:raise HTTPException(409,f'仍有 {len(pending)} 件缺报，先不结案；补录样本货损后重新收回')
 r.result={**estimate(orders,r.n),'n1':r.n1,'n2':r.n2,'key_routes':r.key_routes or []}
 r.state='closed';s.commit()
 audit(s,u,f'结案估值 {r.id} 平均货损{r.result["estimate_mean"]}%');return survey_detail(s,r)

@router.put('/shipments/{i}')
def edit_ship(i:int,data:ShipmentInput,u=Depends(editor),s=Depends(db)):
 row=s.get(Shipment,i)
 if not row:raise HTTPException(404,'班次不存在')
 for k,v in data.model_dump().items():setattr(row,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'班次编号重复')
 audit(s,u,'修改班次 '+str(i));return dump(row)
@router.put('/samples/{i}')
def edit_sample(i:int,data:SampleInput,u=Depends(editor),s=Depends(db)):
 row=s.get(Sample,i)
 if not row:raise HTTPException(404,'样本不存在')
 ensure_shipment(s,data.shipment_id)
 for k,v in data.model_dump().items():setattr(row,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'样本编号重复')
 audit(s,u,'修改样本 '+str(i));return dump(row)
