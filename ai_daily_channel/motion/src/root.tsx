import React from 'react';
import {
  AbsoluteFill,
  Composition,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

type Props = {
  toolName: string;
  hook: string;
  freeLabel: string;
  accent: string;
  language: 'ta' | 'hi' | 'en';
};

const TechPack: React.FC<Props> = ({toolName, hook, freeLabel, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 14}});
  const scan = interpolate(frame, [0, 180], [-200, 2100], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{
      background: 'radial-gradient(circle at 50% 25%, #172554 0%, #050816 48%, #02030a 100%)',
      color: 'white',
      fontFamily: 'Inter, Arial, sans-serif',
      overflow: 'hidden',
    }}>
      <div style={{position: 'absolute', inset: 0, opacity: 0.24,
        backgroundImage: 'linear-gradient(rgba(56,189,248,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(56,189,248,.22) 1px, transparent 1px)',
        backgroundSize: '64px 64px', transform: `perspective(700px) rotateX(58deg) translateY(${scan/7}px)`}} />
      <div style={{position: 'absolute', top: scan, left: 0, right: 0, height: 5,
        background: accent, boxShadow: `0 0 38px ${accent}`}} />
      <div style={{position: 'absolute', top: 180, left: 70, right: 70,
        transform: `scale(${0.75 + enter * 0.25})`, opacity: enter}}>
        <div style={{fontSize: 34, letterSpacing: 7, color: accent}}>FREE AI TOOL</div>
        <div style={{fontSize: 98, fontWeight: 900, lineHeight: 1.02, marginTop: 24}}>{hook}</div>
      </div>
      <div style={{position: 'absolute', top: 850, left: 70, right: 70, padding: 40,
        border: `2px solid ${accent}`, borderRadius: 36, background: 'rgba(5,8,22,.72)',
        boxShadow: `0 0 60px ${accent}33`}}>
        <div style={{fontSize: 62, fontWeight: 800}}>{toolName}</div>
        <div style={{display: 'inline-block', marginTop: 28, padding: '16px 26px',
          borderRadius: 999, background: accent, color: '#020617', fontSize: 34, fontWeight: 900}}>
          {freeLabel}
        </div>
      </div>
      <div style={{position: 'absolute', bottom: 110, left: 70, right: 70, fontSize: 27,
        color: '#94a3b8', letterSpacing: 3}}>VERIFIED FREE METHOD • SAVE THIS VIDEO</div>
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition
    id="TechPack"
    component={TechPack}
    durationInFrames={180}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{
      toolName: 'MuseTalk',
      hook: 'STOP PAYING FOR AI AVATARS',
      freeLabel: 'OPEN SOURCE',
      accent: '#22d3ee',
      language: 'en',
    }}
  />
);
