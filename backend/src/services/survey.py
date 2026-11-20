import hashlib
ALGORITHM_VERSION='ht-twophase-1.0'
def draw(ids,k,seed,tag):
 # 以创建批次时提交的种子做哈希排序，取前 k 件：名单可复算，且与已回传货损无关。
 # 同一 tag 下不同名额的抽选互为前缀，并发补抽时由唯一约束保证只生效一份名单。
 return sorted(ids,key=lambda i:hashlib.sha256(f'{seed}:{tag}:{i}'.encode()).hexdigest())[:k]
def combined_pi(n1,n,n2,k):
 # 重点线路合计入样概率 = 头批概率 + 未中头批时的补抽概率；非重点线路只有头批概率 n1/n。
 return n1/n+(1-n1/n)*(n2/k if k else 0)
def estimate(orders,n):
 total=sum(o.loss/o.probability for o in orders)
 losses=[o.loss for o in orders]
 return {'version':ALGORITHM_VERSION,'n':len(orders),'N':n,'estimate_total':round(total,4),'estimate_mean':round(total/n,4),'sample_mean':round(sum(losses)/len(losses),4),'formula':'平均货损估值 = Σ(每件货损 ÷ 两次抽查合计入样概率) ÷ 全批件数','pi_note':'重点线路入样概率 = 头批概率 + 未中头批时的补抽概率；补抽名单由创建批次时提交的种子决定，不读取已回传货损。'}
