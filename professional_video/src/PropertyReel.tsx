import React from 'react';
import '@fontsource/noto-sans-tamil/400.css';
import '@fontsource/noto-sans-tamil/700.css';
import '@fontsource/noto-sans-tamil/900.css';
import {
  AbsoluteFill,
  Audio,
  Img,
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
  return source.video ? <OffthreadVideo src={staticFile(source.src)} muted style={style} /> : <Img src={staticFile(source.src)} style={style} />;
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

const MotionStreaks: React.FC<{color?: string; intensity?: number}> = ({color = cyan, intensity = 1}) => {
  const frame = useCurrentFrame();
  const burst = Math.max(
    interpolate(frame, [0, 3, 15], [0, 1, 0], clamp),
    interpolate(frame, [45, 52, 64], [0, 1, 0], clamp),
  ) * intensity;
  return (
    <AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none', opacity: burst}}>
      {Array.from({length: 11}).map((_, i) => {
        const width = 260 + (i % 4) * 130;
        const travel = interpolate(frame % 64, [0, 64], [-900, 1450], clamp);
        return <div key={i} style={{position: 'absolute', left: travel - i * 74, top: 150 + i * 142, width, height: 3 + i % 3, transform: `rotate(${-18 + i % 4 * 4}deg)`, transformOrigin: 'left center', background: `linear-gradient(90deg,transparent,${color},transparent)`, filter: 'blur(1px)', boxShadow: `0 0 18px ${color}`}} />;
      })}
    </AbsoluteFill>
  );
};

const AutopilotCamera: React.FC<{source?: VisualSource; duration?: number; mode?: 'push'|'pull'|'orbit'|'whip'; dark?: number}> = ({source, duration = 150, mode = 'push', dark = .45}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, duration], [0, 1], clamp);
  const whip = mode === 'whip' ? interpolate(frame, [0, 7, 19, duration], [-180, 38, 0, 24], clamp) : 0;
  const scale = mode === 'pull' ? interpolate(t, [0, 1], [1.34, 1.04]) : mode === 'orbit' ? 1.15 + Math.sin(t * Math.PI) * .08 : interpolate(t, [0, 1], [1.03, 1.24]);
  const x = mode === 'orbit' ? Math.sin(t * Math.PI * 1.3) * 48 : mode === 'whip' ? whip : interpolate(t, [0, 1], [-24, 30]);
  const y = mode === 'orbit' ? Math.cos(t * Math.PI) * 26 : interpolate(t, [0, 1], [18, -26]);
  const rotate = mode === 'orbit' ? interpolate(t, [0, 1], [-1.2, 1.2]) : mode === 'whip' ? interpolate(frame, [0, 10, 24], [-3.5, 1.1, 0], clamp) : 0;
  const blur = mode === 'whip' ? interpolate(frame, [0, 4, 14, 25], [12, 5, 1, 0], clamp) : 0;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: navy}}>
      <AbsoluteFill style={{inset: -55, transform: `perspective(1300px) rotateZ(${rotate}deg)`}}><Visual source={source} scale={scale} x={x} y={y} blur={blur}/></AbsoluteFill>
      <AbsoluteFill style={{background: `linear-gradient(180deg,rgba(2,11,20,.08),rgba(2,11,20,${dark}) 66%,rgba(2,11,20,.93))`}}/>
    </AbsoluteFill>
  );
};

const DepthParallax: React.FC<{source?: VisualSource; duration?: number}> = ({source, duration = 150}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, duration], [0, 1], clamp);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill style={{inset: -70, opacity: .7}}><Visual source={source} scale={1.22 + t * .12} x={-38 + t * 76} blur={8}/></AbsoluteFill>
      <AbsoluteFill style={{clipPath: 'polygon(7% 9%,93% 3%,100% 88%,0 97%)', transform: `perspective(1200px) translate3d(${25-t*50}px,${18-t*34}px,60px) scale(${1.07+t*.08}) rotateY(${interpolate(t,[0,1],[-2,2])}deg)`, filter: 'drop-shadow(0 35px 60px rgba(0,0,0,.48))'}}><Visual source={source}/></AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(2,11,20,.05),transparent 45%,rgba(2,11,20,.86))'}}/>
    </AbsoluteFill>
  );
};

