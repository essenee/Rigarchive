// Deterministic, dependency-free PNG production. Vehicle artwork is never regenerated.
const fs=require('node:fs'),zlib=require('node:zlib'),crypto=require('node:crypto');
const root=require('node:path').resolve(__dirname, '../..'), dest=root+'/static/images/homepage/';
function decode(file){const b=fs.readFileSync(file);let chunks=[],w,h,type;for(let i=8;i<b.length;){let n=b.readUInt32BE(i),t=b.toString('ascii',i+4,i+8),d=b.subarray(i+8,i+8+n);if(t==='IHDR'){w=d.readUInt32BE(0);h=d.readUInt32BE(4);type=d[9];if(d[8]!==8||d[12])throw Error('Unsupported PNG');}if(t==='IDAT')chunks.push(d);i+=n+12;}let channels=type===6?4:3,raw=zlib.inflateSync(Buffer.concat(chunks)),stride=w*channels,pixels=Buffer.alloc(w*h*4),previous=Buffer.alloc(stride),offset=0;for(let y=0;y<h;y++){let f=raw[offset++],row=Buffer.from(raw.subarray(offset,offset+stride));offset+=stride;for(let x=0;x<stride;x++){let a=x>=channels?row[x-channels]:0,b=previous[x],c=x>=channels?previous[x-channels]:0,p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);row[x]=(row[x]+(f===0?0:f===1?a:f===2?b:f===3?Math.floor((a+b)/2):pa<=pb&&pa<=pc?a:pb<=pc?b:c))&255;}for(let x=0;x<w;x++){let i=(y*w+x)*4,j=x*channels;pixels[i]=row[j];pixels[i+1]=row[j+1];pixels[i+2]=row[j+2];pixels[i+3]=channels===4?row[j+3]:255;}previous=row;}return {w,h,pixels};}
let table=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});function crc(b){let c=0xffffffff;for(let v of b)c=table[(c^v)&255]^(c>>>8);return (c^0xffffffff)>>>0;}
function chunk(t,d){let b=Buffer.alloc(d.length+12);b.writeUInt32BE(d.length);b.write(t,4);d.copy(b,8);b.writeUInt32BE(crc(b.subarray(4,d.length+8)),d.length+8);return b;}
function save(name,w,h,p){let hdr=Buffer.alloc(13);hdr.writeUInt32BE(w);hdr.writeUInt32BE(h,4);hdr[8]=8;hdr[9]=6;let raw=Buffer.alloc(h*(w*4+1));for(let y=0;y<h;y++)p.copy(raw,y*(w*4+1)+1,y*w*4,(y+1)*w*4);let out=Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',hdr),chunk('IDAT',zlib.deflateSync(raw,{level:9})),chunk('IEND',Buffer.alloc(0))]);fs.writeFileSync(dest+name,out);console.log(name,w,h,out.length,crypto.createHash('sha256').update(out).digest('hex'));}
function rand(x,y,s=1){let n=Math.imul(x+374761393,s+668265263)^Math.imul(y+1274126177,2246822519);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;}
/* Original extraction retained as a separate explicit production operation.
   Refinement builds never invoke it. */
function extractApprovedDiagram() {
// Pixel-exact diagram extraction. Only alpha outside the actual paper perimeter is changed.
let src=decode(root+'/docs/design/wireframes/homepage_hero_diagram_&background_approved.png');let w=502,h=514,p=Buffer.alloc(w*h*4);let x0=950,y0=146;
for(let y=0;y<h;y++)for(let x=0;x<w;x++){let i=(y*w+x)*4,j=((y+y0)*src.w+x+x0)*4;src.pixels.copy(p,i,j,j+4);let top=3+Math.max(0,2*Math.sin(x*.027)+Math.sin(x*.17));let bottom=507+x*.006+.4*Math.sin(x*.051);let left=2+Math.max(0,Math.sin(y*.04));let right=500-Math.max(0,Math.sin(y*.07));let edge=Math.min(y-top,bottom-y,x-left,right-x);p[i+3]=Math.round(255*Math.max(0,Math.min(1,edge)));}
save('4runner-diagram-approved-paper.png',w,h,p);

}

// Thin, nearly square photographic paper. Wear stays within the border band.
function buildPhotoPaper() {
    const w=1024,h=1024,p=Buffer.alloc(w*h*4);
    for(let y=0;y<h;y++) for(let x=0;x<w;x++) {
        const left=2.4+1.2*Math.sin(y*.017)+.65*Math.sin(y*.113)+rand(0,y,31)*.7;
        const right=1021.6-1.1*Math.sin(y*.021)-.7*Math.sin(y*.097)-rand(1,y,31)*.6;
        const top=2.5+1.1*Math.sin(x*.019)+.7*Math.sin(x*.131)+rand(x,0,47)*.6;
        const bottom=1021.5-.9*Math.sin(x*.023)-.8*Math.sin(x*.107)-rand(x,1,47)*.7;
        const edge=Math.min(x-left,right-x,y-top,bottom-y),band=Math.max(0,1-edge/25);
        const grain=(rand(x,y,17)-.5)*(2+band*8);
        const mottling=band*(Math.sin(x*.063+y*.029)+Math.sin(y*.079-x*.031))*1.5;
        const wear=Math.max(0,1-edge/7)*(2+rand(x,y,29)*4);
        const fiber=band>.3&&rand(x,y,37)>.96?-3:0;
        const value=Math.round(250+grain+mottling-wear-fiber),i=(y*w+x)*4;
        p[i]=p[i+1]=Math.max(235,Math.min(255,value));p[i+2]=Math.max(234,Math.min(254,value-1));
        p[i+3]=Math.round(Math.max(0,Math.min(1,edge/1.3))*255);
    }
    save('hero-photo-paper.png',w,h,p);
}

// Nine-slice photograph frame: straight square perimeter, transparent center, no shadow.
function buildReusablePhotoFrame() {
    const w=256,h=256,slice=32,p=Buffer.alloc(w*h*4);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
        const edge=Math.min(x,y,w-1-x,h-1-y),i=(y*w+x)*4;
        if(edge>=slice)continue;
        const grain=(rand(x,y,181)-.5)*2.5;
        const tone=(rand(Math.floor(x/8),Math.floor(y/8),191)-.5)*1.5;
        const wear=edge<2?(rand(x,y,193)*.65):0;
        const value=Math.round(250+grain+tone-wear);
        p[i]=p[i+1]=value;p[i+2]=value-1;p[i+3]=255;
    }
    save('hero-photo-frame.png',w,h,p);
}

