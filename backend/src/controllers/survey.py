from fastapi import HTTPException
from src.models.entities import Survey,Inspection,Sample
from src.services.business import dump
def ensure_survey(s,i):
 row=s.get(Survey,i)
 if not row:raise HTTPException(404,'抽查批次不存在')
 return row
def latest_loss(s,shipment_id):
 row=s.query(Sample).filter(Sample.shipment_id==shipment_id,Sample.loss.isnot(None)).order_by(Sample.id.desc()).first()
 return row.loss if row else None
def survey_detail(s,r):
 d=dump(r)
 orders=s.query(Inspection).filter_by(survey_id=r.id).order_by(Inspection.id).all()
 d['orders']=[dump(o) for o in orders]
 d['total']=len(orders);d['returned']=sum(1 for o in orders if o.state=='returned');d['pending']=d['total']-d['returned']
 routes={}
 for f in (r.frame or []):routes[f['route']]=routes.get(f['route'],0)+1
 d['frame_routes']=[{'route':k,'count':v} for k,v in sorted(routes.items())]
 return d