const WorldCallout: React.FC<{x:number;y:number;label:string;value:string;delay:number;color?:string}> = ({x,y,label,value,delay,color=gold}) => {
  const frame = useCurrentFrame();
  const enter = spring({frame:frame-delay,fps:30,config:{damping:13,stiffness:190}});
  const line = interpolate(frame,[delay+5,delay+24],[0,112],clamp);
  return (
    <div style={{position:'absolute',left:x,top:y,transform:`translate(-50%,-50%) scale(${enter})`,transformOrigin:'center bottom',fontFamily:typeface,color:cream}}>
      <div style={{position:'absolute',left:'50%',bottom:52,width:3,height:line,background:`linear-gradient(transparent,${color})`,boxShadow:`0 0 13px ${color}`}}/>
      <div style={{width:18,height:18,borderRadius:99,background:cream,border:`5px solid ${color}`,boxShadow:`0 0 0 12px ${color}33,0 0 24px ${color}`}}/>
      <div style={{position:'absolute',left:28,top:-22,minWidth:170,padding:'12px 15px',borderRadius:14,background:'rgba(2,11,20,.9)',border:`1px solid ${color}`,boxShadow:'0 16px 35px rgba(0,0,0,.4)'}}><div style={{fontSize:12,letterSpacing:2.4,color,fontWeight:950}}>{label}</div><div style={{fontSize:20,fontWeight:1000,marginTop:4,whiteSpace:'nowrap'}}>{value}</div></div>
    </div>
  );
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

type ProfessionalHook = 'exterior' | 'interior' | 'location' | 'land' | 'price' | 'parking';

const HookScene: React.FC<{
  source?: VisualSource;
  title: string;
  location: string;
  mode: ProfessionalHook;
  highlight: string;
}> = ({source, title, location, mode, highlight}) => {
  const frame = useCurrentFrame();
  const reveal = spring({frame: frame - 3, fps: 30, config: {damping: 18, stiffness: 135}});
  const zoomByMode: Record<ProfessionalHook, [number, number]> = {
    exterior: [1.16, 1.02],
    interior: [1.04, 1.14],
    location: [1.02, 1.1],
    land: [1.12, 1.03],
    price: [1.08, 1.02],
    parking: [1.12, 1.025],
  };
  const labels: Record<ProfessionalHook, string> = {
    exterior: 'PROPERTY REVEAL',
    interior: 'INTERIOR HIGHLIGHT',
    location: 'LOCATION ADVANTAGE',
    land: 'PLOT REVEAL',
    price: 'VALUE HIGHLIGHT',
    parking: 'PARKING & ACCESS',
  };
  const [zoomStart, zoomEnd] = zoomByMode[mode];
  const zoom = interpolate(frame, [0, 105], [zoomStart, zoomEnd], clamp);
  const shutter = interpolate(frame, [0, 24], [52, 0], clamp);
  return (
    <AbsoluteFill style={{fontFamily: typeface, overflow: 'hidden', background: navy}}>
      <AbsoluteFill style={{clipPath: `inset(0 ${shutter}% 0 ${shutter}%)`}}>
        <Visual source={source} scale={zoom} />
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(2,11,20,.12), rgba(2,11,20,.08) 48%, rgba(2,11,20,.92))'}} />
      {mode === 'land' && <PlotOutline />}
      <SceneCode number="01" label={labels[mode]} />
      <div style={{position: 'absolute', left: 56, right: 56, bottom: 250, opacity: reveal, transform: `translateY(${interpolate(reveal, [0, 1], [55, 0])}px)`}}>
        <div style={{fontSize: 20, color: cyan, letterSpacing: 4, fontWeight: 950, marginBottom: 18}}>LOCATION • {location.toUpperCase()}</div>
        <div style={{fontSize: 74, lineHeight: .98, color: cream, fontWeight: 1000, textShadow: '0 8px 30px rgba(0,0,0,.5)'}}>{highlight}</div>
        <div style={{marginTop: 20, fontSize: 32, color: gold, fontWeight: 900}}>{title}</div>
      </div>
      <div style={{position: 'absolute', left: 120, right: 120, top: 430, height: 3, background: `linear-gradient(90deg, transparent, ${gold}, transparent)`, transform: `scaleX(${reveal})`, boxShadow: `0 0 20px ${gold}`}} />
      <SceneFlash color={mode === 'location' ? cyan : gold} />
    </AbsoluteFill>
  );
};

