const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '..', 'src', 'PropertyReel.tsx');
let source = fs.readFileSync(target, 'utf8');

const replacements = [
  ["  OffthreadVideo,\n  Sequence,", "  OffthreadVideo,\n  Loop,\n  Sequence,"],
  [
    "  return source.video ? <OffthreadVideo src={staticFile(source.src)} muted style={style} /> : <Img src={staticFile(source.src)} style={style} />;",
    "  return source.video ? <Loop durationInFrames={72}><OffthreadVideo src={staticFile(source.src)} muted style={style} /></Loop> : <Img src={staticFile(source.src)} style={style} />;",
  ],
  [
    "  const facts = props.facts;\n  const sceneNodes:",
    "  const facts = props.facts;\n  const allBroll: VisualSource[] = ['exterior','interior','road','land'].flatMap(sceneSources);\n  const styleNames = ['cinematic','fast-cut','premium','location-first','price-first'] as const;\n  const automaticStyle = styleNames[Array.from(props.videoId).reduce((sum,char)=>sum+char.charCodeAt(0),0)%styleNames.length];\n  const style = props.styleVariant || automaticStyle;\n  const rotatePool = (items: VisualSource[], offset: number) => items.length ? [...items.slice(offset % items.length), ...items.slice(0, offset % items.length)] : items;\n  const styleOffset = styleNames.indexOf(style);\n  const exteriorPool = rotatePool(sceneSources('exterior'), styleOffset);\n  const interiorPool = rotatePool(sceneSources('interior'), styleOffset+1);\n  const roadPool = rotatePool(sceneSources('road'), styleOffset+2);\n  const mixedPool = rotatePool(allBroll, styleOffset+3);\n  const sceneNodes:",
  ],
  [
    "    location: props.templateVariant === 'plot'\n      ? <LocationJourneyScene mapSources={mapVisuals} houseSource={sourceFor('exterior') || sourceFor('land')} title={props.title} location={props.location} targetLocation={props.locationLabel}/>\n      : <HookScene source={sourceFor('exterior')} title={props.title} location={props.location}/>,",
    "    location: style === 'fast-cut' && mixedPool.length\n      ? <GalleryScene media={mixedPool} location={props.location}/>\n      : style === 'premium' && mixedPool.length\n        ? <WalkthroughScene media={mixedPool} location={props.location}/>\n        : <HookScene source={exteriorPool[0] || mixedPool[0]} title={props.title} location={props.location}/>,",
  ],
  [
    "    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
    "    land: style === 'fast-cut' || style === 'price-first'\n      ? <FactBurstScene source={mixedPool[1] || mixedPool[0]} facts={facts}/>\n      : <LaserPlotScene source={sourceFor('land') || exteriorPool[1] || mixedPool[0]} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: style === 'premium' && interiorPool.length\n      ? <WalkthroughScene media={interiorPool} location={props.location}/>\n      : style === 'fast-cut' && mixedPool.length\n        ? <GalleryScene media={mixedPool} location={props.location}/>\n        : <BuiltUpScanScene source={interiorPool[0] || exteriorPool[0] || mixedPool[0]} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    price: <PriceScene source={sourceFor('exterior',1)} price={props.price}/>,",
    "    price: style === 'fast-cut'\n      ? <FactBurstScene source={mixedPool[2] || mixedPool[0]} facts={facts}/>\n      : <PriceScene source={exteriorPool[1] || exteriorPool[0] || mixedPool[0]} price={props.price}/>,",
  ],
  [
    "    facing: <FacingScene source={sourceFor('exterior') || sourceFor('land',1)} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
    "    facing: style === 'premium' && exteriorPool.length\n      ? <GalleryScene media={exteriorPool} location={props.location}/>\n      : <FacingScene source={exteriorPool[2] || exteriorPool[0] || mixedPool[0]} fact={facts[2] || {label:'FACING',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    road: <RoadMeasureScene source={sourceFor('road')} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
    "    road: style === 'location-first' && roadPool.length\n      ? <GalleryScene media={roadPool} location={props.location}/>\n      : <RoadMeasureScene source={roadPool[0] || mixedPool[0]} fact={facts[3] || {label:'ROAD',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
    "    approval: style === 'cinematic' || style === 'premium'\n      ? (mixedPool.length ? <GalleryScene media={mixedPool} location={props.location}/> : <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>)\n      : <TrustScene facts={facts} price={props.price}/>,",
  ],
  [
    "    verify: <VerifyScene price={props.price} location={props.location}/>,",
    "    verify: style === 'fast-cut'\n      ? <FactBurstScene source={mixedPool[3] || mixedPool[0]} facts={facts}/>\n      : style === 'premium' && mixedPool.length\n        ? <GalleryScene media={mixedPool} location={props.location}/>\n        : <TrustScene facts={facts} price={props.price}/>,",
  ],
];

for (const [before, after] of replacements) {
  if (!source.includes(before)) {
    if (source.includes(after)) continue;
    throw new Error(`Expected PropertyReel snippet not found: ${before.slice(0, 100)}`);
  }
  source = source.replace(before, after);
}
fs.writeFileSync(target, source);

const pythonTarget = path.join(__dirname, '..', '..', 'prepare_remotion_job.py');
let python = fs.readFileSync(pythonTarget, 'utf8');
const oldDuration = `        duration = max(\n            minimum_frames.get(scene, 120),\n            int(float(item["duration_seconds"]) * 30) + 18,\n        )`;
const newDuration = `        # Keep narration continuous: scene ends only a few frames after speech.\n        # The prior large fixed minimums created obvious dead-air gaps.\n        duration = max(36, int(float(item["duration_seconds"]) * 30) + 3)`;
if (python.includes(oldDuration)) {
  python = python.replace(oldDuration, newDuration);
} else if (!python.includes(newDuration)) {
  throw new Error('Expected prepare_remotion_job duration block not found');
}
fs.writeFileSync(pythonTarget, python);

console.log('Applied continuous R2 B-roll, flowing dialogue, and five property video styles');
