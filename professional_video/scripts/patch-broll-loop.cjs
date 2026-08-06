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
    "  const facts = props.facts;\n  const allBroll: VisualSource[] = ['exterior','interior','road','land'].flatMap(sceneSources);\n  const sceneNodes:",
  ],
  [
    "    location: props.templateVariant === 'plot'\n      ? <LocationJourneyScene mapSources={mapVisuals} houseSource={sourceFor('exterior') || sourceFor('land')} title={props.title} location={props.location} targetLocation={props.locationLabel}/>\n      : <HookScene source={sourceFor('exterior')} title={props.title} location={props.location}/>,",
    "    location: <HookScene source={sourceFor('exterior') || sourceFor('interior') || sourceFor('road')} title={props.title} location={props.location}/>,",
  ],
  [
    "    land: <LaserPlotScene source={sourceFor('land')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
    "    land: <LaserPlotScene source={sourceFor('land') || sourceFor('exterior',1) || sourceFor('road')} fact={facts[0] || {label:'LAND',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    builtUp: <BuiltUpScanScene source={sourceFor('exterior')} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
    "    builtUp: <BuiltUpScanScene source={sourceFor('interior') || sourceFor('exterior',1)} fact={facts[1] || {label:'BUILT-UP',value:'VERIFY ON SITE'}}/>,",
  ],
  [
    "    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
    "    approval: allBroll.length ? <GalleryScene media={allBroll} location={props.location}/> : <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
  ],
  [
    "    verify: <VerifyScene price={props.price} location={props.location}/>,",
    "    verify: allBroll.length ? <FactBurstScene source={allBroll[Math.min(2,allBroll.length-1)]} facts={facts}/> : <VerifyScene price={props.price} location={props.location}/>,",
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

console.log('Applied first-frame R2 B-roll and continuous-dialogue timing patches');