const LocationJourneyScene: React.FC<{mapSources: VisualSource[]; houseSource?: VisualSource; title:string; location:string; targetLocation:string}> = ({mapSources,houseSource,title,location,targetLocation}) => {
  const frame=useCurrentFrame();
  const mapSource = mapSources.length ? mapSources[Math.min(mapSources.length-1, Math.floor(frame/58))] : undefined;
  const mapZoom=interpolate(frame,[0,70,165],[1.05,1.75,4.8],clamp);
  const mapX=interpolate(frame,[0,70,165],[0,-45,-115],clamp);
  const mapY=interpolate(frame,[0,70,165],[0,-80,-230],clamp);
  const cityOpacity=interpolate(frame,[0,18,70,92],[0,1,1,0],clamp);
  const targetOpacity=interpolate(frame,[68,95,165],[0,1,1],clamp);
  const portal=interpolate(frame,[158,222],[0,132],clamp);
  const houseScale=interpolate(frame,[158,267],[1.48,1.02],clamp);
  const titleEnter=spring({frame:frame-205,fps:30,config:{damping:15,stiffness:180}});
  const route=interpolate(frame,[35,125],[720,0],clamp);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden',background:navy}}>
      <AbsoluteFill style={{transform:`perspective(1500px) translate(${mapX}px,${mapY}px) scale(${mapZoom}) rotateZ(${interpolate(frame,[0,165],[-1.4,1.2],clamp)}deg)`}}><Visual source={mapSource}/></AbsoluteFill>
      <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.22),rgba(2,11,20,.68))'}}/>
      <AbsoluteFill style={{opacity:interpolate(frame,[45,75,145,165],[0,.22,.22,0],clamp),backgroundImage:'linear-gradient(rgba(80,216,255,.5) 1px,transparent 1px),linear-gradient(90deg,rgba(80,216,255,.5) 1px,transparent 1px)',backgroundSize:'68px 68px',transform:`perspective(700px) rotateX(62deg) scale(1.5) translateY(${530+frame*1.2}px)`}}/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',opacity:interpolate(frame,[135,172],[1,0],clamp),filter:`drop-shadow(0 0 13px ${gold})`}}>
        <path d="M125 1260 C250 1050 360 1110 450 880 S690 760 835 510" fill="none" stroke="rgba(255,255,255,.22)" strokeWidth="35"/>
        <path d="M125 1260 C250 1050 360 1110 450 880 S690 760 835 510" fill="none" stroke={gold} strokeWidth="8" strokeDasharray="720" strokeDashoffset={route}/>
        <circle cx="540" cy="930" r={35+Math.sin(frame/4)*8} fill="rgba(255,107,44,.24)" stroke={orange} strokeWidth="9"/>
        <circle cx="540" cy="930" r="11" fill={cream}/>
      </svg>
      <div style={{position:'absolute',left:55,right:55,top:260,textAlign:'center',opacity:cityOpacity,transform:`translateY(${interpolate(frame,[0,30],[55,0],clamp)}px)`}}><div style={{fontSize:20,letterSpacing:8,color:cyan,fontWeight:950}}>LOCATION JOURNEY</div><div style={{fontSize:100,lineHeight:.95,fontWeight:1000,marginTop:22}}>COIMBATORE</div><div style={{fontSize:26,marginTop:20,letterSpacing:4}}>TAMIL NADU</div></div>
      <div style={{position:'absolute',left:55,right:55,top:1080,textAlign:'center',opacity:targetOpacity,transform:`scale(${interpolate(frame,[70,130],[.55,1],clamp)})`}}><div style={{fontSize:20,letterSpacing:7,color:gold,fontWeight:950}}>ZOOMING INTO</div><div style={{fontSize:112,lineHeight:1,fontWeight:1000,color:cream,textShadow:`0 0 40px rgba(243,185,40,.45)`,marginTop:16}}>{targetLocation.toUpperCase()}</div><div style={{display:'inline-block',marginTop:20,padding:'13px 22px',borderRadius:99,background:orange,fontSize:20,fontWeight:950,letterSpacing:2}}>TARGET LOCATION</div></div>
      {frame<158&&<><WorldCallout x={235} y={820} label="CONNECTIVITY" value="COIMBATORE" delay={52} color={cyan}/><WorldCallout x={770} y={690} label="TARGET" value={targetLocation.toUpperCase()} delay={78}/><WorldCallout x={720} y={1040} label="ACCESS" value="ROAD LINK" delay={98} color={orange}/></>}
      <AbsoluteFill style={{clipPath:`circle(${portal}% at 50% 58%)`,transform:`scale(${houseScale})`}}><DepthParallax source={houseSource} duration={109}/><AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.03),rgba(2,11,20,.78))'}}/></AbsoluteFill>
      {frame>=165&&<div style={{position:'absolute',left:540,top:890,width:interpolate(frame,[165,205],[8,700],clamp),height:5,transform:'translateX(-50%)',background:`linear-gradient(90deg,transparent,${gold},transparent)`,boxShadow:`0 0 24px ${gold}`}}/>}
      <SceneCode number="01" label={frame<160?('COIMBATORE → '+targetLocation.toUpperCase()):'ENTERING THE PROPERTY'}/>
      <div style={{position:'absolute',left:55,right:55,bottom:225,opacity:titleEnter,transform:`translateY(${interpolate(titleEnter,[0,1],[70,0])}px)`}}><div style={{fontSize:18,letterSpacing:4,color:gold,fontWeight:950}}>LOCATION • {location.toUpperCase()}</div><div style={{fontSize:62,lineHeight:1.08,fontWeight:1000,marginTop:14}}>{title}</div><div style={{fontSize:20,letterSpacing:4,fontWeight:900,marginTop:18,color:cyan}}>MAP → LOCATION → HOME</div></div>
      <MotionStreaks color={frame<160?cyan:gold} intensity={.9}/>{(frame<8||frame>=158&&frame<168)&&<SceneFlash color={frame<8?cyan:gold}/>}<GlobalFX/>
    </AbsoluteFill>
  );
};

