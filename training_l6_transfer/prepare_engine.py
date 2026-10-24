from common import *

source=(BASE/'engines/physics_base.cpp').read_text()
source=source.replace('int main(){','#include "transfer_operators.hpp"\nint main(){',1)
needle='for(U&p:referencePoses)cin>>p;'
assert needle in source
source=source.replace(needle,needle+'readTransferConfig();')
source=source.replace('\n expandedDepth=0;','\n for(auto&z:opStats)z=OpStat();winningOperator=-1;winningMask=0;expandedDepth=0;')
source=source.replace('if(MODE==11||MODE==12)pureSynthesis', 'if(MODE>=13)transferSearch(hint);else if(MODE==11||MODE==12)pureSynthesis')
last="cout<<'\\n'<<flush;"
prefix,suffix=source.rsplit(last,1)
extra="cout<<' '<<winningOperator<<' '<<winningMask;for(auto&s:opStats)cout<<' '<<s.attempts<<' '<<s.edges<<' '<<s.fullValid<<' '<<s.wins<<' '<<s.saved<<' '<<llround(s.seconds*1000000);"
source=prefix+extra+last+suffix
(BASE/'engines/transfer.cpp').write_text(source)
print('ENGINE_PREPARED')

