import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import type {PropertyVideoProps, VoiceSegment} from './types';

const font = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';
const bg = '#07111c';
const cream = '#fff8eb';
const gold = '#ffbd2e';
const muted = 'rgba(255,255,255,.78)';

const fact = (p: PropertyVideoProps, key: string, fallback = 'Verify during visit') =>
  p.facts.find((x) => x.label.toLowerCase().includes(key.toLowerCase()))?.value || fallback;

const sourceFor = (p: PropertyVideoProps, scene: string) => {
  const key = scene === 'price' || scene === 'facing' ? 'exterior' :
    scene === 'builtUp' ? 'living' :
    scene === 'verify' || scene === 'road' ? 'location' : scene;
  const src = p.sceneMedia?.[key]?.[0] || p.representativeVideos?.[0] || p.images?.[0] || '';
  return {src, video: /\.(mp4|mov|m4v|webm)$/i.test(src)};
};

const Copy: React.FC<{title: string; value?: string; note?: string}> = ({title, value, note}) => (
  <div style={{position: 'absolute', left: 56, right: 56, bottom: 120, fontFamily: font, color: cream}}>
    <div style={{fontSize: 24, fontWeight: 800, letterSpacing: 3, textTransform: 'uppercase', color: gold}}>{title}</div>
    {value ? <div style={{fontSize: 66, lineHeight: 1.02, fontWeight: 950, marginTop: 12, textShadow: '0 8px 30px rgba(0,0,0,.65)'}}>{value}</div> : null}
    {note ? <div style={{fontSize: 27, lineHeight: 1.25, fontWeight: 700, marginTop: 14, color: muted}}>{note}</div> : null}
  </div>
);

const MediaScene: React.FC<{p: PropertyVideoProps; scene: string; title: string; value?: string; note?: string}> = ({p, scene, title, value, note}) => {
  const frame = useCurrentFrame();
  const media = sourceFor(p, scene);
  const scale = interpolate(frame, [0, 180], [1.04, 1.10], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      {media.src ? media.video ? (
        <OffthreadVideo src={staticFile(media.src)} muted style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}} />
      ) : (
        <Img src={staticFile(media.src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}} />
      ) : null}
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.04) 35%,rgba(3,9,18,.90) 100%)'}} />
      <Copy title={title} value={value} note={note} />
      <div style={{position: 'absolute', right: 30, top: 34, fontFamily: font, fontSize: 14, fontWeight: 800, color: 'rgba(255,255,255,.72)', letterSpacing: 2}}>REPRESENTATIVE AI VISUAL</div>
    </AbsoluteFill>
  );
};

const MapScene: React.FC<{p: PropertyVideoProps; title: string; value?: string; note?: string}> = ({p, title, value, note}) => {
  const src = p.maps?.[0];
  if (!src) return <MediaScene p={p} scene="location" title={title} value={value} note={note} />;
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.06),rgba(3,9,18,.88) 100%)'}} />
      <Copy title={title} value={value} note={note} />
    </AbsoluteFill>
  );
};

const CTA: React.FC<{p: PropertyVideoProps}> = ({p}) => (
  <AbsoluteFill style={{background: bg, fontFamily: font, color: cream, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 70}}>
    <div>
      <div style={{fontSize: 25, fontWeight: 850, letterSpacing: 4, color: gold}}>SITE VISIT</div>
      <div style={{fontSize: 82, fontWeight: 950, lineHeight: .98, marginTop: 24}}>Interested in this property?</div>
      <div style={{fontSize: 45, fontWeight: 900, marginTop: 42}}>{p.phone}</div>
      <div style={{fontSize: 27, lineHeight: 1.3, color: muted, marginTop: 20}}>{p.cta}</div>
    </div>
  </AbsoluteFill>
);

const voiceFor = (voices: VoiceSegment[], scene: string) => voices.find((v) => v.scene === scene);

const sceneVisual = (p: PropertyVideoProps, scene: string) => {
  switch (scene) {
    case 'location': return <MediaScene p={p} scene="location" title="LOCATION" value={p.locationLabel || p.location} />;
    case 'price': return <MediaScene p={p} scene="price" title="PRICE" value={p.price} />;
    case 'builtUp': return <MediaScene p={p} scene="builtUp" title="BUILT-UP" value={fact(p, 'built')} />;
    case 'facing': return <MediaScene p={p} scene="facing" title="FACING" value={fact(p, 'facing')} />;
    case 'road': return <MapScene p={p} title="ACCESS" value={fact(p, 'road')} note="Verify road width and access during site visit" />;
    case 'approval': return <MapScene p={p} title="APPROVAL" value={fact(p, 'approval')} note="Verify documents before purchase" />;
    case 'verify': return <MapScene p={p} title="VERIFY BEFORE BUYING" note="Location • dimensions • price • documents" />;
    case 'cta': return <CTA p={p} />;
    case 'land': return <MediaScene p={p} scene="land" title="LAND" value={fact(p, 'land')} />;
    default: return <MediaScene p={p} scene="living" title={scene.toUpperCase()} />;
  }
};

export const CleanPropertyReel: React.FC<PropertyVideoProps> = (p) => {
  let at = 0;
  const sequences = p.sceneOrder.map((scene, index) => {
    const duration = p.sceneDurations?.[scene] || 60;
    const from = at;
    at += duration;
    const voice = voiceFor(p.voiceSegments || [], scene);
    return (
      <Sequence key={`${scene}-${index}`} from={from} durationInFrames={duration}>
        {sceneVisual(p, scene)}
        {voice?.src ? <Audio src={staticFile(voice.src)} volume={1} /> : null}
      </Sequence>
    );
  });
  return <AbsoluteFill style={{background: bg}}>{sequences}</AbsoluteFill>;
};
