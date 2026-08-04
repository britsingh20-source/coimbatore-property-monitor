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
import type {Fact, PropertyVideoProps} from './types';

const navy = '#071A2E';
const cream = '#F6F0E5';
const gold = '#D6A53A';
const green = '#22A06B';
const typeface = 'Noto Sans Tamil, Noto Sans, Arial, sans-serif';

const clean = (value: string) => value && value.toUpperCase() !== 'NOT SPECIFIED' ? value : 'நேரில் சரிபார்க்கவும்';

const Atmosphere: React.FC<{light?: boolean}> = ({light = false}) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 32) * 34;
  return (
    <AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none'}}>
      <div style={{position: 'absolute', width: 720, height: 720, borderRadius: 999, left: -280 + drift, top: -260, background: light ? 'rgba(214,165,58,.14)' : 'rgba(41,126,179,.24)', filter: 'blur(55px)'}} />
      <div style={{position: 'absolute', width: 600, height: 600, borderRadius: 999, right: -260 - drift, bottom: -220, background: light ? 'rgba(34,160,107,.1)' : 'rgba(214,165,58,.2)', filter: 'blur(65px)'}} />
      <div style={{position: 'absolute', inset: 0, opacity: .12, backgroundImage: 'linear-gradient(rgba(255,255,255,.16) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.16) 1px, transparent 1px)', backgroundSize: '70px 70px', transform: `perspective(600px) rotateX(58deg) translateY(${700 + drift}px) scale(1.4)`}} />
    </AbsoluteFill>
  );
};

const LightSweep: React.FC<{duration: number}> = ({duration}) => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, duration], [-520, 1500], {extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', top: -300, bottom: -300, left: x, width: 190, transform: 'rotate(14deg)', background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.2), transparent)', filter: 'blur(12px)', pointerEvents: 'none'}} />;
};

const CornerBrackets: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    {[[38, 118], [982, 118], [38, 1660], [982, 1660]].map(([left, top], index) => (
      <div key={index} style={{position: 'absolute', left, top, width: 56, height: 56, borderLeft: index % 2 === 0 ? `3px solid ${gold}` : undefined, borderRight: index % 2 ? `3px solid ${gold}` : undefined, borderTop: index < 2 ? `3px solid ${gold}` : undefined, borderBottom: index >= 2 ? `3px solid ${gold}` : undefined}} />
    ))}
  </AbsoluteFill>
);

const ContactRail: React.FC<{brand: string; phone: string}> = ({brand, phone}) => {
  const frame = useCurrentFrame();
  const enter = spring({frame: frame - 12, fps: 30, config: {damping: 18}});
  return (
    <div style={{
      position: 'absolute', left: 42, right: 42, bottom: 34, height: 88,
      borderRadius: 26, background: 'rgba(7,26,46,.94)', border: '1px solid rgba(255,255,255,.2)',
      boxShadow: '0 16px 50px rgba(0,0,0,.35)', display: 'flex', alignItems: 'center',
      padding: '0 24px', color: cream, fontFamily: typeface,
      transform: `translateY(${interpolate(enter, [0, 1], [120, 0])}px)`, opacity: enter,
    }}>
      <div style={{width: 46, height: 46, borderRadius: 15, background: gold, color: navy, display: 'grid', placeItems: 'center', fontSize: 18, fontWeight: 950}}>CV</div>
      <div style={{marginLeft: 14, fontSize: 16, letterSpacing: 1.8, fontWeight: 900, maxWidth: 245, lineHeight: 1.05}}>{brand}</div>
      <div style={{marginLeft: 'auto', padding: '12px 16px', borderRadius: 18, background: green, fontSize: 21, fontWeight: 950}}>CALL / WHATSAPP</div>
      <div style={{fontSize: 30, marginLeft: 16, fontWeight: 950, letterSpacing: 1}}>{phone}</div>
    </div>
  );
};

