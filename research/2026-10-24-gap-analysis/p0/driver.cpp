#define main unused_endgame_main
#ifdef LEGACY
#include "legacy_compat.cpp"
#else
#include "../endgame.cpp"
#endif
#undef main
static void output(const vector<array<u8,6>>& p) {
    cout<<'[';for(size_t i=0;i<p.size();i++){if(i)cout<<',';int code=0;for(int e=0;e<6;e++)code|=p[i][e]<<(2*e);cout<<code;}cout<<']';
}
#ifndef LEGACY
static void synthetic() {
    Inst in{};in.r=1;in.L=6;in.K=1;in.nrel=2;in.target.w[0]=1;in.rays.assign(6,{});
    in.rays[0][0].w[0]=in.rays[0][1].w[0]=1;
    St start{};start.active=3;Cover cv;cv.build(in,2);array<u8,6> a{};
    assert(allActions().size()==4096);vector<int>codes;
    for(auto& q:allActions()){int code=0;for(int e=0;e<6;e++){assert(q[e]<4);code|=q[e]<<(2*e);}codes.push_back(code);}
    sort(codes.begin(),codes.end());for(int i=0;i<4096;i++)assert(codes[i]==i);
    assert(canFinishInOne(in,start,1,&a));assert((a==array<u8,6>{}));
    SearchStats stats;auto p=endgameSearch(in,cv,start,1,1,2,&stats);
    assert(p.size()==1&&p[0]==a&&stats.terminals==1&&stats.bound==0);
    St accepted=start;apply(in,accepted,a.data());assert(accepted.count==1&&pc(accepted.matter)==0);
    assert(remainingLowerBound(in,cv,accepted,1)==0);
    assert(!canFinishInOne(in,accepted,1));assert(endgameSearch(in,cv,accepted,1,1,2).empty());
    St early=start;apply(in,early,a.data());auto off=a;off[0]=off[1]=3;apply(in,early,off.data());assert(early.count==1&&!finalTransition(accepted,early,1));
    St extra=accepted;apply(in,extra,a.data());assert(extra.count==2&&!finalTransition(accepted,extra,1));
    assert(!finalTransition(start,start,1));assert(!finalTransition(start,accepted,2));
    Inst dirty=in;dirty.forbid.w[0]=2;dirty.rays[0][0].w[0]=dirty.rays[0][1].w[0]=3;
    St blocked=start;apply(dirty,blocked,a.data());assert(blocked.count==0&&covers(blocked.matter,dirty.target)&&common(blocked.matter,dirty.forbid));
    assert(!canFinishInOne(dirty,start,1));
    Node x{},y{},better{};x.st=start;x.key=10;x.par=8;y=x;y.st.pos[5]=1;better=x;better.key=2;better.par=3;
    vector<Node> dup={x,y,better};deduplicate(dup);assert(dup.size()==2);
    auto it=find_if(dup.begin(),dup.end(),[&](auto& n){return sameState(n.st,start);});assert(it!=dup.end()&&it->key==2&&it->par==3);
    // Two different paths (wait/move ordering) meet; verify reconstructed actions.
    in.rays.assign(6,{});in.rays[2][0].w[0]=in.rays[2][1].w[0]=1;start.pos[1]=2;cv.build(in,2);
    for(int ticks:{2,3}){SearchStats s;auto q=endgameSearch(in,cv,start,1,ticks,16,&s);assert(q.size()==size_t(ticks));St st=start;for(int t=0;t<ticks;t++){int old=st.count;apply(in,st,q[t].data());assert(st.count==(t==ticks-1?1:0));if(t==ticks-1)assert(old==0);}assert(s.reconstructed==1);}
    cout<<"{\"synthetic\":\"PASS\",\"actions\":4096,\"negative_predicates\":6,\"dedup_best_parent\":true,\"multi_depth_reconstruction\":true}\n";
}
#endif
int main(int argc,char** argv) {
    auto cases=load("cases.txt");assert(cases.size()==12);
    string mode=argc>1?argv[1]:"regression";
    if(mode=="regression") {
#ifndef LEGACY
        synthetic();
#endif
        for(int i=0;i<int(cases.size());i++) {
            const auto& in=cases[i];assert(validate(in,in.prog));St s{};setInit(s,in);
            for(int t=0;t<int(in.prog.size())-1;t++)apply(in,s,in.prog[t].data());
            St last=s;apply(in,last,in.prog.back().data());assert(s.count==in.K-1&&last.count==in.K);
            Cover cv;cv.build(in,in.nrel);
#ifndef LEGACY
            St cursor{};setInit(cursor,in);for(size_t tick=0;tick<=in.prog.size();tick++) {if(cursor.count==in.K-1)assert(lowerBound(in,cv,cursor)<=int(in.prog.size()-tick));if(tick==in.prog.size())assert(remainingLowerBound(in,cv,cursor,in.K)==0);else apply(in,cursor,in.prog[tick].data());}
#endif
            array<u8,6>a{};bool finish=canFinishInOne(in,s,in.K,&a);
            auto q=endgameSearch(in,cv,s,in.K,1,300);
#ifdef LEGACY
            assert(!finish&&q.empty());
#else
            assert(finish&&q.size()==1);St t=s;apply(in,t,q[0].data());assert(finalTransition(s,t,in.K));assert(remainingLowerBound(in,cv,t,in.K)==0);
#endif
            auto full=in.prog;if(!q.empty())full.back()=q[0];assert(validate(in,full));
            cout<<"{\"case\":"<<i<<",\"can_finish\":"<<(finish?"true":"false")<<",\"found\":"<<q.size()<<",\"program\":";output(full);cout<<"}\n";
        }
        return 0;
    }
#ifndef LEGACY
    assert(mode=="pilot"&&argc==7);int ci=atoi(argv[2]),lo=atoi(argv[3]),hi=atoi(argv[4]),width=atoi(argv[5]),ms=atoi(argv[6]);const auto& in=cases.at(ci);
    vector<St> states(in.prog.size()+1);setInit(states[0],in);for(size_t t=0;t<in.prog.size();t++){states[t+1]=states[t];apply(in,states[t+1],in.prog[t].data());}
    Cover cv;cv.build(in,in.nrel);
    for(int W=lo;W<=hi;W++) {
        if(W>int(in.prog.size()))continue;SearchStats s;auto begin=chrono::steady_clock::now();auto cpu=clock();s.deadline=begin+chrono::milliseconds(ms);
        auto q=endgameSearch(in,cv,states[in.prog.size()-W],in.K,W-1,width,&s);vector<array<u8,6>> full;
        if(!q.empty()){full.assign(in.prog.begin(),in.prog.end()-W);full.insert(full.end(),q.begin(),q.end());}
        bool valid=!full.empty()&&validate(in,full);
        cout<<"{\"case\":"<<ci<<",\"W\":"<<W<<",\"width\":"<<width<<",\"expanded\":"<<s.expanded<<",\"lookahead_expanded\":"<<s.lookaheadExpanded<<",\"pruned_early\":"<<s.early<<",\"pruned_excess\":"<<s.excess<<",\"pruned_no_final_accept\":"<<s.noAccept<<",\"pruned_lb\":"<<s.bound<<",\"duplicates\":"<<s.duplicates<<",\"beam_truncated\":"<<s.truncated<<",\"terminal_transitions\":"<<s.terminals<<",\"terminal_depth\":"<<s.terminalDepth<<",\"depth\":"<<s.depth<<",\"reconstructed\":"<<s.reconstructed<<",\"timeout\":"<<(s.timeout?"true":"false")<<",\"invalid_start\":"<<(s.invalidStart?"true":"false")<<",\"cpp_valid\":"<<(valid?"true":"false")<<",\"cpu_seconds\":"<<double(clock()-cpu)/CLOCKS_PER_SEC<<",\"wall_seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-begin).count()<<",\"program\":";output(full);cout<<",\"retained\":[";for(size_t i=0;i<s.retained.size();i++){if(i)cout<<',';cout<<s.retained[i];}cout<<"],\"best_missing\":[";for(size_t i=0;i<s.bestMissing.size();i++){if(i)cout<<',';cout<<s.bestMissing[i];}cout<<"]}\n"<<flush;
    }
#endif
}
