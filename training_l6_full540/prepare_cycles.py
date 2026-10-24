from common import *
from build import build
s=(BASE/'engines/cellfirst.cpp').read_text()
needle='for(int a:seq){s=step(s,a);prefix.push_back(a);if(s.made>=K)'
replacement='for(int a:seq){int previousMade=s.made;s=step(s,a);prefix.push_back(a);if(s.made>previousMade&&s.made<K){recordPartialDiscovery(s,parent.parent,prefix);if(s.made>=2&&cycleTried.insert(mix(s.pose)^mix(s.made)).second)cycleCompletion(recover(parent.parent,prefix));}if(s.made>=K)'
assert needle in s;s=s.replace(needle,replacement,1)
(BASE/'engines/cellfirst_v2.cpp').write_text(s);build('cellfirst_v2.cpp')
