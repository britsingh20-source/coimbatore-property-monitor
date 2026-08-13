import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';

type Source = {src:string; video:boolean};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
const gold='#ffbf2f'; const cyan='#49ddff'; const green='#28d997'; const cream='#fff7e8'; const navy='#020b14'; const orange='#ff6b2c';
const font='Noto Sans Tamil, Noto Sans, Arial, sans-serif';

const Media:React.FC<{source?:Source;scale?:number;x?:number;y?:number;blur?:number}> = ({source,scale=1,x=0,y=0,blur=0}) => {
  if(!source) return <AbsoluteFill style={{background:'radial-gradient(circle at 50% 35%,#133955,#020b14 70%)'}}/>;
  const style:React.CSSProperties={width:'100%',height:'100%',objectFit:'cover',transform:`translate3d(${x}px,${y}px,0) scale(${scale})`,filter:blur?`blur(${blur}px)`:undefined};
  return source.video?<OffthreadVideo src={staticFile(source.src)} muted style={style}/>:<Img src={staticFile(source.src)} style={style}/>;
};

const EnergyBG:React.FC<{source?:Source;duration?:number}> = ({source,duration=120}) => {
  const f=useCurrentFrame(); const t=interpolate(f,[0,duration],[0,1],clamp);
  const scale=1.04+t*.18; const x=Math.sin(t*Math.PI*1.2)*34; const y=18-t*42;
  return <AbsoluteFill style={{overflow:'hidden',background:navy}}>
    <AbsoluteFill style={{inset:-45}}><Media source={source} scale={scale} x={x} y={y}/></AbsoluteFill>
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.08),rgba(2,11,20,.12) 43%,rgba(2,11,20,.82) 79%,#020b14)'}}/>
  </AbsoluteFill>;
};

const Burst:React.FC<{color?:string;at?:number}> = ({color=gold,at=0}) => {
  const f=useCurrentFrame()-at; const op=interpolate(f,[0,2,10],[.95,.6,0],clamp); const sc=interpolate(f,[0,10],[.6,1.45],clamp);
  return <AbsoluteFill style={{pointerEvents:'none',opacity:op,transform:`scale(${sc})`,background:`radial-gradient(circle at 50% 45%,${color},rgba(255,255,255,.55) 16%,transparent 58%)`,mixBlendMode:'screen'}}/>;
};

const SpeedLines:React.FC<{color?:string;intensity?:number}> = ({color=cyan,intensity=1}) => {
  const f=useCurrentFrame();
  return <AbsoluteFill style={{pointerEvents:'none',overflow:'hidden',opacity:.55*intensity}}>{Array.from({length:14}).map((_,i)=>{
    const travel=((f*42+i*185)%1900)-600; const top=130+i*122;
    return <div key={i} style={{position:'absolute',left:travel,top,width:380+(i%5)*95,height:2+(i%3),transform:`rotate(${-14+(i%4)*4}deg)`,background:`linear-gradient(90deg,transparent,${color},transparent)`,filter:'blur(.5px)',boxShadow:`0 0 16px ${color}`}}/>;
  })}</AbsoluteFill>;
};

const Kinetic:React.FC<{text:string;sub?:string;accent?:string;center?:boolean;start?:number}> = ({text,sub,accent,center=false,start=0}) => {
  const f=useCurrentFrame(); const words=text.split(' ');
  return <div style={{fontFamily:font,textAlign:center?'center':'left'}}>
    <div style={{display:'flex',flexWrap:'wrap',justifyContent:center?'center':'flex-start',gap:'4px 16px'}}>{words.map((w,i)=>{
      const s=spring({frame:f-start-i*4,fps:30,config:{damping:11,stiffness:240}}); const hot=accent&&w.toUpperCase().includes(accent.toUpperCase());
      return <span key={i} style={{fontSize:hot?112:82,lineHeight:.95,fontWeight:1000,color:hot?gold:cream,transform:`translateY(${interpolate(s,[0,1],[95,0])}px) scale(${interpolate(s,[0,1],[.45,1])}) rotate(${interpolate(s,[0,1],[-7,0])}deg)`,opacity:s,textShadow:hot?`0 0 40px rgba(255,191,47,.55)`:'0 14px 45px rgba(0,0,0,.55)',WebkitTextStroke:hot?'1px rgba(255,255,255,.25)':undefined}}>{w}</span>;
    })}</div>
    {sub&&<div style={{marginTop:20,fontSize:22,letterSpacing:4,fontWeight:950,color:cyan,opacity:interpolate(f,[start+12,start+24],[0,1],clamp)}}>{sub}</div>}
  </div>;
};