const PriceScene: React.FC<{source?: VisualSource; price: string}> = ({source, price}) => {
  const frame = useCurrentFrame();
  const pricePop = spring({frame: frame - 24, fps: 30, config: {damping: 11, stiffness: 220}});
  const corridor = interpolate(frame, [0, 80], [0, 1250], clamp);
  return (
    <AbsoluteFill style={{fontFamily: typeface, color: cream, overflow: 'hidden'}}>
      <AutopilotCamera source={source} duration={150} mode="orbit" dark={.46}/>
      <div style={{position: 'absolute', left: 540 - corridor / 2, bottom: -130, width: corridor, height: 1380, background: 'linear-gradient(180deg, rgba(243,185,40,0), rgba(243,185,40,.45))', clipPath: 'polygon(46% 0,54% 0,100% 100%,0 100%)'}} />
      <SceneCode number="02" label="VALUE REVEAL" />
      <div style={{position: 'absolute', left: 58, right: 58, top: 315}}>
        <div style={{fontSize: 27, letterSpacing: 5, fontWeight: 950}}>START YOUR NEXT CHAPTER</div>
        <div style={{fontSize: 104, lineHeight: .92, fontWeight: 1000, color: gold, marginTop: 24, transform: `scale(${interpolate(pricePop, [0, 1], [.45, 1])})`, transformOrigin: 'left center', textShadow: `0 18px 65px rgba(0,0,0,.45)`}}>{price}</div>
        <div style={{display:'flex',gap:14,marginTop:32}}><div style={{padding:'17px 20px',borderRadius:18,background:'rgba(6,25,45,.86)',border:'1px solid rgba(255,255,255,.22)',fontSize:18,letterSpacing:3,fontWeight:950}}>ONE CLEAR ASKING PRICE</div><div style={{padding:'17px 20px',borderRadius:18,background:green,color:cream,fontSize:18,letterSpacing:2,fontWeight:950}}>VERIFY ON SITE</div></div>
      </div>
      {[0,1,2].map(i=>{const card=spring({frame:frame-42-i*9,fps:30,config:{damping:12}});return <div key={i} style={{position:'absolute',left:115+i*285,top:980+i%2*90,width:230,height:135,borderRadius:24,background:i===1?'rgba(243,185,40,.92)':'rgba(2,11,20,.88)',border:`1px solid ${i===1?cream:gold}`,color:i===1?navy:cream,display:'grid',placeItems:'center',fontSize:18,letterSpacing:2,fontWeight:1000,transform:`perspective(800px) translateY(${interpolate(card,[0,1],[180,0])}px) rotateY(${i===1?0:i===0?-12:12}deg) scale(${card})`,boxShadow:'0 25px 55px rgba(0,0,0,.42)'}}>{['CLEAR PRICE','VALUE CHECK','SITE VERIFY'][i]}</div>})}
      <MotionStreaks color={gold}/><SceneFlash color={gold} />
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
  const lift = interpolate(frame,[42,88],[0,96],clamp);
  const raised = points.map(([x,y])=>[x,y-lift]);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <PhotoStage source={source} dark={.62} speed={1.2}/>
      <SceneCode number="02" label="LAND MEASUREMENT"/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 18px ${cyan})`}}>
        <defs><linearGradient id="laser" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={cyan} stopOpacity="0"/><stop offset=".65" stopColor={cyan}/><stop offset="1" stopColor={gold}/></linearGradient></defs>
        <polygon points={`${points[0][0]},${points[0][1]} ${points[1][0]},${points[1][1]} ${raised[1][0]},${raised[1][1]} ${raised[0][0]},${raised[0][1]}`} fill="rgba(80,216,255,.18)" stroke={cyan} strokeWidth="3"/>
        <polygon points={`${points[1][0]},${points[1][1]} ${points[2][0]},${points[2][1]} ${raised[2][0]},${raised[2][1]} ${raised[1][0]},${raised[1][1]}`} fill="rgba(243,185,40,.16)" stroke={gold} strokeWidth="3"/>
        <polygon points={`${points[2][0]},${points[2][1]} ${points[3][0]},${points[3][1]} ${raised[3][0]},${raised[3][1]} ${raised[2][0]},${raised[2][1]}`} fill="rgba(255,107,44,.2)" stroke={orange} strokeWidth="3"/>
        <polygon points={raised.map(p=>p.join(',')).join(' ')} fill={`rgba(243,185,40,${fill})`} stroke={gold} strokeWidth="10" strokeDasharray="1120" strokeDashoffset={draw}/>
        <polygon points="260,1205 350,790 750,760 860,1205" fill="none" stroke="rgba(255,255,255,.9)" strokeWidth="3" strokeDasharray="16 14"/>
        {raised.map(([x,y],i)=><g key={i}><line x1={x} y1="260" x2={x} y2={y} stroke="url(#laser)" strokeWidth={5+i%2*2} opacity={interpolate(frame,[i*7,i*7+18],[0,1],clamp)}/><line x1={points[i][0]} y1={points[i][1]} x2={x} y2={y} stroke={cyan} strokeWidth="5"/><circle cx={x} cy={y} r={10+Math.sin((frame+i*5)/4)*5} fill={cream} stroke={gold} strokeWidth="7"/></g>)}
      </svg>
      <div style={{position:'absolute',left:60,right:60,top:270,textAlign:'center'}}>
        <div style={{fontSize:20,letterSpacing:7,fontWeight:950,color:cyan}}>நில அளவு • LAND AREA</div>
        <div style={{fontSize:112,lineHeight:1,fontWeight:1000,color:gold,marginTop:22,transform:`scale(${interpolate(valuePop,[0,1],[.28,1])})`,textShadow:`0 0 45px rgba(243,185,40,.55)`}}>{clean(fact.value)}</div>
        <div style={{fontSize:23,marginTop:18,letterSpacing:3,fontWeight:900}}>LASER-MAPPED SITE BOUNDARY</div>
      </div>
      <div style={{position:'absolute',left:60,right:60,bottom:180,padding:'22px 26px',borderRadius:20,background:'rgba(2,11,20,.86)',border:`1px solid ${cyan}`,fontSize:19,textAlign:'center'}}>Illustrative boundary • Confirm measurements in the approved document and site survey</div>
      <MotionStreaks color={cyan} intensity={.65}/><SceneFlash color={cyan}/>
    </AbsoluteFill>
  );
};

const BuiltUpScanScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const scan=interpolate(frame,[0,105],[430,1320],clamp);
  const pop=spring({frame:frame-24,fps:30,config:{damping:11,stiffness:210}});
  const floorRise=interpolate(frame,[38,92],[150,0],clamp);
  const floorOpacity=interpolate(frame,[30,52],[0,1],clamp);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <PhotoStage source={source} dark={.48} speed={1.1}/>
      <AbsoluteFill style={{opacity:.22,backgroundImage:'linear-gradient(rgba(80,216,255,.55) 1px,transparent 1px),linear-gradient(90deg,rgba(80,216,255,.55) 1px,transparent 1px)',backgroundSize:'46px 46px',clipPath:`inset(400px 80px ${Math.max(380,1920-scan)}px 80px round 24px)`}}/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 12px ${cyan})`}}><path d="M150 1200 L150 720 L330 530 L775 530 L930 710 L930 1200 Z M440 1200 V820 H680 V1200 M250 760 H410 V930 H250 Z M720 760 H865 V930 H720 Z" fill="rgba(80,216,255,.06)" stroke={cyan} strokeWidth="7" strokeDasharray="1400" strokeDashoffset={interpolate(frame,[5,70],[1400,0],clamp)}/></svg>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',opacity:floorOpacity,transform:`translateY(${floorRise}px)`,filter:`drop-shadow(0 22px 25px rgba(0,0,0,.55)) drop-shadow(0 0 15px ${cyan})`}}>
        <polygon points="210,1180 530,1010 875,1160 540,1355" fill="rgba(6,25,45,.84)" stroke={cyan} strokeWidth="7"/>
        <polygon points="210,1180 540,1355 540,1410 210,1238" fill="rgba(80,216,255,.18)" stroke={cyan} strokeWidth="4"/>
        <polygon points="540,1355 875,1160 875,1217 540,1410" fill="rgba(243,185,40,.16)" stroke={gold} strokeWidth="4"/>
        <path d="M370 1095 L700 1255 M530 1010 L540 1355 M690 1090 L365 1270 M470 1042 L800 1192" fill="none" stroke="rgba(255,255,255,.8)" strokeWidth="5"/>
        <rect x="430" y="1130" width="150" height="110" transform="rotate(27 505 1185)" fill="rgba(243,185,40,.25)" stroke={gold} strokeWidth="5"/>
      </svg>
      <div style={{position:'absolute',left:80,right:80,top:scan,height:5,background:cyan,boxShadow:`0 0 35px 14px ${cyan}`}}/>
      <SceneCode number="03" label="BUILT-UP SCAN"/>
      <div style={{position:'absolute',left:55,right:55,top:250,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,fontWeight:950,color:cyan}}>கட்டிட பரப்பளவு • BUILT-UP AREA</div><div style={{fontSize:104,lineHeight:1.05,fontWeight:1000,color:cream,marginTop:20,transform:`scale(${interpolate(pop,[0,1],[.35,1])})`}}>{clean(fact.value)}</div></div>
      <div style={{position:'absolute',left:55,right:55,bottom:220,display:'flex',justifyContent:'space-between',padding:'20px 24px',borderRadius:22,background:'rgba(2,11,20,.84)',border:'1px solid rgba(80,216,255,.5)',fontSize:18,fontWeight:900}}><span>STRUCTURE SCAN</span><span style={{color:cyan}}>100% COMPLETE</span></div>
      <WorldCallout x={760} y={1120} label="AUTO FLOOR PLAN" value={clean(fact.value)} delay={48} color={cyan}/><MotionStreaks color={cyan} intensity={.55}/><SceneFlash color={cyan}/>
    </AbsoluteFill>
  );
};

const FacingScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const rotate=interpolate(frame,[0,32],[-95,0],clamp);
  const pop=spring({frame:frame-12,fps:30,config:{damping:12}});
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <AutopilotCamera source={source} duration={98} mode="whip" dark={.72}/>
      <SceneCode number="05" label="FACING DIRECTION"/>
      <div style={{position:'absolute',left:290,top:410,width:500,height:500,borderRadius:999,border:'3px solid rgba(255,255,255,.35)',boxShadow:`0 0 0 30px rgba(80,216,255,.08),inset 0 0 70px rgba(0,0,0,.45)`,transform:`scale(${pop}) rotate(${rotate}deg)`}}>
        {['N','E','S','W'].map((d,i)=><div key={d} style={{position:'absolute',left:i%2===0?225:i===1?440:15,top:i%2===0?(i===0?12:438):225,fontSize:33,fontWeight:1000,color:d==='N'?gold:cream}}>{d}</div>)}
        <div style={{position:'absolute',left:241,top:70,width:18,height:360,transformOrigin:'50% 180px',transform:`rotate(${Math.sin(frame/8)*2}deg)`,background:`linear-gradient(180deg,${gold} 0 46%,${cream} 46% 100%)`,clipPath:'polygon(50% 0,100% 48%,70% 46%,70% 100%,30% 100%,30% 46%,0 48%)',filter:`drop-shadow(0 0 15px ${gold})`}}/>
        <div style={{position:'absolute',left:205,top:205,width:84,height:84,borderRadius:999,background:navy,border:`8px solid ${gold}`}}/>
      </div>
      <div style={{position:'absolute',left:50,right:50,top:990,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,color:gold,fontWeight:950}}>பார்க்கும் திசை • FACING</div><div style={{fontSize:74,fontWeight:1000,marginTop:20}}>{clean(fact.value)}</div></div>
      <WorldCallout x={760} y={890} label="ORIENTATION" value="NORTH AXIS" delay={32}/><MotionStreaks color={gold} intensity={.8}/><SceneFlash color={gold}/>
    </AbsoluteFill>
  );
};

