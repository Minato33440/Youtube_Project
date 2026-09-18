'use strict';
const fs=require('fs'),path=require('path');
const sharp=require('C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async()=>{
const m=JSON.parse(fs.readFileSync(path.join(__dirname,'manifest.json'),'utf8'));
const cols=5,cw=280,ch=300,rows=Math.ceil(m.layers.length/cols);
const tiles=[];
for(let i=0;i<m.layers.length;i++){
 const l=m.layers[i], x=(i%cols)*cw,y=Math.floor(i/cols)*ch;
 const b=await sharp(path.join(__dirname,l.source)).extract(l.sourceCrop).resize(250,250,{fit:'inside'}).png().toBuffer();
 const meta=await sharp(b).metadata();
 tiles.push({input:b,left:x+Math.floor((cw-meta.width)/2),top:y+Math.floor((260-meta.height)/2)});
 const svg='<svg width="280" height="40"><text x="140" y="20" text-anchor="middle" font-family="Arial" font-size="13" fill="#26343B">'+l.name+'</text><text x="140" y="36" text-anchor="middle" font-family="Arial" font-size="11" fill="#54616A">'+(l.visible?'default visible':'alternate / default hidden')+'</text></svg>';
 tiles.push({input:Buffer.from(svg),left:x,top:y+260});
}
await sharp({create:{width:cols*cw,height:rows*ch,channels:4,background:'#D7DDE0'}}).composite(tiles).png().toFile(path.join(__dirname,'parts_contact_sheet.png'));
})();
