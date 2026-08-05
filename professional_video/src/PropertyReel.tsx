import React from 'react';
import '@fontsource/noto-sans-tamil/400.css';
import '@fontsource/noto-sans-tamil/700.css';
import '@fontsource/noto-sans-tamil/900.css';
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {Fact, PropertyVideoProps} from './types';

const navy = '#06192d';
const ink = '#020b14';
const cream = '#f7f1e7';
const gold = '#f3b928';
const orange = '#ff6b2c';
const green = '#16b77a';
const cyan = '#50d8ff';
const typeface = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const clean = (value: string) => value && value.toUpperCase() !== 'NOT SPECIFIED' ? value : 'நேரில் சரிபார்க்கவும்';

type VisualSource = {src: string; video: boolean};

const Visual: React.FC<{source?: VisualSource; scale?: number; x?: number; y?: number; blur?: number}> = ({source, scale = 1, x = 0, y = 0, blur = 0}) => {
  if (!source) return <AbsoluteFill style={{background: 'linear-gradient(145deg, #163d5b, #06192d 62%)'}} />;
  const style: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', transform: `translate3d(${x}px, ${y}px, 0) scale(${scale})`, filter: blur ? `blur(${blur}px)` : undefined};
  return source.video ? <Loop durationInFrames={180}><OffthreadVideo src={staticFile(source.src)} muted style={style} /></Loop> : <Img src={staticFile(source.src)} style={style} />;
};

const PhotoStage: React.FC<{source?: VisualSource; direction?: 1 | -1; dark?: number; speed?: number}> = ({source, direction = 1, dark = .48, speed = 1}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 180 / speed], [1.03, 1.18], clamp);
  const x = interpolate(frame, [0, 180 / speed], [-18 * direction, 24 * direction], clamp);
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: navy}}>
      <AbsoluteFill style={{inset: -30}}><Visual source={source} scale={scale} x={x} /></AbsoluteFill>
      <AbsoluteFill style={{background: `linear-gradient(180deg, rgba(2,11,20,.12), rgba(2,11,20,${dark}) 62%, rgba(2,11,20,.94))`}} />
      <AbsoluteFill style={{opacity: .08, backgroundImage: 'repeating-linear-gradient(0deg, transparent 0, transparent 5px, rgba(255,255,255,.45) 6px)'}} />
    </AbsoluteFill>
  );
};

const GlobalFX: React.FC = () => {
  const frame = useCurrentFrame();
  const sweep = ((frame * 18) % 1700) - 420;
  return (
    <AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none'}}>
      {Array.from({length: 24}).map((_, i) => {
        const y = (i * 137 + frame * (1.2 + i % 3)) % 1900;
        const x = (i * 223 + Math.sin((frame + i * 17) / 24) * 90) % 1080;
        return <div key={i} style={{position: 'absolute', left: x, top: y, width: i % 5 === 0 ? 5 : 2, height: i % 5 === 0 ? 5 : 2, borderRadius: 9, background: i % 4 === 0 ? gold : 'rgba(255,255,255,.65)', boxShadow: i % 4 === 0 ? `0 0 14px ${gold}` : undefined, opacity: .28}} />;
      })}
      <div style={{position: 'absolute', left: sweep, top: -400, width: 160, height: 2700, transform: 'rotate(18deg)', background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent)', filter: 'blur(14px)'}} />
      <AbsoluteFill style={{boxShadow: 'inset 0 0 180px rgba(0,0,0,.42)'}} />
    </AbsoluteFill>
  );
};

const SceneFlash: React.FC<{color?: string}> = ({color = cream}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 2, 9], [.9, .7, 0], clamp);
  const scale = interpolate(frame, [0, 9], [.96, 1.08], clamp);
  return <AbsoluteFill style={{background: `radial-gradient(circle, ${color}, transparent 68%)`, opacity, transform: `scale(${scale})`, mixBlendMode: 'screen', pointerEvents: 'none'}} />;
};

const SceneCode: React.FC<{number: string; label: string}> = ({number, label}) => (
  <div style={{position: 'absolute', left: 48, top: 112, display: 'flex', alignItems: 'center', gap: 14, color: cream, fontFamily: typeface}}>
    <div style={{fontSize: 18, letterSpacing: 3, fontWeight: 950, color: gold}}>{number}</div>
    <div style={{width: 54, height: 2, background: gold}} />
    <div style={{fontSize: 16, letterSpacing: 3.2, fontWeight: 900}}>{label}</div>
  </div>
);

const KineticWords: React.FC<{words: string[]; start?: number; size?: number; accent?: number; align?: 'left' | 'center'}> = ({words, start = 0, size = 74, accent = -1, align = 'left'}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: align === 'center' ? 'center' : 'flex-start', gap: '4px 16px', textAlign: align, fontFamily: typeface}}>
      {words.map((word, i) => {
        const enter = spring({frame: frame - start - i * 5, fps: 30, config: {damping: 15, stiffness: 190}});
        return <span key={`${word}-${i}`} style={{fontSize: i === accent ? size * 1.22 : size, lineHeight: .98, fontWeight: i === accent ? 1000 : 850, fontStyle: i < 2 ? 'italic' : 'normal', color: i === accent ? gold : cream, WebkitTextStroke: i === accent ? '1px rgba(255,255,255,.22)' : undefined, textShadow: i === accent ? `0 0 34px rgba(243,185,40,.4)` : '0 5px 25px rgba(0,0,0,.35)', transform: `translateY(${interpolate(enter, [0, 1], [70, 0])}px) scale(${interpolate(enter, [0, 1], [.7, 1])}) rotate(${interpolate(enter, [0, 1], [-4, 0])}deg)`, opacity: enter}}>{word}</span>;
      })}
    </div>
  );
};