const RoadMeasureScene: React.FC<{source?: VisualSource; fact: Fact}> = ({source,fact}) => {
  const frame=useCurrentFrame();
  const widen=interpolate(frame,[8,58],[0,1],clamp);
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <AutopilotCamera source={source} duration={155} mode="pull" dark={.66}/>
      <SceneCode number="06" label="ROAD WIDTH"/>
      <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%',filter:`drop-shadow(0 0 12px ${gold})`}}>
        <path d={`M${540-390*widen} 1370 L${540-120*widen} 630 M${540+390*widen} 1370 L${540+120*widen} 630`} stroke={gold} strokeWidth="9" fill="none"/>
        <path d={`M${540-350*widen} 1180 H${540+350*widen}`} stroke={cream} strokeWidth="6"/><path d={`M${540-350*widen} 1180 l45 -25 v50 Z M${540+350*widen} 1180 l-45 -25 v50 Z`} fill={cream}/>
        <path d="M540 700 V1350" stroke="rgba(255,255,255,.7)" strokeWidth="5" strokeDasharray="28 25"/>
      </svg>
      <div style={{position:'absolute',left:60,right:60,top:260,textAlign:'center'}}><div style={{fontSize:20,letterSpacing:6,color:gold,fontWeight:950}}>சாலை அகலம் • ACCESS ROAD</div><div style={{fontSize:92,fontWeight:1000,marginTop:22,color:cream}}>{clean(fact.value)}</div></div>
      <div style={{position:'absolute',left:180,right:180,top:1210,padding:'18px',borderRadius:18,background:gold,color:navy,fontSize:27,fontWeight:1000,textAlign:'center',letterSpacing:2}}>MEASURED ROAD WIDTH</div>
      <WorldCallout x={250} y={910} label="ROAD EDGE" value="TRACKED" delay={26} color={cyan}/><WorldCallout x={785} y={915} label="ROAD EDGE" value="TRACKED" delay={38}/><MotionStreaks color={gold} intensity={.7}/><SceneFlash color={gold}/>
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
      <MotionStreaks color={green} intensity={.6}/><SceneFlash color={green}/><GlobalFX/>
    </AbsoluteFill>
  );
};

