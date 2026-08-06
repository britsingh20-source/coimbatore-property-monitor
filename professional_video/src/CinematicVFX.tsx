import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import type {StyleVariant} from './types';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const gold = '#f3b928';
const cream = '#f7f1e7';
const cyan = '#50d8ff';
const navy = '#06192d';
const typeface = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';

export const CinematicGrade: React.FC<{styleVariant: StyleVariant}> = ({styleVariant}) => {
  const frame = useCurrentFrame();
  const warmth = styleVariant === 'premium' || styleVariant === 'cinematic';
  const pulse = 0.035 + Math.sin(frame / 42) * 0.012;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', zIndex: 42}}>
      <AbsoluteFill style={{background: warmth
        ? 'linear-gradient(180deg,rgba(255,190,105,.035),transparent 42%,rgba(5,12,20,.18))'
        : 'linear-gradient(180deg,rgba(80,216,255,.018),transparent 48%,rgba(5,12,20,.16))'}} />
      <AbsoluteFill style={{boxShadow: 'inset 0 0 150px rgba(0,0,0,.36), inset 0 -120px 130px rgba(0,0,0,.2)'}} />
      <AbsoluteFill style={{opacity: pulse, mixBlendMode: 'soft-light', backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%270 0 140 140%27 xmlns=%27http://www.w3.org/2000/svg%27%3E%3Cfilter id=%27n%27%3E%3CfeTurbulence type=%27fractalNoise%27 baseFrequency=%27.8%27 numOctaves=%272%27 stitchTiles=%27stitch%27/%3E%3C/filter%3E%3Crect width=%27100%25%27 height=%27100%25%27 filter=%27url(%23n)%27 opacity=%27.75%27/%3E%3C/svg%3E")'}} />
    </AbsoluteFill>
  );
};

const Compass3D: React.FC<{value: string}> = ({value}) => {
  const frame = useCurrentFrame();
  const enter = spring({frame: frame - 4, fps: 30, config: {damping: 15, stiffness: 140}});
  const rotation = interpolate(frame, [0, 34], [-95, 0], clamp);
  return (
    <div style={{position: 'absolute', right: 55, top: 210, width: 205, height: 205, perspective: 900, transform: `scale(${enter})`, opacity: enter}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: 999, transform: 'rotateX(58deg) rotateZ(-8deg)', background: 'radial-gradient(circle at 35% 30%,rgba(255,255,255,.34),rgba(10,35,55,.86) 44%,rgba(2,11,20,.96))', border: '3px solid rgba(243,185,40,.82)', boxShadow: '0 32px 55px rgba(0,0,0,.42), inset 0 0 34px rgba(255,255,255,.14)'}}>
        {[0,45,90,135].map((deg) => <div key={deg} style={{position:'absolute',left:'50%',top:'50%',width:3,height:168,background:'rgba(255,255,255,.14)',transform:`translate(-50%,-50%) rotate(${deg}deg)`}} />)}
        <div style={{position:'absolute',left:'50%',top:'50%',width:7,height:132,transformOrigin:'50% 88%',transform:`translate(-50%,-88%) rotate(${rotation}deg)`,background:`linear-gradient(${gold} 0 50%,${cream} 50%)`,clipPath:'polygon(50% 0,100% 48%,68% 48%,68% 100%,32% 100%,32% 48%,0 48%)',filter:`drop-shadow(0 0 12px ${gold})`}} />
        <div style={{position:'absolute',left:'50%',top:'50%',width:20,height:20,borderRadius:99,background:gold,transform:'translate(-50%,-50%)',boxShadow:`0 0 18px ${gold}`}} />
      </div>
      <div style={{position:'absolute',right:4,bottom:-18,padding:'11px 15px',borderRadius:14,background:'rgba(2,11,20,.88)',border:'1px solid rgba(243,185,40,.62)',fontFamily:typeface,color:cream,fontSize:18,fontWeight:900,boxShadow:'0 12px 30px rgba(0,0,0,.35)'}}>{value}</div>
    </div>
  );
};