const MediaFrame: React.FC<{
  src: string; video: boolean; label: string; index: number; total: number;
  price: string; location: string; facts: Fact[]; duration: number; nextImage?: string;
}> = ({src, video, label, index, total, price, location, facts, duration, nextImage}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, duration], index % 2 ? [1.02, 1.13] : [1.12, 1.02], {extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [0, 12, Math.max(14, duration - 18), duration], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const reveal = interpolate(frame, [0, 20], [100, 0], {extrapolateRight: 'clamp'});
  const tilt = Math.sin((frame + index * 22) / 35) * .7;
  const activeFact = facts.length ? facts[index % facts.length] : null;
  return (
    <AbsoluteFill style={{backgroundColor: navy, opacity, overflow: 'hidden', fontFamily: typeface, clipPath: `inset(0 ${reveal}% 0 0 round 34px)`}}>
      <div style={{position: 'absolute', inset: -25, transform: `perspective(1200px) rotateZ(${tilt}deg) scale(${scale})`}}>
        {video ? (
          <Loop durationInFrames={150}>
            <OffthreadVideo src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          </Loop>
        ) : (
          <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        )}
      </div>
      {!video && nextImage && (
        <div style={{position: 'absolute', right: 48, top: 190, width: 310, height: 390, borderRadius: 30, overflow: 'hidden', border: `5px solid ${cream}`, boxShadow: '0 22px 70px rgba(0,0,0,.5)', transform: `perspective(900px) rotateY(-8deg) rotateZ(2deg) translateY(${interpolate(frame, [0, 24], [-55, 0], {extrapolateRight: 'clamp'})}px)`}}>
          <Img src={staticFile(nextImage)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      )}
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(7,26,46,.18) 20%, rgba(7,26,46,.1) 48%, rgba(7,26,46,.96) 100%)'}} />
      <AbsoluteFill style={{opacity: .09, backgroundImage: 'repeating-linear-gradient(0deg, transparent 0px, transparent 5px, rgba(255,255,255,.45) 6px)'}} />
      <LightSweep duration={duration} />
      <CornerBrackets />
      <div style={{position: 'absolute', right: 52, top: 630, fontSize: 170, lineHeight: 1, color: 'transparent', WebkitTextStroke: '2px rgba(255,255,255,.22)', fontWeight: 950}}>{String(index + 1).padStart(2, '0')}</div>
      <div style={{position: 'absolute', left: 54, top: 135, display: 'flex', gap: 12, alignItems: 'center'}}>
        <div style={{padding: '11px 18px', borderRadius: 99, background: 'rgba(7,26,46,.82)', color: gold, fontSize: 19, letterSpacing: 2, fontWeight: 900}}>{label}</div>
        <div style={{padding: '11px 16px', borderRadius: 99, background: cream, color: navy, fontSize: 19, fontWeight: 900}}>{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</div>
      </div>
      <div style={{position: 'absolute', left: 54, right: 54, bottom: 170, color: cream}}>
        <div style={{fontSize: 25, color: gold, letterSpacing: 3, fontWeight: 900}}>📍 {location}</div>
        <div style={{display: 'flex', gap: 18, alignItems: 'stretch', marginTop: 20}}>
          <div style={{flex: 1, padding: '24px 26px', borderRadius: 25, background: 'rgba(7,26,46,.88)', border: '1px solid rgba(255,255,255,.18)'}}>
            <div style={{fontSize: 18, color: gold, letterSpacing: 3, fontWeight: 900}}>{activeFact?.label || 'PROPERTY'}</div>
            <div style={{fontSize: 34, fontWeight: 900, marginTop: 10}}>{clean(activeFact?.value || price)}</div>
          </div>
          <div style={{display: 'grid', placeItems: 'center', minWidth: 280, padding: '18px 25px', borderRadius: 25, background: gold, color: navy, fontSize: 31, lineHeight: 1.1, textAlign: 'center', fontWeight: 950}}>{price}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Hook: React.FC<Pick<PropertyVideoProps, 'location' | 'title' | 'price'>> = ({location, title, price}) => {
  const frame = useCurrentFrame();
  const rise = spring({frame, fps: 30, config: {damping: 18}});
  const wipe = interpolate(frame, [0, 34], [-1200, 1200], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 62px 230px', color: cream, fontFamily: typeface}}>
      <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
        <div style={{position: 'absolute', left: -55, top: 170, fontSize: 154, fontWeight: 950, lineHeight: .8, letterSpacing: -8, color: 'rgba(255,255,255,.09)'}}>COIMBATORE</div>
        <div style={{position: 'absolute', left: 210, top: 285, fontSize: 164, fontWeight: 950, lineHeight: .8, letterSpacing: -8, color: 'transparent', WebkitTextStroke: `3px rgba(214,165,58,.4)`}}>VEEDU</div>
        <div style={{position: 'absolute', left: wipe, top: -300, width: 340, height: 2500, transform: 'rotate(18deg)', background: 'linear-gradient(90deg, transparent, rgba(214,165,58,.42), transparent)', filter: 'blur(8px)'}} />
      </div>
      <CornerBrackets />
      <div style={{transform: `translateY(${interpolate(rise, [0, 1], [90, 0])}px)`, opacity: rise}}>
        <div style={{display: 'inline-flex', padding: '12px 22px', borderRadius: 99, background: gold, color: navy, fontWeight: 900, fontSize: 23, letterSpacing: 2}}>NEW LISTING • COIMBATOREVEEDU</div>
        <h1 style={{fontSize: 78, lineHeight: 1.02, margin: '30px 0 18px', maxWidth: 900}}>{title}</h1>
        <div style={{fontSize: 38, opacity: .92}}>📍 {location}</div>
        <div style={{display: 'inline-block', fontSize: 45, color: navy, background: gold, borderRadius: 20, padding: '14px 22px', fontWeight: 900, marginTop: 22}}>{price}</div>
      </div>
    </AbsoluteFill>
  );
};

const MapStage: React.FC<{maps: string[]; location: string}> = ({maps, location}) => {
  const frame = useCurrentFrame();
  const index = Math.min(maps.length - 1, Math.floor(frame / 62));
  const zoom = interpolate(frame % 62, [0, 62], [1, 1.08]);
  const pulse = 1 + Math.sin(frame / 5) * .12;
  const scan = interpolate(frame % 70, [0, 70], [190, 1190]);
  if (!maps.length) return null;
  return (
    <AbsoluteFill style={{backgroundColor: navy, fontFamily: typeface}}>
      <Img src={staticFile(maps[Math.max(0, index)])} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(7,26,46,.08), rgba(7,26,46,.83))'}} />
      <div style={{position: 'absolute', left: 0, right: 0, top: scan, height: 5, background: gold, boxShadow: '0 0 32px 12px rgba(214,165,58,.45)'}} />
      <div style={{position: 'absolute', left: 65, top: 150, color: cream, fontSize: 20, letterSpacing: 4, fontWeight: 900}}>LIVE LOCATION ZOOM</div>
      <div style={{position: 'absolute', right: 65, top: 145, padding: '10px 16px', borderRadius: 13, background: 'rgba(7,26,46,.82)', color: gold, fontSize: 20, fontWeight: 900}}>ZOOM 0{index + 1} / 03</div>
      <div style={{position: 'absolute', left: 490, top: 670, width: 100, height: 100, borderRadius: 99, border: `10px solid ${gold}`, boxShadow: '0 0 0 18px rgba(214,165,58,.26)', transform: `scale(${pulse})`}} />
      <div style={{position: 'absolute', left: 58, right: 58, bottom: 158, padding: 34, borderRadius: 34, background: 'rgba(7,26,46,.9)', border: '1px solid rgba(255,255,255,.2)', color: cream}}>
        <div style={{fontSize: 21, color: gold, letterSpacing: 4, fontWeight: 900}}>LOCATION INTELLIGENCE</div>
        <div style={{display: 'flex', gap: 12, marginTop: 20, alignItems: 'center', fontSize: 23, fontWeight: 900}}>
          {['TAMIL NADU', 'COIMBATORE', location.toUpperCase()].map((step, stepIndex) => <React.Fragment key={step}><div style={{padding: '12px 17px', borderRadius: 16, background: stepIndex === 2 ? gold : 'rgba(255,255,255,.12)', color: stepIndex === 2 ? navy : cream}}>{step}</div>{stepIndex < 2 && <div style={{color: gold}}>›</div>}</React.Fragment>)}
        </div>
        <div style={{fontSize: 45, fontWeight: 950, marginTop: 25}}>நகரத்துடன் இணைந்த குடியிருப்பு பகுதி</div>
        <div style={{fontSize: 18, marginTop: 20, opacity: .72}}>© OpenStreetMap contributors • Exact route and distance must be verified during the site visit</div>
      </div>
    </AbsoluteFill>
  );
};

const Facts: React.FC<Pick<PropertyVideoProps, 'facts' | 'location' | 'price'>> = ({facts, location, price}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 100% 0%, #154A70, ${navy} 55%)`, padding: '175px 55px 150px', color: cream, fontFamily: typeface}}>
      <Atmosphere />
      <div style={{position: 'absolute', right: -50, top: 110, fontSize: 240, fontWeight: 950, color: 'transparent', WebkitTextStroke: '2px rgba(255,255,255,.08)'}}>06</div>
      <div style={{fontSize: 23, color: gold, letterSpacing: 5, fontWeight: 900}}>PROPERTY SNAPSHOT</div>
      <div style={{display: 'flex', justifyContent: 'space-between', gap: 24, alignItems: 'end', marginTop: 12}}>
        <div style={{fontSize: 54, fontWeight: 950}}>{location}</div>
        <div style={{fontSize: 28, fontWeight: 950, color: navy, background: gold, borderRadius: 18, padding: '13px 17px', textAlign: 'right'}}>{price}</div>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 48}}>
        {facts.slice(0, 6).map((fact, index) => {
          const enter = spring({frame: frame - index * 7, fps: 30, config: {damping: 18}});
          return (
            <div key={`${fact.label}-${index}`} style={{minHeight: 178, padding: 24, borderRadius: 25, background: 'linear-gradient(135deg, rgba(246,240,229,.14), rgba(246,240,229,.045))', backdropFilter: 'blur(12px)', border: '1px solid rgba(246,240,229,.22)', boxShadow: 'inset 0 1px rgba(255,255,255,.12)', transform: `perspective(800px) rotateX(${interpolate(enter, [0, 1], [25, 0])}deg) translateY(${interpolate(enter, [0, 1], [70, 0])}px)`, opacity: enter}}>
              <div style={{width: 34, height: 5, borderRadius: 99, background: gold, marginBottom: 14}} />
              <div style={{fontSize: 17, color: gold, letterSpacing: 2.5, fontWeight: 900}}>{fact.label}</div>
              <div style={{fontSize: 30, lineHeight: 1.2, fontWeight: 900, marginTop: 14}}>{clean(fact.value)}</div>
            </div>
          );
        })}
      </div>
      <div style={{marginTop: 28, padding: '19px 24px', borderRadius: 22, background: 'rgba(34,160,107,.2)', border: '1px solid rgba(34,160,107,.55)', fontSize: 24, fontWeight: 800}}>✓ ஆவணங்கள் • அளவுகள் • சாலை • விலை — நேரில் சரிபார்த்த பிறகே முடிவு செய்யுங்கள்</div>
    </AbsoluteFill>
  );
};