// Earlier restrained terrain geometry, retained exactly for annotation placement.
function quietContourPaths(halfLevels=false) {
    const size=192,field=[];
    const smooth=t=>t*t*t*(t*(t*6-15)+10);
    function noise(x,y,n,seed) {
        x=(x%1+1)%1*n;y=(y%1+1)%1*n;
        const ix=Math.floor(x),iy=Math.floor(y),fx=smooth(x-ix),fy=smooth(y-iy),v=(a,b)=>rand(a%n,b%n,seed);
        return (v(ix,iy)*(1-fx)+v(ix+1,iy)*fx)*(1-fy)+(v(ix,iy+1)*(1-fx)+v(ix+1,iy+1)*fx)*fy;
    }
    for(let y=0;y<=size;y++) {
        field[y]=[];
        for(let x=0;x<=size;x++) {
            const u=x/size,v=y/size,a=u+.09*Math.sin(2*Math.PI*v)+.04*Math.sin(4*Math.PI*u),b=v+.07*Math.sin(2*Math.PI*u);
            field[y][x]=noise(a,b,3,7)*.65+noise(a,b,6,19)*.24+noise(a,b,12,41)*.085+noise(a,b,24,67)*.025;
        }
    }
    const paths=[],key=p=>p[0].toFixed(4)+','+p[1].toFixed(4);
    for(let level=1;level<47;level++) {
        const t=(level+(halfLevels?.5:0))/48,edges=[],adj=new Map();
        function add(a,b) {
            const index=edges.length;edges.push({a,b,used:false});
            for(const p of [a,b]) {const k=key(p);if(!adj.has(k))adj.set(k,[]);adj.get(k).push(index);}
        }
        for(let y=0;y<size;y++)for(let x=0;x<size;x++) {
            const val=[field[y][x],field[y][x+1],field[y+1][x+1],field[y+1][x]],pos=[[x,y],[x+1,y],[x+1,y+1],[x,y+1]],hits=[];
            for(let e=0;e<4;e++) {const n=(e+1)%4;if((val[e]<t)!==(val[n]<t)) {const q=(t-val[e])/(val[n]-val[e]);hits.push([(pos[e][0]+(pos[n][0]-pos[e][0])*q)*8,(pos[e][1]+(pos[n][1]-pos[e][1])*q)*8]);}}
            for(let e=0;e+1<hits.length;e+=2)add(hits[e],hits[e+1]);
        }
        for(const edge of edges) {
            if(edge.used)continue;
            let point=adj.get(key(edge.a)).length===1?edge.a:adj.get(key(edge.b)).length===1?edge.b:edge.a;
            const points=[point];
            while(true) {
                const next=adj.get(key(point)).find(i=>!edges[i].used);if(next===undefined)break;
                const e=edges[next];e.used=true;point=key(e.a)===key(point)?e.b:e.a;points.push(point);
            }
            const distances=[0];for(let n=1;n<points.length;n++)distances.push(distances[n-1]+Math.hypot(points[n][0]-points[n-1][0],points[n][1]-points[n-1][1]));
            if(distances.at(-1)>70)paths.push({points,distances,length:distances.at(-1)});
        }
    }
    return paths;
}
function pointOnContour(path,distance) {
    let n=1;while(n<path.distances.length-1&&path.distances[n]<distance)n++;
    const a=path.points[n-1],b=path.points[n],span=path.distances[n]-path.distances[n-1],q=span?(distance-path.distances[n-1])/span:0;
    return [a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q];
}
function quietAnnotations() {
    const paths=quietContourPaths(),labels=[];
    for(const [text,wanted] of [['6800',[500,656]],['7200',[1215,640]]]) {
        let best;
        for(const path of paths)for(let d=30;d<path.length-30;d+=8) {
            const p=pointOnContour(path,d),a=pointOnContour(path,d-20),b=pointOnContour(path,d+20);
            let angle=Math.atan2(b[1]-a[1],b[0]-a[0]);if(angle>Math.PI/2)angle-=Math.PI;if(angle< -Math.PI/2)angle+=Math.PI;
            if(Math.abs(angle)>1.2||p[0]<40||p[0]>1496||p[1]<40||p[1]>1496)continue;
            if(text==='6800'&&(p[1]<648||p[1]>665))continue;
            const bend=Math.hypot(p[0]-(a[0]+b[0])/2,p[1]-(a[1]+b[1])/2);
            const score=(p[0]-wanted[0])**2+(p[1]-wanted[1])**2+bend*bend*500;
            if(!best||score<best.score)best={text,x:p[0],y:p[1],angle,tangent:[a,b],score};
        }
        labels.push(best);
    }
    const dottedPaths=quietContourPaths(true),dots=[];
    for(const [index,wanted] of [[840,650],[1000,120],[130,1100]].entries()) {
        let best;
        for(const path of dottedPaths)for(let d=60;d<path.length-60;d+=12) {
            const p=pointOnContour(path,d),score=(p[0]-wanted[0])**2+(p[1]-wanted[1])**2;
            if(!best||score<best.score)best={path,d,score};
        }
        let center=best.d;
        // Keep each existing contour path; expose the first two arcs between paper surfaces.
        if(index<2) {
            let chosenScore=Infinity;
            for(let candidate=Math.max(48,best.d-180);candidate<=Math.min(best.path.length-48,best.d+180);candidate+=6) {
                let hidden=0;
                for(let d=candidate-48;d<=candidate+48;d+=6) {
                    const p=pointOnContour(best.path,d);
                    if(index===0?(p[1]<642||p[1]>740):(p[1]<103||p[1]>165))hidden++;
                }
                const score=(candidate-best.d)**2+hidden*10000;
                if(score<chosenScore){chosenScore=score;center=candidate;}
            }
        }
        const arc=[];for(let d=center-48;d<=center+48;d+=6)arc.push(pointOnContour(best.path,d));dots.push(arc);
    }
    return {labels,dots};
}
function buildTopographicMap() {
    const original=decode(dest+'topographic-subtle-original.png'),w=original.w,h=original.h,p=Buffer.alloc(w*h*4);
    // Remove only the old opaque paper ground. Preserve the earlier contour pixels.
    for(let i=0;i<p.length;i+=4) {
        p[i]=p[i+1]=p[i+2]=124;
        p[i+3]=Math.min(100,Math.round(Math.max(0,248-original.pixels[i]-1)*255/124));
    }
    const plan=quietAnnotations();
    function ink(x,y,alpha) {
        if(x<0||x>=w||y<0||y>=h)return;const i=(y*w+x)*4+3;
        p[i]=Math.max(p[i],Math.min(80,Math.round(255*(alpha+p[i]/255*(1-alpha)))));
    }
    for(const arc of plan.dots)for(const [x,y] of arc)for(let yy=Math.floor(y)-1;yy<=y+1;yy++)for(let xx=Math.floor(x)-1;xx<=x+1;xx++) {
        const d=Math.hypot(x-xx-.5,y-yy-.5);if(d<1)ink(xx,yy,Math.min(.2,(1-d)*.32));
    }
    const glyphs={
        '0':[[[1,0],[4,0],[5,1],[5,8],[4,9],[1,9],[0,8],[0,1],[1,0]]],
        '2':[[[0,1],[1,0],[4,0],[5,1],[5,3],[0,8],[0,9],[5,9]]],
        '6':[[[5,1],[4,0],[1,0],[0,2],[0,8],[1,9],[4,9],[5,8],[5,5],[4,4],[1,4],[0,5]]],
        '7':[[[0,0],[5,0],[1,9]]],
        '8':[[[1,0],[4,0],[5,1],[5,3],[4,4],[1,4],[0,3],[0,1],[1,0]],[[1,4],[4,4],[5,5],[5,8],[4,9],[1,9],[0,8],[0,5],[1,4]]]
    };
    for(const label of plan.labels) {
        const scale=.78,c=Math.cos(label.angle),s=Math.sin(label.angle),convert=(x,y)=>[label.x+scale*(x*c-y*s),label.y+scale*(x*s+y*c)];
        for(let y=Math.floor(label.y)-25;y<label.y+25;y++)for(let x=Math.floor(label.x)-25;x<label.x+25;x++) {
            const dx=x-label.x,dy=y-label.y;
            if(Math.abs(dx*c+dy*s)<19*scale&&Math.abs(-dx*s+dy*c)<6.5*scale)p[(y*w+x)*4+3]=0;
        }
        for(let ch=0;ch<4;ch++)for(const stroke of glyphs[label.text[ch]])for(let n=0;n<stroke.length-1;n++) {
            const a=convert(-14.5+ch*8+stroke[n][0],stroke[n][1]-4.5),b=convert(-14.5+ch*8+stroke[n+1][0],stroke[n+1][1]-4.5),steps=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])*3));
            for(let k=0;k<=steps;k++) {
                const x=a[0]+(b[0]-a[0])*k/steps,y=a[1]+(b[1]-a[1])*k/steps;
                for(let yy=Math.floor(y)-1;yy<=y+1;yy++)for(let xx=Math.floor(x)-1;xx<=x+1;xx++) {const d=Math.hypot(x-xx-.5,y-yy-.5);if(d<.8*scale)ink(xx,yy,(.8*scale-d)*.23);}
            }
        }
    }
    save('topographic-approved-neutral.png',w,h,p);
    console.log('Contour-aligned quiet labels:',plan.labels.map(({text,x,y,angle,tangent})=>({text,x,y,angle,tangent})));
}
/* Local pixel repair: retain native arrow/glyph pixels, repair only their old ink footprint
   with matching nearby paper samples, and leave all vehicle/other-dimension pixels intact. */
