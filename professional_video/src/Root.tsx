import React from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,staticFile} from 'remotion';
import type {PropertyVideoProps} from './types';
import {ImpactHookV2,PriceImpactV2,BuiltUpImpactV2,FacingImpactV2,RoadImpactV2,TrustImpactV2,ImpactCTAV2,ImpactTransitionV2} from './ImpactVFXV2';

type Source={src:string;video:boolean};

const PropertyReelV2:React.FC<PropertyVideoProps>=(props)=>{
  const media=(name:string):Source|undefined=>{
    const directed=props.directorMedia?.[name]?.[0];
    if(directed) return {src:directed.src,video:true};
    const src=props.sceneMedia?.[name]?.[0];
    return src?{src,video:true}:undefined;
  };
  const exterior=media('exterior')||media('location')||media('road')||media('interior');
  const interior=media('interior')||media('living')||media('kitchen')||media('bedroom')||exterior;
  const road=media('road')||exterior;
  const fact=(i:number,fallback:string)=>props.facts?.[i]?.value&&props.facts[i].value.toUpperCase()!=='NOT SPECIFIED'?props.facts[i].value:fallback;
  const scenes:Record<string,React.ReactNode>={
    location:<ImpactHookV2 source={exterior} title={props.title} location={props.location} price={props.price}/>,
    price:<PriceImpactV2 source={exterior} price={props.price}/>,
    builtUp:<BuiltUpImpactV2 source={interior} value={fact(1,'VERIFY ON SITE')}/>,
    facing:<FacingImpactV2 source={exterior} value={fact(2,'VERIFY ON SITE')}/>,
    road:<RoadImpactV2 source={road} value={fact(3,'VERIFY ON SITE')}/>,
    verify:<TrustImpactV2 location={props.location} price={props.price}/>,
    cta:<ImpactCTAV2 source={exterior} brand={props.brand} phone={props.phone} location={props.location}/>,
  };
  const order=props.sceneOrder?.length?props.sceneOrder:['location','price','builtUp','facing','road','verify','cta'];
  let cursor=0; const starts:Record<string,number>={};
  const timeline=order.map(scene=>{const from=cursor;const duration=Math.max(1,props.sceneDurations?.[scene]||100);starts[scene]=from;cursor+=duration;return{scene,from,duration}});
  return <AbsoluteFill style={{background:'#020b14'}}>
    {timeline.map(({scene,from,duration},index)=><Sequence key={scene} from={from} durationInFrames={duration}><AbsoluteFill>{scenes[scene]||<TrustImpactV2 location={props.location} price={props.price}/>}<ImpactTransitionV2 duration={duration} index={index}/></AbsoluteFill></Sequence>)}
    {props.voiceSegments?.map(seg=><Sequence key={seg.scene} from={starts[seg.scene]||0} durationInFrames={props.sceneDurations?.[seg.scene]||100}><Audio src={staticFile(seg.src)} volume={1}/></Sequence>)}
    {!props.voiceSegments?.length&&props.audio&&<Audio src={staticFile(props.audio)} volume={1}/>} 
  </AbsoluteFill>;
};

const defaults:PropertyVideoProps={videoId:'preview',location:'Coimbatore',locationLabel:'Coimbatore',title:'Premium Property',price:'Verified on request',facts:[],maps:[],actualVideos:[],representativeVideos:[],sceneMedia:{},images:[],audio:null,voiceSegments:[],sceneOrder:['location','price','builtUp','facing','road','verify','cta'],sceneDurations:{location:100,price:100,builtUp:110,facing:90,road:100,verify:110,cta:120},templateVariant:'home',durationInFrames:730,isActualProperty:false,disclosure:'',brand:'COIMBATOREVEEDU BUILDERS',cta:'Schedule a verified site visit',phone:''};

export const RemotionRoot:React.FC=()=> <Composition id="PropertyReel" component={PropertyReelV2} width={1080} height={1920} fps={30} durationInFrames={730} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:props.durationInFrames})}/>;
