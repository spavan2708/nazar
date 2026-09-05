"""Optional local encoder + binary head fine-tuning. Dry run is the default."""
import argparse,json,time,random,math,resource
from pathlib import Path
from ml.dataset import DATA,load_split,assert_training_separation,sha
from ml.embeddings import EMBEDDING_MODEL_PATH,MODEL_NAME


def to_device(features, device):
    import torch
    return {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in features.items()}


def run(args):
    if not 1 <= args.max_seconds <= 1800 or not math.isfinite(args.learning_rate) or not 1e-6 <= args.learning_rate <= 1e-3:
        raise ValueError("Use a 1–1800 second budget and a learning rate between 1e-6 and 1e-3")
    import torch
    estimate=dict(model=MODEL_NAME,local_weights_mib=round(sum(p.stat().st_size for p in EMBEDDING_MODEL_PATH.rglob('*') if p.is_file())/2**20),
        expected_ram='3–5 GiB estimate, not measured',disk='up to 1 GiB for one best encoder checkpoint',
        time='CPU: tens of minutes possible; bounded by --max-seconds, checked between batches',
        mps_available=torch.backends.mps.is_available(),python_supported=True,download=False,
        optimizer='AdamW',learning_rate=args.learning_rate,batch_size=args.batch_size,epochs=args.epochs,seed=42)
    print(json.dumps(estimate,indent=2))
    if not args.train:return
    if args.output is None:raise ValueError('--output is required for training')
    if args.output.exists():raise FileExistsError('Use a fresh checkpoint directory')
    from sentence_transformers import SentenceTransformer
    if args.dataset == 'hardening-v2':
        from ml.hardening_data import load as dataset_load, DATA as dataset_dir
    else:
        dataset_load, dataset_dir = load_split, DATA
    train,validation=dataset_load('train'),dataset_load('validation');assert_training_separation(train,validation)
    random.seed(42);torch.manual_seed(42);torch.set_num_threads(4)
    if args.device=='mps' and not torch.backends.mps.is_available():
        raise ValueError('Requested MPS acceleration is unavailable')
    device='mps' if args.device=='mps' and torch.backends.mps.is_available() else 'cpu'
    model=SentenceTransformer(str(EMBEDDING_MODEL_PATH),local_files_only=True,device=device)
    head=torch.nn.Linear(model.get_sentence_embedding_dimension(),1).to(device)
    optimizer=torch.optim.AdamW(list(model.parameters())+list(head.parameters()),lr=args.learning_rate)
    lossfn=torch.nn.BCEWithLogitsLoss();best=float('inf');stale=0;history=[];steps=0;start=time.monotonic()
    args.output.mkdir(parents=True)
    def batch(rows):
        features=to_device(model.tokenize([r['text'] for r in rows]),device)
        logits=head(model(features)['sentence_embedding']).squeeze(-1)
        y=torch.tensor([r['label']=='scam' for r in rows],device=device,dtype=torch.float32)
        return logits,y
    for epoch in range(args.epochs):
        model.train();head.train();order=list(train);random.Random(42+epoch).shuffle(order)
        for i in range(0,len(order),args.batch_size):
            if time.monotonic()-start>args.max_seconds:break
            logits,y=batch(order[i:i+args.batch_size]);loss=lossfn(logits,y)
            optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),1);optimizer.step();steps+=1
        model.eval();head.eval();losses=[]
        with torch.no_grad():
            for i in range(0,len(validation),args.batch_size):
                logits,y=batch(validation[i:i+args.batch_size]);losses.append((float(lossfn(logits,y)),len(y)))
        val=sum(v*n for v,n in losses)/sum(n for _,n in losses);history.append(dict(epoch=epoch+1,validation_loss=val))
        print(json.dumps(history[-1]), flush=True)
        if val<best:
            best=val;stale=0;model.save(str(args.output/'encoder'));torch.save(head.state_dict(),args.output/'head.pt');best_epoch=epoch+1
        else:stale+=1
        if stale>=2 or time.monotonic()-start>args.max_seconds:break
    (args.output/'metadata.json').write_text(json.dumps(dict(resource_estimate=estimate,architecture='MiniLM mean pooling + linear binary head',
        model_version=args.output.name,training_samples=len(train),training_steps=steps,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        dataset_version=args.dataset,dataset_manifest_sha256=sha(dataset_dir/'manifest.json'),history=history,best_epoch=best_epoch,elapsed_seconds=time.monotonic()-start,
        early_stopping_patience=2,device=device,production=False,calibrated=False,test_accessed=False),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--train',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--epochs',type=int,choices=range(1,6),default=3);p.add_argument('--batch-size',type=int,choices=(2,4,8),default=4)
    p.add_argument('--learning-rate',type=float,default=2e-5);p.add_argument('--max-seconds',type=int,default=300)
    p.add_argument('--dataset',choices=('hardening-1','hardening-v2'),default='hardening-1')
    p.add_argument('--device',choices=('cpu','mps'),default='cpu');run(p.parse_args())