export const ImpactHookV2:React.FC<{source?:Source;title:string;location:string;price:string}> = ({source,title,location,price}) => {
  const f=useCurrentFrame(); const shake=f<8?(8-f)*Math.sin(f*7):0;
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream,transform:`translateX(${shake}px)`}}>
    <EnergyBG source={source}/>
    <AbsoluteFill style={{opacity:.32,backgroundImage:'linear-gradient(rgba(73,221,255,.2) 1px,transparent 1px),linear-gradient(90deg,rgba(73,221,255,.2) 1px,transparent 1px)',backgroundSize:'70px 70px',clipPath:`inset(${interpolate(f,[4,26],[100,8],clamp)}% 6% 15% 6% round 28px)`}}/>
    <div style={{position:'absolute',left:54,right:54,top:205}}><Kinetic text={price+' '+title} accent={price.split(' ')[0]} sub={location.toUpperCase()} start={2}/></div>
    <div style={{position:'absolute',left:54,right:54,bottom:265,display:'flex',gap:12,flexWrap:'wrap'}}>{['PROPERTY DROP','COIMBATORE','SITE VISIT'].map((x,i)=>{const s=spring({frame:f-18-i*5,fps:30,config:{damping:12}});return <div key={x} style={{padding:'13px 18px',borderRadius:999,background:i===0?gold:'rgba(2,11,20,.8)',color:i===0?navy:cream,border:`1px solid ${i===0?gold:'rgba(255,255,255,.25)'}`,fontSize:15,letterSpacing:2,fontWeight:1000,transform:`translateY(${interpolate(s,[0,1],[35,0])}px)`,opacity:s}}>{x}</div>})}</div>
    <SpeedLines color={gold} intensity={.8}/><Burst color={gold}/>
  </AbsoluteFill>;
};

export const PriceImpactV2:React.FC<{source?:Source;price:string}> = ({source,price}) => {
  const f=useCurrentFrame(); const p=spring({frame:f-10,fps:30,config:{damping:8,stiffness:280}}); const ring=interpolate(f,[8,55],[.3,1.45],clamp);
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream}}><EnergyBG source={source}/>
    <div style={{position:'absolute',left:540-310*ring,top:960-310*ring,width:620*ring,height:620*ring,borderRadius:999,border:`5px solid rgba(255,191,47,${interpolate(f,[8,55],[.8,0],clamp)})`,boxShadow:`0 0 70px rgba(255,191,47,.35)`}}/>
    <div style={{position:'absolute',left:45,right:45,top:400,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:7,color:cyan,fontWeight:1000}}>ASKING PRICE</div><div style={{fontSize:132,lineHeight:.95,fontWeight:1000,color:gold,marginTop:26,transform:`scale(${interpolate(p,[0,1],[.2,1])}) rotate(${interpolate(p,[0,1],[-8,0])}deg)`,textShadow:'0 25px 80px rgba(0,0,0,.6)'}}>{price}</div><div style={{fontSize:27,fontWeight:900,marginTop:25}}>VALUE FIRST • VERIFY ON SITE</div></div>
    <SpeedLines color={gold}/><Burst color={gold} at={6}/></AbsoluteFill>;
};