const PlotOutline: React.FC = () => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [16, 64], [760, 0], clamp);
  const glow = 14 + Math.sin(frame / 5) * 7;
  return (
    <svg viewBox="0 0 900 760" style={{position: 'absolute', left: 90, top: 430, width: 900, height: 760, filter: `drop-shadow(0 0 ${glow}px ${gold})`}}>
      <polygon points="165,575 305,190 725,250 785,610" fill="rgba(243,185,40,.09)" stroke={gold} strokeWidth="9" strokeDasharray="760" strokeDashoffset={draw} />
      {[[165,575],[305,190],[725,250],[785,610]].map(([cx,cy],i) => <circle key={i} cx={cx} cy={cy} r={12 + Math.sin((frame+i*6)/5)*4} fill={cream} stroke={gold} strokeWidth="6" />)}
      <path d="M220 525 L335 245 L678 294 L730 558 Z" fill="none" stroke="rgba(255,255,255,.8)" strokeWidth="3" strokeDasharray="14 14" />
    </svg>
  );
};

const HookScene: React.FC<{source?: VisualSource; title: string; location: string}> = ({source, title, location}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 120], [1.01, 1.13], clamp);
  return (
    <AbsoluteFill style={{fontFamily: typeface, overflow: 'hidden'}}>
      <AbsoluteFill><Visual source={source} scale={zoom} /></AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(2,11,20,.18), rgba(2,11,20,.14) 45%, rgba(2,11,20,.9))'}} />
      <PlotOutline />
      <SceneCode number="01" label="NEW PROPERTY DROP" />
      <div style={{position: 'absolute', left: 56, right: 56, bottom: 270}}>
        <div style={{fontSize: 21, color: cyan, letterSpacing: 4, fontWeight: 950, marginBottom: 20}}>LOCATION • {location.toUpperCase()}</div>
        <KineticWords words={['OWN', 'YOUR', 'COIMBATORE', 'HOME']} size={76} accent={2} start={4} />
        <div style={{marginTop: 22, fontSize: 35, color: cream, fontWeight: 850, transform: `translateX(${interpolate(frame, [30, 58], [-90, 0], clamp)}px)`, opacity: interpolate(frame, [30, 52], [0, 1], clamp)}}>{title}</div>
      </div>
      <SceneFlash />
    </AbsoluteFill>
  );
};

const LocationJourneyScene: React.FC<{mapSource?: VisualSource; houseSource?: VisualSource; title:string; location:string}> = ({mapSource,houseSource,title,location}) => {
  const frame=useCurrentFrame();
  const mapZoom=interpolate(frame,[0,165],[1.02,2.35],clamp);
  const mapX=interpolate(frame,[0,165],[0,-120],clamp);
  const mapY=interpolate(frame,[0,165],[0,-175],clamp);
  const cityOpacity=interpolate(frame,[0,18,70,92],[0,1,1,0],clamp);
  const pattanamOpacity=interpolate(frame,[68,95,165],[0,1,1],clamp);
  const portal=interpolate(frame,[158,222],[0,132],clamp);
  const houseScale=interpolate(frame,[158,267],[1.48,1.02],clamp);
  const titleEnter=spring({frame:frame-205,fps:30,config:{damping:15,stiffness:180}});
  const route=interpolate(frame,[35,125],[720,0],clamp);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden',background:navy}}>
      <AbsoluteFill style={{transform:`translate(${mapX}px,${mapY}px) scale(${mapZoom})`}}><Visual source={mapSource}/></AbsoluteFill>
      <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.22),rgba(2,11,20,.68))'}}/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',opacity:interpolate(frame,[135,172],[1,0],clamp),filter:`drop-shadow(0 0 13px ${gold})`}}>
        <path d="M125 1260 C250 1050 360 1110 450 880 S690 760 835 510" fill="none" stroke="rgba(255,255,255,.22)" strokeWidth="35"/>
        <path d="M125 1260 C250 1050 360 1110 450 880 S690 760 835 510" fill="none" stroke={gold} strokeWidth="8" strokeDasharray="720" strokeDashoffset={route}/>
        <circle cx="540" cy="930" r={35+Math.sin(frame/4)*8} fill="rgba(255,107,44,.24)" stroke={orange} strokeWidth="9"/>
        <circle cx="540" cy="930" r="11" fill={cream}/>
      </svg>
      <div style={{position:'absolute',left:55,right:55,top:260,textAlign:'center',opacity:cityOpacity,transform:`translateY(${interpolate(frame,[0,30],[55,0],clamp)}px)`}}><div style={{fontSize:20,letterSpacing:8,color:cyan,fontWeight:950}}>LOCATION JOURNEY</div><div style={{fontSize:100,lineHeight:.95,fontWeight:1000,marginTop:22}}>COIMBATORE</div><div style={{fontSize:26,marginTop:20,letterSpacing:4}}>TAMIL NADU</div></div>
      <div style={{position:'absolute',left:55,right:55,top:1080,textAlign:'center',opacity:pattanamOpacity,transform:`scale(${interpolate(frame,[70,130],[.55,1],clamp)})`}}><div style={{fontSize:20,letterSpacing:7,color:gold,fontWeight:950}}>ZOOMING INTO</div><div style={{fontSize:112,lineHeight:1,fontWeight:1000,color:cream,textShadow:`0 0 40px rgba(243,185,40,.45)`,marginTop:16}}>PATTANAM</div><div style={{display:'inline-block',marginTop:20,padding:'13px 22px',borderRadius:99,background:orange,fontSize:20,fontWeight:950,letterSpacing:2}}>TARGET LOCATION</div></div>
      <AbsoluteFill style={{clipPath:`circle(${portal}% at 50% 58%)`}}><Visual source={houseSource} scale={houseScale}/><AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.06),rgba(2,11,20,.82))'}}/></AbsoluteFill>
      {frame>=165&&<div style={{position:'absolute',left:540,top:890,width:interpolate(frame,[165,205],[8,700],clamp),height:5,transform:'translateX(-50%)',background:`linear-gradient(90deg,transparent,${gold},transparent)`,boxShadow:`0 0 24px ${gold}`}}/>}
      <SceneCode number="01" label={frame<160?'COIMBATORE → PATTANAM':'ENTERING THE PROPERTY'}/>
      <div style={{position:'absolute',left:55,right:55,bottom:225,opacity:titleEnter,transform:`translateY(${interpolate(titleEnter,[0,1],[70,0])}px)`}}><div style={{fontSize:18,letterSpacing:4,color:gold,fontWeight:950}}>LOCATION • {location.toUpperCase()}</div><div style={{fontSize:62,lineHeight:1.08,fontWeight:1000,marginTop:14}}>{title}</div><div style={{fontSize:20,letterSpacing:4,fontWeight:900,marginTop:18,color:cyan}}>MAP → LOCATION → HOME</div></div>
      {(frame<8||frame>=158&&frame<168)&&<SceneFlash color={frame<8?cyan:gold}/>}<GlobalFX/>
    </AbsoluteFill>
  );
};

