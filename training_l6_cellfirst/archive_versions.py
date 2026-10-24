from common import *
# Restore the early source snapshots from the retained Stage-C snapshot by
# reversing the later changes. Final sources are kept independently as well.
s=(BASE/'engines/cellfirst_c.cpp').read_text()
s=s.replace('array<array<array<Bits,2>,256>,6> nearRay;\n','').replace('unordered_set<U>cycleTried;\n','')
lines=s.splitlines(True);s=''.join(line for line in lines if not line.startswith('void cycleCompletion(') and not line.startswith(' for(int e=0;e<6;e++)for(int a=0;a<2;a++)for(int p=0;p<L;p++){int byte=p+a*128;'))
s=s.replace('cycleTried.clear();','')
a=s.index('struct Triple {');b=s.index('void forward(){',a)
old='''struct Triple {U pose=0;Effect v;int action=0;};
array<Triple,64> triples(U pose,int first){array<Triple,64>out{};for(int code=0;code<64;code++){auto&z=out[code];for(int j=0;j<3;j++){int e=first+j,op=(code>>(2*j))&3,b=nextByte[e][(pose>>(8*e))&255][op];z.pose|=U(b)<<(8*e);z.action|=op<<(2*e);auto&r=ray[e][b];for(int w=0;w<W;w++){z.v.three.b[w]|=z.v.two.b[w]&r.b[w];z.v.two.b[w]|=z.v.one.b[w]&r.b[w];z.v.one.b[w]|=r.b[w];}}}return out;}
void commandExpand(const Node&parent,int t,vector<vector<Node>>&layers,int cap,bool exhaustive){auto aa=triples(parent.s.pose,0),bb=triples(parent.s.pose,3);for(auto&a:aa)for(auto&b:bb){if(!exhaustive&&((rng()&7)!=0))continue;if((++evaluations&4095)==0&&Clock::now()>=deadline)return;Effect v;for(int w=0;w<W;w++){v.one.b[w]=a.v.one.b[w]|b.v.one.b[w];v.two.b[w]=a.v.two.b[w]|b.v.two.b[w]|(a.v.one.b[w]&b.v.one.b[w]);v.three.b[w]=a.v.three.b[w]|b.v.three.b[w]|(a.v.two.b[w]&b.v.one.b[w])|(a.v.one.b[w]&b.v.two.b[w]);}State s=parent.s;s.pose=a.pose|b.pose;bool accepted=applyEffect(s,v);vector<int>seq={a.action|b.action};if(s.made>=K){if(accepted&&s.made==K&&(goalPose==UINT64_MAX||s.pose==goalPose))save(recover(parent.parent,seq));continue;}Node n;n.s=s;n.parent=parent.parent;n.seq=seq;n.score=stateScore(s,SEED);keep(layers[t+1],move(n),cap);}}
'''
s=s[:a]+old+s[b:]
(BASE/'engines/cellfirst_stage_b.cpp').write_text(s)
a=s.index('struct Evaluation{');b=s.index('int main(){',a);stagea=s[:a]+s[b:]
stagea=stagea.replace('vector<int> nearProgram;int nearCost;\n','').replace('nearProgram.clear();nearCost=1000000000;','')
stagea=''.join(line for line in stagea.splitlines(True) if not line.startswith('   // Long-range master') and not line.startswith('   // lets a large pattern') and not line.startswith('   if(MODE==1||MODE==3){int D='))
stagea=stagea.replace('if(MODE==7||MODE==8)assignmentSearch(hint,MODE==7);else if(MODE>=4)bidirectional();else forward();','if(MODE>=4)bidirectional();else forward();')
stagea=stagea.replace("cout<<' '<<nearCost<<' '<<nearProgram.size();for(int a:nearProgram)cout<<' '<<a;",'')
(BASE/'engines/cellfirst_stage_a.cpp').write_text(stagea)
print('Early source snapshots reconstructed; validate native code hashes after compiling.')
