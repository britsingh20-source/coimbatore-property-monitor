const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '..', 'src', 'PropertyReel.tsx');
let source = fs.readFileSync(target, 'utf8');

const replacements = [
  [
    "import type {Fact, PropertyVideoProps} from './types';",
    "import type {Fact, PropertyVideoProps} from './types';\nimport {CinematicGrade, SceneTransitionOverlay, SceneVFXOverlay} from './CinematicVFX';\nimport {BuildingScanOverlay} from './EngagingAIOverlays';",
  ],
  ["  OffthreadVideo,\n  Sequence,", "  OffthreadVideo,\n  Loop,\n  Sequence,"],
  [
    "type VisualSource = {src: string; video: boolean};",
    "type VisualSource = {src: string; video: boolean; startFrom?: number};",
  ],
  [
    "  return source.video ? <OffthreadVideo src={staticFile(source.src)} muted style={style} /> : <Img src={staticFile(source.src)} style={style} />;",
    "  return source.video ? <Loop durationInFrames={72}><OffthreadVideo src={staticFile(source.src)} startFrom={source.startFrom || 0} muted style={style} /></Loop> : <Img src={staticFile(source.src)} style={style} />;",
  ],
  [
    "      {mode === 'land' && <PlotOutline />}",
    "      {mode === 'land' ? <PlotOutline /> : <BuildingScanOverlay />}",
  ],
  [
    "  const facts = props.facts;\n  const sceneNodes:",
    "  const facts = props.facts;\n  const styleNames = ['cinematic','fast-cut','premium','location-first','price-first'] as const;\n  const automaticStyle = styleNames[Array.from(props.videoId).reduce((sum,char)=>sum+char.charCodeAt(0),0)%styleNames.length];\n  const style = props.styleVariant || automaticStyle;\n  const sceneValue = (scene:string) => ({location: props.location, land: facts[0]?.value, builtUp: facts[1]?.value, price: props.price, facing: facts[2]?.value, road: facts[3]?.value, approval: facts[5]?.value}[scene] || '');\n  const sceneNodes:",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: <BuiltUpScanScene source={sourceFor('interior') || sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
    "const SceneFactOverlay: React.FC<{scene:string;value:string}> = ({scene,value}) => {\n  if (!value || scene === 'location' || scene === 'verify' || scene === 'cta') return null;\n  const labels:Record<string,string> = {land:'LAND AREA',builtUp:'BUILT-UP',price:'PRICE',facing:'FACING',road:'ROAD WIDTH',approval:'APPROVAL'};\n  const frame = useCurrentFrame();\n  const enter = spring({frame:frame-5,fps:30,config:{damping:16,stiffness:170}});\n  const strong = scene === 'price';\n  return <div style={{position:'absolute',zIndex:35,left:52,right:52,top:strong?250:170,fontFamily:typeface,color:cream,textAlign:strong?'center':'left',transform:`translateY(${interpolate(enter,[0,1],[45,0])}px)`,opacity:enter}}>\n    <div style={{fontSize:15,letterSpacing:4,fontWeight:950,color:gold}}>{labels[scene] || scene.toUpperCase()}</div>\n    <div style={{fontSize:strong?78:48,lineHeight:1.05,fontWeight:1000,marginTop:10,textShadow:'0 10px 35px rgba(0,0,0,.75)'}}>{value}</div>\n  </div>;\n};\n\nconst SyncedCaption: React.FC<{text:string}> = ({text}) => (\n  <div style={{position:'absolute',zIndex:80,left:58,right:58,bottom:125,padding:'14px 20px',borderRadius:18,background:'linear-gradient(135deg,rgba(2,11,20,.9),rgba(6,25,45,.82))',border:'1px solid rgba(255,255,255,.18)',boxShadow:'0 16px 42px rgba(0,0,0,.45)',backdropFilter:'blur(12px)',fontFamily:typeface,fontSize:28,lineHeight:1.34,fontWeight:900,textAlign:'center',color:cream,textShadow:'0 3px 12px rgba(0,0,0,.7)'}}>{text}</div>\n);\n\nexport const PropertyReel: React.FC<PropertyVideoProps> = (props) => {",
  ],
  [
    "      {scheduled.map(({scene,from,duration}) => <Sequence key={scene} from={from} durationInFrames={duration}>{sceneNodes[scene]}</Sequence>)}",
    "      {scheduled.map(({scene,from,duration},index) => <Sequence key={scene} from={from + 2} durationInFrames={Math.max(1,duration - 2)}><AbsoluteFill>{sceneNodes[scene]}<SceneFactOverlay scene={scene} value={sceneValue(scene)}/>{scene !== 'location' && <SceneVFXOverlay scene={scene} value={sceneValue(scene)} styleVariant={style}/>}<SceneTransitionOverlay styleVariant={style} duration={Math.max(1,duration - 2)} index={index}/></AbsoluteFill></Sequence>)}",
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
    "      <GlobalFX />\n      <CinematicGrade styleVariant={style}/>\n      <PersistentHUD brand={props.brand} phone={props.phone}/>",
  ],
];

for (const [before, after] of replacements) {
  if (before === after) continue;
  if (!source.includes(before)) {
    if (source.includes(after)) continue;
    throw new Error(`Expected PropertyReel snippet not found: ${before.slice(0, 120)}`);
  }
  source = source.replace(before, after);
}
fs.writeFileSync(target, source);

console.log('Applied AI-first semantic media, restored native cinematic scene VFX, building scan hook, synced captions, transitions and looping motion clips');
