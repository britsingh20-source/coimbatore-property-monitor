import React from 'react';
import {Composition} from 'remotion';
import {PropertyReel} from './PropertyReel';
import type {PropertyVideoProps} from './types';

const defaults: PropertyVideoProps = {
  videoId: 'preview', location: 'Coimbatore', locationLabel: 'Coimbatore', title: 'Premium Property', price: 'Verified on request',
  facts: [], maps: [], actualVideos: [], representativeVideos: [], sceneMedia: {}, images: [], audio: null,
  voiceSegments: [], sceneOrder: ['location','land','builtUp','price','facing','road','approval','verify','cta'],
  sceneDurations: {location:267,land:123,builtUp:137,price:150,facing:98,road:155,approval:127,verify:150,cta:145},
  templateVariant: 'home', durationInFrames: 1615, isActualProperty: false,
  disclosure: '',
  brand: 'COIMBATOREVEEDU BUILDERS', cta: 'Schedule a verified site visit', phone: '9003787621',
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="PropertyReel"
    component={PropertyReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={1615}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})}
  />
);