const PriceScene: React.FC<{source?: VisualSource; price: string}> = ({source, price}) => {
  const frame = useCurrentFrame();
  const pricePop = spring({frame: frame - 24, fps: 30, config: {damping: 11, stiffness: 220}});
  const corridor = interpolate(frame, [0, 80], [0, 1250], clamp);
  return (
    <AbsoluteFill style={{fontFamily: typeface, color: cream, overflow: 'hidden'}}>
      <PhotoStage source={source} direction={-1} dark={.42} speed={1.4} />
      <div style={{position: 'absolute', left: 540 - corridor / 2, bottom: -130, width: corridor, height: 1380, background: 'linear-gradient(180deg, rgba(243,185,40,0), rgba(243,185,40,.45))', clipPath: 'polygon(46% 0,54% 0,100% 100%,0 100%)'}} />
      <SceneCode number="02" label="VALUE REVEAL" />
      <div style={{position: 'absolute', left: 58, right: 58, top: 315}}>
        <div style={{fontSize: 27, letterSpacing: 5, fontWeight: 950}}>START YOUR NEXT CHAPTER</div>
        <div style={{fontSize: 104, lineHeight: .92, fontWeight: 1000, color: gold, marginTop: 24, transform: `scale(${interpolate(pricePop, [0, 1], [.45, 1])})`, transformOrigin: 'left center', textShadow: `0 18px 65px rgba(0,0,0,.45)`}}>{price}</div>
        <div style={{display:'flex',gap:14,marginTop:32}}><div style={{padding:'17px 20px',borderRadius:18,background:'rgba(6,25,45,.86)',border:'1px solid rgba(255,255,255,.22)',fontSize:18,letterSpacing:3,fontWeight:950}}>ONE CLEAR ASKING PRICE</div><div style={{padding:'17px 20px',borderRadius:18,background:green,color:cream,fontSize:18,letterSpacing:2,fontWeight:950}}>VERIFY ON SITE</div></div>
      </div>
      <SceneFlash color={gold} />
    </AbsoluteFill>
  );
};

const WalkthroughScene: React.FC<{media: VisualSource[]; location: string}> = ({media, location}) => {
  const frame = useCurrentFrame();
  const slot = Math.min(2, Math.floor(frame / 60));
  const local = frame % 60;
  const blur = interpolate(local, [0, 5, 50, 59], [10, 0, 0, 12], clamp);
  const zoom = interpolate(local, [0, 60], [1.18, 1.03], clamp);
  const labels = ['EXTERIOR HERO', 'INTERIOR FLOW', 'SPACE TO LIVE'];
  return (
    <AbsoluteFill style={{fontFamily: typeface, overflow: 'hidden', color: cream}}>
      <AbsoluteFill style={{transform: `rotate(${interpolate(local,[0,8],[-2.5,0],clamp)}deg)`}}><Visual source={media[slot % Math.max(1, media.length)]} scale={zoom} blur={blur} /></AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(2,11,20,.05), transparent 48%, rgba(2,11,20,.88))'}} />
      <SceneCode number="03" label="PROPERTY TOUR" />
      <div style={{position: 'absolute', right: 55, top: 360, fontSize: 150, color: 'transparent', WebkitTextStroke: '2px rgba(255,255,255,.3)', fontWeight: 1000}}>0{slot + 1}</div>
      <div style={{position: 'absolute', left: 52, bottom: 310, padding: '16px 22px', background: gold, color: navy, fontWeight: 1000, fontSize: 23, letterSpacing: 3, transform: `perspective(700px) rotateY(-8deg) translateX(${interpolate(local,[4,18],[-160,0],clamp)}px)`}}>{labels[slot]}</div>
      <div style={{position: 'absolute', left: 52, bottom: 245, fontSize: 29, fontWeight: 900}}>LOCATION • {location}</div>
      {local < 8 && <SceneFlash />}
    </AbsoluteFill>
  );
};