export const BuiltUpImpactV2:React.FC<{source?:Source;value:string}> = ({source,value}) => {
  const f=useCurrentFrame(); const scan=interpolate(f,[0,110],[300,1480],clamp); const pop=spring({frame:f-16,fps:30,config:{damping:10,stiffness:230}});
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream}}><EnergyBG source={source}/>
    <AbsoluteFill style={{opacity:.35,backgroundImage:'linear-gradient(rgba(73,221,255,.6) 1px,transparent 1px),linear-gradient(90deg,rgba(73,221,255,.6) 1px,transparent 1px)',backgroundSize:'52px 52px',clipPath:`inset(280px 65px ${Math.max(250,1920-scan)}px 65px round 24px)`}}/>
    <div style={{position:'absolute',left:65,right:65,top:320}}><div style={{fontSize:18,letterSpacing:7,color:cyan,fontWeight:1000}}>SMART SPACE SCAN</div><div style={{fontSize:112,fontWeight:1000,color:cream,marginTop:18,transform:`translateX(${interpolate(pop,[0,1],[-180,0])}px)`,opacity:pop}}>{value}</div><div style={{height:6,width:interpolate(f,[18,58],[0,760],clamp),background:`linear-gradient(90deg,${cyan},${gold})`,boxShadow:`0 0 25px ${cyan}`,marginTop:26}}/></div>
    {[0,1,2].map(i=><div key={i} style={{position:'absolute',left:90+i*290,top:1080+i%2*90,width:235,height:135,borderRadius:22,background:'rgba(2,11,20,.78)',border:`1px solid ${i===1?gold:cyan}`,display:'grid',placeItems:'center',fontSize:16,letterSpacing:2,fontWeight:1000,transform:`perspective(700px) rotateY(${i===0?-10:i===2?10:0}deg)`}}>{['COMPACT','EFFICIENT','PRACTICAL'][i]}</div>)}
    <SpeedLines color={cyan} intensity={.55}/><Burst color={cyan}/></AbsoluteFill>;
};

export const FacingImpactV2:React.FC<{source?:Source;value:string}> = ({source,value}) => {
  const f=useCurrentFrame(); const rot=interpolate(f,[0,42],[-160,0],clamp); const pop=spring({frame:f-7,fps:30,config:{damping:10}});
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream}}><EnergyBG source={source}/>
    <div style={{position:'absolute',left:170,top:500,width:740,height:740,borderRadius:999,border:`5px solid ${gold}`,boxShadow:`0 0 80px rgba(255,191,47,.28),inset 0 0 60px rgba(73,221,255,.15)`,transform:`scale(${interpolate(pop,[0,1],[.4,1])})`}}>
      {[0,45,90,135].map(d=><div key={d} style={{position:'absolute',left:'50%',top:'50%',width:3,height:650,background:'rgba(255,255,255,.14)',transform:`translate(-50%,-50%) rotate(${d}deg)`}}/>)}
      <div style={{position:'absolute',left:'50%',top:'50%',width:18,height:300,transformOrigin:'50% 90%',transform:`translate(-50%,-90%) rotate(${rot}deg)`,background:`linear-gradient(${gold} 0 50%,${cream} 50%)`,clipPath:'polygon(50% 0,100% 48%,68% 48%,68% 100%,32% 100%,32% 48%,0 48%)',filter:`drop-shadow(0 0 25px ${gold})`}}/>
    </div>
    <div style={{position:'absolute',left:60,right:60,top:300,textAlign:'center'}}><div style={{fontSize:18,letterSpacing:7,color:cyan,fontWeight:1000}}>ORIENTATION LOCK</div><div style={{fontSize:88,fontWeight:1000,marginTop:18}}>{value}</div></div><Burst color={gold} at={4}/></AbsoluteFill>;
};