const DisclosureScene: React.FC<{media: VisualSource[]}> = ({media}) => {
  const frame=useCurrentFrame();
  const index=Math.min(2,Math.floor(frame/70));
  const local=frame%70;
  const classifications=[['LOCATION CONTEXT','AUTOMATIC SOURCE'],['NEIGHBOURHOOD','LOCATION BASED'],['PROPERTY VISUAL','REPRESENTATIVE']];
  return (
    <AbsoluteFill style={{fontFamily:typeface,color:cream,overflow:'hidden'}}>
      <DepthParallax source={media[index%Math.max(1,media.length)]} duration={70}/>
      <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.3),rgba(2,11,20,.82))'}}/>
      <SceneCode number="08" label="VISUAL DISCLOSURE"/>
      <div style={{position:'absolute',left:55,right:55,top:250,display:'flex',justifyContent:'center',gap:12}}>{classifications.map(([label,status],i)=>{const active=i===index;return <div key={label} style={{padding:'13px 15px',borderRadius:16,background:active?gold:'rgba(2,11,20,.7)',color:active?navy:cream,border:`1px solid ${active?gold:'rgba(255,255,255,.22)'}`,fontSize:12,letterSpacing:1.4,fontWeight:1000,transform:`translateY(${active?-8:0}px) scale(${active?1.04:.94})`,opacity:active?1:.58}}><div>{label}</div><div style={{fontSize:10,marginTop:5,opacity:.8}}>{status}</div></div>})}</div>
      <div style={{position:'absolute',left:55,right:55,top:520,textAlign:'center',clipPath:`inset(0 ${interpolate(local,[0,18],[100,0],clamp)}% 0 0)`}}><div style={{fontSize:18,letterSpacing:7,color:gold,fontWeight:950}}>IMPORTANT INFORMATION</div><div style={{fontSize:61,lineHeight:1.1,fontWeight:1000,marginTop:24}}>REPRESENTATIVE<br/>VISUALS</div><div style={{fontSize:30,lineHeight:1.45,marginTop:30}}>இந்த காட்சிகள் பகுதியை விளக்கும்<br/>பிரதிநிதி காட்சிகள் மட்டுமே</div></div>
      <div style={{position:'absolute',left:125,right:125,bottom:235,padding:'20px',borderRadius:20,border:'1px solid rgba(255,255,255,.4)',background:'rgba(2,11,20,.7)',fontSize:18,textAlign:'center'}}>Actual property appearance and surroundings must be verified during the site visit.</div>
      <MotionStreaks color={index===2?gold:cyan} intensity={.7}/>{local<6&&<SceneFlash/>}
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
      <MotionStreaks color={gold} intensity={.6}/><GlobalFX/><SceneFlash color={gold}/>
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
      <MotionStreaks color={gold} intensity={.75}/><SceneFlash color={gold}/>
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
      <div style={{position:'absolute',zIndex:50,left:42,right:42,bottom:25,height:72,borderRadius:22,background:'rgba(2,11,20,.92)',border:'1px solid rgba(255,255,255,.2)',boxShadow:'0 16px 48px rgba(0,0,0,.4)',display:'flex',alignItems:'center',padding:'0 18px',fontFamily:typeface,color:cream,transform:`translateY(${interpolate(enter,[0,1],[120,0])}px)`,opacity:enter,overflow:'hidden',backdropFilter:'blur(10px)'}}>
        <div style={{width:42,height:42,borderRadius:13,background:gold,color:navy,display:'grid',placeItems:'center',fontWeight:1000}}>CV</div>
        <div style={{marginLeft:12,width:235,flex:'0 0 235px',fontSize:13,lineHeight:1.05,letterSpacing:1.3,fontWeight:1000}}>{brand}</div>
        <div style={{marginLeft:'auto',width:150,flex:'0 0 150px',whiteSpace:'nowrap',fontSize:14,color:gold,fontWeight:950,letterSpacing:1}}>CALL / WHATSAPP</div>
        <div style={{marginLeft:12,width:205,flex:'0 0 205px',whiteSpace:'nowrap',textAlign:'right',fontSize:27,fontWeight:1000,letterSpacing:.5,color:frame%45<4?gold:cream,textShadow:frame%45<4?`0 0 18px ${gold}`:undefined}}>{phone}</div>
      </div>
      <div style={{position:'absolute',left:45,right:45,top:38,height:6,borderRadius:9,background:'rgba(255,255,255,.2)',overflow:'hidden'}}><div style={{width:`${(frame/durationInFrames)*100}%`,height:'100%',background:`linear-gradient(90deg,${gold},${orange})`}} /></div>
    </>
  );
};