const PlotPlane: React.FC<{value: string}> = ({value}) => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [4, 42], [0, 1], clamp);
  const enter = spring({frame: frame - 2, fps: 30, config: {damping: 18}});
  return (
    <div style={{position:'absolute',left:72,right:72,bottom:250,height:360,perspective:900,pointerEvents:'none',opacity:enter}}>
      <svg viewBox="0 0 900 360" style={{width:'100%',height:'100%',transform:'rotateX(58deg) rotateZ(-2deg)',filter:`drop-shadow(0 18px 24px rgba(0,0,0,.45)) drop-shadow(0 0 15px ${gold})`}}>
        <polygon points="110,280 260,55 730,78 815,286" fill="rgba(243,185,40,.09)" stroke={gold} strokeWidth="7" strokeDasharray="1200" strokeDashoffset={1200 * (1-draw)} />
        <path d="M170 244 L300 102 L690 119 L754 245" fill="none" stroke="rgba(255,255,255,.58)" strokeWidth="3" strokeDasharray="12 13" />
        {[[110,280],[260,55],[730,78],[815,286]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r={8 + draw*5} fill={cream} stroke={gold} strokeWidth="5" />)}
      </svg>
      <div style={{position:'absolute',left:'50%',bottom:5,transform:'translateX(-50%)',padding:'13px 20px',borderRadius:16,background:'rgba(2,11,20,.9)',border:`1px solid ${gold}`,fontFamily:typeface,color:cream,fontSize:22,fontWeight:950,boxShadow:'0 16px 38px rgba(0,0,0,.42)'}}>{value}</div>
    </div>
  );
};

const RoadMeasure3D: React.FC<{value: string}> = ({value}) => {
  const frame = useCurrentFrame();
  const width = interpolate(frame, [8, 40], [0, 700], clamp);
  return (
    <div style={{position:'absolute',left:0,right:0,bottom:300,height:280,pointerEvents:'none',perspective:900}}>
      <div style={{position:'absolute',left:'50%',bottom:55,width,height:4,transform:'translateX(-50%) rotateX(58deg)',background:`linear-gradient(90deg,transparent,${cyan} 12%,${cyan} 88%,transparent)`,boxShadow:`0 0 22px ${cyan}`}} />
      {[-1,1].map(side => <div key={side} style={{position:'absolute',left:`calc(50% + ${side * width/2}px)`,bottom:35,width:3,height:90,background:cyan,boxShadow:`0 0 16px ${cyan}`,transform:'translateX(-50%)'}} />)}
      <div style={{position:'absolute',left:'50%',bottom:118,transform:'translateX(-50%)',padding:'12px 18px',borderRadius:15,background:'rgba(2,11,20,.9)',border:'1px solid rgba(80,216,255,.75)',fontFamily:typeface,color:cream,fontSize:22,fontWeight:950,whiteSpace:'nowrap'}}>{value}</div>
    </div>
  );
};

const LocationPin3D: React.FC<{value: string}> = ({value}) => {
  const frame = useCurrentFrame();
  const enter = spring({frame: frame - 5, fps: 30, config: {damping: 13, stiffness: 170}});
  const float = Math.sin(frame / 7) * 8;
  return (
    <div style={{position:'absolute',right:65,top:245,width:250,height:280,pointerEvents:'none',transform:`translateY(${float}px) scale(${enter})`,opacity:enter}}>
      <div style={{position:'absolute',left:82,top:5,width:104,height:132,borderRadius:'55% 55% 55% 8%',background:`linear-gradient(145deg,${gold},#ff8b2e)`,transform:'rotate(45deg)',boxShadow:'0 28px 42px rgba(0,0,0,.42),0 0 30px rgba(243,185,40,.38)'}}><div style={{position:'absolute',left:28,top:28,width:48,height:48,borderRadius:99,background:navy,border:'6px solid rgba(255,255,255,.78)'}} /></div>
      <div style={{position:'absolute',left:28,right:0,bottom:14,padding:'13px 16px',borderRadius:16,background:'rgba(2,11,20,.9)',border:'1px solid rgba(243,185,40,.62)',fontFamily:typeface,color:cream,fontSize:19,lineHeight:1.25,fontWeight:900,textAlign:'center'}}>{value}</div>
    </div>
  );
};

