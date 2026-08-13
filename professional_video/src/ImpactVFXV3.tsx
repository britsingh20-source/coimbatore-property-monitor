import React from 'react';
import {AbsoluteFill,Audio,Img,OffthreadVideo,Sequence,staticFile} from 'remotion';
import type {PropertyVideoProps} from './types';
import {PriceImpactV2,BuiltUpImpactV2,FacingImpactV2,RoadImpactV2,TrustImpactV2} from './ImpactVFXV2';

const font='Noto Sans Tamil, Noto Sans, Arial, sans-serif';
const gold='#ffbd2e',cyan='#5ce7ff',cream='#fff8eb',navy='#030914',green='#24d990';
const source=(p:PropertyVideoProps,k:string)=>{const src=p.sceneMedia?.[k]?.[0]||p.representativeVideos?.[0]||p.images?.[0]||'';return{src,video:/\.(mp4|mov|webm)$/i.test(src)}};
const fact=(p:PropertyVideoProps,k:string,f='')=>p.facts.find(x=>x.label.toLowerCase().includes(k))?.value||f;
const Media:React.FC<{src:string;video:boolean}>=({src,video})=>video?<OffthreadVideo src={staticFile(src)} muted style={{width:'100%',height:'100%',objectFit:'cover',transform:'scale(1.11)'}}/>:<Img src={staticFile(src)} style={{width:'100%',height:'100%',objectFit:'cover',transform:'scale(1.11)'}}/>;

const Cut:React.FC<{p:PropertyVideoProps;k:string;big:string;small:string}>=({p,k,big,small})=>{const s=source(p,k);return <AbsoluteFill style={{overflow:'hidden',background:navy}}><Media {...s}/><AbsoluteFill style={{background:'linear-gradient(180deg,rgba(3,9,20,.08),rgba(3,9,20,.22) 45%,rgba(3,9,20,.9))'}}/><div style={{position:'absolute',left:50,right:50,top:300,fontFamily:font,fontWeight:1000,color:cream,textShadow:'0 16px 50px rgba(0,0,0,.8)'}}><div style={{fontSize:94,lineHeight:.9,color:gold}}>{big}</div><div style={{fontSize:54,lineHeight:1,marginTop:18}}>{small}</div></div><div style={{position:'absolute',left:0,right:0,top:0,height:12,background:`linear-gradient(90deg,${cyan},${gold})`}}/><div style={{position:'absolute',right:40,bottom:38,fontFamily:font,fontSize:13,fontWeight:900,letterSpacing:2,color:'rgba(255,255,255,.72)'}}>REPRESENTATIVE VISUALS</div></AbsoluteFill>};

const CTA:React.FC<{p:PropertyVideoProps}>=({p})=><AbsoluteFill style={{background:'radial-gradient(circle at 50% 35%,#174e6e,#030914 68%)',fontFamily:font,color:cream,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',padding:55}}><div><div style={{fontSize:19,letterSpacing:7,color:cyan,fontWeight:1000}}>READY TO VISIT?</div><div style={{fontSize:96,lineHeight:.92,fontWeight:1000,marginTop:28}}>BOOK YOUR<br/><span style={{color:gold}}>SITE VISIT</span></div><div style={{margin:'48px auto 0',width:760,padding:'24px 32px',borderRadius:28,background:green,color:navy,fontSize:46,fontWeight:1000,boxShadow:'0 0 60px rgba(36,217,144,.35)'}}>{p.phone}</div><div style={{fontSize:24,fontWeight:900,marginTop:24}}>{p.cta}</div></div></AbsoluteFill>;

export const ImpactVFXV3:React.FC<PropertyVideoProps>=(p)=>{
 const built=fact(p,'built','VERIFY SIZE'),facing=fact(p,'facing','VERIFY'),road=fact(p,'road','VERIFY');
 const shots=[
  {d:30,n:<Cut p={p} k="exterior" big={p.price} small="1 BHK FLAT"/>},
  {d:30,n:<Cut p={p} k="living" big="SMART" small="INTERIORS"/>},
  {d:30,n:<Cut p={p} k="location" big={p.location.toUpperCase()} small="LOCATION"/>},
  {d:42,n:<PriceImpactV2 source={source(p,'exterior')} price={p.price}/>},
  {d:52,n:<BuiltUpImpactV2 source={source(p,'living')} value={built}/>},
  {d:28,n:<Cut p={p} k="living" big="LIVING" small="COMPACT • MODERN"/>},
  {d:28,n:<Cut p={p} k="kitchen" big="KITCHEN" small="PRACTICAL • CLEAN"/>},
  {d:28,n:<Cut p={p} k="bedroom" big="BEDROOM" small="COMFORT • SPACE"/>},
  {d:52,n:<FacingImpactV2 source={source(p,'exterior')} value={facing}/>},
  {d:52,n:<RoadImpactV2 source={source(p,'road')} value={road}/>},
  {d:66,n:<TrustImpactV2 location={p.location} price={p.price}/>},
  {d:110,n:<CTA p={p}/>},
 ];
 let at=0; const seq=shots.map((s,i)=>{const from=at;at+=s.d;return <Sequence key={i} from={from} durationInFrames={s.d}>{s.n}</Sequence>});
 return <AbsoluteFill style={{background:navy}}>{seq}{p.audio&&<Audio src={staticFile(p.audio)} volume={1}/>}</AbsoluteFill>;
};
