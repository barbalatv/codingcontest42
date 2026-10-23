from pathlib import Path
B=Path('training_medium_breakthrough/engines');s=Path('phase2_regress.cpp').read_text();s=s.replace('uint64_t regressResultPose=0;','uint64_t regressResultPose=0;\nvector<uint64_t> regressionTestEnds;')
s=s.replace('  vector<Regression> roots;','  if(!regressionTestEnds.empty())endCandidates=regressionTestEnds;\n  vector<Regression> roots;')
a=s.index('  for(int w=0;w<W;w++){\n    if((three.b[w]&target.b[w])',s.index('for(uint64_t candidatePose:endCandidates)'))
b=s.index('  int rootRemaining=',a)
old=s[a:b];new='''  bool validRoot=true;
  for(int w=0;w<W;w++){
    if((three.b[w]&target.b[w])|((two.b[w]&~three.b[w])&forbid.b[w])){validRoot=false;break;}
    root.ones.b[w]=target.b[w]&~two.b[w];root.zeros.b[w]=forbid.b[w]&~three.b[w];
  }
  if(!validRoot){
#ifdef LEGACY_ROOT_BUG
    return false;
#else
    continue;
#endif
  }
'''
s=s[:a]+new+s[b:];(B/'regress_fixed.cpp').write_text(s);(B/'regress_old.cpp').write_text('#define LEGACY_ROOT_BUG\n#include "regress_fixed.cpp"\n')
# Test hook is used only when mode 99 is requested by the regression fixture.
p=B/'phase2_beam.cpp';c=p.read_text().replace('    regressWindow=variant>=60;', '    regressionTestEnds.clear();if(variant==99){uint64_t a,b;cin>>a>>b;regressionTestEnds={a,b};variant=0;}\n    regressWindow=variant>=60;');c=c.replace('extern Bits regressOnes,regressZeros;', 'extern Bits regressOnes,regressZeros;\nextern vector<uint64_t> regressionTestEnds;');p.write_text(c)
# Reuse original geometry; custom search has its own main and exact simulation.
c=(B/'ultra_core.cpp').read_text();start=c.index('    vector<pair<int,int>> cells;',c.index('int main()'));stop=c.index('    State state;',start)
geometry=c[start:stop]
(B/'geometry.hpp').write_text('#define main unused_ultra_main\n#include "ultra_core.cpp"\n#undef main\nvoid init_geometry(const vector<string>& rows,int variant){L=6*R;\n'+geometry+'}\n')
