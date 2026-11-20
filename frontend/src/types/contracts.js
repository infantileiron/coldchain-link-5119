/** @typedef {{id:number,code:string,route:string,zone:string,driver:string}} Shipment */
/** @typedef {{id:number,state:'queued'|'running'|'done'|'failed',result:object}} Study */
/** @typedef {{id:number,name:string,state:'inspecting'|'closed',n:number,n1:number,n2:number,frame:Array<{shipment_id:number,code:string,route:string}>,orders:Inspection[]}} Survey */
/** @typedef {{id:number,survey_id:number,shipment_id:number,code:string,route:string,phase:1|2,probability:number,loss:number|null,state:'pending'|'returned'}} Inspection */
