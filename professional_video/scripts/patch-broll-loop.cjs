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
    "  const facts = props.facts;\n  const allBroll: VisualSource[] = ['exterior','interior','road','land'].flatMap(sceneSources);\n  const styleNames = ['cinematic','fast-cut','premium','location-first','price-first'] as const;\n  const automaticStyle = styleNames[Array.from(props.videoId).reduce((sum,char)=>sum+char.charCodeAt(0),0)%styleNames.length];\n  const style = props.styleVariant || automaticStyle;\n  const rotatePool = (items: VisualSource[], offset: number) => items.length ? [...items.slice(offset % items.length), ...items.slice(0, offset % items.length)] : items;\n  const styleOffset = styleNames.indexOf(style);\n  const exteriorPool = rotatePool(sceneSources('exterior'), styleOffset);\n  const interiorPool = rotatePool(sceneSources('interior'), styleOffset+1);\n  const roadPool = rotatePool(sceneSources('road'), styleOffset+2);\n  const mixedPool = rotatePool(allBroll, styleOffset+3);\n  const sceneValue = (scene:string) => ({location: props.location, land: facts[0]?.value, builtUp: facts[1]?.value, price: props.price, facing: facts[2]?.value, road: facts[3]?.value, approval: facts[5]?.value}[scene] || '');\n  const sceneNodes:",
  ],
  [
    "    location: props.templateVariant === 'plot'\n      ? <LocationJourneyScene mapSources={mapVisuals} houseSource={sourceFor('exterior') || sourceFor('land')} title={props.title} location={props.location} targetLocation={props.locationLabel}/>\n      : <HookScene source={sourceFor('exterior')} title={props.title} location={props.location}/>,",
    "    location: <HookScene source={exteriorPool[0] || mixedPool[0] || interiorPool[0] || roadPool[0]} title={props.title} location={props.location}/>,",
  ],
  [
    "    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
    "    land: <LaserPlotScene source={sourceFor('land') || exteriorPool[1] || mixedPool[0]} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: <BuiltUpScanScene source={interiorPool[0] || exteriorPool[0] || mixedPool[0]} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    price: <PriceScene source={sourceFor('exterior',1)} price={props.price}/>,",
    "    price: <PriceScene source={exteriorPool[1] || exteriorPool[0] || mixedPool[0]} price={props.price}/>,",
  ],
  [
    "    facing: <FacingScene source={sourceFor('exterior') || sourceFor('land',1)} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
    "    facing: <FacingScene source={exteriorPool[2] || exteriorPool[0] || mixedPool[0]} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    road: <RoadMeasureScene source={sourceFor('road')} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
    "    road: <RoadMeasureScene source={roadPool[0] || mixedPool[0]} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
    "const SyncedCaption: React.FC<{text:string}> = ({text}) => (\n  <div style={{position:'absolute',zIndex:80,left:58,right:58,bottom:125,padding:'16px 22px',borderRadius:18,background:'linear-gradient(135deg,rgba(2,11,20,.91),rgba(6,25,45,.84))',border:'1px solid rgba(255,255,255,.2)',boxShadow:'0 18px 48px rgba(0,0,0,.48)',backdropFilter:'blur(14px)',fontFamily:typeface,fontSize:29,lineHeight:1.36,fontWeight:900,textAlign:'center',color:cream,textShadow:'0 3px 12px rgba(0,0,0,.7)'}}>{text}</div>\n);\n\nexport const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
  ],
  [
    "      {scheduled.map(({scene,from,duration}) => <Sequence key={scene} from={from} durationInFrames={duration}>{sceneNodes[scene]}</Sequence>)}",
    "      {scheduled.map(({scene,from,duration},index) => <Sequence key={scene} from={from + 3} durationInFrames={Math.max(1,duration - 3)}><AbsoluteFill>{sceneNodes[scene]}<SceneVFXOverlay scene={scene} value={sceneValue(scene)} styleVariant={style}/><SceneTransitionOverlay styleVariant={style} duration={Math.max(1,duration - 3)} index={index}/></AbsoluteFill></Sequence>)}",
  ],
  [
    "      {props.voiceSegments?.map((segment) => <Sequence key={`voice-${segment.scene}`} from={starts[segment.scene] || 0} durationInFrames={props.sceneDurations[segment.scene] || 120}><Audio src={staticFile(segment.src)} volume={1}/></Sequence>)}",
    "      {props.voiceSegments?.map((segment) => { const start = starts[segment.scene] || 0; const speechDuration = Math.max(1, segment.durationInFrames || ((props.sceneDurations[segment.scene] || 120) - 45)); return <React.Fragment key={`voice-${segment.scene}`}><Sequence from={start} durationInFrames={speechDuration}><Audio src={staticFile(segment.src)} volume={1}/></Sequence>{segment.text && <Sequence from={start + 3} durationInFrames={Math.max(1,speechDuration - 3)}><SyncedCaption text={segment.text}/></Sequence>}</React.Fragment>; })}",
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

console.log('Applied cinematic grading, contextual 3D property VFX, style-aware transitions, looping B-roll, synced captions, and 1.5-second dialogue gaps');