export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {
  const actualMedia: VisualSource[] = props.actualVideos.map(src=>({src,video:true}));
  const sceneSources = (scene:string): VisualSource[] => {
    if (actualMedia.length) return actualMedia;
    return (props.sceneMedia?.[scene] || []).map(src=>({src,video:true}));
  };
  const sourceFor = (scene:string,index=0): VisualSource | undefined => {
    const sources=sceneSources(scene);
    return sources.length ? sources[index%sources.length] : undefined;
  };
  const mapVisuals: VisualSource[] = props.maps.map(src=>({src,video:false}));
  const facts = props.facts;
  const factValue = (label:string) => facts.find(f=>f.label === label)?.value || '';
  const verified = (value:string) => Boolean(value && !/verify|not specified/i.test(value));
  const hookCandidates: Array<{mode:ProfessionalHook; source?:VisualSource; highlight:string; enabled:boolean}> = [
    {mode:'exterior', source:sourceFor('exterior'), highlight:'A HOME WORTH SEEING', enabled:Boolean(sourceFor('exterior'))},
    {mode:'interior', source:sourceFor('interior') || sourceFor('living') || sourceFor('kitchen'), highlight:'STEP INSIDE', enabled:Boolean(sourceFor('interior') || sourceFor('living') || sourceFor('kitchen'))},
    {mode:'location', source:sourceFor('road') || mapVisuals[0], highlight:props.locationLabel.toUpperCase(), enabled:Boolean(sourceFor('road') || mapVisuals[0])},
    {mode:'land', source:sourceFor('land') || sourceFor('exterior'), highlight:factValue('LAND'), enabled:verified(factValue('LAND')) && Boolean(sourceFor('land') || sourceFor('exterior'))},
    {mode:'price', source:sourceFor('exterior',1) || sourceFor('exterior'), highlight:props.price, enabled:verified(props.price) && Boolean(sourceFor('exterior'))},
    {mode:'parking', source:sourceFor('exterior') || sourceFor('road'), highlight:factValue('PARKING'), enabled:verified(factValue('PARKING')) && Boolean(sourceFor('exterior') || sourceFor('road'))},
  ];
  const availableHooks = hookCandidates.filter(h=>h.enabled);
  const hookSeed = Array.from(props.videoId).reduce((sum,ch)=>sum + ch.charCodeAt(0),0);
  const selectedHook = availableHooks[hookSeed % Math.max(1, availableHooks.length)] || {
    mode:'exterior' as ProfessionalHook,
    source:sourceFor('exterior') || sourceFor('land') || sourceFor('road'),
    highlight:'PROPERTY REVEAL',
  };
  const sceneNodes: Record<string, React.ReactNode> = {
    location: <HookScene source={selectedHook.source} title={props.title} location={props.location} mode={selectedHook.mode} highlight={selectedHook.highlight}/>,
    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,
    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,
    price: <PriceScene source={sourceFor('exterior',1)} price={props.price}/>,
    facing: <FacingScene source={sourceFor('exterior') || sourceFor('land',1)} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,
    road: <RoadMeasureScene source={sourceFor('road')} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,
    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,
    verify: <VerifyScene price={props.price} location={props.location}/>,
    cta: <CTAScene brand={props.brand} cta={props.cta} phone={props.phone} location={props.location}/>,
  };
  const defaultOrder = ['location','land','builtUp','price','facing','road','approval','verify','cta'];
  const order = props.sceneOrder?.length ? props.sceneOrder : defaultOrder;
  let cursor = 0;
  const starts: Record<string, number> = {};
  const scheduled = order.map((scene) => {
    const from = cursor;
    const duration = Math.max(1, props.sceneDurations?.[scene] || 120);
    starts[scene] = from;
    cursor += duration;
    return {scene, from, duration};
  });
  return (
    <AbsoluteFill style={{backgroundColor:navy}}>
      {scheduled.map(({scene,from,duration}) => <Sequence key={scene} from={from} durationInFrames={duration}>{sceneNodes[scene]}</Sequence>)}
      {props.voiceSegments?.map((segment) => <Sequence key={`voice-${segment.scene}`} from={starts[segment.scene] || 0} durationInFrames={props.sceneDurations[segment.scene] || 120}><Audio src={staticFile(segment.src)} volume={1}/></Sequence>)}
      {!props.voiceSegments?.length && props.audio && <Audio src={staticFile(props.audio)} volume={1}/>} 
      <GlobalFX />
      <PersistentHUD brand={props.brand} phone={props.phone}/>
    </AbsoluteFill>
  );
};
