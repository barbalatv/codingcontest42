#define main unused_endgame_main
#include "../endgame.cpp"
#undef main
int main(){
    auto cc=load("cases.txt");auto& in=cc.at(0);Cover cv;cv.build(in,in.nrel);
    vector<St> full(in.prog.size()+1);setInit(full[0],in);for(size_t t=0;t<in.prog.size();t++){full[t+1]=full[t];apply(in,full[t+1],in.prog[t].data());}
    for(auto [W,width]:vector<pair<int,int>>{{4,300},{4,600},{8,300}}){
        vector<St> known(full.end()-W-1,full.end());SearchStats st;st.witness=&known;st.deadline=chrono::steady_clock::now()+chrono::seconds(5);
        // Positive witness at the ORIGINAL horizon W; this is not a shorter plan.
        auto p=endgameSearch(in,cv,known[0],in.K,W,width,&st);
        cout<<"{\"case\":133,\"original_horizon\":"<<W<<",\"width\":"<<width<<",\"expanded\":"<<st.expanded<<",\"lookahead_expanded\":"<<st.lookaheadExpanded<<",\"depth\":"<<st.depth<<",\"timeout\":"<<(st.timeout?"true":"false")<<",\"known_state_rank_before_width_cut\":[";
        for(size_t i=0;i<st.witnessRank.size();i++){if(i)cout<<',';cout<<st.witnessRank[i];}
        cout<<"],\"terminal_found\":"<<(!p.empty()?"true":"false")<<",\"saved\":0}\n"<<flush;
    }
}
