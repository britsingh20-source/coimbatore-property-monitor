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
  useVideoConfig,
} from 'remotion';
import type {PropertyVideoProps, VoiceSegment} from './types';

const font = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';
const bg = '#07111c';
const cream = '#fff8eb';
const gold = '#ffbd2e';
const cyan = '#5ce7ff';
const muted = 'rgba(255,255,255,.78)';

const fact = (p: PropertyVideoProps, key: string, fallback = 'Verify during visit') =>
  p.facts.find((x) => x.label.toLowerCase().includes(key.toLowerCase()))?.value || fallback;

const keyFor = (scene: string) => scene === 'price' || scene === 'facing' ? 'exterior' :
  scene === 'builtUp' ? 'living' :
  scene === 'verify' || scene === 'road' ? 'location' : scene;

const sceneSources = (p: PropertyVideoProps, scene: string) => {
  const key = keyFor(scene);
  const ordered = [
    ...(p.sceneMedia?.[key] || []),
    ...(key === 'living' ? p.sceneMedia?.kitchen || [] : []),
    ...(key === 'living' ? p.sceneMedia?.bedroom || [] : []),
    ...(scene === 'location' ? p.sceneMedia?.exterior || [] : []),
    ...(p.representativeVideos || []),
    ...(p.images || []),
  ];
  return [...new Set(ordered.filter(Boolean))];
};

const isVideo = (src: string) => /\.(mp4|mov|m4v|webm)$/i.test(src);

const AnimatedCopy: React.FC<{title: string; value?: string; note?: string}> = ({title, value, note}) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, 10], [34, 0], {extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: 56, right: 56, bottom: 120, fontFamily: font, color: cream, transform: `translateY(${y}px)`, opacity}}>
      <div style={{fontSize: 22, fontWeight: 850, letterSpacing: 3, textTransform: 'uppercase', color: gold}}>{title}</div>
      {value ? <div style={{fontSize: 64, lineHeight: 1.02, fontWeight: 950, marginTop: 10, textShadow: '0 8px 30px rgba(0,0,0,.65)'}}>{value}</div> : null}
      {note ? <div style={{fontSize: 26, lineHeight: 1.25, fontWeight: 700, marginTop: 14, color: muted}}>{note}</div> : null}
    </div>
  );
};

const MediaLayer: React.FC<{src: string; localFrame: number; direction: number}> = ({src, localFrame, direction}) => {
  const scale = interpolate(localFrame, [0, 75], [1.02, 1.09], {extrapolateRight: 'clamp'});
  const x = interpolate(localFrame, [0, 75], [direction * -10, direction * 10], {extrapolateRight: 'clamp'});
  const common = {width: '100%', height: '100%', objectFit: 'cover' as const, transform: `translateX(${x}px) scale(${scale})`};
  return isVideo(src)
    ? <OffthreadVideo src={staticFile(src)} muted style={common} />
    : <Img src={staticFile(src)} style={common} />;
};

const PacedMediaScene: React.FC<{p: PropertyVideoProps; scene: string; title: string; value?: string; note?: string}> = ({p, scene, title, value, note}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sources = sceneSources(p, scene);
  const beat = Math.max(1, Math.round(fps * 2.25));
  const index = sources.length ? Math.floor(frame / beat) % sources.length : 0;
  const localFrame = frame % beat;
  const src = sources[index] || '';
  const flash = interpolate(localFrame, [0, 3, 7], [0.22, 0.05, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      {src ? <MediaLayer src={src} localFrame={localFrame} direction={index % 2 === 0 ? 1 : -1} /> : null}
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.03) 28%,rgba(3,9,18,.90) 100%)'}} />
      <AbsoluteFill style={{background: `rgba(255,255,255,${flash})`}} />
      <div style={{position: 'absolute', left: 0, top: 0, height: 8, width: `${interpolate(localFrame, [0, beat], [18, 100])}%`, background: `linear-gradient(90deg,${cyan},${gold})`}} />
      <AnimatedCopy title={title} value={value} note={note} />
      <div style={{position: 'absolute', right: 30, top: 32, fontFamily: font, fontSize: 13, fontWeight: 850, color: 'rgba(255,255,255,.68)', letterSpacing: 2}}>REPRESENTATIVE AI VISUAL</div>
    </AbsoluteFill>
  );
};

