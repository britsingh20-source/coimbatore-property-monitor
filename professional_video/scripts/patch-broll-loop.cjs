const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '..', 'src', 'PropertyReel.tsx');
let source = fs.readFileSync(target, 'utf8');

const replacements = [
  [
    "  OffthreadVideo,\n  Sequence,",
    "  OffthreadVideo,\n  Loop,\n  Sequence,",
  ],
  [
    "  return source.video ? <OffthreadVideo src={staticFile(source.src)} muted style={style} /> : <Img src={staticFile(source.src)} style={style} />;",
    "  return source.video ? <Loop durationInFrames={90}><OffthreadVideo src={staticFile(source.src)} muted style={style} /></Loop> : <Img src={staticFile(source.src)} style={style} />;",
  ],
  [
    "  const facts = props.facts;\n  const sceneNodes:",
    "  const facts = props.facts;\n  const allBroll: VisualSource[] = ['exterior','interior','road','land'].flatMap(sceneSources);\n  const sceneNodes:",
  ],
  [
    "    approval: <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
    "    approval: allBroll.length ? <GalleryScene media={allBroll} location={props.location}/> : <ApprovalScene fact={facts[5] || {label:'APPROVAL',value:'VERIFY DOCUMENTS'}}/>,",
  ],
  [
    "    verify: <VerifyScene price={props.price} location={props.location}/>,",
    "    verify: allBroll.length ? <FactBurstScene source={allBroll[0]} facts={facts}/> : <VerifyScene price={props.price} location={props.location}/>,",
  ],
];

for (const [before, after] of replacements) {
  if (!source.includes(before)) {
    throw new Error(`Expected PropertyReel snippet not found: ${before.slice(0, 80)}`);
  }
  source = source.replace(before, after);
}

fs.writeFileSync(target, source);
console.log('Applied continuous R2 B-roll patch to PropertyReel.tsx');
