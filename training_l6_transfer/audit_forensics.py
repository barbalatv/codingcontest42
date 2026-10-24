from forensics import *
import shutil

def births(c,p):
    sim=Sim(c);cells=geometry(c[0])[1];tt=detailed(c,p);events=[];copy=0
    for row in tt:
        bits=int(row['created_target'])
        for j,xy in enumerate(cells):
            if bits>>j&1:
                emitters=[e for e,ray in enumerate(row['rays']) if int(ray)>>j&1]
                assert len(emitters)==2
                events.append(dict(copy=copy,cell=xy,tick=row['tick'],pair=emitters))
        if row['acceptance']:copy+=1
    return events,tt

def main():
    frozen=BASE/'operators/catalog_primary_frozen.json'
    if not frozen.exists():shutil.copyfile(BASE/'transformation_catalog.json',frozen)
    all_events=[json.loads(f.read_text()) for f in (BASE/'transformations').glob('*.json')]
    pure=[e for e in all_events if e['method'].startswith('B') or e['method']=='pass1_B'];results=[];hybrid=[]
    for e in all_events:
        ds=e['dataset'];idx=e['case'];c=cases(ds)[idx-1];a=[tuple(z) for z in e['before_program']];b=[tuple(z) for z in e['after_program']]
        if e['method'].startswith('C') or e['method']=='pass1_C':
            hybrid.append(dict(dataset=ds,case=idx,method=e['method'],saved=e['saved'],matched_variants=e['matched_variants'],setup_saved=e['before_metrics']['first_copy']-e['after_metrics']['first_copy'],later_saved=e['saved']-(e['before_metrics']['first_copy']-e['after_metrics']['first_copy']),taxonomy=e['taxonomy'],mechanism_scope='exact transformed segment matches are evidence; whole causal contribution of Pure vs history is not reconstructed from final path alone'))
        if e not in pure:continue
        ba,ta=births(c,a);bb,tb=births(c,b);pairs_a=collections.defaultdict(set);pairs_b=collections.defaultdict(set);first_a={};first_b={}
        for events,pairs,first in [(ba,pairs_a,first_a),(bb,pairs_b,first_b)]:
            for v in events:
                key=tuple(v['cell']);pairs[key].add(tuple(v['pair']))
                if v['copy']==0:first.setdefault(key,v['tick'])
        changed_pairs=[list(xy) for xy in sorted(c[1]) if pairs_a[xy]!=pairs_b[xy]]
        comparable=flipped=ties=0
        for j,xy in enumerate(sorted(c[1])):
            for zw in sorted(c[1])[j+1:]:
                x=first_a[xy]-first_a[zw];y=first_b[xy]-first_b[zw]
                if x==0 or y==0:ties+=1
                else:comparable+=1;flipped+=x*y<0
        source=None;matched=False;flags=None
        folders={'pass1_B':'pass1','B_macro_cycles':'pure_cycles','B_continuation4':'continuation4'}
        if e['method'] in folders:
            source=OLD/'experiments'/folders[e['method']]/f'{ds}_{idx}.json';row=next(r for r in json.loads(source.read_text())['rows'] if r['strategy']=='B');matched=[tuple(z) for z in row['program']]==b
            flags={k:row.get(k,False) for k in ['incumbent_structure_used','incumbent_trajectory_used','state_hints_used','incumbent_transitions_used']};assert matched and not any(flags.values())
        else:
            source=OLD/'cellfirst/pure_graph'/f'{ds}_{idx}.json';matched=[tuple(z) for z in json.loads(source.read_text())['program']]==b;record=json.loads((OLD/'experiments/pure_graph'/f'{ds}_{idx}.json').read_text());flags={k:record[k] for k in ['incumbent_structure_used','incumbent_trajectory_used','state_hints_used','incumbent_transitions_used']};assert matched and not any(flags.values())
        results.append(dict(dataset=ds,case=idx,method=e['method'],saved=e['saved'],radius=c[0],K=c[2],target_cells=len(c[1]),source=str(source.relative_to(REPO)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),saved_program_matches_source=matched,recorded_provenance_flags=flags,provenance_scope='audited saved record and matching program; original timed generation not rerun',ray_pair_changed_cells=changed_pairs,first_creation_reversed_pairs=flipped,first_creation_comparable_pairs=comparable,first_creation_tied_pairs=ties,first_creation_order_changed=flipped>0,acceptance_poses_changed=[(r['positions'],r['active']) for r in ta if r['acceptance']]!=[(r['positions'],r['active']) for r in tb if r['acceptance']],before_metrics=e['before_metrics'],after_metrics=e['after_metrics'],before_births=ba,after_births=bb))
    exact_support=collections.defaultdict(set)
    for e in all_events:
        for v in e['matched_variants']:exact_support[v['variant']].add((e['dataset'],e['case']))
    atomic_json(BASE/'experiments/pure_forensic_audit.json',dict(unique_cases=len({(r['dataset'],r['case']) for r in results}),events=len(results),saved=sum(r['saved'] for r in results),records=results))
    atomic_json(BASE/'experiments/hybrid_forensic_audit.json',dict(events=len(hybrid),saved=sum(e['saved'] for e in hybrid),records=hybrid))
    atomic_json(BASE/'experiments/operator_support_audit.json',dict(exact_variant_support={str(k):sorted(v) for k,v in exact_support.items()},warning='initial operator known_successes lists were broad source examples; only exact_variant_support establishes fitted rewrite matches. Prospective successes are recorded separately; phase/scheduling are hypotheses until verified on recipients.'))
    print('FORENSIC_AUDIT_PASS','Pure',len(results),'events',len({(r['dataset'],r['case']) for r in results}),'cases; Hybrid saved',sum(e['saved'] for e in hybrid),flush=True)

if __name__=='__main__':main()