const CTA: React.FC<Pick<PropertyVideoProps, 'brand' | 'cta' | 'disclosure' | 'phone'>> = ({brand, cta, disclosure, phone}) => {
  const frame = useCurrentFrame();
  const pop = spring({frame, fps: 30, config: {damping: 15}});
  const ring = interpolate(frame, [0, 165], [0, 210]);
  return (
    <AbsoluteFill style={{backgroundColor: cream, color: navy, justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '70px 70px 140px', fontFamily: typeface, overflow: 'hidden'}}>
      <Atmosphere light />
      {[0, 1, 2].map((item) => <div key={item} style={{position: 'absolute', left: 540 - (ring + item * 120) / 2, top: 500 - (ring + item * 120) / 2, width: ring + item * 120, height: ring + item * 120, borderRadius: 999, border: `2px solid rgba(214,165,58,${.35 - item * .08})`}} />)}
      <div style={{width: 138, height: 138, borderRadius: 32, background: navy, color: gold, display: 'grid', placeItems: 'center', fontSize: 48, fontWeight: 950, transform: `scale(${pop})`, boxShadow: '0 24px 70px rgba(7,26,46,.3)'}}>CV</div>
      <div style={{fontSize: 27, letterSpacing: 4, fontWeight: 950, marginTop: 30}}>{brand}</div>
      <div style={{fontSize: 58, fontWeight: 950, lineHeight: 1.08, marginTop: 42}}>{cta}</div>
      <div style={{fontSize: 66, letterSpacing: 2, fontWeight: 950, marginTop: 34, color: green}}>{phone}</div>
      <div style={{fontSize: 27, maxWidth: 820, lineHeight: 1.45, marginTop: 28, color: '#405166'}}>{disclosure}</div>
      <div style={{marginTop: 42, padding: '18px 32px', borderRadius: 99, background: gold, fontSize: 25, fontWeight: 950}}>CALL • WHATSAPP • BOOK SITE VISIT</div>
      <LightSweep duration={165} />
    </AbsoluteFill>
  );
};

