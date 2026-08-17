import React from 'react';
import {Composition} from 'remotion';
import type {PropertyVideoProps} from './types';
import {LayeredReelV2} from './LayeredReelV2';

const defaults: PropertyVideoProps = {
  videoId: 'preview', location: 'Coimbatore', locationLabel: 'Coimbatore', title: 'Premium Property', price: 'Verified on request',
  facts: [], maps: [], actualVideos: [], representativeVideos: [], sceneMedia: {}, images: [], audio: null,
  voiceSegments: [], sceneOrder: ['location','price','builtUp','facing','road','verify','cta'], sceneDurations: {},
  templateVariant: 'home', durationInFrames: 548, isActualProperty: false, disclosure: '',
  brand: 'COIMBATOREVEEDU BUILDERS', cta: 'Schedule a verified site visit', phone: ''
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="PropertyReel"
    component={LayeredReelV2}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={548}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, Number((props as PropertyVideoProps).durationInFrames || 548))})}
  />
);
