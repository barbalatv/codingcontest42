from common import *
from build import build
def main():
    # Start from the original source, not a previously patched claim.
    core=(REPO/'phase2_beam.cpp').read_text()
    core=core.replace('extern Bits regressOnes,regressZeros;','extern Bits regressOnes,regressZeros;\nextern vector<uint64_t> regressionTestEnds;')
    core=core.replace('    regressWindow=variant>=60;','    regressionTestEnds.clear();if(variant==99){uint64_t a,b;cin>>a>>b;regressionTestEnds={a,b};variant=0;}\n    regressWindow=variant>=60;')
    (BASE/'engines/phase2_beam.cpp').write_text(core)
    source=(REPO/'phase2_regress.cpp').read_text().replace('uint64_t regressResultPose=0;','uint64_t regressResultPose=0;\nvector<uint64_t> regressionTestEnds;')
    source=source.replace('  vector<Regression> roots;','  if(!regressionTestEnds.empty())endCandidates=regressionTestEnds;\n  vector<Regression> roots;')
    source=source.replace('  for(int w=0;w<W;w++){\n    if((three.b[w]&target.b[w])|((two.b[w]&~three.b[w])&forbid.b[w]))return false;', '  bool validRoot=true;\n  for(int w=0;w<W;w++){\n    if((three.b[w]&target.b[w])|((two.b[w]&~three.b[w])&forbid.b[w])){validRoot=false;break;}')
    source=source.replace('  int rootRemaining=evaluate(root,one,0);', '  if(!validRoot){\n#ifdef LEGACY_ROOT_BUG\n    return false;\n#else\n    continue;\n#endif\n  }\n  int rootRemaining=evaluate(root,one,0);')
    assert 'if(!validRoot)' in source
    (BASE/'engines/regress_fixed.cpp').write_text(source)
    (BASE/'engines/regress_old.cpp').write_text('#define LEGACY_ROOT_BUG\n#include "regress_fixed.cpp"\n')
    build('regress_fixed.cpp');build('regress_old.cpp')
if __name__=='__main__':main()