function correctApprovedDiagramLength() {
const source=decode(dest+'4runner-diagram-approved-paper.png');
if(source.w!==502||source.h!==514)throw Error('Unexpected diagram dimensions; correction stopped');
const pixels=Buffer.from(source.pixels),w=source.w,h=source.h;
const rectangles=[[191,32,212,42],[214,23,279,49],[280,31,453,46],[448,27,454,66]];
const inside=(x,y)=>rectangles.some(([a,b,c,d])=>x>=a&&x<c&&y>=b&&y<d);
const mask=new Uint8Array(w*h),seeds=[];
for(let y=23;y<66;y++)for(let x=191;x<454;x++)if(inside(x,y)&&source.pixels[(y*w+x)*4]<210)seeds.push([x,y]);
for(const [x,y] of seeds)for(let yy=y-2;yy<=y+2;yy++)for(let xx=x-2;xx<=x+2;xx++)if(inside(xx,yy))mask[yy*w+xx]=1;
const background=new Map();
function paper(x,y) {
 const key=y*w+x;if(background.has(key))return background.get(key);
 const guide=[];
 for(let dy=-5;dy<=5;dy++)for(let dx=-5;dx<=5;dx++) {
  const i=((y+dy)*w+x+dx)*4;
  if(!mask[(y+dy)*w+x+dx]&&source.pixels[i]>=225)guide.push([dx,dy,i]);
 }
 let best=Infinity,donor;
 for(let yy=Math.max(7,y-30);yy<=Math.min(89,y+30);yy++)for(let xx=Math.max(20,x-30);xx<=Math.min(494,x+30);xx++) {
  if(mask[yy*w+xx]||source.pixels[(yy*w+xx)*4]<225)continue;
  let score=((xx-x)**2+(yy-y)**2)*.012,valid=0;
  for(const [dx,dy,i] of guide) {
   const j=((yy+dy)*w+xx+dx)*4;
   if(mask[(yy+dy)*w+xx+dx]||source.pixels[j]<225){score=Infinity;break;}
   for(let c=0;c<3;c++)score+=(source.pixels[i+c]-source.pixels[j+c])**2/guide.length;
   valid++;
   if(score>best)break;
  }
  if(valid===guide.length&&score<best){best=score;donor=(yy*w+xx)*4;}
 }
 if(donor===undefined)throw Error('No clean paper donor at '+x+','+y);
 const value=Array.from(source.pixels.subarray(donor,donor+3));background.set(key,value);return value;
}
for(let y=23;y<66;y++)for(let x=191;x<454;x++)if(mask[y*w+x]){const b=paper(x,y),i=(y*w+x)*4;for(let c=0;c<3;c++)pixels[i+c]=b[c];}
const cleanPaper=Buffer.from(pixels);
function transfer(x,y,xx,yy) {
 if(!mask[y*w+x])return;const src=(y*w+x)*4,dst=(yy*w+xx)*4,b=paper(x,y);
 for(let c=0;c<3;c++){const contrast=Math.max(0,b[c]-source.pixels[src+c]);pixels[dst+c]=Math.min(pixels[dst+c],Math.max(0,Math.round(cleanPaper[dst+c]-contrast)));}
}
// Same handwritten glyphs, moved as a unit; visual ink bounds center at x226.
for(let y=23;y<49;y++)for(let x=214;x<279;x++)transfer(x,y,x-20,y);
// Retain the native right-hand line ink and its slight paper-perspective slope.
for(let y=32;y<45;y++)for(let x=281;x<=424;x++)transfer(x,y,x-20,y);
// Native arrowhead, 36px left. No resampling or regeneration.
for(let y=32;y<46;y++)for(let x=439;x<450;x++)transfer(x,y,x-36,y);
// Center a short witness on y39.5 using the original witness's own cap pixels.
for(let y=32;y<=47;y++){const sy=y<40?28+(y-32):28+(47-y);for(let x=449;x<453;x++)transfer(x,sy,x-36,y);}

    save('4runner-diagram-approved-paper-length-corrected.png',w,h,pixels);
}

// This refinement changes only the contour asset by default.
if(require.main===module) {
    if(process.argv.includes('--extract-diagram'))extractApprovedDiagram();
    else if(process.argv.includes('--photo-paper'))buildPhotoPaper();
    else if(process.argv.includes('--photo-frame'))buildReusablePhotoFrame();
    else if(process.argv.includes('--correct-length'))correctApprovedDiagramLength();
    else buildTopographicMap();
}
module.exports={decode,quietAnnotations};
