'use strict';
const fs=require('fs'),path=require('path');
const sharp=require('C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname;
// Rectangular extraction of image_gen sprites and layout transforms only.
// No painting, synthesized fill, background removal or color replacement is performed here.
const specs=[
['Hair_Back','hair_back',[110,85,925,1110],[350,12,366,418]],
['Neck','head',[274,845,560,479],[467,295,168,144]],
['Head_Skin_Nose','head_only',[60,90,985,1098],[426,56,251,280]],
['Arm_ViewerLeft','arm_L',[362,20,435,1390],[192,433,195,869]],
['Arm_ViewerRight','arm_R',[375,22,444,1390],[723,433,195,869]],
['Body_Clothes','body',[222,140,662,1282],[269,348,564,1074]],
['EyeWhite_ViewerLeft','eyes',[54,832,464,192],[474,205,54,18]],
['Iris_ViewerLeft','eyes',[193,1090,240,241],[489,202,25,25],true,'EyeWhite_ViewerLeft'],
['LidUpper_ViewerLeft','eyes',[35,365,461,185],[469,197,63,21]],
['LidLower_ViewerLeft','eyes',[119,665,349,94],[474,216,54,8]],
['Brow_ViewerLeft','eyes',[70,183,430,97],[473,177,61,9]],
['EyeWhite_ViewerRight','eyes',[596,832,449,192],[570,205,54,18]],
['Iris_ViewerRight','eyes',[669,1090,240,242],[585,202,25,25],true,'EyeWhite_ViewerRight'],
['LidUpper_ViewerRight','eyes',[614,365,459,185],[564,197,63,21]],
['LidLower_ViewerRight','eyes',[638,665,349,94],[570,216,54,8]],
['Brow_ViewerRight','eyes',[607,183,429,97],[568,177,61,9]],
['Mouth_Closed','mouth',[325,210,459,134],[524,283,56,12]],
['Mouth_Interior','mouth',[410,1125,284,116],[526,284,52,21],false],
['Mouth_LipUpper','mouth',[330,590,450,84],[524,282,56,10],false],
['Mouth_LipLower','mouth',[366,870,370,111],[525,300,54,12],false],
['Hair_Front_Sides_Pin','hair_front',[0,20,1106,1312],[346,10,373,426]],
['Ear_ViewerLeft','ears',[60,135,600,607],[428,195,35,45],false],
['Ear_ViewerRight','ears',[1120,135,600,607],[637,195,35,45]]
];
(async()=>{
const layers=[];
for(const [name,source,r,d,visible=true,clipTo] of specs){
 const [left,top,width,height]=r;
 const dest=path.join(root,'parts',name+'.png');
 await sharp(path.join(root,'generated',source+'.png')).extract({left,top,width,height}).resize(d[2],d[3],{fit:'fill',kernel:'lanczos3'}).png().toFile(dest);
 layers.push({name,path:'parts/'+name+'.png',left:d[0],top:d[1],visible,...(clipTo?{clipTo}:{}),source:'generated/'+source+'.png',sourceCrop:{left,top,width,height},layoutSize:{width:d[2],height:d[3]}});
}
const manifest={canvas:{width:1106,height:1422},layers,output:{psd:'Risa_Live2D_Parts_v1.psd',flattenedPng:'Risa_Live2D_Parts_v1.png',previewPng:'Risa_Live2D_Parts_v1_preview.png',verificationJson:'psd_verification.json',previewBackground:'#F7F5F0'}};
fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log('Prepared '+layers.length+' layers.');
})().catch(e=>{console.error(e);process.exitCode=1});
