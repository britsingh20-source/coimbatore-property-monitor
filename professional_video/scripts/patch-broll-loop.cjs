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
    "  const facts = props.facts;\n  const allBroll: VisualSource[] = ['exterior','interior','road','land'].flatMap(sceneSources);\n  const uniqueSources = (items:VisualSource[]) => items.filter((item,index,array)=>array.findIndex(other=>other.src===item.src)===index);\n  const styleNames = ['cinematic','fast-cut','premium','location-first','price-first'] as const;\n  const automaticStyle = styleNames[Array.from(props.videoId).reduce((sum,char)=>sum+char.charCodeAt(0),0)%styleNames.length];\n  const style = props.styleVariant || automaticStyle;\n  const rotatePool = (items: VisualSource[], offset: number) => items.length ? [...items.slice(offset % items.length), ...items.slice(0, offset % items.length)] : items;\n  const styleOffset = styleNames.indexOf(style);\n  const exteriorPool = uniqueSources(rotatePool(sceneSources('exterior'), styleOffset));\n  const interiorPool = uniqueSources(rotatePool(sceneSources('interior'), styleOffset+1));\n  const roadPool = uniqueSources(rotatePool(sceneSources('road'), styleOffset+2));\n  const landPool = uniqueSources(rotatePool(sceneSources('land'), styleOffset+3));\n  const globalPool = uniqueSources(rotatePool(allBroll, styleOffset+3));\n  const scenePlaylist = (primary:VisualSource[], offset:number) => uniqueSources([...rotatePool(primary,offset),...rotatePool(globalPool,offset)]);\n  const locationPool = scenePlaylist([...exteriorPool,...roadPool,...landPool,...interiorPool],0);\n  const landScenePool = scenePlaylist([...landPool,...exteriorPool,...roadPool],2);\n  const builtScenePool = scenePlaylist([...interiorPool,...exteriorPool],4);\n  const priceScenePool = scenePlaylist([...exteriorPool,...interiorPool],6);\n  const facingScenePool = scenePlaylist([...exteriorPool,...landPool],8);\n  const roadScenePool = scenePlaylist([...roadPool,...exteriorPool],10);\n  const approvalScenePool = scenePlaylist([...interiorPool,...exteriorPool,...landPool],12);\n  const verifyScenePool = scenePlaylist(globalPool,14);\n  const sceneValue = (scene:string) => ({location: props.location, land: facts[0]?.value, builtUp: facts[1]?.value, price: props.price, facing: facts[2]?.value, road: facts[3]?.value, approval: facts[5]?.value}[scene] || '');\n  const sceneNodes:",
  ],
  [
    "    location: props.templateVariant === 'plot'\n      ? <LocationJourneyScene mapSources={mapVisuals} houseSource={sourceFor('exterior') || sourceFor('land')} title={props.title} location={props.location} targetLocation={props.locationLabel}/>\n      : <HookScene source={sourceFor('exterior')} title={props.title} location={props.location}/>,",
    "    location: <RotatingBrollScene media={locationPool} startOffset={0}/>,",
  ],
  [
    "    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
    "    land: <RotatingBrollScene media={landScenePool} startOffset={1}/>,",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: <RotatingBrollScene media={builtScenePool} startOffset={2}/>,",
  ],
  [
    "    price: <PriceScene source={sourceFor('exterior',1)} price={props.price}/>,",
    "    price: <RotatingBrollScene media={priceScenePool} startOffset={3}/>,",
  ],
  [
    "    facing: <FacingScene source={sourceFor('exterior') || sourceFor('land',1)} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
    "    facing: <RotatingBrollScene media={facingScenePool} startOffset={4}/>,",
  ],
  [
    "    road: <RoadMeasureScene source={sourceFor('road')} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
    "    road: <RotatingBrollScene media={roadScenePool} startOffset={5}/>,",
  ],
  [
    "    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
    "    approval: <RotatingBrollScene media={approvalScenePool} startOffset={6}/>,",
  ],
  [
    "    verify: <VerifyScene price={props.price} location={props.location}/>,",
    "    verify: <RotatingBrollScene media={verifyScenePool} startOffset={7}/>,",
  ],
  [
    "export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
    "const RotatingBrollScene: React.FC<{media:VisualSource[];startOffset?:number}> = ({media,startOffset=0}) => {\n  const frame = useCurrentFrame();\n  if (!media.length) return <AbsoluteFill><Visual /></AbsoluteFill>;\n  const shotFrames = 72;\n  const fadeFrames = 8;\n  const slot = Math.floor(frame / shotFrames);\n  const local = frame % shotFrames;\n  const currentIndex = (startOffset + slot) % media.length;\n  const nextIndex = (currentIndex + 1) % media.length;\n  const current = media[currentIndex];\n  const next = media[nextIndex];\n  const fade = interpolate(local,[shotFrames-fadeFrames,shotFrames],[0,1],clamp);\n  const scale = interpolate(local,[0,shotFrames],[1.025,1.085],clamp);\n  return <AbsoluteFill style={{overflow:'hidden',backgroundColor:navy}}>\n    <AbsoluteFill><Visual source={current} scale={scale}/></AbsoluteFill>\n    {media.length > 1 && <AbsoluteFill style={{opacity:fade}}><Visual source={next} scale={1.03}/></AbsoluteFill>}\n    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(2,11,20,.04),rgba(2,11,20,.1) 55%,rgba(2,11,20,.68))'}}/>\n  </AbsoluteFill>;\n};\n\nconst SyncedCaption: React.FC<{text:string}> = ({text}) => (\n  <div style={{position:'absolute',zIndex:80,left:58,right:58,bottom:125,padding:'16px 22px',borderRadius:18,background:'linear-gradient(135deg,rgba(2,11,20,.91),rgba(6,25,45,.84))',border:'1px solid rgba(255,255,255,.2)',boxShadow:'0 18px 48px rgba(0,0,0,.48)',backdropFilter:'blur(14px)',fontFamily:typeface,fontSize:29,lineHeight:1.36,fontWeight:900,textAlign:'center',color:cream,textShadow:'0 3px 12px rgba(0,0,0,.7)'}}>{text}</div>\n);\n\nexport const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
  ],
  [
    "      {scheduled.map(({scene,from,duration}) => <Sequence key={scene} from={from} durationInFrames={duration}>{sceneNodes[scene]}</Sequence>)}",
    "      {scheduled.map(({scene,from,duration},index) => <Sequence key={scene} from={from + 3} durationInFrames={Math.max(1,duration - 3)}><AbsoluteFill>{sceneNodes[scene]}<SceneVFXOverlay scene={scene} value={sceneValue(scene)} styleVariant={style}/><SceneTransitionOverlay styleVariant={style} duration={Math.max(1,duration - 3)} index={index}/></AbsoluteFill></Sequence>)}",
  ],
  [
    "      {props.voiceSegments?.map((segment) => <Sequence key={`voice-${segment.scene}`} from={starts[segment.scene] || 0} durationInFrames={props.sceneDurations[segment.scene] || 120}><Audio src={staticFile(segment.src)} volume={1}/></Sequence>)}",
    "      {props.voiceSegments?.map((segment) => { const start = starts[segment.scene] || 0; const speechDuration = Math.max(1, segment.durationInFrames || ((props.sceneDurations[segment.scene] || 120) - 45)); return segment.text ? <Sequence key={`caption-${segment.scene}`} from={start + 3} durationInFrames={Math.max(1,speechDuration - 3)}><SyncedCaption text={segment.text}/></Sequence> : null; })}",
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

console.log('Applied continuous master narration, non-repeating scene offsets, 2.4-second B-roll rotation, synced captions, and cinematic VFX');