const MapScene: React.FC<{location: string}> = ({location}) => {
  const frame = useCurrentFrame();
  const route = interpolate(frame, [12, 116], [820, 0], clamp);
  const pins = [
    {x: 170, y: 610, icon: 'H', label: 'HOSPITAL'},
    {x: 690, y: 430, icon: 'S', label: 'SCHOOL'},
    {x: 810, y: 900, icon: 'M', label: 'SHOPS'},
    {x: 310, y: 1030, icon: 'R', label: 'MAIN ROAD'},
  ];
  return (
    <AbsoluteFill style={{background: 'linear-gradient(145deg,#0d3551,#06192d 65%)', color: cream, fontFamily: typeface, overflow: 'hidden'}}>
      <AbsoluteFill style={{opacity: .14, backgroundImage: 'linear-gradient(rgba(255,255,255,.4) 2px,transparent 2px),linear-gradient(90deg,rgba(255,255,255,.4) 2px,transparent 2px)', backgroundSize: '86px 86px', transform: `perspective(700px) rotateX(24deg) scale(1.3) translateY(${Math.sin(frame/20)*10}px)`}} />
      <svg viewBox="0 0 1080 1500" style={{position: 'absolute', left: 0, top: 140, width: 1080, height: 1500}}>
        <path d="M90 1140 C260 920 210 650 430 580 S735 770 940 300" fill="none" stroke="rgba(255,255,255,.15)" strokeWidth="48" />
        <path d="M90 1140 C260 920 210 650 430 580 S735 770 940 300" fill="none" stroke={gold} strokeWidth="10" strokeDasharray="820" strokeDashoffset={route} />
        <path d="M120 320 C360 420 650 290 970 510" fill="none" stroke="rgba(80,216,255,.3)" strokeWidth="24" />
      </svg>
      <SceneCode number="04" label="LOCATION INTELLIGENCE" />
      <div style={{position: 'absolute', left: 52, top: 195, fontSize: 51, lineHeight: 1.03, fontWeight: 1000}}>EVERYTHING<br/><span style={{color: gold}}>WITHIN REACH</span></div>
      {pins.map((pin, i) => {
        const enter = spring({frame: frame - 28 - i * 16, fps: 30, config: {damping: 12}});
        return <div key={pin.label} style={{position: 'absolute', left: pin.x, top: pin.y, transform: `translate(-50%,-50%) scale(${enter})`, textAlign: 'center'}}><div style={{width: 82, height: 82, borderRadius: 25, display: 'grid', placeItems: 'center', fontSize: 38, background: i === 3 ? gold : 'rgba(247,241,231,.95)', color: navy, boxShadow: '0 16px 45px rgba(0,0,0,.35)'}}>{pin.icon}</div><div style={{marginTop: 9, padding: '8px 12px', borderRadius: 12, background: 'rgba(2,11,20,.84)', fontSize: 14, letterSpacing: 2, fontWeight: 950}}>{pin.label}</div></div>;
      })}
      <div style={{position: 'absolute', left: 450, top: 745, transform: `scale(${1 + Math.sin(frame/4)*.08})`}}><div style={{width: 118, height: 118, borderRadius: 999, border: `12px solid ${orange}`, boxShadow: `0 0 0 24px rgba(255,107,44,.18),0 0 45px ${orange}`}}/><div style={{marginTop: 12, marginLeft: -80, width: 280, textAlign: 'center', fontSize: 19, fontWeight: 950, letterSpacing: 2}}>{location.toUpperCase()}</div></div>
      <div style={{position: 'absolute', left: 52, right: 52, bottom: 185, fontSize: 18, opacity: .72}}>Map graphics are indicative • Verify exact route and distance during site visit</div>
      <SceneFlash color={cyan} />
    </AbsoluteFill>
  );
};

const LaserPlotScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source, fact}) => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [4, 48], [1120, 0], clamp);
  const fill = interpolate(frame, [26, 60], [0, .32], clamp);
  const valuePop = spring({frame: frame - 32, fps: 30, config: {damping: 11, stiffness: 210}});
  const points = [[205,1280],[315,720],[785,685],[925,1280]];
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <PhotoStage source={source} dark={.62} speed={1.2}/>
      <SceneCode number="02" label="LAND MEASUREMENT"/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 18px ${cyan})`}}>
        <defs><linearGradient id="laser" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={cyan} stopOpacity="0"/><stop offset=".65" stopColor={cyan}/><stop offset="1" stopColor={gold}/></linearGradient></defs>
        <polygon points={points.map(p=>p.join(',')).join(' ')} fill={`rgba(243,185,40,${fill})`} stroke={gold} strokeWidth="10" strokeDasharray="1120" strokeDashoffset={draw}/>
        <polygon points="260,1205 350,790 750,760 860,1205" fill="none" stroke="rgba(255,255,255,.9)" strokeWidth="3" strokeDasharray="16 14"/>
        {points.map(([x,y],i)=><g key={i}><line x1={x} y1="260" x2={x} y2={y} stroke="url(#laser)" strokeWidth={5+i%2*2} opacity={interpolate(frame,[i*7,i*7+18],[0,1],clamp)}/><circle cx={x} cy={y} r={10+Math.sin((frame+i*5)/4)*5} fill={cream} stroke={gold} strokeWidth="7"/></g>)}
      </svg>
      <div style={{position:'absolute',left:60,right:60,top:270,textAlign:'center'}}>
        <div style={{fontSize:20,letterSpacing:7,fontWeight:950,color:cyan}}>நில அளவு • LAND AREA</div>
        <div style={{fontSize:112,lineHeight:1,fontWeight:1000,color:gold,marginTop:22,transform:`scale(${interpolate(valuePop,[0,1],[.28,1])})`,textShadow:`0 0 45px rgba(243,185,40,.55)`}}>{clean(fact.value)}</div>
        <div style={{fontSize:23,marginTop:18,letterSpacing:3,fontWeight:900}}>LASER-MAPPED SITE BOUNDARY</div>
      </div>
      <div style={{position:'absolute',left:60,right:60,bottom:180,padding:'22px 26px',borderRadius:20,background:'rgba(2,11,20,.86)',border:`1px solid ${cyan}`,fontSize:19,textAlign:'center'}}>Illustrative boundary • Confirm measurements in the approved document and site survey</div>
      <SceneFlash color={cyan}/>
    </AbsoluteFill>
  );
};

const BuiltUpScanScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const scan=interpolate(frame,[0,105],[430,1320],clamp);
  const pop=spring({frame:frame-24,fps:30,config:{damping:11,stiffness:210}});
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <PhotoStage source={source} dark={.48} speed={1.1}/>
      <AbsoluteFill style={{opacity:.22,backgroundImage:'linear-gradient(rgba(80,216,255,.55) 1px,transparent 1px),linear-gradient(90deg,rgba(80,216,255,.55) 1px,transparent 1px)',backgroundSize:'46px 46px',clipPath:`inset(400px 80px ${Math.max(380,1920-scan)}px 80px round 24px)`}}/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 12px ${cyan})`}}><path d="M150 1200 L150 720 L330 530 L775 530 L930 710 L930 1200 Z M440 1200 V820 H680 V1200 M250 760 H410 V930 H250 Z M720 760 H865 V930 H720 Z" fill="rgba(80,216,255,.06)" stroke={cyan} strokeWidth="7" strokeDasharray="1400" strokeDashoffset={interpolate(frame,[5,70],[1400,0],clamp)}/></svg>
      <div style={{position:'absolute',left:80,right:80,top:scan,height:5,background:cyan,boxShadow:`0 0 35px 14px ${cyan}`}}/>
      <SceneCode number="03" label="BUILT-UP SCAN"/>
      <div style={{position:'absolute',left:55,right:55,top:250,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,fontWeight:950,color:cyan}}>கட்டிட பரப்பளவு • BUILT-UP AREA</div><div style={{fontSize:104,lineHeight:1.05,fontWeight:1000,color:cream,marginTop:20,transform:`scale(${interpolate(pop,[0,1],[.35,1])})`}}>{clean(fact.value)}</div></div>
      <div style={{position:'absolute',left:55,right:55,bottom:220,display:'flex',justifyContent:'space-between',padding:'20px 24px',borderRadius:22,background:'rgba(2,11,20,.84)',border:'1px solid rgba(80,216,255,.5)',fontSize:18,fontWeight:900}}><span>STRUCTURE SCAN</span><span style={{color:cyan}}>100% COMPLETE</span></div>
      <SceneFlash color={cyan}/>
    </AbsoluteFill>
  );
};

const FacingScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const rotate=interpolate(frame,[0,32],[-95,0],clamp);
  const pop=spring({frame:frame-12,fps:30,config:{damping:12}});
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <PhotoStage source={source} dark={.74}/>
      <SceneCode number="05" label="FACING DIRECTION"/>
      <div style={{position:'absolute',left:290,top:410,width:500,height:500,borderRadius:999,border:'3px solid rgba(255,255,255,.35)',boxShadow:`0 0 0 30px rgba(80,216,255,.08),inset 0 0 70px rgba(0,0,0,.45)`,transform:`scale(${pop}) rotate(${rotate}deg)`}}>
        {['N','E','S','W'].map((d,i)=><div key={d} style={{position:'absolute',left:i%2===0?225:i===1?440:15,top:i%2===0?(i===0?12:438):225,fontSize:33,fontWeight:1000,color:d==='N'?gold:cream}}>{d}</div>)}
        <div style={{position:'absolute',left:241,top:70,width:18,height:360,transformOrigin:'50% 180px',transform:`rotate(${Math.sin(frame/8)*2}deg)`,background:`linear-gradient(180deg,${gold} 0 46%,${cream} 46% 100%)`,clipPath:'polygon(50% 0,100% 48%,70% 46%,70% 100%,30% 100%,30% 46%,0 48%)',filter:`drop-shadow(0 0 15px ${gold})`}}/>
        <div style={{position:'absolute',left:205,top:205,width:84,height:84,borderRadius:999,background:navy,border:`8px solid ${gold}`}}/>
      </div>
      <div style={{position:'absolute',left:50,right:50,top:990,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,color:gold,fontWeight:950}}>பார்க்கும் திசை • FACING</div><div style={{fontSize:74,fontWeight:1000,marginTop:20}}>{clean(fact.value)}</div></div>
      <SceneFlash color={gold}/>
    </AbsoluteFill>
  );
};

const RoadMeasureScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const widen=interpolate(frame,[8,58],[0,1],clamp);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <AbsoluteFill><Visual source={source} scale={interpolate(frame,[0,155],[1.34,1.01],clamp)}/><AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.28),rgba(2,11,20,.76))'}}/></AbsoluteFill>
      <SceneCode number="06" label="ROAD WIDTH"/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 12px ${gold})`}}>
        <path d={`M${540-390*widen} 1370 L${540-120*widen} 630 M${540+390*widen} 1370 L${540+120*widen} 630`} stroke={gold} strokeWidth="9" fill="none"/>
        <path d={`M${540-350*widen} 1180 H${540+350*widen}`} stroke={cream} strokeWidth="6"/><path d={`M${540-350*widen} 1180 l45 -25 v50 Z M${540+350*widen} 1180 l-45 -25 v50 Z`} fill={cream}/>
        <path d="M540 700 V1350" stroke="rgba(255,255,255,.7)" strokeWidth="5" strokeDasharray="28 25"/>
      </svg>
      <div style={{position:'absolute',left:60,right:60,top:260,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,color:gold,fontWeight:950}}>சாலை அகலம் • ACCESS ROAD</div><div style={{fontSize:92,fontWeight:1000,marginTop:22,color:cream}}>{clean(fact.value)}</div></div>
      <div style={{position:'absolute',left:180,right:180,top:1210,padding:'18px',borderRadius:18,background:gold,color:navy,fontSize:27,fontWeight:1000,textAlign:'center',letterSpacing:2}}>MEASURED ROAD WIDTH</div>
      <SceneFlash color={gold}/>
    </AbsoluteFill>
  );
};

const ApprovalScene: React.FC<{fact: Fact}> = ({fact}) => {
  const frame=useCurrentFrame();
  const enter=spring({frame:frame-10,fps:30,config:{damping:14}});
  const check=interpolate(frame,[38,78],[220,0],clamp);
  return (
    <AbsoluteFill style={{background:`radial-gradient(circle at 50% 35%,#1b5677,${navy} 65%)`,fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <SceneCode number="07" label="DOCUMENT STATUS"/>
      <div style={{position:'absolute',left:190,top:330,width:700,height:920,borderRadius:34,background:cream,color:navy,boxShadow:'0 35px 100px rgba(0,0,0,.5)',padding:'62px 54px',transform:`perspective(1200px) rotateY(${interpolate(enter,[0,1],[-22,0])}deg) translateY(${interpolate(enter,[0,1],[120,0])}px)`,opacity:enter}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}><div style={{width:85,height:85,borderRadius:22,background:navy,color:gold,display:'grid',placeItems:'center',fontSize:31,fontWeight:1000}}>CV</div><div style={{fontSize:16,letterSpacing:3,fontWeight:950}}>PROPERTY DOCUMENT</div></div>
        <div style={{marginTop:65,fontSize:22,color:'#587084',letterSpacing:4,fontWeight:950}}>அனுமதி • APPROVAL</div>
        <div style={{fontSize:55,lineHeight:1.15,fontWeight:1000,marginTop:25}}>{clean(fact.value)}</div>
        {[0,1,2,3].map(i=><div key={i} style={{height:13,width:`${90-i*10}%`,borderRadius:9,background:'rgba(6,25,45,.13)',marginTop:i===0?62:25}}/>)}
        <svg viewBox="0 0 220 220" style={{position:'absolute',right:45,bottom:45,width:220,height:220,filter:`drop-shadow(0 0 18px rgba(22,183,122,.4))`}}><circle cx="110" cy="110" r="92" fill="rgba(22,183,122,.12)" stroke={green} strokeWidth="12"/><path d="M55 112 L92 148 L166 70" fill="none" stroke={green} strokeWidth="18" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="220" strokeDashoffset={check}/></svg>
      </div>
      <div style={{position:'absolute',left:120,right:120,bottom:235,textAlign:'center',fontSize:22,letterSpacing:4,fontWeight:950,color:green}}>✓ VERIFY ORIGINAL DOCUMENTS</div>
      <SceneFlash color={green}/><GlobalFX/>
    </AbsoluteFill>
  );
};

