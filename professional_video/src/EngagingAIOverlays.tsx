import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const BuildingScanOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = spring({frame: frame - 5, fps: 30, config: {damping: 14}});
  const y = interpolate(frame, [0, 75], [380, 1370], clamp);
  return <AbsoluteFill style={{pointerEvents:'none',zIndex:21}}>
    <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%'}}>
      <path d="M220 1320 L220 520 L365 370 L760 370 L880 520 L880 1320 Z" fill="rgba(80,216,255,.03)" stroke="#50d8ff" strokeWidth="5" strokeDasharray="18 10" opacity={enter}/>
      <path d="M290 690 H810 M290 880 H810 M290 1070 H810" stroke="rgba(255,255,255,.45)" strokeWidth="3" strokeDasharray="14 12"/>
      <line x1="170" x2="920" y1={y} y2={y} stroke="#f3b928" strokeWidth="5"/>
    </svg>
    <div style={{position:'absolute',right:55,top:225,padding:'12px 16px',borderRadius:14,background:'rgba(2,11,20,.86)',border:'1px solid #50d8ff',color:'#f7f1e7',fontFamily:'Noto Sans Tamil, Noto Sans, Arial, sans-serif',fontSize:14,fontWeight:900,letterSpacing:2,opacity:enter}}>AI REPRESENTATIVE APARTMENT</div>
  </AbsoluteFill>;
};