const MapScene: React.FC<{p: PropertyVideoProps; title: string; value?: string; note?: string}> = ({p, title, value, note}) => {
  const frame = useCurrentFrame();
  const src = p.maps?.[0];
  if (!src) return <PacedMediaScene p={p} scene="location" title={title} value={value} note={note} />;
  const scale = interpolate(frame, [0, 180], [1.02, 1.10], {extrapolateRight: 'clamp'});
  const pulse = 1 + Math.sin(frame / 6) * 0.04;
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.04),rgba(3,9,18,.88) 100%)'}} />
      <div style={{position: 'absolute', left: '50%', top: '42%', width: 34, height: 34, marginLeft: -17, marginTop: -17, borderRadius: 999, border: `5px solid ${gold}`, transform: `scale(${pulse})`, boxShadow: `0 0 28px ${gold}`}} />
      <AnimatedCopy title={title} value={value} note={note} />
    </AbsoluteFill>
  );
};

const CTA: React.FC<{p: PropertyVideoProps}> = ({p}) => {
  const frame = useCurrentFrame();
  const pop = interpolate(frame, [0, 14], [0.84, 1], {extrapolateRight: 'clamp'});
  const glow = 18 + Math.max(0, Math.sin(frame / 5)) * 16;
  return (
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 36%,#174e6e,#07111c 67%)', fontFamily: font, color: cream, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 70}}>
      <div style={{transform: `scale(${pop})`}}>
        <div style={{fontSize: 24, fontWeight: 900, letterSpacing: 4, color: cyan}}>SITE VISIT</div>
        <div style={{fontSize: 78, fontWeight: 950, lineHeight: .98, marginTop: 24}}>Interested in this property?</div>
        <div style={{fontSize: 45, fontWeight: 950, marginTop: 42, padding: '22px 34px', borderRadius: 24, background: gold, color: bg, boxShadow: `0 0 ${glow}px rgba(255,189,46,.45)`}}>{p.phone}</div>
        <div style={{fontSize: 27, lineHeight: 1.3, color: muted, marginTop: 22}}>{p.cta}</div>
      </div>
    </AbsoluteFill>
  );
};

const voiceFor = (voices: VoiceSegment[], scene: string) => voices.find((v) => v.scene === scene);

const sceneVisual = (p: PropertyVideoProps, scene: string) => {
  switch (scene) {
    case 'location': return <PacedMediaScene p={p} scene="location" title="LOCATION" value={p.locationLabel || p.location} />;
    case 'price': return <PacedMediaScene p={p} scene="price" title="PRICE" value={p.price} />;
    case 'builtUp': return <PacedMediaScene p={p} scene="builtUp" title="BUILT-UP" value={fact(p, 'built')} />;
    case 'facing': return <PacedMediaScene p={p} scene="facing" title="FACING" value={fact(p, 'facing')} />;
    case 'road': return <MapScene p={p} title="ACCESS" value={fact(p, 'road')} note="Verify road width and access during site visit" />;
    case 'approval': return <MapScene p={p} title="APPROVAL" value={fact(p, 'approval')} note="Verify documents before purchase" />;
    case 'verify': return <MapScene p={p} title="VERIFY BEFORE BUYING" note="Location • dimensions • price • documents" />;
    case 'cta': return <CTA p={p} />;
    case 'land': return <PacedMediaScene p={p} scene="land" title="LAND" value={fact(p, 'land')} />;
    default: return <PacedMediaScene p={p} scene="living" title={scene.toUpperCase()} />;
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