const DisclosureScene: React.FC<{media: VisualSource[]}> = ({media}) => {
  const frame=useCurrentFrame();
  const index=Math.min(2,Math.floor(frame/70));
  const local=frame%70;
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <AbsoluteFill style={{inset:-30}}><Visual source={media[index%Math.max(1,media.length)]} scale={interpolate(local,[0,70],[1.03,1.14],clamp)} x={interpolate(local,[0,70],[-20,24],clamp)}/></AbsoluteFill>
      <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.3),rgba(2,11,20,.82))'}}/>
      <SceneCode number="08" label="VISUAL DISCLOSURE"/>
      <div style={{position:'absolute',left:55,right:55,top:500,textAlign:'center'}}><div style={{fontSize:18,letterSpacing:7,color:gold,fontWeight:950}}>IMPORTANT INFORMATION</div><div style={{fontSize:61,lineHeight:1.1,fontWeight:1000,marginTop:24}}>REPRESENTATIVE<br/>VISUALS</div><div style={{fontSize:30,lineHeight:1.45,marginTop:30}}>இந்த காட்சிகள் பகுதியை விளக்கும்<br/>பிரதிநிதி காட்சிகள் மட்டுமே</div></div>
      <div style={{position:'absolute',left:125,right:125,bottom:235,padding:'20px',borderRadius:20,border:'1px solid rgba(255,255,255,.4)',background:'rgba(2,11,20,.7)',fontSize:18,textAlign:'center'}}>Actual property appearance and surroundings must be verified during the site visit.</div>
      {local<6&&<SceneFlash/>}
    </AbsoluteFill>
  );
};

const VerifyScene: React.FC<{price:string;location:string}> = ({price,location}) => {
  const frame=useCurrentFrame();
  const rows=[['DOC','DOCUMENTS'],['LOC','LOCATION'],['₹','PRICE'],['SIZE','MEASUREMENTS']];
  return (
    <AbsoluteFill style={{background:`radial-gradient(circle at 90% 10%,#1b5677,${navy} 58%)`,fontFamily:typeface,color:cream,padding:'210px 70px 190px',overflow:'hidden'}}>
      <SceneCode number="09" label="BUYER CHECKLIST"/>
      <div style={{fontSize:56,lineHeight:1.08,fontWeight:1000,marginTop:100}}>VERIFY FIRST.<br/><span style={{color:gold}}>DECIDE CONFIDENTLY.</span></div>
      <div style={{display:'grid',gap:16,marginTop:55}}>{rows.map(([icon,label],i)=>{const enter=spring({frame:frame-i*10,fps:30,config:{damping:15}});return <div key={label} style={{height:116,borderRadius:24,background:'rgba(255,255,255,.09)',border:'1px solid rgba(255,255,255,.19)',display:'flex',alignItems:'center',padding:'0 25px',transform:`translateX(${interpolate(enter,[0,1],[-130,0])}px)`,opacity:enter}}><div style={{width:66,height:66,borderRadius:18,background:gold,color:navy,display:'grid',placeItems:'center',fontSize:30,fontWeight:1000}}>{icon}</div><div style={{marginLeft:22,fontSize:25,letterSpacing:3,fontWeight:950}}>{label}</div><div style={{marginLeft:'auto',fontSize:34,color:green,fontWeight:1000}}>✓</div></div>})}</div>
      <div style={{marginTop:28,fontSize:22,lineHeight:1.5,opacity:.85}}>{location} • {price}<br/>நேரில் சரிபார்த்த பிறகே முடிவு செய்யுங்கள்</div>
      <GlobalFX/><SceneFlash color={gold}/>
    </AbsoluteFill>
  );
};

