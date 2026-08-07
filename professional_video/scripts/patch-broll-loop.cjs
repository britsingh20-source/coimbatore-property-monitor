const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '..', 'src', 'PropertyReel.tsx');
let source = fs.readFileSync(target, 'utf8');

const replacements = [
  [
    "import type {Fact, PropertyVideoProps} from './types';",
    "import type {Fact, PropertyVideoProps} from './types';\nimport {CinematicGrade, SceneTransitionOverlay, SceneVFXOverlay} from './CinematicVFX';",
  ],
  ["  OffthreadVideo,\n  Sequence,", "  OffthreadVideo,\n  Loop,\n  Sequence,"],
  [
    "  return source.video ? <OffthreadVideo src={staticFile(source.src)} muted style={style} /> : <Img src={staticFile(source.src)} style={style} />;",
    "  return source.video ? <Loop durationInFrames={72}><OffthreadVideo src={staticFile(source.src)} muted style={style} /></Loop> : <Img src={staticFile(source.src)} style={style} />;",
  ],
  [
    "  const facts = props.facts;\n  const sceneNodes:",
    "  const facts = props.facts;\n  const uniqueSources = (items:VisualSource[]) => items.filter((item,index,array)=>array.findIndex(other=>other.src===item.src)===index);\n  const styleNames = ['cinematic','fast-cut','premium','location-first','price-first'] as const;\n  const automaticStyle = styleNames[Array.from(props.videoId).reduce((sum,char)=>sum+char.charCodeAt(0),0)%styleNames.length];\n  const style = props.styleVariant || automaticStyle;\n  const rotatePool = (items: VisualSource[], offset: number) => items.length ? [...items.slice(offset % items.length), ...items.slice(0, offset % items.length)] : items;\n  const styleOffset = styleNames.indexOf(style);\n  const exteriorPool = uniqueSources(rotatePool(sceneSources('exterior'), styleOffset));\n  const interiorPool = uniqueSources(rotatePool(sceneSources('interior'), styleOffset+1));\n  const roadPool = uniqueSources(rotatePool(sceneSources('road'), styleOffset+2));\n  const landPool = uniqueSources(rotatePool(sceneSources('land'), styleOffset+3));\n  const globalPool = uniqueSources([...exteriorPool,...interiorPool,...roadPool,...landPool]);\n  const usedBroll = new Set<string>();\n  const allocate = (primary:VisualSource[], fallback:VisualSource[], count:number, offset:number) => {\n    const candidates = uniqueSources([...rotatePool(primary,offset),...rotatePool(fallback,offset)]);\n    const fresh = candidates.filter(item=>!usedBroll.has(item.src));\n    const chosen = fresh.slice(0,count);\n    chosen.forEach(item=>usedBroll.add(item.src));\n    if (chosen.length === 0 && candidates.length) { chosen.push(candidates[0]); }\n    return chosen;\n  };\n  // Reserve the most semantically important categories first. Reuse happens only\n  // after the available relevant/global pool has actually been exhausted.\n  const roadScenePool = allocate(roadPool, [], 2, 0);\n  const builtScenePool = allocate(interiorPool, exteriorPool, 2, 1);\n  const landScenePool = allocate(landPool, exteriorPool, 2, 2);\n  const locationScenePool = allocate(exteriorPool, [...roadPool,...landPool], 3, 3);\n  const priceScenePool = allocate([...exteriorPool,...interiorPool], globalPool, 2, 4);\n  const facingScenePool = allocate([...exteriorPool,...landPool], globalPool, 2, 5);\n  const approvalScenePool = allocate([...exteriorPool,...interiorPool], globalPool, 2, 6);\n  const verifyScenePool = allocate(globalPool, globalPool, 3, 7);\n  const ctaScenePool = allocate([...exteriorPool,...interiorPool], globalPool, 2, 8);\n  const fallbackPool = globalPool.length ? globalPool : uniqueSources(props.representativeVideos.map(src=>({src,video:true})));\n  const safePool = (items:VisualSource[]) => items.length ? items : fallbackPool;\n  const sceneValue = (scene:string) => ({location: props.location, land: facts[0]?.value, builtUp: facts[1]?.value, price: props.price, facing: facts[2]?.value, road: facts[3]?.value, approval: facts[5]?.value}[scene] || '');\n  const sceneNodes:",
  ],
  [
    "    location: props.templateVariant === 'plot'\n      ? <LocationJourneyScene mapSources={mapVisuals} houseSource={sourceFor('exterior') || sourceFor('land')} title={props.title} location={props.location} targetLocation={props.locationLabel}/>\n      : <HookScene source={sourceFor('exterior')} title={props.title} location={props.location}/>,",
    "    location: <RotatingBrollScene media={safePool(locationScenePool)} shotFrames={48}/>,",
  ],
  [
    "    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
    "    land: <RotatingBrollScene media={safePool(landScenePool)} shotFrames={62}/>,",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: <RotatingBrollScene media={safePool(builtScenePool)} shotFrames={58}/>,",
  ],
  [
    "    price: <PriceScene source={sourceFor('exterior',1)} price={props.price}/>,",
    "    price: <RotatingBrollScene media={safePool(priceScenePool)} shotFrames={64}/>,",
  ],
  [
    "    facing: <FacingScene source={sourceFor('exterior') || sourceFor('land',1)} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
    "    facing: <RotatingBrollScene media={safePool(facingScenePool)} shotFrames={64}/>,",
  ],
  [
    "    road: <RoadMeasureScene source={sourceFor('road')} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
    "    road: <RotatingBrollScene media={safePool(roadScenePool)} shotFrames={58}/>,",
  ],
  [
    "    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
    "    approval: <RotatingBrollScene media={safePool(approvalScenePool)} shotFrames={64}/>,",
  ],
  [
    "    verify: <VerifyScene price={props.price} location={props.location}/>,",
    "    verify: <RotatingBrollScene media={safePool(verifyScenePool)} shotFrames={58}/>,",
  ],
  [
    "    cta: <CTAScene brand={props.brand} cta={props.cta} phone={props.phone} location={props.location}/>,",
    "    cta: <MovingCTAScene media={safePool(ctaScenePool)} brand={props.brand} cta={props.cta} phone={props.phone} location={props.location}/>,",
  ],
  [
    "export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
    "const RotatingBrollScene: React.FC<{media:VisualSource[];shotFrames?:number}> = ({media,shotFrames=64}) => {\n  const frame = useCurrentFrame();\n  if (!media.length) return <AbsoluteFill><Visual /></AbsoluteFill>;\n  const fadeFrames = 8;\n  const slot = Math.floor(frame / shotFrames);\n  const local = frame % shotFrames;\n  const currentIndex = slot % media.length;\n  const nextIndex = (currentIndex + 1) % media.length;\n  const current = media[currentIndex];\n  const next = media[nextIndex];\n  const fade = interpolate(local,[shotFrames-fadeFrames,shotFrames],[0,1],clamp);\n  const scale = interpolate(local,[0,shotFrames],[1.02,1.075],clamp);\n  return <AbsoluteFill style={{overflow:'hidden',backgroundColor:navy}}>\n    <AbsoluteFill><Visual source={current} scale={scale}/></AbsoluteFill>\n    {media.length > 1 && <AbsoluteFill style={{opacity:fade}}><Visual source={next} scale={1.025}/></AbsoluteFill>}\n    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.03),rgba(2,11,20,.08) 55%,rgba(2,11,20,.62))'}}/>\n  </AbsoluteFill>;\n};\n\nconst SceneFactOverlay: React.FC<{scene:string;value:string}> = ({scene,value}) => {\n  if (!value || scene === 'location' || scene === 'verify' || scene === 'cta') return null;\n  const labels:Record<string,string> = {land:'LAND AREA',builtUp:'BUILT-UP',price:'PRICE',facing:'FACING',road:'ROAD WIDTH',approval:'APPROVAL'};\n  const frame = useCurrentFrame();\n  const enter = spring({frame:frame-5,fps:30,config:{damping:16,stiffness:170}});\n  const strong = scene === 'price';\n  return <div style={{position:'absolute',zIndex:35,left:52,right:52,top:strong?250:170,fontFamily:typeface,color:cream,textAlign:strong?'center':'left',transform:`translateY(${interpolate(enter,[0,1],[45,0])}px)`,opacity:enter}}>\n    <div style={{fontSize:15,letterSpacing:4,fontWeight:950,color:gold}}>{labels[scene] || scene.toUpperCase()}</div>\n    <div style={{fontSize:strong?78:48,lineHeight:1.05,fontWeight:1000,marginTop:10,textShadow:'0 10px 35px rgba(0,0,0,.75)'}}>{value}</div>\n  </div>;\n};\n\nconst MovingCTAScene: React.FC<{media:VisualSource[];brand:string;cta:string;phone:string;location:string}> = ({media,brand,cta,phone,location}) => (\n  <AbsoluteFill style={{fontFamily:typeface,color:cream}}>\n    <RotatingBrollScene media={media} shotFrames={60}/>\n    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.18),rgba(2,11,20,.62) 52%,rgba(2,11,20,.9))'}}/>\n    <div style={{position:'absolute',left:55,right:55,bottom:190,textAlign:'center'}}>\n      <div style={{fontSize:18,letterSpacing:3,color:gold,fontWeight:950}}>{brand}</div>\n      <div style={{fontSize:42,lineHeight:1.12,fontWeight:1000,marginTop:14}}>{cta}</div>\n      <div style={{fontSize:20,marginTop:12,opacity:.9}}>{location}</div>\n      <div style={{fontSize:62,color:'#2cdc94',fontWeight:1000,marginTop:18}}>{phone}</div>\n      <div style={{display:'inline-block',marginTop:12,padding:'12px 24px',borderRadius:999,background:gold,color:navy,fontSize:18,fontWeight:1000}}>CALL • WHATSAPP • SITE VISIT</div>\n    </div>\n  </AbsoluteFill>\n);\n\nconst SyncedCaption: React.FC<{text:string}> = ({text}) => (\n  <div style={{position:'absolute',zIndex:80,left:58,right:58,bottom:125,padding:'14px 20px',borderRadius:18,background:'linear-gradient(135deg,rgba(2,11,20,.9),rgba(6,25,45,.82))',border:'1px solid rgba(255,255,255,.18)',boxShadow:'0 16px 42px rgba(0,0,0,.45)',backdropFilter:'blur(12px)',fontFamily:typeface,fontSize:28,lineHeight:1.34,fontWeight:900,textAlign:'center',color:cream,textShadow:'0 3px 12px rgba(0,0,0,.7)'}}>{text}</div>\n);\n\nexport const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
  ],
  [
    "      {scheduled.map(({scene,from,duration}) => <Sequence key={scene} from={from} durationInFrames={duration}>{sceneNodes[scene]}</Sequence>)}",
    "      {scheduled.map(({scene,from,duration},index) => <Sequence key={scene} from={from + 2} durationInFrames={Math.max(1,duration - 2)}><AbsoluteFill>{sceneNodes[scene]}<SceneFactOverlay scene={scene} value={sceneValue(scene)}/><SceneVFXOverlay scene={scene} value={sceneValue(scene)} styleVariant={style}/><SceneTransitionOverlay styleVariant={style} duration={Math.max(1,duration - 2)} index={index}/></AbsoluteFill></Sequence>)}",
  ],
  [
    "      {props.voiceSegments?.map((segment) => <Sequence key={`voice-${segment.scene}`} from={starts[segment.scene] || 0} durationInFrames={props.sceneDurations[segment.scene] || 120}><Audio src={staticFile(segment.src)} volume={1}/></Sequence>)}",
    "      {props.voiceSegments?.map((segment) => { const start = starts[segment.scene] || 0; const speechDuration = Math.max(1, segment.durationInFrames || ((props.sceneDurations[segment.scene] || 120) - 11)); return segment.text ? <Sequence key={`caption-${segment.scene}`} from={start + 2} durationInFrames={Math.max(1,speechDuration - 2)}><SyncedCaption text={segment.text}/></Sequence> : null; })}",
  ],
  [
    "      {!props.voiceSegments?.length && props.audio && <Audio src={staticFile(props.audio)} volume={1}/>} ",
    "      {props.audio && <Audio src={staticFile(props.audio)} volume={1}/>} ",
  ],
  [
    "      <GlobalFX />\n      <PersistentHUD brand={props.brand} phone={props.phone}/>",
    "      <CinematicGrade styleVariant={style}/>\n      <PersistentHUD brand={props.brand} phone={props.phone}/>",
  ],
];

for (const [before, after] of replacements) {
  if (before === after) continue;
  if (!source.includes(before)) {
    if (source.includes(after)) continue;
    throw new Error(`Expected PropertyReel snippet not found: ${before.slice(0, 100)}`);
  }
  source = source.replace(before, after);
}
fs.writeFileSync(target, source);

console.log('Applied narration-driven semantic B-roll, global no-repeat allocation, short natural audio gaps, moving CTA, synced captions, and cinematic VFX');
