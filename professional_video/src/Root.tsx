import React from 'react';
import {Composition} from 'remotion';
import {PropertyReel} from './PropertyReel';
import type {PropertyVideoProps} from './types';

const defaults: PropertyVideoProps = {
  videoId: 'preview', location: 'Coimbatore', title: 'Premium Property', price: 'Verified on request',
  facts: [], maps: [], actualVideos: [], representativeVideos: [], images: [], audio: null,
  voiceSegments: [], sceneOrder: ['location','land','builtUp','price','facing','road','approval','disclosure','verify','cta'],
  sceneDurations: {location:267,land:123,builtUp:137,price:150,facing:98,road:155,approval:127,disclosure:214,verify:179,cta:165},
  templateVariant: 'home', durationInFrames: 1615, isActualProperty: false,
  disclosure: 'Representative visuals; verify the actual property before purchase.',
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