export const PropertyReel: React.FC<PropertyVideoProps> = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const mapStart = 105;
  const mediaStart = 285;
  const ctaStart = durationInFrames - 165;
  const factsStart = ctaStart - 210;
  const clips = props.actualVideos.length ? props.actualVideos : props.representativeVideos;
  const media = clips.length ? clips.map((src) => ({src, video: true})) : props.images.map((src) => ({src, video: false}));
  const mediaFrames = Math.max(120, Math.ceil((factsStart - mediaStart) / Math.max(1, media.length)));
  const disclosure = props.isActualProperty ? 'ACTUAL PROPERTY • AUTHORIZED MEDIA' : 'REPRESENTATIVE VISUALS • VERIFY PROPERTY';

  return (
    <AbsoluteFill style={{backgroundColor: navy}}>
      {media[0] && <MediaFrame {...media[0]} label={disclosure} index={0} total={media.length} price={props.price} location={props.location} facts={props.facts} duration={durationInFrames} nextImage={props.images[1]} />}
      <Sequence from={0} durationInFrames={135}><Hook location={props.location} title={props.title} price={props.price} /></Sequence>
      <Sequence from={mapStart} durationInFrames={205}><MapStage maps={props.maps} location={props.location} /></Sequence>
      {media.map((item, index) => (
        <Sequence key={`${item.src}-${index}`} from={mediaStart + index * mediaFrames} durationInFrames={mediaFrames + 10}>
          <MediaFrame {...item} label={disclosure} index={index} total={media.length} price={props.price} location={props.location} facts={props.facts} duration={mediaFrames + 10} nextImage={!item.video && props.images.length > 1 ? props.images[(index + 1) % props.images.length] : undefined} />
        </Sequence>
      ))}
      <Sequence from={factsStart} durationInFrames={218}><Facts facts={props.facts} location={props.location} price={props.price} /></Sequence>
      <Sequence from={ctaStart} durationInFrames={165}><CTA brand={props.brand} cta={props.cta} disclosure={props.disclosure} phone={props.phone} /></Sequence>
      {props.audio && <Audio src={staticFile(props.audio)} />}
      <div style={{position: 'absolute', top: 38, left: 45, right: 45, height: 7, borderRadius: 99, background: 'rgba(255,255,255,.2)', overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${(frame / durationInFrames) * 100}%`, background: gold}} />
      </div>
      <div style={{position: 'absolute', top: 67, left: 46, color: cream, fontFamily: typeface, fontSize: 18, fontWeight: 950, letterSpacing: 2.4}}>{props.brand}</div>
      <ContactRail brand={props.brand} phone={props.phone} />
    </AbsoluteFill>
  );
};
