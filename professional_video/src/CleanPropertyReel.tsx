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
  const semantic = [
    ...(p.sceneMedia?.[key] || []),
    ...(key === 'living' ? p.sceneMedia?.kitchen || [] : []),
    ...(key === 'living' ? p.sceneMedia?.bedroom || [] : []),
    ...(scene === 'location' ? p.sceneMedia?.exterior || [] : []),
    ...(scene === 'location' ? p.sceneMedia?.living || [] : []),
    ...(scene === 'location' ? p.sceneMedia?.kitchen || [] : []),
    ...(scene === 'location' ? p.sceneMedia?.bedroom || [] : []),
  ];
  const clean = [...new Set(semantic.filter(Boolean))];
  if (clean.length) return clean;
  return [...new Set([...(p.representativeVideos || []), ...(p.images || [])].filter(Boolean))];
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
  const x = interpolate(localFrame, [0, 75], [direction * -12, direction * 12], {extrapolateRight: 'clamp'});
  const common = {width: '100%', height: '100%', objectFit: 'cover' as const, transform: `translateX(${x}px) scale(${scale})`};
  return isVideo(src)
    ? <OffthreadVideo src={staticFile(src)} muted style={common} />
    : <Img src={staticFile(src)} style={common} />;
};

const PacedMediaScene: React.FC<{p: PropertyVideoProps; scene: string; title: string; value?: string; note?: string}> = ({p, scene, title, value, note}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sources = sceneSources(p, scene);
  const beat = Math.max(1, Math.round(fps * 2.0));
  const index = sources.length ? Math.floor(frame / beat) % sources.length : 0;
  const localFrame = frame % beat;
  const src = sources[index] || '';
  const flash = interpolate(localFrame, [0, 3, 7], [0.20, 0.04, 0], {extrapolateRight: 'clamp'});
  const bar = interpolate(localFrame, [0, beat], [10, 100], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      {src ? <MediaLayer src={src} localFrame={localFrame} direction={index % 2 === 0 ? 1 : -1} /> : null}
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.02) 25%,rgba(3,9,18,.90) 100%)'}} />
      <AbsoluteFill style={{background: `rgba(255,255,255,${flash})`}} />
      <div style={{position: 'absolute', left: 0, top: 0, height: 8, width: `${bar}%`, background: `linear-gradient(90deg,${cyan},${gold})`}} />
      <AnimatedCopy title={title} value={value} note={note} />
      <div style={{position: 'absolute', right: 30, top: 32, fontFamily: font, fontSize: 13, fontWeight: 850, color: 'rgba(255,255,255,.68)', letterSpacing: 2}}>REPRESENTATIVE AI VISUAL</div>
    </AbsoluteFill>
  );
};

const MapScene: React.FC<{p: PropertyVideoProps; title: string; value?: string; note?: string}> = ({p, title, value, note}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const maps = (p.maps || []).filter(Boolean);
  if (!maps.length) return <PacedMediaScene p={p} scene="location" title={title} value={value} note={note} />;
  const beat = Math.max(1, Math.round(fps * 2.0));
  const index = Math.floor(frame / beat) % maps.length;
  const localFrame = frame % beat;
  const src = maps[index];
  const scale = interpolate(localFrame, [0, beat], [1.01, 1.13], {extrapolateRight: 'clamp'});
  const x = interpolate(localFrame, [0, beat], [index % 2 ? 16 : -16, index % 2 ? -16 : 16], {extrapolateRight: 'clamp'});
  const flash = interpolate(localFrame, [0, 3, 7], [0.18, 0.04, 0], {extrapolateRight: 'clamp'});
  const pulse = 1 + Math.sin(frame / 5) * 0.08;
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `translateX(${x}px) scale(${scale})`}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.02),rgba(3,9,18,.90) 100%)'}} />
      <AbsoluteFill style={{background: `rgba(255,255,255,${flash})`}} />
      <div style={{position: 'absolute', left: '50%', top: '42%', width: 36, height: 36, marginLeft: -18, marginTop: -18, borderRadius: 999, border: `5px solid ${gold}`, transform: `scale(${pulse})`, boxShadow: `0 0 34px ${gold}`}} />
      <div style={{position: 'absolute', left: 0, top: 0, height: 8, width: `${interpolate(localFrame, [0, beat], [12, 100])}%`, background: `linear-gradient(90deg,${cyan},${gold})`}} />
      <AnimatedCopy title={title} value={value} note={note} />
    </AbsoluteFill>
  );
};

const CTA: React.FC<{p: PropertyVideoProps}> = ({p}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sources = sceneSources(p, 'location');
  const beat = Math.max(1, Math.round(fps * 2.0));
  const index = sources.length ? Math.floor(frame / beat) % sources.length : 0;
  const localFrame = frame % beat;
  const src = sources[index] || '';
  const pop = interpolate(frame, [0, 14], [0.82, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(frame, [0, 16], [48, 0], {extrapolateRight: 'clamp'});
  const glow = 18 + Math.max(0, Math.sin(frame / 5)) * 20;
  return (
    <AbsoluteFill style={{background: bg, fontFamily: font, color: cream, overflow: 'hidden'}}>
      {src ? <MediaLayer src={src} localFrame={localFrame} direction={index % 2 === 0 ? -1 : 1} /> : null}
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(3,9,18,.48),rgba(3,9,18,.92))'}} />
      <div style={{position: 'absolute', left: 52, right: 52, top: 420, textAlign: 'center', transform: `translateY(${rise}px) scale(${pop})`}}>
        <div style={{fontSize: 24, fontWeight: 900, letterSpacing: 4, color: cyan}}>SITE VISIT</div>
        <div style={{fontSize: 78, fontWeight: 950, lineHeight: .98, marginTop: 24}}>Interested in this property?</div>
        <div style={{fontSize: 45, fontWeight: 950, margin: '42px auto 0', padding: '22px 34px', borderRadius: 24, background: gold, color: bg, boxShadow: `0 0 ${glow}px rgba(255,189,46,.55)`, maxWidth: 760}}>{p.phone}</div>
        <div style={{fontSize: 27, lineHeight: 1.3, color: muted, marginTop: 22}}>{p.cta}</div>
      </div>
      <div style={{position: 'absolute', left: 0, bottom: 0, height: 10, width: `${interpolate(frame % beat, [0, beat], [8, 100])}%`, background: `linear-gradient(90deg,${gold},${cyan})`}} />
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
