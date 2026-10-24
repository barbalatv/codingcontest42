#define main unused_rtds_main
#include "../rtds.cpp"
#undef main
int main(){
    Inst in{};in.r=1;in.L=6;in.K=2;in.nrel=1;in.target.w[0]=1;in.rays.assign(6,{});in.rays[0][0].w[0]=in.rays[0][1].w[0]=1;
    St start{};Covers cv;cv.build(in,1);St goal=start;array<u8,6>a{};a[0]=a[1]=3;apply(in,goal,a.data());
    auto free=beamWindow(in,cv,start,goal,true,false,1,32);assert(free.size()==1);St endpoint=start;apply(in,endpoint,free[0].data());
    auto exact=beamWindow(in,cv,start,endpoint,true,true,1,32);assert(exact.size()==1);St result=start;apply(in,result,exact[0].data());assert(sameState(result,endpoint));
    St bad=endpoint;bad.pos[5]=4;assert(!sameState(bad,endpoint));assert(beamWindow(in,cv,start,bad,true,true,1,32).empty());
    bad=endpoint;bad.active^=32;assert(!sameState(bad,endpoint));bad=endpoint;bad.count++;assert(!sameState(bad,endpoint));bad=endpoint;bad.matter.w[0]=1;assert(!sameState(bad,endpoint));
    // Matching endpoints imply matching immutable suffix transitions.
    array<u8,6> noop{};apply(in,result,noop.data());apply(in,endpoint,noop.data());assert(sameState(result,endpoint));
    cout<<"{\"rtds_suffix\":\"PASS\",\"components\":4,\"free_endpoint_can_differ\":true,\"exact_search_rejects_wrong_pose\":true}\n";
}