const ApprovalSeal: React.FC<{value: string}> = ({value}) => {
  const frame = useCurrentFrame();
  const enter = spring({frame: frame - 4, fps: 30, config: {damping: 11, stiffness: 180}});
  return (
    <div style={{position:'absolute',right:70,top:260,width:230,height:230,borderRadius:999,display:'grid',placeItems:'center',transform:`rotate(${interpolate(enter,[0,1],[-22,-7])}deg) scale(${enter})`,opacity:enter,background:'rgba(9,46,39,.86)',border:'7px double rgba(44,220,148,.92)',boxShadow:'0 28px 55px rgba(0,0,0,.42), inset 0 0 36px rgba(44,220,148,.18)',fontFamily:typeface,color:cream,textAlign:'center',padding:25}}>
      <div><div style={{fontSize:46,color:'#2cdc94',fontWeight:1000}}>✓</div><div style={{fontSize:17,letterSpacing:2,fontWeight:1000}}>APPROVAL</div><div style={{fontSize:17,lineHeight:1.25,fontWeight:900,marginTop:8}}>{value}</div></div>
    </div>
  );
};

export const SceneVFXOverlay: React.FC<{scene: string; value: string; styleVariant: StyleVariant}> = ({scene, value, styleVariant}) => {
  if (!value) return null;
  const muted = styleVariant === 'premium' || styleVariant === 'cinematic';
  return (
    <AbsoluteFill style={{pointerEvents:'none',zIndex:28,opacity:muted ? .88 : 1}}>
      {scene === 'location' && <LocationPin3D value={value} />}
      {scene === 'land' && <PlotPlane value={value} />}
      {scene === 'road' && <RoadMeasure3D value={value} />}
      {scene === 'facing' && <Compass3D value={value} />}
      {scene === 'approval' && <ApprovalSeal value={value} />}
    </AbsoluteFill>
  );
};

export const SceneTransitionOverlay: React.FC<{styleVariant: StyleVariant; duration: number; index: number}> = ({styleVariant, duration, index}) => {
  const frame = useCurrentFrame();
  const inT = interpolate(frame, [0, 11], [1, 0], clamp);
  const outT = interpolate(frame, [Math.max(0,duration-8), duration], [0, 1], clamp);
  const t = Math.max(inT, outT);
  if (styleVariant === 'fast-cut') {
    const x = interpolate(frame, [0, 10], [index % 2 ? -1150 : 1150, 0], clamp);
    return <AbsoluteFill style={{zIndex:70,pointerEvents:'none',overflow:'hidden',opacity:t}}><div style={{position:'absolute',inset:-100,transform:`translateX(${x}px) skewX(-12deg)`,background:'linear-gradient(90deg,transparent,rgba(80,216,255,.55),rgba(255,255,255,.82),transparent)',filter:'blur(18px)'}} /></AbsoluteFill>;
  }
  if (styleVariant === 'premium') {
    return <AbsoluteFill style={{zIndex:70,pointerEvents:'none',opacity:t,background:'radial-gradient(circle at 48% 42%,rgba(255,235,185,.78),rgba(243,185,40,.26) 28%,rgba(5,13,22,.96) 82%)',mixBlendMode:'screen'}} />;
  }
  if (styleVariant === 'location-first') {
    const line = interpolate(frame,[0,12],[0,115],clamp);
    return <AbsoluteFill style={{zIndex:70,pointerEvents:'none',opacity:t,background:`linear-gradient(105deg,rgba(3,14,24,.96) 0 ${Math.max(0,line-18)}%,rgba(80,216,255,.85) ${line}%,transparent ${Math.min(100,line+8)}%)`}} />;
  }
  if (styleVariant === 'price-first') {
    const y = interpolate(frame,[0,10],[-2100,2100],clamp);
    return <AbsoluteFill style={{zIndex:70,pointerEvents:'none',opacity:t}}><div style={{position:'absolute',left:-150,right:-150,top:y,height:250,transform:'rotate(-8deg)',background:`linear-gradient(180deg,transparent,${gold},rgba(255,255,255,.9),${gold},transparent)`,filter:'blur(8px)'}} /></AbsoluteFill>;
  }
  return <AbsoluteFill style={{zIndex:70,pointerEvents:'none',opacity:t,background:'linear-gradient(115deg,rgba(2,11,20,.96),rgba(243,185,40,.18) 46%,rgba(255,255,255,.4) 51%,rgba(2,11,20,.96) 72%)',mixBlendMode:'screen'}} />;
};
