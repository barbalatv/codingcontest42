#define main unused_ultra_main
#include "ultra_core.cpp"
#undef main
void init_geometry(const vector<string>& rows,int variant){L=6*R;
    vector<pair<int,int>> cells;vector<vector<int>> index(2*R+1,vector<int>(4*R+1,-1));
    for(int y=1;y<2*R;y++)for(int x=0;x<=4*R;x++)if(rows[y][x]=='O'||rows[y][x]=='M'){
      index[y][x]=(int)cells.size();cells.push_back({y,x});
    }
    W=((int)cells.size()+63)/64;target=Bits();forbid=Bits();hardTarget=Bits();randomTarget=Bits();NT=0;
    int dy[6]={0,1,1,0,-1,-1},dx[6]={2,1,-1,-2,-1,1};
    for(int k=0;k<(int)cells.size();k++){
      auto[y,x]=cells[k];if(rows[y][x]=='M'){target.b[k/64]|=1ULL<<(k%64);NT++;}
      else for(int i=0;i<6;i++){
        int yy=y+dy[i],xx=x+dx[i];
        if(yy>=0&&yy<=2*R&&xx>=0&&xx<=4*R&&rows[yy][xx]=='M')forbid.b[k/64]|=1ULL<<(k%64);
      }
    }
    for(int k=0;k<(int)cells.size();k++)if((target.b[k/64]>>(k%64))&1){
      auto[y,x]=cells[k];
      for(int i=0;i<6;i++){
        int yy=y+dy[i],xx=x+dx[i];
        if(yy>=0&&yy<=2*R&&xx>=0&&xx<=4*R){int j=index[yy][xx];
          if(j>=0&&((forbid.b[j/64]>>(j%64))&1))hardTarget.b[k/64]|=1ULL<<(k%64);
        }
      }
      if(mix(k+uint64_t(variant)*31337)&1)randomTarget.b[k/64]|=1ULL<<(k%64);
    }
    rays.assign(L,{});pair<int,int> corners[6]={{R,0},{2*R,R},{2*R,3*R},{R,4*R},{0,3*R},{0,R}};
    for(int side=0;side<6;side++)for(int j=0;j<R;j++){
      auto[y,x]=corners[side];auto[yy,xx]=corners[(side+1)%6];y+=j*(yy-y)/R;x+=j*(xx-x)/R;
      int p=side*R+j;
      for(int i=0;i<6;i++){
        int ny=y+dy[i],nx=x+dx[i];
        while(ny>=0&&ny<=2*R&&nx>=0&&nx<=4*R){
          int k=index[ny][nx];if(k>=0)rays[p][i].b[k/64]|=(1ULL<<(k%64))&(target.b[k/64]|forbid.b[k/64]);
          ny+=dy[i];nx+=dx[i];
        }
      }
    }
    for(int i=0;i<6;i++)for(int v=0;v<256;v++)for(int h=0;h<4;h++)nearMask[i][v][h]=Bits();
    for(int i=0;i<6;i++)for(int p=0;p<L;p++)for(int active=0;active<2;active++)for(int q=0;q<L;q++){
      int dist=min((p-q+L)%L,(q-p+L)%L)+(active?0:1);
      for(int h=0;h<4;h++)if(dist<=h+1)for(int w=0;w<W;w++)nearMask[i][p+128*active][h].b[w]|=rays[q][i].b[w];
    }
}