export const RoadImpactV2:React.FC<{source?:Source;value:string}> = ({source,value}) => {
  const f=useCurrentFrame(); const w=interpolate(f,[8,55],[0,360],clamp);
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream}}><EnergyBG source={source}/>
    <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 16px ${cyan})`}}><path d={`M${540-w} 1440 L${540-w*.35} 650 M${540+w} 1440 L${540+w*.35} 650`} stroke={cyan} strokeWidth="10"/><path d={`M${540-w*.88} 1220 H${540+w*.88}`} stroke={gold} strokeWidth="8"/><path d={`M${540-w*.88} 1220 l45 -26 v52 Z M${540+w*.88} 1220 l-45 -26 v52 Z`} fill={gold}/><path d="M540 700V1410" stroke="rgba(255,255,255,.8)" strokeWidth="5" strokeDasharray="28 26"/></svg>
    <div style={{position:'absolute',left:60,right:60,top:285,textAlign:'center'}}><div style={{fontSize:18,letterSpacing:7,color:cyan,fontWeight:1000}}>ACCESS ROAD</div><div style={{fontSize:82,fontWeight:1000,marginTop:18}}>{value}</div><div style={{fontSize:22,marginTop:18,color:gold,fontWeight:950}}>VERIFY MEASUREMENT ON SITE</div></div><SpeedLines color={cyan} intensity={.7}/><Burst color={cyan}/></AbsoluteFill>;
};

export const TrustImpactV2:React.FC<{location:string;price:string}> = ({location,price}) => {
  const f=useCurrentFrame(); const rows=[['DOCS','DOCUMENTS'],['LOC','LOCATION'],['₹','PRICE'],['SIZE','MEASUREMENTS']];
  return <AbsoluteFill style={{background:'radial-gradient(circle at 80% 15%,#164a6b,#020b14 62%)',fontFamily:font,color:cream,padding:'220px 65px 180px',overflow:'hidden'}}>
    <div style={{fontSize:62,lineHeight:1.02,fontWeight:1000}}>VERIFY FAST.<br/><span style={{color:gold}}>DECIDE SMART.</span></div>
    <div style={{display:'grid',gap:18,marginTop:62}}>{rows.map(([icon,label],i)=>{const s=spring({frame:f-i*8,fps:30,config:{damping:11,stiffness:220}});return <div key={label} style={{height:118,borderRadius:25,background:'rgba(255,255,255,.08)',border:'1px solid rgba(255,255,255,.2)',display:'flex',alignItems:'center',padding:'0 24px',transform:`translateX(${interpolate(s,[0,1],[-180,0])}px) scale(${interpolate(s,[0,1],[.85,1])})`,opacity:s}}><div style={{width:70,height:70,borderRadius:20,background:i===2?gold:cyan,color:navy,display:'grid',placeItems:'center',fontSize:26,fontWeight:1000}}>{icon}</div><div style={{marginLeft:22,fontSize:25,letterSpacing:3,fontWeight:1000}}>{label}</div><div style={{marginLeft:'auto',fontSize:36,color:green,fontWeight:1000}}>✓</div></div>})}</div>
    <div style={{marginTop:28,fontSize:24,lineHeight:1.5}}>{location}<br/><span style={{color:gold,fontWeight:1000}}>{price}</span></div><SpeedLines color={green} intensity={.45}/></AbsoluteFill>;
};

export const ImpactCTAV2:React.FC<{source?:Source;brand:string;phone:string;location:string}> = ({source,brand,phone,location}) => {
  const f=useCurrentFrame(); const pop=spring({frame:f-5,fps:30,config:{damping:9,stiffness:230}}); const pulse=1+Math.sin(f/5)*.045;
  return <AbsoluteFill style={{overflow:'hidden',fontFamily:font,color:cream}}><EnergyBG source={source}/><AbsoluteFill style={{background:'radial-gradient(circle at 50% 45%,rgba(0,0,0,.08),rgba(2,11,20,.94) 72%)'}}/>
    <div style={{position:'absolute',left:55,right:55,top:320,textAlign:'center',transform:`scale(${pop})`,opacity:pop}}><div style={{fontSize:18,letterSpacing:7,color:gold,fontWeight:1000}}>READY FOR A SITE VISIT?</div><div style={{fontSize:68,lineHeight:1.06,fontWeight:1000,marginTop:28}}>CALL • WHATSAPP<br/><span style={{color:gold}}>{brand}</span></div><div style={{fontSize:25,marginTop:24,opacity:.9}}>{location}</div>
    <div style={{display:'inline-block',marginTop:45,padding:'24px 38px',borderRadius:999,background:green,color:'#03150e',fontSize:54,fontWeight:1000,letterSpacing:2,transform:`scale(${pulse})`,boxShadow:'0 0 55px rgba(40,217,151,.45)'}}>{phone}</div><div style={{marginTop:26,fontSize:20,letterSpacing:4,fontWeight:950}}>BOOK YOUR VERIFIED PROPERTY VISIT</div></div><SpeedLines color={gold} intensity={.9}/><Burst color={gold} at={3}/></AbsoluteFill>;
};

export const ImpactTransitionV2:React.FC<{duration:number;index:number}> = ({duration,index}) => {
  const f=useCurrentFrame(); const inT=interpolate(f,[0,7],[1,0],clamp); const outT=interpolate(f,[Math.max(0,duration-6),duration],[0,1],clamp); const t=Math.max(inT,outT);
  const travel=interpolate(f,[0,8],[index%2?-1300:1300,0],clamp);
  return <AbsoluteFill style={{pointerEvents:'none',zIndex:90,overflow:'hidden',opacity:t}}><div style={{position:'absolute',inset:-260,transform:`translateX(${travel}px) skewX(-14deg) rotate(-3deg)`,background:`linear-gradient(90deg,transparent,${index%2?cyan:gold},rgba(255,255,255,.95),${index%2?gold:cyan},transparent)`,filter:'blur(10px)'}}/></AbsoluteFill>;
};