const FactBurstScene: React.FC<{source?: VisualSource; facts: Fact[]}> = ({source, facts}) => {
  const frame = useCurrentFrame();
  const index = Math.min(Math.max(0, facts.length - 1), Math.floor(frame / 30));
  const local = frame % 30;
  const fact = facts[index] || {label: 'PROPERTY', value: 'VERIFY ON SITE'};
  const pop = spring({frame: local, fps: 30, config: {damping: 10, stiffness: 240}});
  return (
    <AbsoluteFill style={{fontFamily: typeface, color: cream, overflow: 'hidden'}}>
      <PhotoStage source={source} dark={.68} speed={1.7} />
      <SceneCode number="05" label="THE NUMBERS" />
      <div style={{position: 'absolute', left: -30, right: -30, top: 410, textAlign: 'center'}}>
        <div style={{fontSize: 25, letterSpacing: 8, fontWeight: 950, color: cyan}}>{fact.label}</div>
        <div style={{fontSize: 86, lineHeight: 1.02, fontWeight: 1000, marginTop: 25, color: index % 2 ? cream : gold, transform: `scale(${interpolate(pop,[0,1],[.35,1])}) rotate(${interpolate(pop,[0,1],[-5,0])}deg)`, textShadow: '0 20px 70px rgba(0,0,0,.5)'}}>{clean(fact.value)}</div>
        <div style={{width: interpolate(local,[0,24],[0,760],clamp), height: 6, margin: '42px auto 0', background: `linear-gradient(90deg, transparent, ${gold}, transparent)`, boxShadow: `0 0 25px ${gold}`}} />
      </div>
      <div style={{position: 'absolute', left: 54, right: 54, bottom: 225, display: 'flex', justifyContent: 'center', gap: 12}}>{facts.slice(0,6).map((_,i)=><div key={i} style={{height: 7, width: i === index ? 90 : 28, borderRadius: 8, background: i === index ? gold : 'rgba(255,255,255,.3)'}} />)}</div>
      {local < 5 && <SceneFlash color={index % 2 ? cyan : gold} />}
    </AbsoluteFill>
  );
};

const GalleryScene: React.FC<{media: VisualSource[]; location: string}> = ({media, location}) => {
  const frame = useCurrentFrame();
  const index = Math.min(2, Math.floor(frame / 60));
  const local = frame % 60;
  const direction = index % 2 ? -1 : 1;
  const x = interpolate(local, [0,60], [-35*direction,35*direction], clamp);
  return (
    <AbsoluteFill style={{fontFamily: typeface, color: cream, overflow: 'hidden'}}>
      <AbsoluteFill style={{inset: -50}}><Visual source={media[index % Math.max(1,media.length)]} scale={1.12} x={x} /></AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(2,11,20,.05),rgba(2,11,20,.08) 54%,rgba(2,11,20,.92))'}} />
      <SceneCode number="06" label="LOOK CLOSER" />
      <div style={{position: 'absolute', left: 0, right: 0, top: interpolate(local,[0,60],[-180,2020],clamp), height: 3, background: cyan, boxShadow: `0 0 28px ${cyan}`}} />
      <div style={{position: 'absolute', left: 52, right: 52, bottom: 245}}>
        <div style={{fontSize: 17, letterSpacing: 5, color: gold, fontWeight: 950}}>FRAME {String(index+1).padStart(2,'0')} / 03</div>
        <div style={{fontSize: 54, fontWeight: 1000, marginTop: 12}}>{['A HOME THAT FEELS RIGHT','SPACE FOR EVERY MOMENT','YOUR COIMBATORE ADDRESS'][index]}</div>
        <div style={{fontSize: 24, marginTop: 14}}>LOCATION • {location}</div>
      </div>
      {local < 7 && <SceneFlash />}
    </AbsoluteFill>
  );
};

const TrustScene: React.FC<{facts: Fact[]; price: string}> = ({facts, price}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 90% 10%, #1b5677, ${navy} 58%)`, color: cream, fontFamily: typeface, padding: '170px 52px 200px', overflow: 'hidden'}}>
      <SceneCode number="07" label="VERIFY BEFORE YOU BUY" />
      <div style={{fontSize: 55, lineHeight: 1.05, fontWeight: 1000, marginTop: 80}}>CLEAR FACTS.<br/><span style={{color: gold}}>CONFIDENT DECISIONS.</span></div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 42}}>
        {facts.slice(0,6).map((fact,i)=>{const enter=spring({frame:frame-i*6,fps:30,config:{damping:16}});return <div key={fact.label} style={{minHeight: 150,padding:20,borderRadius:22,background:'rgba(255,255,255,.09)',border:'1px solid rgba(255,255,255,.18)',transform:`translateY(${interpolate(enter,[0,1],[55,0])}px) rotateX(${interpolate(enter,[0,1],[12,0])}deg)`,opacity:enter}}><div style={{fontSize:14,color:gold,letterSpacing:2.2,fontWeight:950}}>{fact.label}</div><div style={{fontSize:25,lineHeight:1.2,fontWeight:900,marginTop:10}}>{clean(fact.value)}</div></div>})}
      </div>
      <div style={{marginTop: 18, padding: '20px 24px', borderRadius: 20, background: gold, color: navy, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}><span style={{fontSize:18,letterSpacing:2,fontWeight:950}}>ASKING PRICE</span><span style={{fontSize:33,fontWeight:1000}}>{price}</span></div>
      <div style={{marginTop: 20,fontSize:20,lineHeight:1.45,opacity:.8}}>✓ ஆவணங்கள் • அளவுகள் • சாலை • விலை — நேரில் சரிபார்க்கவும்</div>
      <GlobalFX />
    </AbsoluteFill>
  );
};

