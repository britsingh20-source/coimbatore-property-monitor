export type Fact = {label: string; value: string};

export type PropertyVideoProps = {
  videoId: string;
  location: string;
  title: string;
  price: string;
  facts: Fact[];
  maps: string[];
  actualVideos: string[];
  representativeVideos: string[];
  images: string[];
  audio: string | null;
  durationInFrames: number;
  isActualProperty: boolean;
  disclosure: string;
  brand: string;
  cta: string;
};
