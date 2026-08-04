import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {PropertyVideoProps} from './types';

const navy = '#071A2E';
const cream = '#F6F0E5';
const gold = '#D6A53A';
const typeface = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';

const MediaFrame: React.FC<{src: string; video: boolean; label: string; index: number}> = ({src, video, label, index}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 180], index % 2 ? [1.02, 1.12] : [1.1, 1.02], {extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [0, 14, 165, 180], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: navy, opacity, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${scale})`}}>
        {video ? (
          <Loop durationInFrames={150}>
            <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          </Loop>
        ) : (
          <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        )}
      </div>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(7,26,46,.05) 40%, rgba(7,26,46,.92) 100%)'}} />
      <div style={{position: 'absolute', left: 62, bottom: 170, color: cream, fontFamily: typeface}}>
        <div style={{fontSize: 24, letterSpacing: 4, color: gold, fontWeight: 800}}>{label}</div>
      </div>
    </AbsoluteFill>
  );
};

const Hook: React.FC<Pick<PropertyVideoProps, 'location' | 'title' | 'price'>> = ({location, title, price}) => {
  const frame = useCurrentFrame();
  const rise = spring({frame, fps: 30, config: {damping: 18}});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 62px 210px', color: cream, fontFamily: typeface}}>
      <div style={{transform: `translateY(${interpolate(rise, [0, 1], [90, 0])}px)`, opacity: rise}}>
        <div style={{display: 'inline-flex', padding: '12px 22px', borderRadius: 99, background: gold, color: navy, fontWeight: 900, fontSize: 23, letterSpacing: 2}}>NEW PROPERTY • COIMBATORE</div>
        <h1 style={{fontSize: 78, lineHeight: 1.02, margin: '30px 0 18px', maxWidth: 900}}>{title}</h1>
        <div style={{fontSize: 38, opacity: .92}}>📍 {location}</div>
        <div style={{fontSize: 46, color: gold, fontWeight: 800, marginTop: 22}}>{price}</div>
      </div>
    </AbsoluteFill>
  );
};

const MapStage: React.FC<{maps: string[]; location: string}> = ({maps, location}) => {
  const frame = useCurrentFrame();
  const index = Math.min(maps.length - 1, Math.floor(frame / 70));
  const zoom = interpolate(frame % 70, [0, 70], [1, 1.07]);
  if (!maps.length) return null;
  return (
    <AbsoluteFill style={{backgroundColor: navy, fontFamily: typeface}}>
      <Img src={staticFile(maps[Math.max(0, index)])} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(7,26,46,.15), rgba(7,26,46,.82))'}} />
      <div style={{position: 'absolute', left: 60, right: 60, bottom: 150, padding: 38, borderRadius: 34, background: 'rgba(7,26,46,.86)', border: '1px solid rgba(255,255,255,.2)', color: cream}}>
        <div style={{fontSize: 22, color: gold, letterSpacing: 4, fontWeight: 800}}>LOCATION INTELLIGENCE</div>
        <div style={{fontSize: 52, fontWeight: 900, marginTop: 14}}>Tamil Nadu → Coimbatore</div>
        <div style={{fontSize: 36, marginTop: 8}}>{location}</div>
        <div style={{fontSize: 19, marginTop: 22, opacity: .72}}>© OpenStreetMap contributors • Pin is locality-level unless exact coordinates are verified</div>
      </div>
    </AbsoluteFill>
  );
};

const Facts: React.FC<Pick<PropertyVideoProps, 'facts' | 'location'>> = ({facts, location}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 100% 0%, #154A70, ${navy} 55%)`, padding: '220px 60px', color: cream, fontFamily: typeface}}>
      <div style={{fontSize: 24, color: gold, letterSpacing: 5, fontWeight: 800}}>VERIFIED LISTING FACTS</div>
      <div style={{fontSize: 60, fontWeight: 900, marginTop: 18}}>{location}</div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22, marginTop: 70}}>
        {facts.slice(0, 4).map((fact, index) => {
          const enter = spring({frame: frame - index * 10, fps: 30, config: {damping: 18}});
          return (
            <div key={fact.label} style={{minHeight: 230, padding: 30, borderRadius: 28, background: 'rgba(246,240,229,.09)', border: '1px solid rgba(246,240,229,.2)', transform: `translateY(${interpolate(enter, [0, 1], [70, 0])}px)`, opacity: enter}}>
              <div style={{fontSize: 20, color: gold, letterSpacing: 3, fontWeight: 800}}>{fact.label}</div>
              <div style={{fontSize: 37, lineHeight: 1.22, fontWeight: 800, marginTop: 20}}>{fact.value}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const CTA: React.FC<Pick<PropertyVideoProps, 'brand' | 'cta' | 'disclosure'>> = ({brand, cta, disclosure}) => {
  const frame = useCurrentFrame();
  const pop = spring({frame, fps: 30, config: {damping: 15}});
  return (
    <AbsoluteFill style={{backgroundColor: cream, color: navy, justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: 80, fontFamily: typeface}}>
      <div style={{width: 150, height: 150, borderRadius: 34, background: navy, color: gold, display: 'grid', placeItems: 'center', fontSize: 62, fontWeight: 900, transform: `scale(${pop})`}}>SB</div>
      <div style={{fontSize: 32, letterSpacing: 8, fontWeight: 900, marginTop: 36}}>{brand}</div>
      <div style={{fontSize: 62, fontWeight: 900, lineHeight: 1.08, marginTop: 54}}>{cta}</div>
      <div style={{fontSize: 30, maxWidth: 760, lineHeight: 1.5, marginTop: 38, color: '#405166'}}>{disclosure}</div>
      <div style={{marginTop: 64, padding: '20px 34px', borderRadius: 99, background: gold, fontSize: 27, fontWeight: 900}}>VERIFY DETAILS • VISIT • DECIDE</div>
    </AbsoluteFill>
  );
};

export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const mediaStart = 300;
  const factsStart = Math.max(mediaStart + 180, durationInFrames - 390);
  const ctaStart = durationInFrames - 180;
  const clips = props.actualVideos.length ? props.actualVideos : props.representativeVideos;
  const media = clips.length ? clips.map((src) => ({src, video: true})) : props.images.map((src) => ({src, video: false}));
  const mediaFrames = Math.max(90, Math.ceil((factsStart - mediaStart) / Math.max(1, media.length)));
  const disclosure = props.isActualProperty ? 'ACTUAL PROPERTY FOOTAGE' : 'REPRESENTATIVE VISUALS • VERIFY ACTUAL PROPERTY';

  return (
    <AbsoluteFill style={{backgroundColor: navy}}>
      {media[0] && <MediaFrame {...media[0]} label={disclosure} index={0} />}
      <Sequence from={0} durationInFrames={120}><Hook location={props.location} title={props.title} price={props.price} /></Sequence>
      <Sequence from={110} durationInFrames={210}><MapStage maps={props.maps} location={props.location} /></Sequence>
      {media.map((item, index) => (
        <Sequence key={`${item.src}-${index}`} from={mediaStart + index * mediaFrames} durationInFrames={mediaFrames + 8}>
          <MediaFrame {...item} label={disclosure} index={index} />
        </Sequence>
      ))}
      <Sequence from={factsStart} durationInFrames={ctaStart - factsStart + 8}><Facts facts={props.facts} location={props.location} /></Sequence>
      <Sequence from={ctaStart} durationInFrames={180}><CTA brand={props.brand} cta={props.cta} disclosure={props.disclosure} /></Sequence>
      {props.audio && <Audio src={staticFile(props.audio)} />}
      <div style={{position: 'absolute', top: 42, left: 48, right: 48, height: 7, borderRadius: 99, background: 'rgba(255,255,255,.2)', overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${(frame / durationInFrames) * 100}%`, background: gold}} />
      </div>
      <div style={{position: 'absolute', top: 72, left: 48, color: cream, fontFamily: typeface, fontSize: 21, fontWeight: 900, letterSpacing: 4}}>{props.brand}</div>
    </AbsoluteFill>
  );
};