const CTAScene: React.FC<Pick<PropertyVideoProps,'brand'|'cta'|'phone'|'location'>> = ({brand,cta,phone,location}) => {
  const frame = useCurrentFrame();
  const pop = spring({frame: frame - 5, fps: 30, config: {damping: 13, stiffness: 180}});
  const logoDraw = interpolate(frame,[0,38],[420,0],clamp);
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 50% 34%, #164c70, ${ink} 67%)`,color:cream,fontFamily:typeface,alignItems:'center',textAlign:'center',padding:'210px 60px 190px',overflow:'hidden'}}>
      {[0,1,2].map(i=><div key={i} style={{position:'absolute',left:540-(310+i*170)/2,top:510-(310+i*170)/2,width:310+i*170,height:310+i*170,borderRadius:999,border:`2px solid rgba(243,185,40,${.35-i*.09})`,transform:`scale(${interpolate(frame,[0,120],[.35,1.25],clamp)})`,opacity:interpolate(frame,[60,120],[1,0],clamp)}} />)}
      <svg viewBox="0 0 220 220" style={{width:190,height:190,filter:`drop-shadow(0 0 26px ${gold})`}}><rect x="14" y="14" width="192" height="192" rx="42" fill={navy} stroke={gold} strokeWidth="8" strokeDasharray="420" strokeDashoffset={logoDraw}/><path d="M55 73 L110 42 L165 73 V151 L110 182 L55 151 Z" fill="none" stroke={gold} strokeWidth="8"/><text x="110" y="132" textAnchor="middle" fill={cream} fontSize="58" fontWeight="950">CV</text></svg>
      <div style={{fontSize:25,letterSpacing:4,fontWeight:1000,marginTop:18,transform:`scale(${pop})`}}>{brand}</div>
      <div style={{fontSize:56,lineHeight:1.08,fontWeight:1000,marginTop:35}}>{cta}</div>
      <div style={{fontSize:24,color:gold,letterSpacing:3,fontWeight:950,marginTop:22}}>LOCATION • {location.toUpperCase()}</div>
      <div style={{fontSize:69,color:green,fontWeight:1000,letterSpacing:3,marginTop:28,textShadow:'0 0 34px rgba(22,183,122,.35)'}}>{phone}</div>
      <div style={{marginTop:22,padding:'17px 30px',borderRadius:99,background:gold,color:navy,fontSize:22,fontWeight:1000,letterSpacing:2}}>CALL • WHATSAPP • SITE VISIT</div>
      <SceneFlash color={gold}/>
      <GlobalFX />
    </AbsoluteFill>
  );
};

const PersistentHUD: React.FC<{brand:string;phone:string}> = ({brand,phone}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const enter = spring({frame:frame-8,fps:30,config:{damping:17}});
  return (
    <>
      <div style={{position:'absolute',zIndex:50,left:42,right:42,bottom:28,height:88,borderRadius:25,background:'rgba(2,11,20,.94)',border:'1px solid rgba(255,255,255,.2)',boxShadow:'0 18px 60px rgba(0,0,0,.42)',display:'flex',alignItems:'center',padding:'0 21px',fontFamily:typeface,color:cream,transform:`translateY(${interpolate(enter,[0,1],[120,0])}px)`,opacity:enter,overflow:'hidden'}}>
        <div style={{width:48,height:48,borderRadius:15,background:gold,color:navy,display:'grid',placeItems:'center',fontWeight:1000}}>CV</div>
        <div style={{marginLeft:13,width:255,flex:'0 0 255px',fontSize:14,lineHeight:1.05,letterSpacing:1.4,fontWeight:1000}}>{brand}</div>
        <div style={{marginLeft:'auto',width:150,flex:'0 0 150px',whiteSpace:'nowrap',fontSize:14,color:gold,fontWeight:950,letterSpacing:1}}>CALL / WHATSAPP</div>
        <div style={{marginLeft:12,width:205,flex:'0 0 205px',whiteSpace:'nowrap',textAlign:'right',fontSize:27,fontWeight:1000,letterSpacing:.5}}>{phone}</div>
      </div>
      <div style={{position:'absolute',left:45,right:45,top:38,height:6,borderRadius:9,background:'rgba(255,255,255,.2)',overflow:'hidden'}}><div style={{width:`${(frame/durationInFrames)*100}%`,height:'100%',background:`linear-gradient(90deg,${gold},${orange})`}} /></div>
    </>
  );
};

export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {
  const {durationInFrames} = useVideoConfig();
  const clips = props.actualVideos.length ? props.actualVideos : props.representativeVideos;
  const media: VisualSource[] = clips.length ? clips.map(src=>({src,video:true})) : props.images.map(src=>({src,video:false}));
  const get = (index:number) => media.length ? media[index % media.length] : undefined;
  const mapVisual: VisualSource | undefined = props.maps.length ? {src:props.maps[0],video:false} : get(0);
  return (
    <AbsoluteFill style={{backgroundColor:navy}}>
      <Sequence from={0} durationInFrames={267}><LocationJourneyScene mapSource={mapVisual} houseSource={get(1)} title={props.title} location={props.location}/></Sequence>
      <Sequence from={267} durationInFrames={123}><LaserPlotScene source={get(1)} fact={props.facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/></Sequence>
      <Sequence from={390} durationInFrames={137}><BuiltUpScanScene source={get(2)} fact={props.facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/></Sequence>
      <Sequence from={527} durationInFrames={150}><PriceScene source={get(1)} price={props.price}/></Sequence>
      <Sequence from={677} durationInFrames={98}><FacingScene source={get(0)} fact={props.facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/></Sequence>
      <Sequence from={775} durationInFrames={155}><RoadMeasureScene source={get(1)} fact={props.facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/></Sequence>
      <Sequence from={930} durationInFrames={127}><ApprovalScene fact={props.facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/></Sequence>
      <Sequence from={1057} durationInFrames={214}><DisclosureScene media={media}/></Sequence>
      <Sequence from={1271} durationInFrames={179}><VerifyScene price={props.price} location={props.location}/></Sequence>
      <Sequence from={1450} durationInFrames={Math.max(1,durationInFrames-1450)}><CTAScene brand={props.brand} cta={props.cta} phone={props.phone} location={props.location}/></Sequence>
      {props.audio && <Audio src={staticFile(props.audio)} />}
      <GlobalFX />
      <PersistentHUD brand={props.brand} phone={props.phone}/>
    </AbsoluteFill>
  );
};
