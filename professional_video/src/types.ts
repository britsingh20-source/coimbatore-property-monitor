export type Fact = {label: string; value: string};
export type VoiceSegment = {scene: string; src: string};

export type PropertyVideoProps = {
  videoId: string;
  location: string;
  locationLabel: string;
  title: string;
  price: string;
  facts: Fact[];
  maps: string[];
  actualVideos: string[];
  representativeVideos: string[];
  sceneMedia: Record<string, string[]>;
  images: string[];
  audio: string | null;
  voiceSegments: VoiceSegment[];
  sceneOrder: string[];
  sceneDurations: Record<string, number>;
  templateVariant: 'plot' | 'home';
  durationInFrames: number;
  isActualProperty: boolean;
  disclosure: string;
  brand: string;
  cta: string;
  phone: string;
};
